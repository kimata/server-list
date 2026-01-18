#!/usr/bin/env python3
# ruff: noqa: S101
"""
ups_collector.py のユニットテスト
"""

import unittest.mock

import server_list.spec.ups_collector as ups_collector


class TestParseListUps:
    """LIST UPS レスポンスのパースをテスト"""

    def test_parse_single_ups(self):
        """単一 UPS のパース"""
        lines = [
            "BEGIN LIST UPS",
            'UPS bl100t "Omron BL100T"',
            "END LIST UPS",
        ]
        result = ups_collector._parse_list_ups(lines)
        assert len(result) == 1
        assert result[0] == ("bl100t", "Omron BL100T")

    def test_parse_multiple_ups(self):
        """複数 UPS のパース"""
        lines = [
            "BEGIN LIST UPS",
            'UPS ups1 "APC Smart-UPS"',
            'UPS ups2 "CyberPower"',
            "END LIST UPS",
        ]
        result = ups_collector._parse_list_ups(lines)
        assert len(result) == 2
        assert result[0] == ("ups1", "APC Smart-UPS")
        assert result[1] == ("ups2", "CyberPower")

    def test_parse_empty_response(self):
        """空のレスポンスを正しく処理"""
        lines = [
            "BEGIN LIST UPS",
            "END LIST UPS",
        ]
        result = ups_collector._parse_list_ups(lines)
        assert len(result) == 0


class TestParseListVar:
    """LIST VAR レスポンスのパースをテスト"""

    def test_parse_variables(self):
        """変数リストのパース"""
        lines = [
            "BEGIN LIST VAR bl100t",
            'VAR bl100t ups.model "BL100T"',
            'VAR bl100t battery.charge "100"',
            'VAR bl100t battery.runtime "1800"',
            'VAR bl100t ups.status "OL"',
            "END LIST VAR bl100t",
        ]
        result = ups_collector._parse_list_var(lines)
        assert result["ups.model"] == "BL100T"
        assert result["battery.charge"] == "100"
        assert result["battery.runtime"] == "1800"
        assert result["ups.status"] == "OL"

    def test_parse_empty_variables(self):
        """空の変数リスト"""
        lines = [
            "BEGIN LIST VAR bl100t",
            "END LIST VAR bl100t",
        ]
        result = ups_collector._parse_list_var(lines)
        assert len(result) == 0


class TestParseListClient:
    """LIST CLIENT レスポンスのパースをテスト"""

    def test_parse_clients(self):
        """クライアントリストのパース"""
        lines = [
            "BEGIN LIST CLIENT bl100t",
            "CLIENT bl100t 192.168.1.10",
            "CLIENT bl100t 192.168.1.20",
            "END LIST CLIENT bl100t",
        ]
        result = ups_collector._parse_list_client(lines)
        assert len(result) == 2
        assert "192.168.1.10" in result
        assert "192.168.1.20" in result

    def test_parse_no_clients(self):
        """クライアントなし"""
        lines = [
            "BEGIN LIST CLIENT bl100t",
            "END LIST CLIENT bl100t",
        ]
        result = ups_collector._parse_list_client(lines)
        assert len(result) == 0


class TestSafeConversions:
    """安全な型変換のテスト"""

    def test_safe_float_valid(self):
        """有効な float 変換"""
        assert ups_collector._safe_float("100.5") == 100.5
        assert ups_collector._safe_float("0") == 0.0

    def test_safe_float_none(self):
        """None の処理"""
        assert ups_collector._safe_float(None) is None

    def test_safe_float_invalid(self):
        """無効な値の処理"""
        assert ups_collector._safe_float("invalid") is None
        assert ups_collector._safe_float("") is None

    def test_safe_int_valid(self):
        """有効な int 変換"""
        assert ups_collector._safe_int("100") == 100
        assert ups_collector._safe_int("100.5") == 100

    def test_safe_int_none(self):
        """None の処理"""
        assert ups_collector._safe_int(None) is None

    def test_safe_int_invalid(self):
        """無効な値の処理"""
        assert ups_collector._safe_int("invalid") is None


class TestConnectToNut:
    """NUT サーバー接続のテスト"""

    def test_connect_success(self):
        """接続成功"""
        mock_socket = unittest.mock.MagicMock()
        with unittest.mock.patch("socket.socket", return_value=mock_socket):
            result = ups_collector.connect_to_nut("localhost", 3493)
            assert result is mock_socket
            mock_socket.connect.assert_called_once_with(("localhost", 3493))

    def test_connect_failure(self):
        """接続失敗"""
        with unittest.mock.patch("socket.socket") as mock_socket_class:
            mock_socket = mock_socket_class.return_value
            mock_socket.connect.side_effect = OSError("Connection refused")
            result = ups_collector.connect_to_nut("localhost", 3493)
            assert result is None


class TestFetchUpsInfo:
    """UPS 情報取得のテスト"""

    def test_fetch_ups_info_success(self):
        """UPS 情報取得成功"""
        mock_socket = unittest.mock.MagicMock()
        mock_socket.recv.side_effect = [
            b"BEGIN LIST VAR bl100t\n"
            b'VAR bl100t ups.model "BL100T"\n'
            b'VAR bl100t battery.charge "95"\n'
            b'VAR bl100t battery.runtime "1800"\n'
            b'VAR bl100t ups.load "30"\n'
            b'VAR bl100t ups.status "OL"\n'
            b"END LIST VAR bl100t\n",
        ]

        with unittest.mock.patch(
            "server_list.spec.ups_collector.connect_to_nut",
            return_value=mock_socket,
        ):
            result = ups_collector.fetch_ups_info("localhost", "bl100t")

        assert result is not None
        assert result.ups_name == "bl100t"
        assert result.host == "localhost"
        assert result.model == "BL100T"
        assert result.battery_charge == 95.0
        assert result.battery_runtime == 1800
        assert result.ups_load == 30.0
        assert result.ups_status == "OL"

    def test_fetch_ups_info_connection_failed(self):
        """接続失敗時は None を返す"""
        with unittest.mock.patch(
            "server_list.spec.ups_collector.connect_to_nut",
            return_value=None,
        ):
            result = ups_collector.fetch_ups_info("localhost", "bl100t")
            assert result is None
