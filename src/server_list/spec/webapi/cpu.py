#!/usr/bin/env python3
"""
Web API for CPU benchmark data.
Endpoint: /server-list/api/cpu/benchmark
"""

from flask import Blueprint, jsonify, request

from server_list.spec.cpu_benchmark import (
    get_benchmark,
    fetch_and_save_benchmark,
    init_db,
)

cpu_api = Blueprint("cpu_api", __name__)

# Initialize database once at module load
init_db()


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
    cpu_name = request.args.get("cpu")

    if not cpu_name:
        return jsonify({"error": "CPU name is required"}), 400

    # Check database first
    result = get_benchmark(cpu_name)

    if result:
        return jsonify({
            "success": True,
            "data": result,
            "source": "cache"
        })

    # Optionally fetch from web
    if request.args.get("fetch", "").lower() == "true":
        result = fetch_and_save_benchmark(cpu_name)
        if result:
            return jsonify({
                "success": True,
                "data": result,
                "source": "web"
            })

    return jsonify({
        "success": False,
        "error": f"Benchmark data not found for: {cpu_name}"
    }), 404


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
    data = request.get_json()

    if not data or "cpus" not in data:
        return jsonify({"error": "CPU list is required"}), 400

    cpu_list = data["cpus"]
    should_fetch = data.get("fetch", False)
    results = {}

    for cpu_name in cpu_list:
        result = get_benchmark(cpu_name)
        if result:
            results[cpu_name] = {
                "success": True,
                "data": result,
                "source": "cache"
            }
        elif should_fetch:
            # Fetch from web if not in cache
            result = fetch_and_save_benchmark(cpu_name)
            if result:
                results[cpu_name] = {
                    "success": True,
                    "data": result,
                    "source": "web"
                }
            else:
                results[cpu_name] = {
                    "success": False,
                    "data": None
                }
        else:
            results[cpu_name] = {
                "success": False,
                "data": None
            }

    return jsonify({
        "success": True,
        "results": results
    })
