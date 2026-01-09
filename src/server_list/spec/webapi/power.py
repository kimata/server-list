#!/usr/bin/env python3
"""
Power API for iLO hosts.
Provides power consumption information via REST API from SQLite cache.
"""

import flask

from server_list.spec.data_collector import get_power_info, get_all_power_info

power_api = flask.Blueprint("power_api", __name__)


@power_api.route("/power", methods=["GET"])
def get_all_power():
    """Get power consumption information for all hosts."""
    data = get_all_power_info()

    return flask.jsonify({
        "success": True,
        "data": data,
    })


@power_api.route("/power/<host>", methods=["GET"])
def get_host_power(host: str):
    """Get power consumption information for a specific host."""
    info = get_power_info(host)

    if info:
        return flask.jsonify({
            "success": True,
            "data": info,
        })

    return flask.jsonify({
        "success": False,
        "error": f"No power data for host: {host}",
    }), 404
