#!/usr/bin/env python3
"""
Unified data collector for server-list.
Collects ESXi VM data and uptime, caches to SQLite.
Runs periodically every 5 minutes.
"""

import atexit
import logging
import sqlite3
import ssl
import threading
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

import requests
from pyVim.connect import Disconnect, SmartConnect
from pyVmomi import vim

import my_lib.config
import my_lib.safe_access
import my_lib.webapp.event

import server_list.spec.db as db
import server_list.spec.db_config as db_config
import server_list.spec.models as models

UPDATE_INTERVAL_SEC = 300  # 5 minutes

_update_thread: threading.Thread | None = None
_should_stop = threading.Event()
_db_lock = threading.Lock()


@contextmanager
def _get_locked_connection() -> Generator[sqlite3.Connection, None, None]:
    """ロック付きDB接続を取得するコンテキストマネージャ."""
    with _db_lock, db.get_connection(db_config.get_server_data_db_path()) as conn:
        yield conn


def init_db():
    """Initialize the SQLite database using schema file."""
    db.init_schema_from_file(db_config.get_server_data_db_path(), db.SQLITE_SCHEMA_PATH)


def load_secret() -> dict:
    """Load secret.yaml containing ESXi credentials.

    Constructs path from db.BASE_DIR to allow test mocking.
    """
    secret_path = db.BASE_DIR / "secret.yaml"
    if not secret_path.exists():
        return {}

    return my_lib.config.load(secret_path, db.SECRET_SCHEMA_PATH)


def load_config() -> dict:
    """Load config.yaml containing machine definitions.

    Constructs path from db.BASE_DIR to allow test mocking.
    """
    config_path = db.BASE_DIR / "config.yaml"
    if not config_path.exists():
        return {}

    return my_lib.config.load(config_path, db.CONFIG_SCHEMA_PATH)


