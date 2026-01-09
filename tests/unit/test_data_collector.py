#!/usr/bin/env python3
# ruff: noqa: S101
"""
data_collector.py のユニットテスト
"""

import sqlite3
import unittest.mock
from pathlib import Path


class TestInitDb:
    """init_db 関数のテスト"""

    def test_creates_tables(self, temp_data_dir):
        """テーブルが正しく作成される"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"

        with (
            unittest.mock.patch.object(data_collector, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(data_collector, "DB_PATH", db_path),
            unittest.mock.patch.object(data_collector, "SQLITE_SCHEMA_PATH", schema_path),
        ):
            data_collector.init_db()

        # テーブルが作成されていることを確認
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "vm_info" in tables
        assert "uptime_info" in tables
        assert "fetch_status" in tables


class TestLoadSecret:
    """load_secret 関数のテスト"""

    def test_returns_empty_when_file_not_exists(self, temp_data_dir):
        """ファイルが存在しない場合は空の辞書を返す"""
        from server_list.spec import data_collector

        with unittest.mock.patch.object(data_collector, "BASE_DIR", temp_data_dir):
            result = data_collector.load_secret()

        assert result == {}

    def test_loads_secret_file(self, temp_data_dir, sample_secret):
        """シークレットファイルを正しく読み込む"""
        from server_list.spec import data_collector

        with (
            unittest.mock.patch.object(data_collector, "BASE_DIR", temp_data_dir),
            unittest.mock.patch("my_lib.config.load", return_value=sample_secret),
            unittest.mock.patch.object(Path, "exists", return_value=True),
        ):
            result = data_collector.load_secret()

        assert "esxi_auth" in result


class TestSaveAndGetVmData:
    """VM データの保存・取得テスト"""

    def test_save_and_get_vm_info(self, temp_data_dir):
        """VMデータの保存と取得が正しく動作する"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"

        with (
            unittest.mock.patch.object(data_collector, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(data_collector, "DB_PATH", db_path),
            unittest.mock.patch.object(data_collector, "SQLITE_SCHEMA_PATH", schema_path),
        ):
            data_collector.init_db()

            vm_data = [
                {
                    "esxi_host": "test-host",
                    "vm_name": "test-vm",
                    "cpu_count": 4,
                    "ram_mb": 8192,
                    "storage_gb": 100.0,
                    "power_state": "poweredOn",
                }
            ]

            data_collector.save_vm_data("test-host", vm_data)

            result = data_collector.get_vm_info("test-vm", "test-host")

        assert result is not None
        assert result["vm_name"] == "test-vm"
        assert result["cpu_count"] == 4
        assert result["ram_mb"] == 8192

    def test_get_all_vm_info_for_host(self, temp_data_dir):
        """ホスト別VM一覧取得が正しく動作する"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"

        with (
            unittest.mock.patch.object(data_collector, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(data_collector, "DB_PATH", db_path),
            unittest.mock.patch.object(data_collector, "SQLITE_SCHEMA_PATH", schema_path),
        ):
            data_collector.init_db()

            vm_data = [
                {
                    "esxi_host": "test-host",
                    "vm_name": "vm1",
                    "cpu_count": 2,
                    "ram_mb": 4096,
                    "storage_gb": 50.0,
                    "power_state": "poweredOn",
                },
                {
                    "esxi_host": "test-host",
                    "vm_name": "vm2",
                    "cpu_count": 4,
                    "ram_mb": 8192,
                    "storage_gb": 100.0,
                    "power_state": "poweredOff",
                },
            ]

            data_collector.save_vm_data("test-host", vm_data)

            result = data_collector.get_all_vm_info_for_host("test-host")

        assert len(result) == 2
        assert {vm["vm_name"] for vm in result} == {"vm1", "vm2"}


class TestSaveAndGetUptimeInfo:
    """稼働時間データの保存・取得テスト"""

    def test_save_and_get_uptime_info(self, temp_data_dir):
        """稼働時間データの保存と取得が正しく動作する"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"

        with (
            unittest.mock.patch.object(data_collector, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(data_collector, "DB_PATH", db_path),
            unittest.mock.patch.object(data_collector, "SQLITE_SCHEMA_PATH", schema_path),
        ):
            data_collector.init_db()

            host_info = {
                "host": "test-host",
                "boot_time": "2024-01-01T00:00:00",
                "uptime_seconds": 86400.0,
                "status": "running",
                "cpu_threads": 16,
                "cpu_cores": 8,
            }

            data_collector.save_host_info(host_info)

            result = data_collector.get_uptime_info("test-host")

        assert result is not None
        assert result["host"] == "test-host"
        assert result["status"] == "running"
        assert result["cpu_threads"] == 16

    def test_save_host_info_failed(self, temp_data_dir):
        """失敗状態の保存が正しく動作する"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"

        with (
            unittest.mock.patch.object(data_collector, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(data_collector, "DB_PATH", db_path),
            unittest.mock.patch.object(data_collector, "SQLITE_SCHEMA_PATH", schema_path),
        ):
            data_collector.init_db()

            data_collector.save_host_info_failed("test-host")

            result = data_collector.get_uptime_info("test-host")

        assert result is not None
        assert result["status"] == "unknown"  # ESXi に到達できない場合は unknown
        assert result["boot_time"] is None

    def test_get_all_uptime_info(self, temp_data_dir):
        """全稼働時間情報取得が正しく動作する"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"

        with (
            unittest.mock.patch.object(data_collector, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(data_collector, "DB_PATH", db_path),
            unittest.mock.patch.object(data_collector, "SQLITE_SCHEMA_PATH", schema_path),
        ):
            data_collector.init_db()

            for i in range(3):
                host_info = {
                    "host": f"host-{i}",
                    "boot_time": "2024-01-01T00:00:00",
                    "uptime_seconds": 86400.0,
                    "status": "running",
                    "cpu_threads": 8,
                    "cpu_cores": 4,
                }
                data_collector.save_host_info(host_info)

            result = data_collector.get_all_uptime_info()

        assert len(result) == 3
        assert "host-0" in result
        assert "host-1" in result
        assert "host-2" in result


class TestCollectorStartStop:
    """コレクターの開始・停止テスト"""

    def test_start_and_stop_collector(self, temp_data_dir):
        """コレクターの開始と停止が正しく動作する"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"

        with (
            unittest.mock.patch.object(data_collector, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(data_collector, "DB_PATH", db_path),
            unittest.mock.patch.object(data_collector, "SQLITE_SCHEMA_PATH", schema_path),
            unittest.mock.patch.object(data_collector, "collect_all_data"),
            unittest.mock.patch.object(data_collector, "UPDATE_INTERVAL_SEC", 0.1),
        ):
            data_collector.start_collector()

            # スレッドが開始されていることを確認
            assert data_collector._update_thread is not None
            assert data_collector._update_thread.is_alive()

            data_collector.stop_collector()

            # スレッドが停止していることを確認
            assert not data_collector._update_thread.is_alive()
