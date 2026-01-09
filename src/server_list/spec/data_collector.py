#!/usr/bin/env python3
"""
Unified data collector for server-list.
Collects ESXi VM data and uptime, caches to SQLite.
Runs periodically every 5 minutes.
"""

import atexit
import logging
import ssl
import threading
from datetime import datetime

import requests
from pyVim.connect import Disconnect, SmartConnect
from pyVmomi import vim

import my_lib.config
import my_lib.webapp.event

from server_list.spec.db import (
    BASE_DIR,
    DATA_DIR,
    SERVER_DATA_DB,
    SQLITE_SCHEMA_PATH,
    get_connection,
    init_schema_from_file,
)

# Re-export for backward compatibility with tests
DB_PATH = SERVER_DATA_DB
__all__ = ["BASE_DIR", "DATA_DIR", "DB_PATH", "SQLITE_SCHEMA_PATH"]  # noqa: F401

UPDATE_INTERVAL_SEC = 300  # 5 minutes

_update_thread: threading.Thread | None = None
_should_stop = threading.Event()
_db_lock = threading.Lock()


def init_db():
    """Initialize the SQLite database using schema file."""
    init_schema_from_file(DB_PATH, SQLITE_SCHEMA_PATH)


def load_secret() -> dict:
    """Load secret.yaml containing ESXi credentials.

    Constructs path from BASE_DIR to allow test mocking.
    """
    secret_path = BASE_DIR / "secret.yaml"
    if not secret_path.exists():
        return {}

    schema_path = BASE_DIR / "schema" / "secret.schema"
    return my_lib.config.load(secret_path, schema_path)


def load_config() -> dict:
    """Load config.yaml containing machine definitions.

    Constructs path from BASE_DIR to allow test mocking.
    """
    config_path = BASE_DIR / "config.yaml"
    if not config_path.exists():
        return {}

    schema_path = BASE_DIR / "schema" / "config.schema"
    return my_lib.config.load(config_path, schema_path)