def connect_to_esxi(host: str, username: str, password: str, port: int = 443) -> Any | None:
    """Connect to ESXi host."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    try:
        si: Any = SmartConnect(
            host=host,
            user=username,
            pwd=password,
            port=port,
            sslContext=context
        )
        atexit.register(Disconnect, si)
        return si
    except Exception as e:  # pyVmomi can raise various unexpected exceptions
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
    except Exception as e:
        # pyVmomi attribute access can fail for various reasons
        logging.debug("Failed to get storage size for VM: %s", e)

    return total_bytes / (1024 ** 3)


def fetch_vm_data(si, esxi_host: str) -> list[models.VMInfo]:
    """Fetch VM data from ESXi."""
    content = si.RetrieveContent()
    container = content.rootFolder
    view_type = [vim.VirtualMachine]
    recursive = True

    container_view = content.viewManager.CreateContainerView(
        container, view_type, recursive
    )

    vms: list[models.VMInfo] = []
    for vm in container_view.view:
        try:
            # Get CPU and memory usage from quickStats
            cpu_usage_mhz = None
            memory_usage_mb = None
            if vm.summary and vm.summary.quickStats:
                stats = vm.summary.quickStats
                cpu_usage_mhz = stats.overallCpuUsage
                memory_usage_mb = stats.guestMemoryUsage

            vm_info = models.VMInfo(
                esxi_host=esxi_host,
                vm_name=vm.name,
                cpu_count=vm.config.hardware.numCPU if vm.config else None,
                ram_mb=vm.config.hardware.memoryMB if vm.config else None,
                storage_gb=get_vm_storage_size(vm) if vm.config else None,
                power_state=str(vm.runtime.powerState) if vm.runtime else None,
                cpu_usage_mhz=cpu_usage_mhz,
                memory_usage_mb=memory_usage_mb,
            )
            vms.append(vm_info)
        except Exception as e:  # pyVmomi attribute access can fail unexpectedly
            logging.warning("Error getting VM info for %s: %s", vm.name, e)

    container_view.Destroy()
    return vms


def _extract_cpu_info(host_system) -> tuple[int | None, int | None]:
    """ESXi ホストから CPU 情報を抽出.

    Args:
        host_system: pyVmomi HostSystem オブジェクト

    Returns:
        (cpu_threads, cpu_cores) のタプル
    """
    safe_host = my_lib.safe_access.safe(host_system)
    cpu_info = safe_host.hardware.cpuInfo
    return (cpu_info.numCpuThreads.value(), cpu_info.numCpuCores.value())


def _extract_memory_total(host_system) -> float | None:
    """ESXi ホストから合計メモリを抽出.

    Args:
        host_system: pyVmomi HostSystem オブジェクト

    Returns:
        メモリサイズ (bytes) または None
    """
    safe_host = my_lib.safe_access.safe(host_system)
    memory_size = safe_host.hardware.memorySize.value()
    return float(memory_size) if memory_size else None


def _extract_usage_from_quickstats(
    host_system, memory_total_bytes: float | None
) -> tuple[float | None, float | None, float | None]:
    """ESXi quickStats から CPU/メモリ使用率を抽出.

    Args:
        host_system: pyVmomi HostSystem オブジェクト
        memory_total_bytes: 合計メモリ (bytes)

    Returns:
        (cpu_usage_percent, memory_usage_percent, memory_used_bytes) のタプル
    """
    cpu_usage_percent = None
    memory_usage_percent = None
    memory_used_bytes = None

    safe_host = my_lib.safe_access.safe(host_system)
    stats = safe_host.summary.quickStats.value()
    if not stats:
        return cpu_usage_percent, memory_usage_percent, memory_used_bytes

    # CPU usage in MHz
    cpu_info = safe_host.hardware.cpuInfo
    cpu_hz = cpu_info.hz.value()
    num_cores = cpu_info.numCpuCores.value()
    if stats.overallCpuUsage is not None and cpu_hz and num_cores:
        total_cpu_mhz = (cpu_hz / 1_000_000) * num_cores
        cpu_usage_percent = (stats.overallCpuUsage / total_cpu_mhz) * 100

    # Memory usage in MB
    if stats.overallMemoryUsage is not None and memory_total_bytes:
        memory_used_bytes = float(stats.overallMemoryUsage * 1024 * 1024)
        memory_usage_percent = (memory_used_bytes / memory_total_bytes) * 100

    return cpu_usage_percent, memory_usage_percent, memory_used_bytes


def _extract_os_version(host_system) -> str | None:
    """ESXi ホストから OS バージョンを抽出.

    Args:
        host_system: pyVmomi HostSystem オブジェクト

    Returns:
        OS バージョン文字列 (例: "VMware ESXi 8.0.0 build-xxx")
    """
    safe_host = my_lib.safe_access.safe(host_system)
    return safe_host.config.product.fullName.value()


def fetch_host_info(si, host: str) -> models.HostInfo | None:
    """Fetch host info including uptime, CPU, memory usage, and ESXi version from ESXi host."""
    try:
        content = si.RetrieveContent()

        for datacenter in content.rootFolder.childEntity:
            if not hasattr(datacenter, "hostFolder"):
                continue

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
                        if not boot_time:
                            continue

                        # ヘルパー関数で各情報を抽出
                        cpu_threads, cpu_cores = _extract_cpu_info(host_system)
                        memory_total_bytes = _extract_memory_total(host_system)
                        cpu_usage, mem_usage, mem_used = _extract_usage_from_quickstats(
                            host_system, memory_total_bytes
                        )
                        os_version = _extract_os_version(host_system)

                        return models.HostInfo(
                            host=host,
                            boot_time=boot_time.isoformat(),
                            uptime_seconds=(datetime.now(boot_time.tzinfo) - boot_time).total_seconds(),
                            status="running",
                            cpu_threads=cpu_threads,
                            cpu_cores=cpu_cores,
                            os_version=os_version,
                            cpu_usage_percent=cpu_usage,
                            memory_usage_percent=mem_usage,
                            memory_total_bytes=memory_total_bytes,
                            memory_used_bytes=mem_used,
                        )
                    except Exception as e:  # pyVmomi attribute access can fail unexpectedly
                        logging.warning("Error getting host info: %s", e)

    except Exception as e:  # pyVmomi can raise various unexpected exceptions
        logging.warning("Failed to get host info for %s: %s", host, e)

    return None


# =============================================================================
# iLO Power Meter functions (via Redfish API)
# =============================================================================


def fetch_ilo_power(host: str, username: str, password: str) -> models.PowerInfo | None:
    """Fetch power consumption data from HP iLO via Redfish API.

    Args:
        host: iLO hostname or IP address
        username: iLO username
        password: iLO password

    Returns:
        PowerInfo or None if failed
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

        return models.PowerInfo(
            power_watts=power_watts,
            power_average_watts=power_average,
            power_max_watts=power_max,
            power_min_watts=power_min,
        )

    except requests.exceptions.Timeout:
        logging.warning("Timeout connecting to iLO at %s", host)
        return None
    except requests.exceptions.ConnectionError as e:
        logging.warning("Connection error to iLO at %s: %s", host, e)
        return None
    except (requests.RequestException, ValueError, KeyError) as e:
        # Handle JSON parsing errors and unexpected response format
        logging.warning("Error fetching power data from iLO at %s: %s", host, e)
        return None


def save_power_info(host: str, power_data: models.PowerInfo):
    """Save power consumption info to SQLite cache."""
    collected_at = datetime.now().isoformat()

    with _get_locked_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO power_info
            (host, power_watts, power_average_watts, power_max_watts, power_min_watts, collected_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            host,
            power_data.power_watts,
            power_data.power_average_watts,
            power_data.power_max_watts,
            power_data.power_min_watts,
            collected_at
        ))

        conn.commit()


def get_power_info(host: str) -> models.PowerInfo | None:
    """Get power consumption info from cache."""
    with _get_locked_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT power_watts, power_average_watts, power_max_watts, power_min_watts, collected_at
            FROM power_info
            WHERE host = ?
        """, (host,))

        row = cursor.fetchone()
        return models.PowerInfo.parse_row(row) if row else None


def get_all_power_info() -> dict[str, models.PowerInfo]:
    """Get all power consumption info from cache."""
    with _get_locked_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT host, power_watts, power_average_watts, power_max_watts, power_min_watts, collected_at
            FROM power_info
        """)

        return dict(models.PowerInfo.parse_row_with_host(row) for row in cursor.fetchall())


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
            logging.info("  Cached power data for %s: %s W", host, power_data.power_watts)


