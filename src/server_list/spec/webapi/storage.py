#!/usr/bin/env python3
"""
Storage API for ZFS pools and mount points.
Provides storage information via REST API from SQLite cache.
"""

import dataclasses

import flask

from server_list.spec.data_collector import get_mount_info, get_zfs_pool_info

storage_api = flask.Blueprint("storage_api", __name__)


@storage_api.route("/storage/zfs/<host>", methods=["GET"])
def get_host_zfs_pools(host: str):
    """Get ZFS pool information for a specific host."""
    pools = get_zfs_pool_info(host)

    if pools:
        return flask.jsonify({
            "success": True,
            "data": [dataclasses.asdict(p) for p in pools],
        })

    return flask.jsonify({
        "success": False,
        "error": f"No ZFS pool data for host: {host}",
    }), 404


@storage_api.route("/storage/mount/<host>", methods=["GET"])
def get_host_mounts(host: str):
    """Get mount point information for a specific host."""
    mounts = get_mount_info(host)

    if mounts:
        return flask.jsonify({
            "success": True,
            "data": [dataclasses.asdict(m) for m in mounts],
        })

    return flask.jsonify({
        "success": False,
        "error": f"No mount data for host: {host}",
    }), 404