def connect_to_esxi(host: str, username: str, password: str, port: int = 443):
    """Connect to ESXi host."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    try:
        si = SmartConnect(
            host=host,
            user=username,
            pwd=password,
            port=port,
            sslContext=context
        )
        atexit.register(Disconnect, si)
        return si
    except Exception as e:
        logging.warning("Failed to connect to %s: %s", host, e)
        return None


def get_vm_storage_size(vm) -> float:
    """Calculate total storage size for a VM in GB."""
    total_bytes = 0

    try:
        for device in vm.config.hardware.device:
            if isinstance(device, vim.vm.device.VirtualDisk):
                if device.capacityInBytes is not None:
                    total_bytes += device.capacityInBytes
    except Exception:
        pass

    return total_bytes / (1024 ** 3)


def fetch_vm_data(si, esxi_host: str) -> list[dict]:
    """Fetch VM data from ESXi."""
    content = si.RetrieveContent()
    container = content.rootFolder
    view_type = [vim.VirtualMachine]
    recursive = True

    container_view = content.viewManager.CreateContainerView(
        container, view_type, recursive
    )

    vms = []
    for vm in container_view.view:
        try:
            vm_info = {
                "esxi_host": esxi_host,
                "vm_name": vm.name,
                "cpu_count": vm.config.hardware.numCPU if vm.config else None,
                "ram_mb": vm.config.hardware.memoryMB if vm.config else None,
                "storage_gb": get_vm_storage_size(vm) if vm.config else None,
                "power_state": str(vm.runtime.powerState) if vm.runtime else None,
            }
            vms.append(vm_info)
        except Exception as e:
            logging.warning("Error getting VM info for %s: %s", vm.name, e)

    container_view.Destroy()
    return vms


def fetch_host_info(si, host: str) -> dict | None:
    """Fetch host info including uptime, CPU, and ESXi version from ESXi host."""
    try:
        content = si.RetrieveContent()

        for datacenter in content.rootFolder.childEntity:
            if hasattr(datacenter, "hostFolder"):
                for cluster in datacenter.hostFolder.childEntity:
                    hosts = []
                    if hasattr(cluster, "host"):
                        hosts = cluster.host
                    elif hasattr(cluster, "childEntity"):
                        for child in cluster.childEntity:
                            if hasattr(child, "host"):
                                hosts.extend(child.host)

                    for host_system in hosts:
                        try:
                            boot_time = host_system.runtime.bootTime
                            cpu_threads = None
                            cpu_cores = None
                            esxi_version = None

                            # Get CPU info from hardware
                            if hasattr(host_system, "hardware") and host_system.hardware:
                                hw = host_system.hardware
                                if hasattr(hw, "cpuInfo") and hw.cpuInfo:
                                    cpu_threads = hw.cpuInfo.numCpuThreads
                                    cpu_cores = hw.cpuInfo.numCpuCores

                            # Get ESXi version from config.product
                            if hasattr(host_system, "config") and host_system.config:
                                cfg = host_system.config
                                if hasattr(cfg, "product") and cfg.product:
                                    # fullName contains "VMware ESXi 8.0.0 build-xxx"
                                    esxi_version = cfg.product.fullName

                            if boot_time:
                                return {
                                    "host": host,
                                    "boot_time": boot_time.isoformat(),
                                    "uptime_seconds": (datetime.now(boot_time.tzinfo) - boot_time).total_seconds(),
                                    "status": "running",
                                    "cpu_threads": cpu_threads,
                                    "cpu_cores": cpu_cores,
                                    "esxi_version": esxi_version,
                                }
                        except Exception as e:
                            logging.warning("Error getting host info: %s", e)

    except Exception as e:
        logging.warning("Failed to get host info for %s: %s", host, e)

    return None


# =============================================================================
# iLO Power Meter functions (via Redfish API)
# =============================================================================


def fetch_ilo_power(host: str, username: str, password: str) -> dict | None:
    """Fetch power consumption data from HP iLO via Redfish API.

    Args:
        host: iLO hostname or IP address
        username: iLO username
        password: iLO password

    Returns:
        Power data dictionary or None if failed
    """
    # iLO uses self-signed certificates, disable verification
    url = f"https://{host}/redfish/v1/Chassis/1/Power"

    try:
        response = requests.get(
            url,
            auth=(username, password),
            verify=False,  # noqa: S501 - iLO uses self-signed certs
            timeout=30
        )

        if response.status_code != 200:
            logging.warning("iLO API returned status %d for %s", response.status_code, host)
            return None

        data = response.json()

        # Extract power data from PowerControl array
        power_control = data.get("PowerControl", [])
        if not power_control:
            logging.warning("No PowerControl data in iLO response for %s", host)
            return None

        # Get first PowerControl entry (main chassis power)
        power_entry = power_control[0]
        power_watts = power_entry.get("PowerConsumedWatts")

        # Get power metrics (average, min, max)
        power_metrics = power_entry.get("PowerMetrics", {})
        power_average = power_metrics.get("AverageConsumedWatts")
        power_max = power_metrics.get("MaxConsumedWatts")
        power_min = power_metrics.get("MinConsumedWatts")

        return {
            "power_watts": power_watts,
            "power_average_watts": power_average,
            "power_max_watts": power_max,
            "power_min_watts": power_min,
        }

    except requests.exceptions.Timeout:
        logging.warning("Timeout connecting to iLO at %s", host)
        return None
    except requests.exceptions.ConnectionError as e:
        logging.warning("Connection error to iLO at %s: %s", host, e)
        return None
    except Exception as e:
        logging.warning("Error fetching power data from iLO at %s: %s", host, e)
        return None


def save_power_info(host: str, power_data: dict):
    """Save power consumption info to SQLite cache."""
    collected_at = datetime.now().isoformat()

    with _db_lock, get_connection(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO power_info
            (host, power_watts, power_average_watts, power_max_watts, power_min_watts, collected_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            host,
            power_data.get("power_watts"),
            power_data.get("power_average_watts"),
            power_data.get("power_max_watts"),
            power_data.get("power_min_watts"),
            collected_at
        ))

        conn.commit()


def get_power_info(host: str) -> dict | None:
    """Get power consumption info from cache."""
    with _db_lock, get_connection(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT host, power_watts, power_average_watts, power_max_watts, power_min_watts, collected_at
            FROM power_info
            WHERE host = ?
        """, (host,))

        row = cursor.fetchone()

        if row:
            return {
                "host": row[0],
                "power_watts": row[1],
                "power_average_watts": row[2],
                "power_max_watts": row[3],
                "power_min_watts": row[4],
                "collected_at": row[5],
            }

    return None