# =============================================================================
# Prometheus common helpers
# =============================================================================


def _prometheus_request(prometheus_url: str, query: str) -> list[dict]:
    """Prometheus API への HTTP リクエスト共通処理.

    Args:
        prometheus_url: Prometheus サーバー URL
        query: PromQL クエリ

    Returns:
        結果リスト（失敗時は空リスト）
    """
    try:
        response = requests.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": query},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "success":
            return []

        return data.get("data", {}).get("result", [])

    except requests.RequestException as e:
        logging.warning("Prometheus query failed: %s", e)
        return []


def _execute_prometheus_query(prometheus_url: str, query: str) -> dict | None:
    """Prometheus API 呼び出しで最初の結果を取得.

    Args:
        prometheus_url: Prometheus サーバー URL
        query: PromQL クエリ

    Returns:
        最初の結果エントリ (dict)、または None (失敗時)
    """
    results = _prometheus_request(prometheus_url, query)
    return results[0] if results else None


def _fetch_prometheus_metric(prometheus_url: str, query: str) -> float | None:
    """Prometheus から単一メトリクスを取得する共通関数.

    Args:
        prometheus_url: Prometheus サーバー URL
        query: PromQL クエリ

    Returns:
        メトリクス値 (float) または None (失敗時)
    """
    result = _execute_prometheus_query(prometheus_url, query)
    if result:
        try:
            value = result.get("value", [None, None])[1]
            return float(value) if value is not None else None
        except (ValueError, TypeError, IndexError) as e:
            logging.debug("Prometheus metric parsing failed: %s", e)
    return None


def _fetch_prometheus_metric_with_timestamp(prometheus_url: str, query: str) -> tuple[float, float] | None:
    """Prometheus からタイムスタンプ付きでメトリクスを取得.

    Args:
        prometheus_url: Prometheus サーバー URL
        query: PromQL クエリ

    Returns:
        (timestamp, value) のタプル、または None (失敗時)
    """
    result = _execute_prometheus_query(prometheus_url, query)
    if result:
        try:
            value_list = result.get("value", [])
            if len(value_list) >= 2:
                return float(value_list[0]), float(value_list[1])
        except (ValueError, TypeError, IndexError) as e:
            logging.debug("Prometheus metric with timestamp parsing failed: %s", e)
    return None


# =============================================================================
# Prometheus uptime functions (for Linux servers)
# =============================================================================


def fetch_prometheus_uptime(
    prometheus_url: str, instance: str, is_windows: bool = False
) -> models.UptimeData | None:
    """Fetch uptime data from Prometheus.

    Linux/Windows 共通の uptime 取得関数。
    Linux: node_boot_time_seconds メトリクス
    Windows: windows_system_system_up_time メトリクス

    Args:
        prometheus_url: Prometheus server URL (e.g., http://192.168.0.20:9090)
        instance: Prometheus instance label
        is_windows: True の場合 Windows メトリクスを使用

    Returns:
        UptimeData object or None if failed
    """
    if is_windows:
        metric = f'windows_system_system_up_time{{instance=~"{instance}.*"}}'
    else:
        metric = f'node_boot_time_seconds{{instance=~"{instance}.*"}}'

    result = _fetch_prometheus_metric_with_timestamp(prometheus_url, metric)
    if result is None:
        os_name = "Windows" if is_windows else "Linux"
        logging.warning("No Prometheus %s uptime data for instance %s", os_name, instance)
        return None

    current_time, boot_time = result
    uptime_seconds = current_time - boot_time

    return models.UptimeData(
        boot_time=datetime.fromtimestamp(boot_time).isoformat(),
        uptime_seconds=uptime_seconds,
        status="running",
    )


