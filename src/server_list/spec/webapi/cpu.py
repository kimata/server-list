#!/usr/bin/env python3
"""
Web API for CPU benchmark data.
Endpoint: /server-list/api/cpu/benchmark
"""

import dataclasses

import flask

import server_list.spec.cpu_benchmark as cpu_benchmark
import server_list.spec.webapi as webapi

cpu_api = flask.Blueprint("cpu_api", __name__)


@cpu_api.route("/cpu/benchmark", methods=["GET"])
def get_cpu_benchmark():
    """
    Get CPU benchmark score.

    Query parameters:
        cpu: CPU name to look up (required)
        fetch: If "true", fetch from web if not in cache (optional)

    Returns:
        JSON with cpu_name, multi_thread_score, single_thread_score
    """
    cpu_name = flask.request.args.get("cpu")

    if not cpu_name:
        return webapi.error_response("CPU name is required", 400)

    # Check database first
    result = cpu_benchmark.get_benchmark(cpu_name)

    if result:
        result_dict = dataclasses.asdict(result)
        result_dict["source"] = "cache"
        return webapi.success_response(result_dict)

    # Optionally fetch from web
    if flask.request.args.get("fetch", "").lower() == "true":
        result = cpu_benchmark.fetch_and_save_benchmark(cpu_name)
        if result:
            result_dict = dataclasses.asdict(result)
            result_dict["source"] = "web"
            return webapi.success_response(result_dict)

    return webapi.error_response(f"Benchmark data not found for: {cpu_name}")


@cpu_api.route("/cpu/benchmark/batch", methods=["POST"])
def get_cpu_benchmarks_batch():
    """
    Get CPU benchmark scores for multiple CPUs.

    Request body (JSON):
        cpus: List of CPU names to look up
        fetch: If true, fetch from web if not in cache (optional)

    Returns:
        JSON with results for each CPU
    """
    data = flask.request.get_json()

    if not data or "cpus" not in data:
        return webapi.error_response("CPU list is required", 400)

    cpu_list = data["cpus"]
    should_fetch = data.get("fetch", False)
    results = {}

    for cpu_name in cpu_list:
        result = cpu_benchmark.get_benchmark(cpu_name)
        if result:
            result_dict = dataclasses.asdict(result)
            result_dict["source"] = "cache"
            results[cpu_name] = {
                "success": True,
                "data": result_dict,
            }
        elif should_fetch:
            # Fetch from web if not in cache
            result = cpu_benchmark.fetch_and_save_benchmark(cpu_name)
            if result:
                result_dict = dataclasses.asdict(result)
                result_dict["source"] = "web"
                results[cpu_name] = {
                    "success": True,
                    "data": result_dict,
                }
            else:
                results[cpu_name] = {
                    "success": False,
                    "data": None,
                }
        else:
            results[cpu_name] = {
                "success": False,
                "data": None,
            }

    return flask.jsonify({
        "success": True,
        "results": results
    })