def get_all_power_info() -> dict[str, dict]:
    """Get all power consumption info from cache."""
    with _db_lock, get_connection(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT host, power_watts, power_average_watts, power_max_watts, power_min_watts, collected_at
            FROM power_info
        """)

        rows = cursor.fetchall()

        return {
            row[0]: {
                "power_watts": row[1],
                "power_average_watts": row[2],
                "power_max_watts": row[3],
                "power_min_watts": row[4],
                "collected_at": row[5],
            }
            for row in rows
        }


def collect_ilo_power_data():
    """Collect power data from configured iLO hosts."""
    secret = load_secret()
    ilo_auth = secret.get("ilo_auth", {})

    if not ilo_auth:
        return

    for host, credentials in ilo_auth.items():
        ilo_host = credentials.get("host", host)
        logging.info("Collecting power data from iLO %s...", ilo_host)

        power_data = fetch_ilo_power(
            host=ilo_host,
            username=credentials["username"],
            password=credentials["password"]
        )

        if power_data:
            save_power_info(host, power_data)
            logging.info("  Cached power data for %s: %s W", host, power_data.get("power_watts"))


# =============================================================================
# Database save/get functions
# =============================================================================


def save_vm_data(esxi_host: str, vms: list[dict]):
    """Save VM data to SQLite cache.

    Deletes all existing VMs for the host first, then inserts new data.
    This ensures deleted VMs are removed from the cache.
    """
    collected_at = datetime.now().isoformat()

    with _db_lock, get_connection(DB_PATH) as conn:
        cursor = conn.cursor()

        # Delete all existing VMs for this host first
        cursor.execute("DELETE FROM vm_info WHERE esxi_host = ?", (esxi_host,))

        # Insert new VM data
        for vm in vms:
            cursor.execute("""
                INSERT INTO vm_info
                (esxi_host, vm_name, cpu_count, ram_mb, storage_gb, power_state, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                vm["esxi_host"],
                vm["vm_name"],
                vm["cpu_count"],
                vm["ram_mb"],
                vm["storage_gb"],
                vm["power_state"],
                collected_at
            ))

        conn.commit()


def save_host_info(host_info: dict):
    """Save host info (uptime + CPU + ESXi version) to SQLite cache."""
    collected_at = datetime.now().isoformat()

    with _db_lock, get_connection(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO uptime_info
            (host, boot_time, uptime_seconds, status, cpu_threads, cpu_cores, esxi_version, collected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            host_info["host"],
            host_info.get("boot_time"),
            host_info.get("uptime_seconds"),
            host_info["status"],
            host_info.get("cpu_threads"),
            host_info.get("cpu_cores"),
            host_info.get("esxi_version"),
            collected_at
        ))

        conn.commit()