def fetch_prometheus_usage(
    prometheus_url: str, instance: str, is_windows: bool = False
) -> models.UsageMetrics | None:
    """Fetch CPU and memory usage from Prometheus.

    Linux/Windows 共通の CPU/メモリ使用率取得関数。

    Linux (node_exporter):
    - CPU: 100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
    - Memory: node_memory_MemTotal_bytes, node_memory_MemAvailable_bytes

    Windows (windows_exporter):
    - CPU: 100 - (avg by (instance) (rate(windows_cpu_time_total{mode="idle"}[5m])) * 100)
    - Memory: windows_cs_physical_memory_bytes, windows_os_physical_memory_free_bytes

    Args:
        prometheus_url: Prometheus server URL
        instance: Prometheus instance label
        is_windows: True の場合 Windows メトリクスを使用

    Returns:
        UsageMetrics object with cpu/memory usage, or None if no data available
    """
    cpu_usage_percent: float | None = None
    memory_usage_percent: float | None = None
    memory_total_bytes: float | None = None
    memory_used_bytes: float | None = None

    # OS 固有のメトリクス名を設定
    if is_windows:
        cpu_metric = "windows_cpu_time_total"
        mem_total_metric = "windows_cs_physical_memory_bytes"
        mem_avail_metric = "windows_os_physical_memory_free_bytes"
    else:
        cpu_metric = "node_cpu_seconds_total"
        mem_total_metric = "node_memory_MemTotal_bytes"
        mem_avail_metric = "node_memory_MemAvailable_bytes"

    # Get CPU usage (100 - idle percentage)
    cpu_query = f'100 - (avg by (instance) (rate({cpu_metric}{{instance=~"{instance}.*",mode="idle"}}[5m])) * 100)'
    cpu_usage_percent = _fetch_prometheus_metric(prometheus_url, cpu_query)

    # Get memory total
    mem_total_query = f'{mem_total_metric}{{instance=~"{instance}.*"}}'
    memory_total_bytes = _fetch_prometheus_metric(prometheus_url, mem_total_query)

    # Get memory available/free
    mem_avail_query = f'{mem_avail_metric}{{instance=~"{instance}.*"}}'
    mem_avail = _fetch_prometheus_metric(prometheus_url, mem_avail_query)
    if mem_avail is not None and memory_total_bytes is not None:
        memory_used_bytes = memory_total_bytes - mem_avail
        memory_usage_percent = (memory_used_bytes / memory_total_bytes) * 100

    # Return None if no data was collected
    if all(v is None for v in [cpu_usage_percent, memory_usage_percent, memory_total_bytes, memory_used_bytes]):
        return None

    return models.UsageMetrics(
        cpu_usage_percent=cpu_usage_percent,
        memory_usage_percent=memory_usage_percent,
        memory_total_bytes=memory_total_bytes,
        memory_used_bytes=memory_used_bytes,
    )


def get_prometheus_instance(host: str, instance_map: dict) -> str:
    """Get Prometheus instance name for a host.

    If the host is in instance_map, use that mapping.
    Otherwise, derive from FQDN (use first part before the dot).

    Args:
        host: Host name (e.g., "tanzania.green-rabbit.net")
        instance_map: Optional mapping of host -> instance

    Returns:
        Prometheus instance name (e.g., "tanzania")
    """
    if host in instance_map:
        return instance_map[host]

    # Derive from FQDN: use the first part before the dot
    if "." in host:
        return host.split(".")[0]

    return host


def collect_prometheus_uptime_data() -> bool:
    """Collect uptime and usage data from Prometheus for configured hosts.

    Automatically collects uptime and CPU/memory usage for machines without ESXi configuration.
    Uses node_boot_time_seconds for Linux and windows_system_system_up_time for Windows.
    Instance name is derived from FQDN (first part) unless explicitly
    configured in prometheus.instance_map.

    Returns:
        True if any data was collected, False otherwise
    """
    config = load_config()
    cfg = my_lib.config.accessor(config)

    prometheus_url = cfg.get("prometheus", "url")
    if not prometheus_url:
        return False

    instance_map = cfg.get_dict("prometheus", "instance_map")

    # Find machines without ESXi (servers that need Prometheus uptime)
    machines = cfg.get_list("machine")
    target_machines = [(m["name"], m.get("os", "")) for m in machines if not m.get("esxi")]

    if not target_machines:
        return False

    updated = False

    for host, os_type in target_machines:
        instance = get_prometheus_instance(host, instance_map)
        logging.info("Collecting uptime and usage from Prometheus for %s (instance: %s, os: %s)...", host, instance, os_type)

        # Use appropriate fetch function based on OS
        is_windows = os_type.lower() == "windows"
        uptime_data = fetch_prometheus_uptime(prometheus_url, instance, is_windows=is_windows)
        usage_data = fetch_prometheus_usage(prometheus_url, instance, is_windows=is_windows)

        if uptime_data:
            host_info = models.HostInfo(
                host=host,
                boot_time=uptime_data.boot_time,
                uptime_seconds=uptime_data.uptime_seconds,
                status=uptime_data.status,
                cpu_threads=None,
                cpu_cores=None,
                os_version=None,
                cpu_usage_percent=usage_data.cpu_usage_percent if usage_data else None,
                memory_usage_percent=usage_data.memory_usage_percent if usage_data else None,
                memory_total_bytes=usage_data.memory_total_bytes if usage_data else None,
                memory_used_bytes=usage_data.memory_used_bytes if usage_data else None,
            )
            save_host_info(host_info)
            logging.info("  Cached uptime for %s: %.1f days",
                        host, uptime_data.uptime_seconds / 86400)
            updated = True
        else:
            save_host_info_failed(host)

    return updated


# =============================================================================
# Prometheus ZFS pool functions (for Linux servers with ZFS)
# =============================================================================


