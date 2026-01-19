#!/usr/bin/env python3
"""
Web API for CPU benchmark data.
Endpoint: /server-list/api/cpu/benchmark

All endpoints respond immediately with cached data.
If data is not cached and fetch is requested, a background task is queued
and the frontend is notified via SSE when data becomes available.
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
        fetch: If "true", queue background fetch if not in cache (optional)

    Returns:
        JSON with cpu_name, multi_thread_score, single_thread_score
        If data is not cached and fetch is requested, returns pending=true
    """
    cpu_name = flask.request.args.get("cpu")

    if not cpu_name:
        return webapi.error_response("CPU name is required", 400)

    # Check database first
    result = cpu_benchmark.get_benchmark(cpu_name)

    if result:
        result_dict = dataclasses.asdict(result)
        result_dict["source"] = "cache"
        result_dict["pending"] = False
        return webapi.success_response(result_dict)

    # Queue background fetch if requested
    should_fetch = flask.request.args.get("fetch", "").lower() == "true"
    if should_fetch:
        queued = cpu_benchmark.queue_background_fetch(cpu_name)
        pending = queued or cpu_benchmark.is_fetch_pending(cpu_name)
        return flask.jsonify({
            "success": True,
            "data": None,
            "pending": pending,
            "message": "Fetching benchmark data in background" if pending else "Fetch already in progress",
        })

    return webapi.error_response(f"Benchmark data not found for: {cpu_name}")


@cpu_api.route("/cpu/benchmark/batch", methods=["POST"])
def get_cpu_benchmarks_batch():
    """
    Get CPU benchmark scores for multiple CPUs.

    Request body (JSON):
        cpus: List of CPU names to look up
        fetch: If true, queue background fetch for missing CPUs (optional)

    Returns:
        JSON with results for each CPU.
        Missing CPUs are marked with pending=true if background fetch was queued.

    Optimized: Uses batch query to fetch all benchmarks in a single DB query.
    Always responds immediately - no blocking on web requests.
    """
    data = flask.request.get_json()

    if not data or "cpus" not in data:
        return webapi.error_response("CPU list is required", 400)

    cpu_list = data["cpus"]
    should_fetch = data.get("fetch", False)
    results = {}
    missing_cpus = []

    # Batch fetch all benchmarks in a single query
    batch_results = cpu_benchmark.get_benchmarks_batch(cpu_list)

    for cpu_name in cpu_list:
        result = batch_results.get(cpu_name)
        if result:
            result_dict = dataclasses.asdict(result)
            result_dict["source"] = "cache"
            result_dict["pending"] = False
            results[cpu_name] = {
                "success": True,
                "data": result_dict,
            }
        else:
            missing_cpus.append(cpu_name)
            results[cpu_name] = {
                "success": False,
                "data": None,
                "pending": False,
            }

    # Queue background fetches for missing CPUs
    if should_fetch and missing_cpus:
        queued_count = cpu_benchmark.queue_background_fetch_batch(missing_cpus)
        # Update pending status for missing CPUs
        for cpu_name in missing_cpus:
            results[cpu_name]["pending"] = cpu_benchmark.is_fetch_pending(cpu_name)
        if queued_count > 0:
            results["_meta"] = {
                "queued": queued_count,
                "message": f"Queued {queued_count} background fetch(es)",
            }

    return flask.jsonify({
        "success": True,
        "results": results
    })
