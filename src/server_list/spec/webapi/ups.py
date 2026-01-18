#!/usr/bin/env python3
"""
UPS API.
Provides UPS information and topology via REST API from SQLite cache.
"""

import dataclasses

import flask

import server_list.spec.data_collector as data_collector
import server_list.spec.webapi as webapi

ups_api = flask.Blueprint("ups_api", __name__)


@ups_api.route("/ups", methods=["GET"])
def get_all_ups():
    """Get all UPS information with topology (clients)."""
    ups_info_list = data_collector.get_all_ups_info()
    all_clients = data_collector.get_all_ups_clients()

    # Group clients by UPS
    clients_by_ups: dict[tuple[str, str], list[dict]] = {}
    for client in all_clients:
        key = (client.ups_name, client.host)
        if key not in clients_by_ups:
            clients_by_ups[key] = []
        clients_by_ups[key].append(dataclasses.asdict(client))

    # Build response with topology
    result = []
    for ups in ups_info_list:
        ups_data = dataclasses.asdict(ups)
        key = (ups.ups_name, ups.host)
        ups_data["clients"] = clients_by_ups.get(key, [])
        result.append(ups_data)

    return webapi.success_response(result)


@ups_api.route("/ups/<host>/<ups_name>", methods=["GET"])
def get_ups_detail(host: str, ups_name: str):
    """Get specific UPS information with clients."""
    ups_info = data_collector.get_ups_info(ups_name, host)

    if not ups_info:
        return webapi.error_response(f"UPS not found: {ups_name}@{host}", 404)

    clients = data_collector.get_ups_clients(ups_name, host)

    result = dataclasses.asdict(ups_info)
    result["clients"] = [dataclasses.asdict(c) for c in clients]

    return webapi.success_response(result)
