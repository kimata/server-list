#!/usr/bin/env python3
# ruff: noqa: S101
"""
data_collector.py の ESXi 関連ユニットテスト
"""

import unittest.mock
from datetime import UTC, datetime
from pathlib import Path


class TestConnectToEsxi:
    """connect_to_esxi 関数のテスト"""

    def test_successful_connection(self):
        """ESXi への接続成功"""
        from server_list.spec.data_collector import connect_to_esxi

        mock_si = unittest.mock.MagicMock()

        with (
            unittest.mock.patch("server_list.spec.data_collector.SmartConnect", return_value=mock_si),
            unittest.mock.patch("atexit.register"),
        ):
            result = connect_to_esxi("host", "user", "pass")

        assert result == mock_si

    def test_connection_failure(self):
        """ESXi への接続失敗"""
        from server_list.spec.data_collector import connect_to_esxi

        with unittest.mock.patch(
            "server_list.spec.data_collector.SmartConnect",
            side_effect=Exception("Connection failed"),
        ):
            result = connect_to_esxi("host", "user", "pass")

        assert result is None


class TestGetVmStorageSize:
    """get_vm_storage_size 関数のテスト"""

    def test_calculates_storage_size(self):
        """ストレージサイズを計算する"""
        from server_list.spec.data_collector import get_vm_storage_size

        # 共通のクラスを作成してisinstance チェックを通す
        class MockVirtualDisk:
            def __init__(self, capacity_bytes: int):
                self.capacityInBytes = capacity_bytes

        mock_disk1 = MockVirtualDisk(100 * 1024**3)  # 100 GB
        mock_disk2 = MockVirtualDisk(50 * 1024**3)  # 50 GB

        mock_vm = unittest.mock.MagicMock()
        mock_vm.config.hardware.device = [mock_disk1, mock_disk2]

        # VirtualDisk であることを判定させるためのモック
        with unittest.mock.patch(
            "server_list.spec.data_collector.vim.vm.device.VirtualDisk",
            new=MockVirtualDisk,
        ):
            result = get_vm_storage_size(mock_vm)

        assert result == 150.0

    def test_handles_exception(self):
        """例外時は 0 を返す"""
        from server_list.spec.data_collector import get_vm_storage_size

        mock_vm = unittest.mock.MagicMock()
        mock_vm.config.hardware.device = None  # AttributeError を発生させる

        result = get_vm_storage_size(mock_vm)

        assert result == 0.0


class TestFetchVmData:
    """fetch_vm_data 関数のテスト"""

    def test_fetches_vm_data(self):
        """VMデータを取得する"""
        from server_list.spec.data_collector import fetch_vm_data

        mock_vm = unittest.mock.MagicMock()
        mock_vm.name = "test-vm"
        mock_vm.config.hardware.numCPU = 4
        mock_vm.config.hardware.memoryMB = 8192
        mock_vm.runtime.powerState = "poweredOn"

        mock_view = unittest.mock.MagicMock()
        mock_view.view = [mock_vm]

        mock_content = unittest.mock.MagicMock()
        mock_content.viewManager.CreateContainerView.return_value = mock_view

        mock_si = unittest.mock.MagicMock()
        mock_si.RetrieveContent.return_value = mock_content

        with unittest.mock.patch(
            "server_list.spec.data_collector.get_vm_storage_size",
            return_value=100.0,
        ):
            result = fetch_vm_data(mock_si, "esxi-host")

        assert len(result) == 1
        assert result[0]["vm_name"] == "test-vm"
        assert result[0]["cpu_count"] == 4
        assert result[0]["ram_mb"] == 8192
        assert result[0]["esxi_host"] == "esxi-host"

    def test_handles_vm_error(self):
        """VM取得エラーを処理する"""
        from server_list.spec.data_collector import fetch_vm_data

        mock_vm = unittest.mock.MagicMock()
        mock_vm.name = "error-vm"
        mock_vm.config = None  # エラーを発生させる

        mock_view = unittest.mock.MagicMock()
        mock_view.view = [mock_vm]

        mock_content = unittest.mock.MagicMock()
        mock_content.viewManager.CreateContainerView.return_value = mock_view

        mock_si = unittest.mock.MagicMock()
        mock_si.RetrieveContent.return_value = mock_content

        result = fetch_vm_data(mock_si, "esxi-host")

        # エラーが発生してもリストは返る（空かもしれない）
        assert isinstance(result, list)