def fetch_prometheus_zfs_pools(prometheus_url: str, instance: str) -> list[models.ZfsPoolInfo]:
    """Fetch ZFS pool data from Prometheus.

    Args:
        prometheus_url: Prometheus server URL
        instance: Prometheus instance label

    Returns:
        List of ZfsPoolInfo objects (empty list if no data)
    """
    metrics = ["zfs_pool_size_bytes", "zfs_pool_allocated_bytes", "zfs_pool_free_bytes", "zfs_pool_health"]
    pool_data: dict[str, dict[str, float | None]] = {}

    for metric in metrics:
        query = f'{metric}{{instance=~"{instance}.*"}}'
        results = _prometheus_request(prometheus_url, query)

        for result in results:
            pool_name = result.get("metric", {}).get("pool", "unknown")
            value = result.get("value", [None, None])[1]

            if pool_name not in pool_data:
                pool_data[pool_name] = {}

            # Convert metric name to field name
            field = metric.replace("zfs_pool_", "")
            if value is not None:
                try:
                    pool_data[pool_name][field] = float(value)
                except (ValueError, TypeError) as e:
                    logging.debug("ZFS metric value conversion failed: %s", e)

    if not pool_data:
        return []

    return [
        models.ZfsPoolInfo(
            pool_name=name,
            size_bytes=data.get("size_bytes"),
            allocated_bytes=data.get("allocated_bytes"),
            free_bytes=data.get("free_bytes"),
            health=data.get("health"),
        )
        for name, data in pool_data.items()
    ]


def save_zfs_pool_info(host: str, pools: list[models.ZfsPoolInfo]):
    """Save ZFS pool info to SQLite cache."""
    collected_at = datetime.now().isoformat()

    with _get_locked_connection() as conn:
        cursor = conn.cursor()

        # Delete existing pools for this host
        cursor.execute("DELETE FROM zfs_pool_info WHERE host = ?", (host,))

        # Insert new pool data
        for pool in pools:
            cursor.execute("""
                INSERT INTO zfs_pool_info
                (host, pool_name, size_bytes, allocated_bytes, free_bytes, health, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                host,
                pool.pool_name,
                pool.size_bytes,
                pool.allocated_bytes,
                pool.free_bytes,
                pool.health,
                collected_at
            ))

        conn.commit()


def get_zfs_pool_info(host: str) -> list[models.ZfsPoolInfo]:
    """Get ZFS pool info from cache."""
    with _get_locked_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT pool_name, size_bytes, allocated_bytes, free_bytes, health, collected_at
            FROM zfs_pool_info
            WHERE host = ?
        """, (host,))

        return [models.ZfsPoolInfo.parse_row(row) for row in cursor.fetchall()]


def collect_prometheus_zfs_data() -> bool:
    """Collect ZFS pool data from Prometheus for configured hosts.

    Automatically collects ZFS pool data for machines with filesystem: ['zfs'].
    Instance name is derived from FQDN (first part) unless explicitly
    configured in prometheus.instance_map.

    Returns:
        True if any data was collected, False otherwise
    """
    config = load_config()
    cfg = my_lib.config.accessor(config)

    prometheus_url = cfg.get("prometheus", "url")
    if not prometheus_url:
        return False

    instance_map = cfg.get_dict("prometheus", "instance_map")

    # Find machines with filesystem: ['zfs']
    machines = cfg.get_list("machine")
    target_hosts = [m["name"] for m in machines if "zfs" in m.get("filesystem", [])]

    if not target_hosts:
        return False

    updated = False

    for host in target_hosts:
        instance = get_prometheus_instance(host, instance_map)
        logging.info("Collecting ZFS pool data from Prometheus for %s (instance: %s)...", host, instance)

        pools = fetch_prometheus_zfs_pools(prometheus_url, instance)

        if pools:
            save_zfs_pool_info(host, pools)
            logging.info("  Cached %d ZFS pools for %s", len(pools), host)
            updated = True

    return updated


# =============================================================================
# Prometheus mount point functions (for Linux servers)
# =============================================================================


def fetch_btrfs_uuid(prometheus_url: str, label: str) -> str | None:
    """Get btrfs UUID from label via node_btrfs_info metric.

    Args:
        prometheus_url: Prometheus server URL
        label: Btrfs filesystem label

    Returns:
        UUID string or None if not found
    """
    query = f'node_btrfs_info{{label="{label}"}}'
    result = _execute_prometheus_query(prometheus_url, query)
    if result:
        uuid = result.get("metric", {}).get("uuid")
        return str(uuid) if uuid is not None else None
    return None


def fetch_btrfs_metrics(prometheus_url: str, uuid: str) -> models.StorageMetrics | None:
    """Fetch btrfs size and used bytes from Prometheus.

    Args:
        prometheus_url: Prometheus server URL
        uuid: Btrfs filesystem UUID

    Returns:
        StorageMetrics with size_bytes, avail_bytes, used_bytes or None if failed
    """
    # Get total size: sum of all device sizes
    size_query = f'sum(node_btrfs_device_size_bytes{{uuid="{uuid}"}})'
    size_bytes = _fetch_prometheus_metric(prometheus_url, size_query)

    # Get used bytes: sum of used across all block group types
    used_query = f'sum(node_btrfs_used_bytes{{uuid="{uuid}"}})'
    used_bytes = _fetch_prometheus_metric(prometheus_url, used_query)

    if size_bytes is not None and used_bytes is not None:
        return models.StorageMetrics(
            size_bytes=size_bytes,
            avail_bytes=size_bytes - used_bytes,
            used_bytes=used_bytes,
        )

    return None


