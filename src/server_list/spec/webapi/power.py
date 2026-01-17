#!/usr/bin/env python3
"""
Power API for iLO hosts.
Provides power consumption information via REST API from SQLite cache.
"""

import dataclasses

import flask

import server_list.spec.data_collector as data_collector

power_api = flask.Blueprint("power_api", __name__)


@power_api.route("/power", methods=["GET"])
def get_all_power():
    """Get power consumption information for all hosts."""
    power_info_map = data_collector.get_all_power_info()

    # Convert PowerInfo dataclass to dict for JSON serialization
    data = {host: dataclasses.asdict(info) for host, info in power_info_map.items()}

    return flask.jsonify({
        "success": True,
        "data": data,
    })


@power_api.route("/power/<host>", methods=["GET"])
def get_host_power(host: str):
    """Get power consumption information for a specific host."""
    info = data_collector.get_power_info(host)

    if info:
        return flask.jsonify({
            "success": True,
            "data": dataclasses.asdict(info),
        })

    return flask.jsonify({
        "success": False,
        "error": f"No power data for host: {host}",
    }), 404