def save_host_info_failed(host: str):
    """Save failed host info status to SQLite cache.

    When ESXi is unreachable, set status to 'unknown' to indicate
    we cannot determine the actual state.
    """
    collected_at = datetime.now().isoformat()

    with _db_lock, get_connection(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO uptime_info
            (host, boot_time, uptime_seconds, status, cpu_threads, cpu_cores, esxi_version, collected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (host, None, None, "unknown", None, None, None, collected_at))

        conn.commit()


def update_fetch_status(esxi_host: str, status: str):
    """Update the fetch status for a host."""
    with _db_lock, get_connection(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO fetch_status (esxi_host, last_fetch, status)
            VALUES (?, ?, ?)
        """, (esxi_host, datetime.now().isoformat(), status))

        conn.commit()


def get_fetch_status(esxi_host: str) -> dict | None:
    """Get the fetch status for a host."""
    with _db_lock, get_connection(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT esxi_host, last_fetch, status
            FROM fetch_status
            WHERE esxi_host = ?
        """, (esxi_host,))

        row = cursor.fetchone()

        if row:
            return {
                "esxi_host": row[0],
                "last_fetch": row[1],
                "status": row[2],
            }

    return None


def is_host_reachable(esxi_host: str) -> bool:
    """Check if a host was successfully reached in the last fetch."""
    status = get_fetch_status(esxi_host)
    return status is not None and status.get("status") == "success"


def get_vm_info(vm_name: str, esxi_host: str | None = None) -> dict | None:
    """Get VM info from cache."""
    with _db_lock, get_connection(DB_PATH) as conn:
        cursor = conn.cursor()

        if esxi_host:
            cursor.execute("""
                SELECT vm_name, cpu_count, ram_mb, storage_gb, power_state, esxi_host, collected_at
                FROM vm_info
                WHERE vm_name = ? AND esxi_host = ?
            """, (vm_name, esxi_host))
        else:
            cursor.execute("""
                SELECT vm_name, cpu_count, ram_mb, storage_gb, power_state, esxi_host, collected_at
                FROM vm_info
                WHERE vm_name = ?
            """, (vm_name,))

        row = cursor.fetchone()

        if row:
            return {
                "vm_name": row[0],
                "cpu_count": row[1],
                "ram_mb": row[2],
                "storage_gb": round(row[3], 1) if row[3] else None,
                "power_state": row[4],
                "esxi_host": row[5],
                "collected_at": row[6],
            }

    return None


def get_all_vm_info_for_host(esxi_host: str) -> list[dict]:
    """Get all VM info for a specific ESXi host from cache."""
    with _db_lock, get_connection(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT vm_name, cpu_count, ram_mb, storage_gb, power_state, collected_at
            FROM vm_info
            WHERE esxi_host = ?
        """, (esxi_host,))

        rows = cursor.fetchall()

        return [
            {
                "vm_name": row[0],
                "cpu_count": row[1],
                "ram_mb": row[2],
                "storage_gb": round(row[3], 1) if row[3] else None,
                "power_state": row[4],
                "collected_at": row[5],
            }
            for row in rows
        ]


def get_uptime_info(host: str) -> dict | None:
    """Get uptime info from cache."""
    with _db_lock, get_connection(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT host, boot_time, uptime_seconds, status, cpu_threads, cpu_cores, esxi_version, collected_at
            FROM uptime_info
            WHERE host = ?
        """, (host,))

        row = cursor.fetchone()

        if row:
            return {
                "host": row[0],
                "boot_time": row[1],
                "uptime_seconds": row[2],
                "status": row[3],
                "cpu_threads": row[4],
                "cpu_cores": row[5],
                "esxi_version": row[6],
                "collected_at": row[7],
            }

    return None


def get_all_uptime_info() -> dict[str, dict]:
    """Get all uptime info from cache."""
    with _db_lock, get_connection(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT host, boot_time, uptime_seconds, status, cpu_threads, cpu_cores, esxi_version, collected_at
            FROM uptime_info
        """)

        rows = cursor.fetchall()

        return {
            row[0]: {
                "boot_time": row[1],
                "uptime_seconds": row[2],
                "status": row[3],
                "cpu_threads": row[4],
                "cpu_cores": row[5],
                "esxi_version": row[6],
                "collected_at": row[7],
            }
            for row in rows
        }


def collect_all_data():
    """Collect all data from configured ESXi and iLO hosts."""
    secret = load_secret()
    esxi_auth = secret.get("esxi_auth", {})

    updated = False

    # Collect ESXi data
    if esxi_auth:
        for host, credentials in esxi_auth.items():
            logging.info("Collecting data from %s...", host)

            si = connect_to_esxi(
                host=credentials.get("host", host),
                username=credentials["username"],
                password=credentials["password"],
                port=credentials.get("port", 443)
            )

            if not si:
                update_fetch_status(host, "connection_failed")
                save_host_info_failed(host)
                continue

            try:
                # Collect VM data
                vms = fetch_vm_data(si, host)
                save_vm_data(host, vms)
                logging.info("  Cached %d VMs from %s", len(vms), host)

                # Collect host info (uptime + CPU)
                host_info = fetch_host_info(si, host)
                if host_info:
                    save_host_info(host_info)
                    logging.info("  Cached host info for %s (CPU threads: %s)", host, host_info.get("cpu_threads"))
                else:
                    save_host_info_failed(host)

                update_fetch_status(host, "success")
                updated = True

            except Exception as e:
                logging.warning("Error collecting data from %s: %s", host, e)
                update_fetch_status(host, f"error: {e}")
                save_host_info_failed(host)

            finally:
                Disconnect(si)

    # Collect iLO power data
    collect_ilo_power_data()

    if updated:
        my_lib.webapp.event.notify_event(my_lib.webapp.event.EVENT_TYPE.DATA)
        logging.info("Data collection complete, clients notified")


def collect_host_data(host: str) -> bool:
    """Collect data from a specific ESXi host.

    Args:
        host: The ESXi host name to collect data from

    Returns:
        True if data was successfully collected, False otherwise
    """
    secret = load_secret()
    esxi_auth = secret.get("esxi_auth", {})

    if host not in esxi_auth:
        logging.warning("No credentials found for host: %s", host)
        return False

    credentials = esxi_auth[host]
    logging.info("Collecting data from %s (manual refresh)...", host)

    si = connect_to_esxi(
        host=credentials.get("host", host),
        username=credentials["username"],
        password=credentials["password"],
        port=credentials.get("port", 443)
    )

    if not si:
        update_fetch_status(host, "connection_failed")
        save_host_info_failed(host)
        my_lib.webapp.event.notify_event(my_lib.webapp.event.EVENT_TYPE.DATA)
        return False

    try:
        # Collect VM data
        vms = fetch_vm_data(si, host)
        save_vm_data(host, vms)
        logging.info("  Cached %d VMs from %s", len(vms), host)

        # Collect host info (uptime + CPU)
        host_info = fetch_host_info(si, host)
        if host_info:
            save_host_info(host_info)
            logging.info("  Cached host info for %s (CPU threads: %s)", host, host_info.get("cpu_threads"))
        else:
            save_host_info_failed(host)

        update_fetch_status(host, "success")
        my_lib.webapp.event.notify_event(my_lib.webapp.event.EVENT_TYPE.DATA)
        logging.info("Data collection complete for %s, clients notified", host)
        return True

    except Exception as e:
        logging.warning("Error collecting data from %s: %s", host, e)
        update_fetch_status(host, f"error: {e}")
        save_host_info_failed(host)
        my_lib.webapp.event.notify_event(my_lib.webapp.event.EVENT_TYPE.DATA)
        return False

    finally:
        Disconnect(si)


def _update_worker():
    """Background worker that collects data periodically."""
    logging.info("Data collector started (interval: %d sec)", UPDATE_INTERVAL_SEC)

    # Initial collection
    collect_all_data()

    while not _should_stop.wait(UPDATE_INTERVAL_SEC):
        collect_all_data()

    logging.info("Data collector stopped")


def start_collector():
    """Start the background data collector."""
    global _update_thread

    init_db()

    if _update_thread and _update_thread.is_alive():
        return

    _should_stop.clear()
    _update_thread = threading.Thread(target=_update_worker, daemon=True)
    _update_thread.start()


def stop_collector():
    """Stop the background data collector."""
    _should_stop.set()
    if _update_thread:
        _update_thread.join(timeout=5)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    init_db()

    if "--once" in sys.argv:
        collect_all_data()
    else:
        start_collector()
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            stop_collector()
