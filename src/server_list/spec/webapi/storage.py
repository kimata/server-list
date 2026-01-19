#!/usr/bin/env python3
"""
Storage API for ZFS pools and mount points.
Provides storage information via REST API from SQLite cache.
"""

import dataclasses
from typing import Any

import flask

import server_list.spec.data_collector as data_collector
import server_list.spec.webapi as webapi

storage_api = flask.Blueprint("storage_api", __name__)


@storage_api.route("/storage/zfs/<host>", methods=["GET"])
def get_host_zfs_pools(host: str):
    """Get ZFS pool information for a specific host."""
    pools = data_collector.get_zfs_pool_info(host)

    if pools:
        return webapi.success_response([dataclasses.asdict(p) for p in pools])

    return webapi.error_response(f"No ZFS pool data for host: {host}")


@storage_api.route("/storage/mount/<host>", methods=["GET"])
def get_host_mounts(host: str):
    """Get mount point information for a specific host."""
    mounts = data_collector.get_mount_info(host)

    if mounts:
        return webapi.success_response([dataclasses.asdict(m) for m in mounts])

    return webapi.error_response(f"No mount data for host: {host}")


@storage_api.route("/storage/batch", methods=["POST"])
def get_storage_batch():
    """Get storage information for multiple hosts in a single request.

    Request body:
    {
        "zfs_hosts": ["host1", "host2"],      # optional
        "mount_hosts": ["host3", "host4"]     # optional
    }

    Response:
    {
        "success": true,
        "data": {
            "zfs": {
                "host1": [pools...],
                "host2": [pools...]
            },
            "mount": {
                "host3": [mounts...],
                "host4": [mounts...]
            }
        }
    }
    """
    body = flask.request.get_json(silent=True)
    if not body or not isinstance(body, dict):
        return webapi.error_response("Request body is required", 400)

    zfs_hosts: list[str] = body.get("zfs_hosts", [])
    mount_hosts: list[str] = body.get("mount_hosts", [])

    if not zfs_hosts and not mount_hosts:
        return webapi.error_response("At least one of zfs_hosts or mount_hosts is required", 400)

    result: dict[str, dict[str, Any]] = {"zfs": {}, "mount": {}}

    for host in zfs_hosts:
        pools = data_collector.get_zfs_pool_info(host)
        result["zfs"][host] = [dataclasses.asdict(p) for p in pools]

    for host in mount_hosts:
        mounts = data_collector.get_mount_info(host)
        result["mount"][host] = [dataclasses.asdict(m) for m in mounts]

    return webapi.success_response(result)
