#!/usr/bin/env python3
"""
Web API for VM information.
Endpoint: /server-list/api/vm
"""

import dataclasses

import flask

import server_list.spec.data_collector as data_collector
from server_list.spec.models import VMInfo  # Used in type annotation

vm_api = flask.Blueprint("vm_api", __name__)


def apply_unknown_power_state_if_unreachable(vm_info: VMInfo | None) -> dict | None:
    """Apply 'unknown' power_state if the ESXi host is unreachable.

    When ESXi host cannot be contacted, we use cached data but
    set power_state to 'unknown' to indicate the current state
    cannot be determined. The original cached value is preserved
    in cached_power_state for resource calculations.

    Converts VMInfo to dict for JSON serialization.
    """
    if vm_info is None:
        return None

    result = dataclasses.asdict(vm_info)
    cached_power_state = result.get("power_state")
    result["cached_power_state"] = cached_power_state

    esxi_host = result.get("esxi_host")
    if esxi_host and not data_collector.is_host_reachable(esxi_host):
        result["power_state"] = "unknown"

    return result


@vm_api.route("/vm/info", methods=["GET"])
def get_vm_info_api():
    """
    Get VM information.

    Query parameters:
        vm_name: VM name to look up (required)
        esxi_host: ESXi host (optional, for disambiguation)

    Returns:
        JSON with VM info (cpu_count, ram_mb, storage_gb, power_state, collected_at)
    """
    vm_name = flask.request.args.get("vm_name")

    if not vm_name:
        return flask.jsonify({"success": False, "error": "vm_name is required"}), 400

    esxi_host = flask.request.args.get("esxi_host")

    result = data_collector.get_vm_info(vm_name, esxi_host)

    if result:
        # Apply unknown power_state if host is unreachable
        result_dict = apply_unknown_power_state_if_unreachable(result)
        return flask.jsonify({
            "success": True,
            "data": result_dict
        })

    return flask.jsonify({
        "success": False,
        "error": f"VM not found: {vm_name}"
    }), 404


@vm_api.route("/vm/info/batch", methods=["POST"])
def get_vm_info_batch():
    """
    Get VM information for multiple VMs.

    Request body (JSON):
        vms: List of VM names to look up
        esxi_host: ESXi host (optional)

    Returns:
        JSON with results for each VM
    """
    data = flask.request.get_json()

    if not data or "vms" not in data:
        return flask.jsonify({"success": False, "error": "VM list is required"}), 400

    vm_list = data["vms"]
    esxi_host = data.get("esxi_host")
    results = {}

    for vm_name in vm_list:
        result = data_collector.get_vm_info(vm_name, esxi_host)
        if result:
            # Apply unknown power_state if host is unreachable
            result_dict = apply_unknown_power_state_if_unreachable(result)
            results[vm_name] = {
                "success": True,
                "data": result_dict
            }
        else:
            results[vm_name] = {
                "success": False,
                "data": None
            }

    return flask.jsonify({
        "success": True,
        "results": results
    })


@vm_api.route("/vm/host/<esxi_host>", methods=["GET"])
def get_vms_for_host(esxi_host: str):
    """
    Get all VMs for a specific ESXi host.

    Returns:
        JSON with list of VMs and their info
    """
    vms = data_collector.get_all_vm_info_for_host(esxi_host)

    # Apply unknown power_state if host is unreachable
    # Keep cached_power_state for resource calculations
    host_reachable = data_collector.is_host_reachable(esxi_host)
    vms_result = [
        {
            **dataclasses.asdict(vm),
            "cached_power_state": vm.power_state,
            "power_state": vm.power_state if host_reachable else "unknown",
        }
        for vm in vms
    ]

    return flask.jsonify({
        "success": True,
        "esxi_host": esxi_host,
        "vms": vms_result
    })


@vm_api.route("/vm/refresh/<esxi_host>", methods=["POST"])
def refresh_host_data(esxi_host: str):
    """
    Trigger immediate data collection from an ESXi host.

    This endpoint triggers the data collector to fetch fresh data
    from the specified ESXi host. After collection is complete,
    an SSE event is sent to notify connected clients.

    Returns:
        JSON with success status
    """
    success = data_collector.collect_host_data(esxi_host)

    if success:
        return flask.jsonify({
            "success": True,
            "message": f"Data collection completed for {esxi_host}",
        })

    return flask.jsonify({
        "success": False,
        "error": f"Failed to collect data from {esxi_host}",
    }), 500
