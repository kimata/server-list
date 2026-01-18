#!/usr/bin/env python3
# ruff: noqa: S101
"""
data_collector.py の UPS 関連ユニットテスト
"""

import unittest.mock
from pathlib import Path

from server_list.spec import db, db_config
from server_list.spec.models import UPSClient, UPSInfo


class TestSaveUpsInfo:
    """save_ups_info 関数のテスト"""

    def test_save_ups_info(self, temp_data_dir):
        """UPS 情報を保存する"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"
        db_config.set_server_data_db_path(db_path)

        ups_info = UPSInfo(
            ups_name="bl100t",
            host="engine",
            model="Omron BL100T",
            battery_charge=95.0,
            battery_runtime=1800,
            ups_load=30.0,
            ups_status="OL",
            ups_temperature=25.0,
            input_voltage=100.0,
            output_voltage=100.0,
            collected_at="2024-01-01T00:00:00",
        )

        with unittest.mock.patch.object(db, "SQLITE_SCHEMA_PATH", schema_path):
            data_collector.init_db()
            data_collector.save_ups_info([ups_info])

            # 保存されたことを確認
            result = data_collector.get_ups_info("bl100t", "engine")

            assert result is not None
            assert result.ups_name == "bl100t"
            assert result.host == "engine"
            assert result.model == "Omron BL100T"
            assert result.battery_charge == 95.0

    def test_save_ups_info_empty_list(self, temp_data_dir):
        """空リストを保存してもエラーにならない"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"
        db_config.set_server_data_db_path(db_path)

        with unittest.mock.patch.object(db, "SQLITE_SCHEMA_PATH", schema_path):
            data_collector.init_db()
            # エラーが発生しないことを確認
            data_collector.save_ups_info([])


class TestSaveUpsClients:
    """save_ups_clients 関数のテスト"""

    def test_save_ups_clients(self, temp_data_dir):
        """UPS クライアント情報を保存する"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"
        db_config.set_server_data_db_path(db_path)

        ups_client = UPSClient(
            ups_name="bl100t",
            host="engine",
            client_ip="192.168.1.10",
            client_hostname="server1.local",
            collected_at="2024-01-01T00:00:00",
        )

        with unittest.mock.patch.object(db, "SQLITE_SCHEMA_PATH", schema_path):
            data_collector.init_db()
            data_collector.save_ups_clients([ups_client])

            # 保存されたことを確認
            result = data_collector.get_ups_clients("bl100t", "engine")

            assert len(result) == 1
            assert result[0].client_ip == "192.168.1.10"
            assert result[0].client_hostname == "server1.local"


class TestGetUpsInfo:
    """get_ups_info 関数のテスト"""

    def test_get_ups_info_exists(self, temp_data_dir):
        """存在する UPS 情報を取得する"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"
        db_config.set_server_data_db_path(db_path)

        ups_info = UPSInfo(
            ups_name="bl100t",
            host="engine",
            model="Omron BL100T",
            battery_charge=95.0,
            collected_at="2024-01-01T00:00:00",
        )

        with unittest.mock.patch.object(db, "SQLITE_SCHEMA_PATH", schema_path):
            data_collector.init_db()
            data_collector.save_ups_info([ups_info])

            result = data_collector.get_ups_info("bl100t", "engine")

            assert result is not None
            assert result.ups_name == "bl100t"

    def test_get_ups_info_not_exists(self, temp_data_dir):
        """存在しない UPS 情報を取得すると None を返す"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"
        db_config.set_server_data_db_path(db_path)

        with unittest.mock.patch.object(db, "SQLITE_SCHEMA_PATH", schema_path):
            data_collector.init_db()
            result = data_collector.get_ups_info("engine", "nonexistent")

        assert result is None


class TestGetAllUpsInfo:
    """get_all_ups_info 関数のテスト"""

    def test_get_all_ups_info(self, temp_data_dir):
        """全 UPS 情報を取得する"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"
        db_config.set_server_data_db_path(db_path)

        ups_info_1 = UPSInfo(
            ups_name="bl100t",
            host="engine",
            model="Omron BL100T",
            collected_at="2024-01-01T00:00:00",
        )
        ups_info_2 = UPSInfo(
            ups_name="smart-ups",
            host="server1",
            model="APC Smart-UPS",
            collected_at="2024-01-01T00:00:00",
        )

        with unittest.mock.patch.object(db, "SQLITE_SCHEMA_PATH", schema_path):
            data_collector.init_db()
            data_collector.save_ups_info([ups_info_1, ups_info_2])
            result = data_collector.get_all_ups_info()

        assert len(result) == 2

    def test_get_all_ups_info_empty(self, temp_data_dir):
        """UPS がない場合は空リストを返す"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"
        db_config.set_server_data_db_path(db_path)

        with unittest.mock.patch.object(db, "SQLITE_SCHEMA_PATH", schema_path):
            data_collector.init_db()
            result = data_collector.get_all_ups_info()

        assert result == []


class TestGetUpsClients:
    """get_ups_clients 関数のテスト"""

    def test_get_ups_clients(self, temp_data_dir):
        """特定 UPS のクライアントを取得する"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"
        db_config.set_server_data_db_path(db_path)

        ups_client_1 = UPSClient(
            ups_name="bl100t",
            host="engine",
            client_ip="192.168.1.10",
            collected_at="2024-01-01T00:00:00",
        )
        ups_client_2 = UPSClient(
            ups_name="bl100t",
            host="engine",
            client_ip="192.168.1.20",
            collected_at="2024-01-01T00:00:00",
        )
        ups_client_other = UPSClient(
            ups_name="other-ups",
            host="server1",
            client_ip="192.168.1.30",
            collected_at="2024-01-01T00:00:00",
        )

        with unittest.mock.patch.object(db, "SQLITE_SCHEMA_PATH", schema_path):
            data_collector.init_db()
            data_collector.save_ups_clients([ups_client_1, ups_client_2, ups_client_other])

            result = data_collector.get_ups_clients("bl100t", "engine")

            assert len(result) == 2