def fetch_windows_disk_metrics(
    prometheus_url: str, volume: str, instance: str
) -> models.StorageMetrics | None:
    """Fetch Windows logical disk metrics from Prometheus.

    Uses windows_exporter metrics:
    - windows_logical_disk_size_bytes{volume="C:"}
    - windows_logical_disk_free_bytes{volume="C:"}

    Args:
        prometheus_url: Prometheus server URL
        volume: Windows volume label (e.g., "C:")
        instance: Prometheus instance name (derived from FQDN)

    Returns:
        StorageMetrics with size_bytes, avail_bytes, used_bytes or None if failed
    """
    # Get total size
    size_query = f'windows_logical_disk_size_bytes{{volume="{volume}",instance=~"{instance}.*"}}'
    size_bytes = _fetch_prometheus_metric(prometheus_url, size_query)

    # Get free bytes
    avail_query = f'windows_logical_disk_free_bytes{{volume="{volume}",instance=~"{instance}.*"}}'
    avail_bytes = _fetch_prometheus_metric(prometheus_url, avail_query)

    if size_bytes is not None and avail_bytes is not None:
        return models.StorageMetrics(
            size_bytes=size_bytes,
            avail_bytes=avail_bytes,
            used_bytes=size_bytes - avail_bytes,
        )

    return None


def _fetch_filesystem_mount_metrics(prometheus_url: str, label: str, path: str) -> models.StorageMetrics | None:
    """node_filesystem_* メトリクスからマウント情報を取得.

    Args:
        prometheus_url: Prometheus server URL
        label: Prometheus instance label
        path: マウントポイントのパス

    Returns:
        StorageMetrics with size_bytes, avail_bytes, used_bytes or None if failed
    """
    size_query = f'node_filesystem_size_bytes{{instance=~"{label}.*",mountpoint="{path}"}}'
    avail_query = f'node_filesystem_avail_bytes{{instance=~"{label}.*",mountpoint="{path}"}}'

    size_bytes = _fetch_prometheus_metric(prometheus_url, size_query)
    avail_bytes = _fetch_prometheus_metric(prometheus_url, avail_query)

    if size_bytes is not None and avail_bytes is not None:
        return models.StorageMetrics(
            size_bytes=size_bytes,
            avail_bytes=avail_bytes,
            used_bytes=size_bytes - avail_bytes,
        )

    return None


def _fetch_mount_for_config(
    prometheus_url: str, mount_config: dict, host: str, instance_map: dict
) -> models.MountInfo | None:
    """単一のマウント設定からマウント情報を取得.

    Args:
        prometheus_url: Prometheus server URL
        mount_config: マウント設定 (label, path, type)
        host: ホスト名 (FQDN)
        instance_map: ホスト -> Prometheus instance マッピング

    Returns:
        MountInfo、または None
    """
    label = mount_config.get("label", "")
    path = mount_config.get("path", label)
    mount_type = mount_config.get("type", "filesystem")

    if not label:
        return None

    storage_data: models.StorageMetrics | None = None

    if mount_type == "btrfs":
        uuid = fetch_btrfs_uuid(prometheus_url, label)
        if uuid:
            storage_data = fetch_btrfs_metrics(prometheus_url, uuid)
    elif mount_type == "windows":
        instance = get_prometheus_instance(host, instance_map)
        storage_data = fetch_windows_disk_metrics(prometheus_url, label, instance)
    else:
        storage_data = _fetch_filesystem_mount_metrics(prometheus_url, label, path)

    if storage_data:
        return models.MountInfo(
            mountpoint=path,
            size_bytes=storage_data.size_bytes,
            avail_bytes=storage_data.avail_bytes,
            used_bytes=storage_data.used_bytes,
        )

    return None


def fetch_prometheus_mount_info(
    prometheus_url: str, mount_configs: list[dict], host: str, instance_map: dict
) -> list[models.MountInfo]:
    """Fetch mount point data from Prometheus.

    Supports filesystem (node_filesystem_*), btrfs (node_btrfs_*),
    and windows (windows_logical_disk_*) metrics.

    Args:
        prometheus_url: Prometheus server URL
        mount_configs: List of mount configs with 'label', 'path', and optional 'type'
        host: Host name (FQDN) for deriving Prometheus instance
        instance_map: Optional mapping of host -> instance

    Returns:
        List of MountInfo (empty list if no data collected)
    """
    mount_data: list[models.MountInfo] = []

    for mount_config in mount_configs:
        result = _fetch_mount_for_config(prometheus_url, mount_config, host, instance_map)
        if result:
            mount_data.append(result)

    return mount_data


def save_mount_info(host: str, mounts: list[models.MountInfo]):
    """Save mount info to SQLite cache."""
    collected_at = datetime.now().isoformat()

    with _get_locked_connection() as conn:
        cursor = conn.cursor()

        # Delete existing mounts for this host
        cursor.execute("DELETE FROM mount_info WHERE host = ?", (host,))

        # Insert new mount data
        for mount in mounts:
            cursor.execute("""
                INSERT INTO mount_info
                (host, mountpoint, size_bytes, avail_bytes, used_bytes, collected_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                host,
                mount.mountpoint,
                mount.size_bytes,
                mount.avail_bytes,
                mount.used_bytes,
                collected_at,
            ))

        conn.commit()


def get_mount_info(host: str) -> list[models.MountInfo]:
    """Get mount info from cache."""
    with _get_locked_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT mountpoint, size_bytes, avail_bytes, used_bytes, collected_at
            FROM mount_info
            WHERE host = ?
        """, (host,))

        return [models.MountInfo.parse_row(row) for row in cursor.fetchall()]


