#!/usr/bin/env python3
"""
Web API for VM information.
Endpoint: /server-list/api/vm
"""

import dataclasses

import flask

import server_list.spec.data_collector as data_collector
import server_list.spec.models as models
import server_list.spec.webapi as webapi

vm_api = flask.Blueprint("vm_api", __name__)


def _vm_to_response(vm: models.VMInfo, host_reachable: bool) -> dict:
    """VMInfo をAPIレスポンス用dictに変換.

    Args:
        vm: VMInfo dataclass
        host_reachable: ESXi ホストへの到達可否

    Returns:
        API レスポンス用 dict (cached_power_state を含む)
    """
    result = dataclasses.asdict(vm)
    result["cached_power_state"] = result.get("power_state")
    if not host_reachable:
        result["power_state"] = "unknown"
    return result


def apply_unknown_power_state_if_unreachable(vm_info: models.VMInfo) -> dict:
    """Apply 'unknown' power_state if the ESXi host is unreachable.

    When ESXi host cannot be contacted, we use cached data but
    set power_state to 'unknown' to indicate the current state
    cannot be determined. The original cached value is preserved
    in cached_power_state for resource calculations.

    Converts VMInfo to dict for JSON serialization.

    Note: 呼び出し元で vm_info の None チェックを行うこと。
    """
    host_reachable = data_collector.is_host_reachable(vm_info.esxi_host)
    return _vm_to_response(vm_info, host_reachable)


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
        return webapi.error_response("vm_name is required", 400)

    esxi_host = flask.request.args.get("esxi_host")

    result = data_collector.get_vm_info(vm_name, esxi_host)

    if result:
        # Apply unknown power_state if host is unreachable
        result_dict = apply_unknown_power_state_if_unreachable(result)
        return webapi.success_response(result_dict)

    return webapi.error_response(f"VM not found: {vm_name}")


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
        return webapi.error_response("VM list is required", 400)

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
    host_reachable = data_collector.is_host_reachable(esxi_host)

    return webapi.success_response({
        "esxi_host": esxi_host,
        "vms": [_vm_to_response(vm, host_reachable) for vm in vms],
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

    return webapi.error_response(f"Failed to collect data from {esxi_host}", 500)