class TestGetAllUpsClients:
    """get_all_ups_clients 関数のテスト"""

    def test_get_all_ups_clients(self, temp_data_dir):
        """全クライアントを取得する"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"
        db_config.set_server_data_db_path(db_path)

        ups_client_1 = UPSClient(
            ups_name="bl100t",
            host="engine",
            client_ip="192.168.1.10",
            collected_at="2024-01-01T00:00:00",
        )
        ups_client_2 = UPSClient(
            ups_name="other-ups",
            host="server1",
            client_ip="192.168.1.20",
            collected_at="2024-01-01T00:00:00",
        )

        with unittest.mock.patch.object(db, "SQLITE_SCHEMA_PATH", schema_path):
            data_collector.init_db()
            data_collector.save_ups_clients([ups_client_1, ups_client_2])
            result = data_collector.get_all_ups_clients()

        assert len(result) == 2


class TestCollectUpsData:
    """collect_ups_data 関数のテスト"""

    def test_collect_ups_data_success(self, temp_data_dir):
        """UPS データ収集成功"""
        from server_list.spec import data_collector, ups_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"
        db_config.set_server_data_db_path(db_path)

        mock_ups_info = UPSInfo(
            ups_name="bl100t",
            host="engine",
            model="Omron BL100T",
            battery_charge=95.0,
            collected_at="2024-01-01T00:00:00",
        )
        mock_ups_client = UPSClient(
            ups_name="bl100t",
            host="engine",
            client_ip="192.168.1.10",
            collected_at="2024-01-01T00:00:00",
        )

        mock_config = {
            "ups": [{"host": "engine"}]
        }

        with (
            unittest.mock.patch.object(db, "SQLITE_SCHEMA_PATH", schema_path),
            unittest.mock.patch.object(
                data_collector,
                "load_config",
                return_value=mock_config,
            ),
            unittest.mock.patch.object(
                ups_collector,
                "fetch_all_ups_from_host",
                return_value=([mock_ups_info], [mock_ups_client]),
            ),
        ):
            data_collector.init_db()
            result = data_collector.collect_ups_data()

        assert result is True

        # データが保存されていることを確認
        saved_info = data_collector.get_all_ups_info()
        assert len(saved_info) == 1
        assert saved_info[0].ups_name == "bl100t"

    def test_collect_ups_data_no_config(self, temp_data_dir):
        """UPS 設定がない場合"""
        from server_list.spec import data_collector

        db_path = temp_data_dir / "test.db"
        schema_path = Path(__file__).parent.parent.parent / "schema" / "sqlite.schema"
        db_config.set_server_data_db_path(db_path)

        mock_config = {}  # ups セクションなし

        with (
            unittest.mock.patch.object(db, "SQLITE_SCHEMA_PATH", schema_path),
            unittest.mock.patch.object(
                data_collector,
                "load_config",
                return_value=mock_config,
            ),
        ):
            data_collector.init_db()
            result = data_collector.collect_ups_data()

        assert result is False
