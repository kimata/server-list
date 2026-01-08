#!/usr/bin/env python3
# ruff: noqa: S101
"""
API 統合テスト

Flask アプリケーションの API エンドポイントをテストします。
実際の ESXi アクセスは行いません。
"""

import unittest.mock
from pathlib import Path


class TestConfigApiIntegration:
    """設定 API の統合テスト"""

    def test_full_config_flow(self, client, temp_data_dir, sample_config):
        """設定取得の完全なフロー"""
        from server_list.spec import cache_manager

        db_path = temp_data_dir / "cache.db"
        config_path = temp_data_dir / "config.yaml"

        import yaml

        config_path.write_text(yaml.dump(sample_config))

        with (
            unittest.mock.patch.object(cache_manager, "DB_PATH", db_path),
            unittest.mock.patch.object(cache_manager, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(cache_manager, "CONFIG_PATH", config_path),
        ):
            cache_manager.init_db()
            cache_manager.set_cache("config", sample_config)

            response = client.get("/server-list/api/config")

            assert response.status_code == 200
            data = response.get_json()
            assert "machine" in data


class TestCpuApiIntegration:
    """CPU API の統合テスト"""

    def test_benchmark_lookup_and_cache(self, client, temp_data_dir):
        """ベンチマーク検索とキャッシュ"""
        from server_list.spec import cpu_benchmark

        db_path = temp_data_dir / "cpu_spec.db"

        with unittest.mock.patch.object(cpu_benchmark, "DB_PATH", db_path):
            cpu_benchmark.init_db()
            cpu_benchmark.save_benchmark("Intel Core i7-12700K", 30000, 4000)

            response = client.get("/server-list/api/cpu/benchmark?cpu=Intel Core i7-12700K")

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert data["data"]["cpu_name"] == "Intel Core i7-12700K"
            assert data["data"]["multi_thread_score"] == 30000
            assert data["data"]["single_thread_score"] == 4000

    def test_batch_benchmark_lookup(self, client, temp_data_dir):
        """バッチベンチマーク検索"""
        from server_list.spec import cpu_benchmark

        db_path = temp_data_dir / "cpu_spec.db"

        with unittest.mock.patch.object(cpu_benchmark, "DB_PATH", db_path):
            cpu_benchmark.init_db()
            cpu_benchmark.save_benchmark("Intel Core i7-12700K", 30000, 4000)
            cpu_benchmark.save_benchmark("Intel Core i5-12600K", 25000, 3500)

            response = client.post(
                "/server-list/api/cpu/benchmark/batch",
                json={"cpus": ["Intel Core i7-12700K", "Intel Core i5-12600K"]},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert len(data["results"]) == 2


class TestVmApiIntegration:
    """VM API の統合テスト"""

    def test_vm_info_lookup(self, client, temp_data_dir):
        """VM 情報検索"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"

        vms = [
            {
                "esxi_host": "esxi-01",
                "vm_name": "test-vm",
                "cpu_count": 4,
                "ram_mb": 8192,
                "storage_gb": 100.0,
                "power_state": "on",
            }
        ]

        with (
            unittest.mock.patch.object(data_collector, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(data_collector, "DB_PATH", db_path),
            unittest.mock.patch.object(data_collector, "SQLITE_SCHEMA_PATH", schema_path),
        ):
            data_collector.init_db()
            data_collector.save_vm_data("esxi-01", vms)

            response = client.get("/server-list/api/vm/info?vm_name=test-vm&esxi_host=esxi-01")

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert data["data"]["vm_name"] == "test-vm"
            assert data["data"]["cpu_count"] == 4

    def test_vms_for_host(self, client, temp_data_dir):
        """ホストの VM 一覧取得"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"

        vms = [
            {
                "esxi_host": "esxi-01",
                "vm_name": "vm-1",
                "cpu_count": 2,
                "ram_mb": 4096,
                "storage_gb": 50.0,
                "power_state": "on",
            },
            {
                "esxi_host": "esxi-01",
                "vm_name": "vm-2",
                "cpu_count": 4,
                "ram_mb": 8192,
                "storage_gb": 100.0,
                "power_state": "on",
            },
        ]

        with (
            unittest.mock.patch.object(data_collector, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(data_collector, "DB_PATH", db_path),
            unittest.mock.patch.object(data_collector, "SQLITE_SCHEMA_PATH", schema_path),
        ):
            data_collector.init_db()
            data_collector.save_vm_data("esxi-01", vms)

            response = client.get("/server-list/api/vm/host/esxi-01")

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert data["esxi_host"] == "esxi-01"
            assert len(data["vms"]) == 2


class TestUptimeApiIntegration:
    """Uptime API の統合テスト"""

    def test_uptime_info_lookup(self, client, temp_data_dir):
        """稼働時間情報検索"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"

        host_info = {
            "host": "server-01",
            "boot_time": "2024-01-01T00:00:00",
            "uptime_seconds": 86400,
            "status": "running",
            "cpu_threads": 16,
            "cpu_cores": 8,
        }

        with (
            unittest.mock.patch.object(data_collector, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(data_collector, "DB_PATH", db_path),
            unittest.mock.patch.object(data_collector, "SQLITE_SCHEMA_PATH", schema_path),
        ):
            data_collector.init_db()
            data_collector.save_host_info(host_info)

            response = client.get("/server-list/api/uptime/server-01")

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert data["data"]["host"] == "server-01"
            assert data["data"]["status"] == "running"

    def test_all_uptime_info(self, client, temp_data_dir):
        """全ホストの稼働時間情報取得"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"

        host_info_1 = {
            "host": "server-01",
            "boot_time": "2024-01-01T00:00:00",
            "uptime_seconds": 86400,
            "status": "running",
            "cpu_threads": 16,
            "cpu_cores": 8,
        }
        host_info_2 = {
            "host": "server-02",
            "boot_time": "2024-01-02T00:00:00",
            "uptime_seconds": 43200,
            "status": "running",
            "cpu_threads": 8,
            "cpu_cores": 4,
        }

        with (
            unittest.mock.patch.object(data_collector, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(data_collector, "DB_PATH", db_path),
            unittest.mock.patch.object(data_collector, "SQLITE_SCHEMA_PATH", schema_path),
        ):
            data_collector.init_db()
            data_collector.save_host_info(host_info_1)
            data_collector.save_host_info(host_info_2)

            response = client.get("/server-list/api/uptime")

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert len(data["data"]) == 2
