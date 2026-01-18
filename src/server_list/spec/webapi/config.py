#!/usr/bin/env python3
"""
Web API for serving config.yaml dynamically.
Endpoint: /server-list/api/config

For ESXi hosts, VM list is automatically populated from collected data.
"""

import flask

import server_list.spec.data_collector as data_collector
import server_list.spec.webapi as webapi

config_api = flask.Blueprint("config_api", __name__)


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

    Optimized: Uses batch queries to fetch all VM info and collection
    statuses in 2 DB queries instead of 2N queries (N = number of hosts).
    """
    if "machine" not in config:
        return config

    # Batch fetch all data in 2 queries instead of 2N queries
    all_vm_info = data_collector.get_all_vm_info()
    all_status = data_collector.get_all_collection_status()

    enriched_machines = []

    for machine in config["machine"]:
        machine_copy = dict(machine)

        if is_esxi_host(machine_copy):
            host_name = machine_copy.get("name", "")
            vm_list = all_vm_info.get(host_name, [])

            if vm_list:
                # Check if host is reachable from pre-fetched status
                status = all_status.get(host_name)
                host_reachable = status is not None and status.status == "success"

                # Convert to config format with additional info
                machine_copy["vm"] = [
                    {
                        "name": vm.vm_name,
                        "power_state": vm.power_state if host_reachable else "unknown",
                    }
                    for vm in vm_list
                ]

        enriched_machines.append(machine_copy)

    return {**config, "machine": enriched_machines}


@config_api.route("/config", methods=["GET"])
def get_config_api():
    """
    Get the server configuration.

    For ESXi hosts, VM list is automatically populated from collected data.

    Returns:
        JSON with machine configuration data
    """
    from server_list.config import Config

    config: Config | None = flask.current_app.config.get("CONFIG")

    if config is None:
        return webapi.error_response("Config not available", 503)

    # Convert Config dataclass to dict and enrich with VM data
    config_dict = config.to_dict()
    enriched_config = enrich_config_with_vm_data(config_dict)
    return webapi.success_response(enriched_config)
