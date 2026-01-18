#!/usr/bin/env python3
# ruff: noqa: S101
"""
webapi/cpu.py のユニットテスト
"""

import unittest.mock

from server_list.spec.models import CPUBenchmark


class TestCpuBenchmarkApi:
    """CPU ベンチマーク API のテスト"""

    def test_get_benchmark_success(self, client):
        """GET /api/cpu/benchmark が正常に動作する"""
        benchmark_data = CPUBenchmark(
            cpu_name="Intel Core i7-12700K",
            multi_thread_score=30000,
            single_thread_score=4000,
        )

        with unittest.mock.patch(
            "server_list.spec.cpu_benchmark.get_benchmark",
            return_value=benchmark_data,
        ):
            response = client.get("/server-list/api/cpu/benchmark?cpu=Intel%20Core%20i7-12700K")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["multi_thread_score"] == 30000
        assert data["data"]["source"] == "cache"

    def test_get_benchmark_missing_cpu_param(self, client):
        """CPU パラメータがない場合に400を返す"""
        response = client.get("/server-list/api/cpu/benchmark")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_get_benchmark_not_found(self, client):
        """ベンチマークが見つからない場合に404を返す"""
        with unittest.mock.patch(
            "server_list.spec.cpu_benchmark.get_benchmark",
            return_value=None,
        ):
            response = client.get("/server-list/api/cpu/benchmark?cpu=Unknown%20CPU")

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False

    def test_get_benchmark_fetch_from_web(self, client):
        """fetch=true でウェブから取得する"""
        benchmark_data = CPUBenchmark(
            cpu_name="Intel Core i7-12700K",
            multi_thread_score=30000,
            single_thread_score=4000,
        )

        with (
            unittest.mock.patch("server_list.spec.cpu_benchmark.get_benchmark", return_value=None),
            unittest.mock.patch(
                "server_list.spec.cpu_benchmark.fetch_and_save_benchmark",
                return_value=benchmark_data,
            ),
        ):
            response = client.get("/server-list/api/cpu/benchmark?cpu=Intel%20Core%20i7-12700K&fetch=true")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["source"] == "web"


class TestCpuBenchmarkBatchApi:
    """CPU ベンチマーク バッチ API のテスト"""

    def test_batch_success(self, client):
        """POST /api/cpu/benchmark/batch が正常に動作する"""
        benchmark_data = CPUBenchmark(
            cpu_name="Intel Core i7-12700K",
            multi_thread_score=30000,
            single_thread_score=4000,
        )

        with unittest.mock.patch(
            "server_list.spec.cpu_benchmark.get_benchmarks_batch",
            return_value={"Intel Core i7-12700K": benchmark_data},
        ):
            response = client.post(
                "/server-list/api/cpu/benchmark/batch",
                json={"cpus": ["Intel Core i7-12700K"]},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "Intel Core i7-12700K" in data["results"]

    def test_batch_missing_cpus(self, client):
        """cpus パラメータがない場合に400を返す"""
        response = client.post("/server-list/api/cpu/benchmark/batch", json={})

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_batch_multiple_cpus(self, client):
        """複数のCPUを処理する"""
        batch_results = {
            "CPU1": CPUBenchmark(cpu_name="CPU1", multi_thread_score=10000, single_thread_score=2000),
            "CPU2": None,
        }

        with unittest.mock.patch(
            "server_list.spec.cpu_benchmark.get_benchmarks_batch",
            return_value=batch_results,
        ):
            response = client.post(
                "/server-list/api/cpu/benchmark/batch",
                json={"cpus": ["CPU1", "CPU2"]},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["results"]["CPU1"]["success"] is True
        assert data["results"]["CPU2"]["success"] is False
