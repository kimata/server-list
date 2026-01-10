#!/usr/bin/env python3
"""
Storage API for ZFS pools.
Provides ZFS pool information via REST API from SQLite cache.
"""

import flask

from server_list.spec.data_collector import get_zfs_pool_info

storage_api = flask.Blueprint("storage_api", __name__)


@storage_api.route("/storage/zfs/<host>", methods=["GET"])
def get_host_zfs_pools(host: str):
    """Get ZFS pool information for a specific host."""
    pools = get_zfs_pool_info(host)

    if pools:
        return flask.jsonify({
            "success": True,
            "data": pools,
        })

    return flask.jsonify({
        "success": False,
        "error": f"No ZFS pool data for host: {host}",
    }), 404
