#!/usr/bin/env python3
"""
NUT (Network UPS Tools) data collector.

Communicates with NUT server via TCP socket to collect UPS information.
"""

import logging
import socket

import server_list.spec.models as models

DEFAULT_PORT = 3493
SOCKET_TIMEOUT = 10


def _send_command(sock: socket.socket, command: str) -> list[str]:
    """Send a command to NUT server and receive response.

    Args:
        sock: Connected socket
        command: NUT command to send

    Returns:
        List of response lines
    """
    sock.sendall(f"{command}\n".encode("utf-8"))

    response = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        response += chunk
        # Check for end of response
        decoded = response.decode("utf-8")
        if "END LIST" in decoded or decoded.startswith("ERR "):
            break

    return response.decode("utf-8").strip().split("\n")


def _parse_list_ups(lines: list[str]) -> list[tuple[str, str]]:
    """Parse LIST UPS response.

    Args:
        lines: Response lines from LIST UPS command

    Returns:
        List of (ups_name, description) tuples
    """
    ups_list = []
    for line in lines:
        if line.startswith("UPS "):
            # Format: UPS <upsname> "<description>"
            parts = line.split(" ", 2)
            if len(parts) >= 2:
                ups_name = parts[1]
                description = parts[2].strip('"') if len(parts) > 2 else ""
                ups_list.append((ups_name, description))
    return ups_list


def _parse_list_var(lines: list[str]) -> dict[str, str]:
    """Parse LIST VAR response.

    Args:
        lines: Response lines from LIST VAR command

    Returns:
        Dict mapping variable name to value
    """
    variables = {}
    for line in lines:
        if line.startswith("VAR "):
            # Format: VAR <upsname> <varname> "<value>"
            parts = line.split(" ", 3)
            if len(parts) >= 4:
                var_name = parts[2]
                value = parts[3].strip('"')
                variables[var_name] = value
    return variables


def _parse_list_client(lines: list[str]) -> list[str]:
    """Parse LIST CLIENT response.

    Args:
        lines: Response lines from LIST CLIENT command

    Returns:
        List of client IP addresses
    """
    clients = []
    for line in lines:
        if line.startswith("CLIENT "):
            # Format: CLIENT <upsname> <client_ip>
            parts = line.split(" ")
            if len(parts) >= 3:
                clients.append(parts[2])
    return clients


def _safe_float(value: str | None) -> float | None:
    """Convert string to float safely."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _safe_int(value: str | None) -> int | None:
    """Convert string to int safely."""
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def connect_to_nut(host: str, port: int = DEFAULT_PORT) -> socket.socket | None:
    """Connect to NUT server.

    Args:
        host: NUT server hostname
        port: NUT server port (default: 3493)

    Returns:
        Connected socket or None if connection failed
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(SOCKET_TIMEOUT)
        sock.connect((host, port))
        return sock
    except (OSError, socket.error) as e:
        logging.warning("Failed to connect to NUT server %s:%d: %s", host, port, e)
        return None


def list_ups(sock: socket.socket) -> list[tuple[str, str]]:
    """List all UPS devices on the NUT server.

    Args:
        sock: Connected socket

    Returns:
        List of (ups_name, description) tuples
    """
    try:
        lines = _send_command(sock, "LIST UPS")
        return _parse_list_ups(lines)
    except (OSError, socket.error) as e:
        logging.warning("Failed to list UPS: %s", e)
        return []


def get_ups_variables(sock: socket.socket, ups_name: str) -> dict[str, str]:
    """Get all variables for a UPS.

    Args:
        sock: Connected socket
        ups_name: UPS name

    Returns:
        Dict mapping variable name to value
    """
    try:
        lines = _send_command(sock, f"LIST VAR {ups_name}")
        return _parse_list_var(lines)
    except (OSError, socket.error) as e:
        logging.warning("Failed to get UPS variables for %s: %s", ups_name, e)
        return {}


