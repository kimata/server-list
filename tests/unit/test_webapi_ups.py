#!/usr/bin/env python3
# ruff: noqa: S101
"""
webapi/ups.py のユニットテスト
"""

import unittest.mock

import pytest

from server_list.spec.models import UPSClient, UPSInfo


@pytest.fixture
def sample_ups_info():
    """サンプル UPS 情報"""
    return UPSInfo(
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


@pytest.fixture
def sample_ups_client():
    """サンプル UPS クライアント"""
    return UPSClient(
        ups_name="bl100t",
        host="engine",
        client_ip="192.168.1.10",
        client_hostname="server1.local",
        collected_at="2024-01-01T00:00:00",
    )


class TestUpsApi:
    """UPS API のテスト"""

    def test_get_all_ups(self, client, sample_ups_info, sample_ups_client):
        """GET /api/ups が正常に動作する"""
        with (
            unittest.mock.patch(
                "server_list.spec.data_collector.get_all_ups_info",
                return_value=[sample_ups_info],
            ),
            unittest.mock.patch(
                "server_list.spec.data_collector.get_all_ups_clients",
                return_value=[sample_ups_client],
            ),
        ):
            response = client.get("/server-list/api/ups")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        ups = data["data"][0]
        assert ups["ups_name"] == "bl100t"
        assert ups["host"] == "engine"
        assert ups["model"] == "Omron BL100T"
        assert ups["battery_charge"] == 95.0
        assert len(ups["clients"]) == 1

    def test_get_all_ups_empty(self, client):
        """UPS がない場合は空リストを返す"""
        with (
            unittest.mock.patch(
                "server_list.spec.data_collector.get_all_ups_info",
                return_value=[],
            ),
            unittest.mock.patch(
                "server_list.spec.data_collector.get_all_ups_clients",
                return_value=[],
            ),
        ):
            response = client.get("/server-list/api/ups")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"] == []

    def test_get_ups_detail_success(self, client, sample_ups_info, sample_ups_client):
        """GET /api/ups/<host>/<ups_name> が正常に動作する"""
        with (
            unittest.mock.patch(
                "server_list.spec.data_collector.get_ups_info",
                return_value=sample_ups_info,
            ),
            unittest.mock.patch(
                "server_list.spec.data_collector.get_ups_clients",
                return_value=[sample_ups_client],
            ),
        ):
            response = client.get("/server-list/api/ups/engine/bl100t")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["ups_name"] == "bl100t"
        assert data["data"]["host"] == "engine"
        assert len(data["data"]["clients"]) == 1

    def test_get_ups_detail_not_found(self, client):
        """UPS が見つからない場合に 404 を返す"""
        with unittest.mock.patch(
            "server_list.spec.data_collector.get_ups_info",
            return_value=None,
        ):
            response = client.get("/server-list/api/ups/engine/nonexistent")

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert "error" in data