def collect_prometheus_mount_data() -> bool:
    """Collect mount point data from Prometheus for configured hosts.

    Automatically collects mount data for machines with mount configuration.
    Each mount config specifies 'label' (Prometheus label to match) and
    optional 'path' (display path, defaults to label).
    The 'type' field determines the metrics source: filesystem, btrfs, or windows.
    If 'type' is not specified and machine os is 'Windows', defaults to 'windows'.

    Returns:
        True if any data was collected, False otherwise
    """
    config = load_config()
    cfg = my_lib.config.accessor(config)

    prometheus_url = cfg.get("prometheus", "url")
    if not prometheus_url:
        return False

    instance_map = cfg.get_dict("prometheus", "instance_map")

    # Find machines with mount configuration
    machines = cfg.get_list("machine")
    target_machines = [
        (m["name"], m["mount"], m.get("os", ""))
        for m in machines if m.get("mount")
    ]

    if not target_machines:
        return False

    updated = False

    for host, mount_configs, os_type in target_machines:
        logging.info("Collecting mount data from Prometheus for %s...", host)

        # Auto-detect type based on OS if not specified
        processed_configs = []
        for mc in mount_configs:
            config_copy = dict(mc)
            if "type" not in config_copy and os_type.lower() == "windows":
                config_copy["type"] = "windows"
            processed_configs.append(config_copy)

        mounts = fetch_prometheus_mount_info(prometheus_url, processed_configs, host, instance_map)

        if mounts:
            save_mount_info(host, mounts)
            logging.info("  Cached %d mount points for %s", len(mounts), host)
            updated = True

    return updated


# =============================================================================
# Database save/get functions
# =============================================================================


# -----------------------------------------------------------------------------
# Save functions
# -----------------------------------------------------------------------------


def save_vm_data(esxi_host: str, vms: list[models.VMInfo]):
    """Save VM data to SQLite cache.

    Deletes all existing VMs for the host first, then inserts new data.
    This ensures deleted VMs are removed from the cache.
    """
    collected_at = datetime.now().isoformat()

    with _get_locked_connection() as conn:
        cursor = conn.cursor()

        # Delete all existing VMs for this host first
        cursor.execute("DELETE FROM vm_info WHERE esxi_host = ?", (esxi_host,))

        # Insert new VM data
        for vm in vms:
            cursor.execute("""
                INSERT INTO vm_info
                (esxi_host, vm_name, cpu_count, ram_mb, storage_gb, power_state,
                 cpu_usage_mhz, memory_usage_mb, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                vm.esxi_host,
                vm.vm_name,
                vm.cpu_count,
                vm.ram_mb,
                vm.storage_gb,
                vm.power_state,
                vm.cpu_usage_mhz,
                vm.memory_usage_mb,
                collected_at
            ))

        conn.commit()


def save_host_info(host_info: models.HostInfo):
    """Save host info (uptime + CPU + ESXi version + usage) to SQLite cache."""
    collected_at = datetime.now().isoformat()

    with _get_locked_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO host_info
            (host, boot_time, uptime_seconds, status, cpu_threads, cpu_cores, os_version,
             cpu_usage_percent, memory_usage_percent, memory_total_bytes, memory_used_bytes, collected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            host_info.host,
            host_info.boot_time,
            host_info.uptime_seconds,
            host_info.status,
            host_info.cpu_threads,
            host_info.cpu_cores,
            host_info.os_version,
            host_info.cpu_usage_percent,
            host_info.memory_usage_percent,
            host_info.memory_total_bytes,
            host_info.memory_used_bytes,
            collected_at
        ))

        conn.commit()


def save_host_info_failed(host: str):
    """Save failed host info status to SQLite cache.

    When ESXi is unreachable, set status to 'unknown' to indicate
    we cannot determine the actual state.
    """
    collected_at = datetime.now().isoformat()

    with _get_locked_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO host_info
            (host, boot_time, uptime_seconds, status, cpu_threads, cpu_cores, os_version,
             cpu_usage_percent, memory_usage_percent, memory_total_bytes, memory_used_bytes, collected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (host, None, None, "unknown", None, None, None, None, None, None, None, collected_at))

        conn.commit()


def update_collection_status(host: str, status: str):
    """Update the collection status for a host."""
    with _get_locked_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO collection_status (host, last_fetch, status)
            VALUES (?, ?, ?)
        """, (host, datetime.now().isoformat(), status))

        conn.commit()