class TestFetchHostInfo:
    """fetch_host_info 関数のテスト"""

    def test_fetches_host_info(self):
        """ホスト情報を取得する"""
        from server_list.spec.data_collector import fetch_host_info

        boot_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)

        mock_host = unittest.mock.MagicMock()
        mock_host.runtime.bootTime = boot_time
        mock_host.hardware.cpuInfo.numCpuThreads = 16
        mock_host.hardware.cpuInfo.numCpuCores = 8

        mock_cluster = unittest.mock.MagicMock()
        mock_cluster.host = [mock_host]

        mock_datacenter = unittest.mock.MagicMock()
        mock_datacenter.hostFolder.childEntity = [mock_cluster]

        mock_content = unittest.mock.MagicMock()
        mock_content.rootFolder.childEntity = [mock_datacenter]

        mock_si = unittest.mock.MagicMock()
        mock_si.RetrieveContent.return_value = mock_content

        result = fetch_host_info(mock_si, "esxi-host")

        assert result is not None
        assert result["host"] == "esxi-host"
        assert result["status"] == "running"
        assert result["cpu_threads"] == 16
        assert result["cpu_cores"] == 8

    def test_handles_exception(self):
        """例外を処理する"""
        from server_list.spec.data_collector import fetch_host_info

        mock_si = unittest.mock.MagicMock()
        mock_si.RetrieveContent.side_effect = Exception("Error")

        result = fetch_host_info(mock_si, "esxi-host")

        assert result is None


class TestCollectAllData:
    """collect_all_data 関数のテスト"""

    def test_collects_data_from_hosts(self, temp_data_dir, sample_secret):
        """全ホストからデータを収集する"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"

        mock_si = unittest.mock.MagicMock()
        vm_data = [
            {
                "esxi_host": "test",
                "vm_name": "vm1",
                "cpu_count": 2,
                "ram_mb": 4096,
                "storage_gb": 50.0,
                "power_state": "on",
            }
        ]
        host_info = {
            "host": "test",
            "boot_time": "2024-01-01",
            "uptime_seconds": 86400,
            "status": "running",
            "cpu_threads": 8,
            "cpu_cores": 4,
        }

        with (
            unittest.mock.patch.object(data_collector, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(data_collector, "DB_PATH", db_path),
            unittest.mock.patch.object(data_collector, "SQLITE_SCHEMA_PATH", schema_path),
            unittest.mock.patch.object(data_collector, "load_secret", return_value=sample_secret),
            unittest.mock.patch.object(data_collector, "connect_to_esxi", return_value=mock_si),
            unittest.mock.patch.object(data_collector, "fetch_vm_data", return_value=vm_data),
            unittest.mock.patch.object(data_collector, "fetch_host_info", return_value=host_info),
            unittest.mock.patch.object(data_collector, "Disconnect"),
            unittest.mock.patch("my_lib.webapp.event.notify_event"),
        ):
            data_collector.init_db()
            data_collector.collect_all_data()

    def test_handles_no_credentials(self):
        """認証情報がない場合"""
        from server_list.spec import data_collector

        with (
            unittest.mock.patch.object(data_collector, "load_secret", return_value={}),
            # Prometheus 関連の収集もモックする（DBアクセスを避ける）
            unittest.mock.patch.object(data_collector, "collect_ilo_power_data"),
            unittest.mock.patch.object(data_collector, "collect_prometheus_uptime_data", return_value=False),
            unittest.mock.patch.object(data_collector, "collect_prometheus_zfs_data", return_value=False),
            unittest.mock.patch.object(data_collector, "collect_prometheus_mount_data", return_value=False),
        ):
            # 例外が発生しないことを確認
            data_collector.collect_all_data()

    def test_handles_connection_failure(self, temp_data_dir, sample_secret):
        """接続失敗を処理する"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"

        with (
            unittest.mock.patch.object(data_collector, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(data_collector, "DB_PATH", db_path),
            unittest.mock.patch.object(data_collector, "SQLITE_SCHEMA_PATH", schema_path),
            unittest.mock.patch.object(data_collector, "load_secret", return_value=sample_secret),
            unittest.mock.patch.object(data_collector, "connect_to_esxi", return_value=None),
        ):
            data_collector.init_db()
            data_collector.collect_all_data()


class TestUpdateCollectionStatus:
    """update_collection_status 関数のテスト"""

    def test_updates_status(self, temp_data_dir):
        """ステータスを更新する"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"

        with (
            unittest.mock.patch.object(data_collector, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(data_collector, "DB_PATH", db_path),
            unittest.mock.patch.object(data_collector, "SQLITE_SCHEMA_PATH", schema_path),
        ):
            data_collector.init_db()
            data_collector.update_collection_status("test-host", "success")

            # ステータスが保存されていることを確認
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM collection_status WHERE host = ?", ("test-host",))
            row = cursor.fetchone()
            conn.close()

            assert row is not None
            assert row[0] == "success"


class TestLoadConfig:
    """load_config 関数のテスト"""

    def test_returns_empty_when_file_not_exists(self, temp_data_dir):
        """ファイルが存在しない場合は空の辞書を返す"""
        from server_list.spec import data_collector

        with unittest.mock.patch.object(data_collector, "BASE_DIR", temp_data_dir):
            result = data_collector.load_config()

        assert result == {}
