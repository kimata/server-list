#!/usr/bin/env python3
# ruff: noqa: S101
"""
webapi/uptime.py のユニットテスト
"""

import unittest.mock


class TestUptimeApi:
    """ホスト情報 API のテスト"""

    def test_get_all_uptime(self, client, sample_uptime_info):
        """GET /api/uptime が正常に動作する"""
        uptime_data = {
            "test-server-1.example.com": {
                "boot_time": sample_uptime_info["boot_time"],
                "uptime_seconds": sample_uptime_info["uptime_seconds"],
                "status": sample_uptime_info["status"],
                "cpu_threads": sample_uptime_info["cpu_threads"],
                "cpu_cores": sample_uptime_info["cpu_cores"],
                "collected_at": sample_uptime_info["collected_at"],
            }
        }

        with unittest.mock.patch(
            "server_list.spec.webapi.uptime.get_all_host_info",
            return_value=uptime_data,
        ):
            response = client.get("/server-list/api/uptime")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "test-server-1.example.com" in data["data"]

    def test_get_host_uptime_success(self, client, sample_uptime_info):
        """GET /api/uptime/<host> が正常に動作する"""
        with unittest.mock.patch(
            "server_list.spec.webapi.uptime.get_host_info",
            return_value=sample_uptime_info,
        ):
            response = client.get("/server-list/api/uptime/test-server-1.example.com")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["host"] == "test-server-1.example.com"
        assert data["data"]["status"] == "running"

    def test_get_host_uptime_not_found(self, client):
        """ホストが見つからない場合に404を返す"""
        with unittest.mock.patch(
            "server_list.spec.webapi.uptime.get_host_info",
            return_value=None,
        ):
            response = client.get("/server-list/api/uptime/nonexistent.example.com")

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert "error" in data
