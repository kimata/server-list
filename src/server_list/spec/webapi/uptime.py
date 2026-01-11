#!/usr/bin/env python3
"""
Host info API.
Provides host information (uptime, CPU/memory usage) via REST API from SQLite cache.
"""

import flask

from server_list.spec.data_collector import get_host_info, get_all_host_info

uptime_api = flask.Blueprint("uptime_api", __name__)


@uptime_api.route("/uptime", methods=["GET"])
def get_all_uptime():
    """Get host information for all hosts."""
    data = get_all_host_info()

    return flask.jsonify({
        "success": True,
        "data": data,
    })


@uptime_api.route("/uptime/<host>", methods=["GET"])
def get_host_uptime(host: str):
    """Get host information for a specific host."""
    info = get_host_info(host)

    if info:
        return flask.jsonify({
            "success": True,
            "data": info,
        })

    return flask.jsonify({
        "success": False,
        "error": f"No host data for: {host}",
    }), 404
