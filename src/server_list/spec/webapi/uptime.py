#!/usr/bin/env python3
"""
Uptime API for ESXi hosts.
Provides uptime information via REST API from SQLite cache.
"""

import flask

from server_list.spec.data_collector import get_uptime_info, get_all_uptime_info

uptime_api = flask.Blueprint("uptime_api", __name__)


@uptime_api.route("/uptime", methods=["GET"])
def get_all_uptime():
    """Get uptime information for all hosts."""
    data = get_all_uptime_info()

    return flask.jsonify({
        "success": True,
        "data": data,
    })


@uptime_api.route("/uptime/<host>", methods=["GET"])
def get_host_uptime(host: str):
    """Get uptime information for a specific host."""
    info = get_uptime_info(host)

    if info:
        return flask.jsonify({
            "success": True,
            "data": info,
        })

    return flask.jsonify({
        "success": False,
        "error": f"No uptime data for host: {host}",
    }), 404
