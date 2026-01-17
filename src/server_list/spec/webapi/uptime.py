#!/usr/bin/env python3
"""
Host info API.
Provides host information (uptime, CPU/memory usage) via REST API from SQLite cache.
"""

import dataclasses

import flask

import server_list.spec.data_collector as data_collector

uptime_api = flask.Blueprint("uptime_api", __name__)


@uptime_api.route("/uptime", methods=["GET"])
def get_all_uptime():
    """Get host information for all hosts."""
    host_info_map = data_collector.get_all_host_info()

    # Convert HostInfo dataclass to dict for JSON serialization
    data = {host: dataclasses.asdict(info) for host, info in host_info_map.items()}

    return flask.jsonify({
        "success": True,
        "data": data,
    })


@uptime_api.route("/uptime/<host>", methods=["GET"])
def get_host_uptime(host: str):
    """Get host information for a specific host."""
    info = data_collector.get_host_info(host)

    if info:
        return flask.jsonify({
            "success": True,
            "data": dataclasses.asdict(info),
        })

    return flask.jsonify({
        "success": False,
        "error": f"No host data for: {host}",
    }), 404