def get_ups_clients(sock: socket.socket, ups_name: str) -> list[str]:
    """Get all clients connected to a UPS.

    Args:
        sock: Connected socket
        ups_name: UPS name

    Returns:
        List of client IP addresses
    """
    try:
        lines = _send_command(sock, f"LIST CLIENT {ups_name}")
        return _parse_list_client(lines)
    except (OSError, socket.error) as e:
        logging.warning("Failed to get UPS clients for %s: %s", ups_name, e)
        return []


def fetch_ups_info(host: str, ups_name: str, port: int = DEFAULT_PORT) -> models.UPSInfo | None:
    """Fetch UPS information from NUT server.

    Args:
        host: NUT server hostname
        ups_name: UPS name
        port: NUT server port

    Returns:
        UPSInfo or None if failed
    """
    sock = connect_to_nut(host, port)
    if not sock:
        return None

    try:
        variables = get_ups_variables(sock, ups_name)
        if not variables:
            return None

        return models.UPSInfo(
            ups_name=ups_name,
            host=host,
            model=variables.get("ups.model"),
            battery_charge=_safe_float(variables.get("battery.charge")),
            battery_runtime=_safe_int(variables.get("battery.runtime")),
            ups_load=_safe_float(variables.get("ups.load")),
            ups_status=variables.get("ups.status"),
            ups_temperature=_safe_float(variables.get("ups.temperature")),
            input_voltage=_safe_float(variables.get("input.voltage")),
            output_voltage=_safe_float(variables.get("output.voltage")),
        )
    finally:
        sock.close()


def fetch_ups_clients(host: str, ups_name: str, port: int = DEFAULT_PORT) -> list[models.UPSClient]:
    """Fetch UPS client information from NUT server.

    Args:
        host: NUT server hostname
        ups_name: UPS name
        port: NUT server port

    Returns:
        List of UPSClient objects
    """
    sock = connect_to_nut(host, port)
    if not sock:
        return []

    try:
        client_ips = get_ups_clients(sock, ups_name)
        return [
            models.UPSClient(
                ups_name=ups_name,
                host=host,
                client_ip=ip,
                client_hostname=None,  # Hostname resolution can be added if needed
            )
            for ip in client_ips
        ]
    finally:
        sock.close()


def fetch_all_ups_from_host(
    host: str, port: int = DEFAULT_PORT, ups_name_filter: str | None = None
) -> tuple[list[models.UPSInfo], list[models.UPSClient]]:
    """Fetch all UPS information from a NUT host.

    Args:
        host: NUT server hostname
        port: NUT server port
        ups_name_filter: If specified, only fetch this UPS

    Returns:
        Tuple of (list of UPSInfo, list of UPSClient)
    """
    sock = connect_to_nut(host, port)
    if not sock:
        return [], []

    try:
        # Get list of UPS devices
        if ups_name_filter:
            ups_list = [(ups_name_filter, "")]
        else:
            ups_list = list_ups(sock)

        all_ups_info: list[models.UPSInfo] = []
        all_clients: list[models.UPSClient] = []

        for ups_name, _ in ups_list:
            # Get UPS variables
            variables = get_ups_variables(sock, ups_name)
            if variables:
                ups_info = models.UPSInfo(
                    ups_name=ups_name,
                    host=host,
                    model=variables.get("ups.model"),
                    battery_charge=_safe_float(variables.get("battery.charge")),
                    battery_runtime=_safe_int(variables.get("battery.runtime")),
                    ups_load=_safe_float(variables.get("ups.load")),
                    ups_status=variables.get("ups.status"),
                    ups_temperature=_safe_float(variables.get("ups.temperature")),
                    input_voltage=_safe_float(variables.get("input.voltage")),
                    output_voltage=_safe_float(variables.get("output.voltage")),
                )
                all_ups_info.append(ups_info)

            # Get UPS clients
            client_ips = get_ups_clients(sock, ups_name)
            for ip in client_ips:
                client = models.UPSClient(
                    ups_name=ups_name,
                    host=host,
                    client_ip=ip,
                    client_hostname=None,
                )
                all_clients.append(client)

        return all_ups_info, all_clients

    finally:
        sock.close()
