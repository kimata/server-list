#!/usr/bin/env python3
"""
Web API for serving config.yaml dynamically.
Endpoint: /server-list/api/config

Uses cache for fast responses.
For ESXi hosts, VM list is automatically populated from collected data.
"""

from flask import Blueprint, jsonify

from server_list.spec.cache_manager import get_config, init_db
from server_list.spec.data_collector import get_all_vm_info_for_host, is_host_reachable

config_api = Blueprint("config_api", __name__)

# Initialize cache database
init_db()


def is_esxi_host(machine: dict) -> bool:
    """Check if machine is an ESXi host."""
    os_name = machine.get("os", "").lower()
    return "esxi" in os_name


def enrich_config_with_vm_data(config: dict) -> dict:
    """Enrich config with VM data from ESXi hosts.

    For machines running ESXi, automatically populate the VM list
    from collected ESXi data instead of using config.yaml.

    When ESXi host is unreachable, cached data is used but power_state
    is set to 'unknown' to indicate the current state cannot be determined.
    """
    if "machine" not in config:
        return config

    enriched_machines = []

    for machine in config["machine"]:
        machine_copy = dict(machine)

        if is_esxi_host(machine_copy):
            # Get VM list from collected ESXi data
            host_name = machine_copy.get("name", "")
            vm_list = get_all_vm_info_for_host(host_name)

            if vm_list:
                # Check if host is reachable to determine power_state handling
                host_reachable = is_host_reachable(host_name)

                # Convert to config format with additional info
                machine_copy["vm"] = [
                    {
                        "name": vm["vm_name"],
                        "power_state": vm.get("power_state") if host_reachable else "unknown",
                    }
                    for vm in vm_list
                ]

        enriched_machines.append(machine_copy)

    return {**config, "machine": enriched_machines}


@config_api.route("/config", methods=["GET"])
def get_config_api():
    """
    Get the server configuration from cache.

    For ESXi hosts, VM list is automatically populated from collected data.

    Returns:
        JSON with machine configuration data
    """
    config = get_config()

    if config:
        # Enrich config with VM data from ESXi
        enriched_config = enrich_config_with_vm_data(config)
        return jsonify(enriched_config)

    return jsonify({"error": "Config not available"}), 503
