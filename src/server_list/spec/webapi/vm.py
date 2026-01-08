#!/usr/bin/env python3
"""
Web API for VM information.
Endpoint: /server-list/api/vm
"""

from flask import Blueprint, jsonify, request

from server_list.spec.data_collector import get_vm_info, get_all_vm_info_for_host

vm_api = Blueprint("vm_api", __name__)


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
    vm_name = request.args.get("vm_name")

    if not vm_name:
        return jsonify({"error": "vm_name is required"}), 400

    esxi_host = request.args.get("esxi_host")

    result = get_vm_info(vm_name, esxi_host)

    if result:
        return jsonify({
            "success": True,
            "data": result
        })

    return jsonify({
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
    data = request.get_json()

    if not data or "vms" not in data:
        return jsonify({"error": "VM list is required"}), 400

    vm_list = data["vms"]
    esxi_host = data.get("esxi_host")
    results = {}

    for vm_name in vm_list:
        result = get_vm_info(vm_name, esxi_host)
        if result:
            results[vm_name] = {
                "success": True,
                "data": result
            }
        else:
            results[vm_name] = {
                "success": False,
                "data": None
            }

    return jsonify({
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
    vms = get_all_vm_info_for_host(esxi_host)

    return jsonify({
        "success": True,
        "esxi_host": esxi_host,
        "vms": vms
    })
