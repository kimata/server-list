#!/usr/bin/env python3
# ruff: noqa: S101
"""
data_collector.py の追加ユニットテスト（100%カバレッジ用）
"""

import sqlite3
import unittest.mock
from pathlib import Path

from server_list.spec import db, db_config


class TestLoadSecretEdgeCases:
    """load_secret 関数のエッジケーステスト"""

    def test_handles_exception(self, temp_data_dir):
        """例外時は空の辞書を返す"""
        from server_list.spec import data_collector

        # 存在しないパスを指定して例外を発生させる
        nonexistent_path = temp_data_dir / "nonexistent"

        with unittest.mock.patch.object(db, "BASE_DIR", nonexistent_path):
            result = data_collector.load_secret()

        assert result == {}


class TestLoadConfig:
    """load_config 関数のテスト"""

    def test_handles_exception(self, temp_data_dir):
        """例外時は空の辞書を返す"""
        from server_list.spec import data_collector

        # 存在しないパスを指定して例外を発生させる
        nonexistent_path = temp_data_dir / "nonexistent"

        with unittest.mock.patch.object(db, "BASE_DIR", nonexistent_path):
            result = data_collector.load_config()

        assert result == {}


class TestSaveVmData:
    """save_vm_data 関数のテスト"""

    def test_saves_vm_data(self, temp_data_dir):
        """VM データを保存する"""
        from server_list.spec import data_collector
        from server_list.spec.models import VMInfo

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"
        db_config.set_server_data_db_path(db_path)

        vms = [
            VMInfo(
                esxi_host="test-host",
                vm_name="test-vm",
                cpu_count=4,
                ram_mb=8192,
                storage_gb=100.0,
                power_state="on",
            )
        ]

        with (
            unittest.mock.patch.object(db, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(db, "SQLITE_SCHEMA_PATH", schema_path),
        ):
            data_collector.init_db()
            data_collector.save_vm_data("test-host", vms)

            # 保存されていることを確認
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT vm_name FROM vm_info WHERE esxi_host = ?", ("test-host",))
            row = cursor.fetchone()
            conn.close()

            assert row is not None
            assert row[0] == "test-vm"


class TestSaveHostInfo:
    """save_host_info 関数のテスト"""

    def test_saves_host_info(self, temp_data_dir):
        """ホスト情報を保存する"""
        from server_list.spec import data_collector
        from server_list.spec.models import HostInfo

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"
        db_config.set_server_data_db_path(db_path)

        host_info = HostInfo(
            host="test-host",
            boot_time="2024-01-01T00:00:00",
            uptime_seconds=86400.0,
            status="running",
            cpu_threads=16,
            cpu_cores=8,
        )

        with (
            unittest.mock.patch.object(db, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(db, "SQLITE_SCHEMA_PATH", schema_path),
        ):
            data_collector.init_db()
            data_collector.save_host_info(host_info)

            # 保存されていることを確認
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM host_info WHERE host = ?", ("test-host",))
            row = cursor.fetchone()
            conn.close()

            assert row is not None
            assert row[0] == "running"


class TestSaveHostInfoFailed:
    """save_host_info_failed 関数のテスト"""

    def test_saves_failed_status(self, temp_data_dir):
        """失敗ステータスを保存する"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"
        db_config.set_server_data_db_path(db_path)

        with (
            unittest.mock.patch.object(db, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(db, "SQLITE_SCHEMA_PATH", schema_path),
        ):
            data_collector.init_db()
            data_collector.save_host_info_failed("test-host")

            # 保存されていることを確認
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM host_info WHERE host = ?", ("test-host",))
            row = cursor.fetchone()
            conn.close()

            assert row is not None
            assert row[0] == "unknown"  # ホストに到達できない場合は unknown


class TestGetAllVmInfoForHost:
    """get_all_vm_info_for_host 関数のテスト"""

    def test_gets_all_vm_info(self, temp_data_dir):
        """特定ホストの全 VM 情報を取得する"""
        from server_list.spec import data_collector
        from server_list.spec.models import VMInfo

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"
        db_config.set_server_data_db_path(db_path)

        vms = [
            VMInfo(
                esxi_host="test-host",
                vm_name="test-vm",
                cpu_count=4,
                ram_mb=8192,
                storage_gb=100.0,
                power_state="on",
            )
        ]

        with (
            unittest.mock.patch.object(db, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(db, "SQLITE_SCHEMA_PATH", schema_path),
        ):
            data_collector.init_db()
            data_collector.save_vm_data("test-host", vms)

            result = data_collector.get_all_vm_info_for_host("test-host")

            assert len(result) == 1
            assert result[0].vm_name == "test-vm"


class TestGetHostInfo:
    """get_host_info 関数のテスト"""

    def test_gets_host_info(self, temp_data_dir):
        """ホスト情報を取得する"""
        from server_list.spec import data_collector
        from server_list.spec.models import HostInfo

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"
        db_config.set_server_data_db_path(db_path)

        host_info = HostInfo(
            host="test-host",
            boot_time="2024-01-01T00:00:00",
            uptime_seconds=86400.0,
            status="running",
            cpu_threads=16,
            cpu_cores=8,
        )

        with (
            unittest.mock.patch.object(db, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(db, "SQLITE_SCHEMA_PATH", schema_path),
        ):
            data_collector.init_db()
            data_collector.save_host_info(host_info)

            result = data_collector.get_host_info("test-host")

            assert result is not None
            assert result.host == "test-host"

    def test_returns_none_when_not_found(self, temp_data_dir):
        """見つからない場合は None を返す"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"
        db_config.set_server_data_db_path(db_path)

        with (
            unittest.mock.patch.object(db, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(db, "SQLITE_SCHEMA_PATH", schema_path),
        ):
            data_collector.init_db()

            result = data_collector.get_host_info("nonexistent")

            assert result is None


class TestFetchHostInfoEdgeCases:
    """fetch_host_info 関数のエッジケーステスト"""

    def test_handles_no_host_in_cluster(self):
        """クラスタにホストがない場合"""
        from server_list.spec.data_collector import fetch_host_info

        mock_cluster = unittest.mock.MagicMock()
        mock_cluster.host = []

        mock_datacenter = unittest.mock.MagicMock()
        mock_datacenter.hostFolder.childEntity = [mock_cluster]

        mock_content = unittest.mock.MagicMock()
        mock_content.rootFolder.childEntity = [mock_datacenter]

        mock_si = unittest.mock.MagicMock()
        mock_si.RetrieveContent.return_value = mock_content

        result = fetch_host_info(mock_si, "esxi-host")

        assert result is None


class TestCollectorWorker:
    """_update_worker 関数のテスト"""

    def test_worker_runs_and_stops(self, temp_data_dir, sample_secret):
        """ワーカーが実行されて停止する"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"
        db_config.set_server_data_db_path(db_path)

        with (
            unittest.mock.patch.object(db, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(db, "SQLITE_SCHEMA_PATH", schema_path),
            unittest.mock.patch.object(data_collector, "load_secret", return_value=sample_secret),
            unittest.mock.patch.object(data_collector, "connect_to_esxi", return_value=None),
            unittest.mock.patch.object(data_collector, "UPDATE_INTERVAL_SEC", 0.1),
        ):
            data_collector.init_db()
            data_collector.start_collector()

            import time

            time.sleep(0.2)

            data_collector.stop_collector()


class TestUpdateCollectionStatusException:
    """update_collection_status 関数の例外テスト"""

    def test_updates_collection_status(self, temp_data_dir):
        """ステータスを更新する"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"
        db_config.set_server_data_db_path(db_path)

        with (
            unittest.mock.patch.object(db, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(db, "SQLITE_SCHEMA_PATH", schema_path),
        ):
            data_collector.init_db()
            data_collector.update_collection_status("test-host", "success")

            # 保存されていることを確認
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status FROM collection_status WHERE host = ?", ("test-host",)
            )
            row = cursor.fetchone()
            conn.close()

            assert row is not None
            assert row[0] == "success"