def get_collection_status(host: str) -> models.CollectionStatus | None:
    """Get the collection status for a host."""
    with _get_locked_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT host, last_fetch, status
            FROM collection_status
            WHERE host = ?
        """, (host,))

        row = cursor.fetchone()
        return models.CollectionStatus.parse_row(row) if row else None


def is_host_reachable(host: str) -> bool:
    """Check if a host was successfully reached in the last collection."""
    status = get_collection_status(host)
    return status is not None and status.status == "success"


def get_vm_info(vm_name: str, esxi_host: str | None = None) -> models.VMInfo | None:
    """Get VM info from cache."""
    with _get_locked_connection() as conn:
        cursor = conn.cursor()

        if esxi_host:
            cursor.execute("""
                SELECT vm_name, cpu_count, ram_mb, storage_gb, power_state, esxi_host,
                       cpu_usage_mhz, memory_usage_mb, collected_at
                FROM vm_info
                WHERE vm_name = ? AND esxi_host = ?
            """, (vm_name, esxi_host))
        else:
            cursor.execute("""
                SELECT vm_name, cpu_count, ram_mb, storage_gb, power_state, esxi_host,
                       cpu_usage_mhz, memory_usage_mb, collected_at
                FROM vm_info
                WHERE vm_name = ?
            """, (vm_name,))

        row = cursor.fetchone()
        return models.VMInfo.parse_row_full(row) if row else None


def get_all_vm_info_for_host(esxi_host: str) -> list[models.VMInfo]:
    """Get all VM info for a specific ESXi host from cache."""
    with _get_locked_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT vm_name, cpu_count, ram_mb, storage_gb, power_state,
                   cpu_usage_mhz, memory_usage_mb, collected_at
            FROM vm_info
            WHERE esxi_host = ?
        """, (esxi_host,))

        return [models.VMInfo.parse_row(row, esxi_host) for row in cursor.fetchall()]


def get_host_info(host: str) -> models.HostInfo | None:
    """Get uptime info from cache."""
    with _get_locked_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT host, boot_time, uptime_seconds, status, cpu_threads, cpu_cores, os_version,
                   cpu_usage_percent, memory_usage_percent, memory_total_bytes, memory_used_bytes, collected_at
            FROM host_info
            WHERE host = ?
        """, (host,))

        row = cursor.fetchone()
        return models.HostInfo.parse_row(row) if row else None


def get_all_host_info() -> dict[str, models.HostInfo]:
    """Get all uptime info from cache."""
    with _get_locked_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT host, boot_time, uptime_seconds, status, cpu_threads, cpu_cores, os_version,
                   cpu_usage_percent, memory_usage_percent, memory_total_bytes, memory_used_bytes, collected_at
            FROM host_info
        """)

        return {row[0]: models.HostInfo.parse_row(row) for row in cursor.fetchall()}


def _collect_esxi_host_data(si, host: str) -> bool:
    """単一 ESXi ホストからデータ収集の共通処理.

    Args:
        si: ESXi 接続インスタンス (SmartConnect の戻り値)
        host: ホスト名

    Returns:
        True: 成功, False: 失敗
    """
    try:
        # Collect VM data
        vms = fetch_vm_data(si, host)
        save_vm_data(host, vms)
        logging.info("  Cached %d VMs from %s", len(vms), host)

        # Collect host info (uptime + CPU)
        host_info = fetch_host_info(si, host)
        if host_info:
            save_host_info(host_info)
            logging.info("  Cached host info for %s (CPU threads: %s)", host, host_info.cpu_threads)
        else:
            save_host_info_failed(host)

        update_collection_status(host, "success")
        return True

    except Exception as e:  # ESXi/pyVmomi operations can raise various exceptions
        logging.warning("Error collecting data from %s: %s", host, e)
        update_collection_status(host, f"error: {e}")
        save_host_info_failed(host)
        return False

    finally:
        Disconnect(si)


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
                port=credentials.get("port", 443),
            )

            if not si:
                update_collection_status(host, "connection_failed")
                save_host_info_failed(host)
                continue

            if _collect_esxi_host_data(si, host):
                updated = True

    # Collect iLO power data
    collect_ilo_power_data()

    # Collect Prometheus uptime data (for Linux servers)
    if collect_prometheus_uptime_data():
        updated = True

    # Collect Prometheus ZFS pool data (for Linux servers with ZFS)
    if collect_prometheus_zfs_data():
        updated = True

    # Collect Prometheus mount point data
    if collect_prometheus_mount_data():
        updated = True

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
        port=credentials.get("port", 443),
    )

    if not si:
        update_collection_status(host, "connection_failed")
        save_host_info_failed(host)
        my_lib.webapp.event.notify_event(my_lib.webapp.event.EVENT_TYPE.DATA)
        return False

    success = _collect_esxi_host_data(si, host)
    my_lib.webapp.event.notify_event(my_lib.webapp.event.EVENT_TYPE.DATA)
    logging.info("Data collection complete for %s, clients notified", host)
    return success


def _update_worker():
    """Background worker that collects data periodically."""
    logging.info("Data collector started (interval: %d sec)", UPDATE_INTERVAL_SEC)

    # Initial collection
    try:
        collect_all_data()
    except Exception:
        logging.exception("Error in initial data collection")

    while not _should_stop.wait(UPDATE_INTERVAL_SEC):
        try:
            collect_all_data()
        except Exception:
            logging.exception("Error in periodic data collection")

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
