#!/usr/bin/env python3
"""
Storage API for ZFS pools and mount points.
Provides storage information via REST API from SQLite cache.
"""

import dataclasses

import flask

import server_list.spec.data_collector
import server_list.spec.webapi as webapi

storage_api = flask.Blueprint("storage_api", __name__)


@storage_api.route("/storage/zfs/<host>", methods=["GET"])
def get_host_zfs_pools(host: str):
    """Get ZFS pool information for a specific host."""
    pools = server_list.spec.data_collector.get_zfs_pool_info(host)

    if pools:
        return webapi.success_response([dataclasses.asdict(p) for p in pools])

    return webapi.error_response(f"No ZFS pool data for host: {host}")


@storage_api.route("/storage/mount/<host>", methods=["GET"])
def get_host_mounts(host: str):
    """Get mount point information for a specific host."""
    mounts = server_list.spec.data_collector.get_mount_info(host)

    if mounts:
        return webapi.success_response([dataclasses.asdict(m) for m in mounts])

    return webapi.error_response(f"No mount data for host: {host}")
