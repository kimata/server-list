#!/usr/bin/env python3
# ruff: noqa: S101
"""
webapi/config.py のユニットテスト
"""

import unittest.mock


class TestConfigApi:
    """config API のテスト"""

    def test_get_config_success(self, client):
        """GET /api/config が正常に動作する"""
        # flask_app fixture で CONFIG が設定済み
        with unittest.mock.patch(
            "server_list.spec.data_collector.get_all_vm_info_for_host",
            return_value=[],
        ):
            response = client.get("/server-list/api/config")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "machine" in data["data"]
        assert len(data["data"]["machine"]) == 1
        assert data["data"]["machine"][0]["name"] == "test-server-1.example.com"

    def test_get_config_not_available(self, flask_app):
        """設定が取得できない場合に503を返す"""
        # CONFIG を一時的に None に設定
        original_config = flask_app.config.get("CONFIG")
        flask_app.config["CONFIG"] = None
        try:
            with flask_app.test_client() as client:
                response = client.get("/server-list/api/config")

            assert response.status_code == 503
            data = response.get_json()
            assert data["success"] is False
            assert "error" in data
        finally:
            flask_app.config["CONFIG"] = original_config


class TestIsEsxiHost:
    """is_esxi_host 関数のテスト"""

    def test_esxi_host_detected(self):
        """ESXi ホストが正しく検出される"""
        from server_list.spec.webapi.config import is_esxi_host

        machine = {"os": "ESXi 8.0 Update 3"}
        assert is_esxi_host(machine) is True

    def test_esxi_host_case_insensitive(self):
        """ESXi 検出が大文字小文字を区別しない"""
        from server_list.spec.webapi.config import is_esxi_host

        machine = {"os": "ESXI 7.0"}
        assert is_esxi_host(machine) is True

    def test_non_esxi_host(self):
        """非ESXi ホストが正しく検出される"""
        from server_list.spec.webapi.config import is_esxi_host

        machine = {"os": "Ubuntu 22.04"}
        assert is_esxi_host(machine) is False

    def test_missing_os_field(self):
        """OS フィールドがない場合"""
        from server_list.spec.webapi.config import is_esxi_host

        machine = {"name": "test"}
        assert is_esxi_host(machine) is False


class TestEnrichConfigWithVmData:
    """enrich_config_with_vm_data 関数のテスト"""

    def test_enriches_esxi_host_with_vms(self):
        """ESXi ホストにVM情報が追加される"""
        from server_list.spec.models import CollectionStatus, VMInfo
        from server_list.spec.webapi.config import enrich_config_with_vm_data

        config = {
            "machine": [
                {
                    "name": "esxi-host.example.com",
                    "os": "ESXi 8.0",
                }
            ]
        }
        vm_list = [
            VMInfo(
                esxi_host="esxi-host.example.com",
                vm_name="vm1",
                cpu_count=2,
                ram_mb=4096,
                storage_gb=50.0,
                power_state="poweredOn",
            ),
            VMInfo(
                esxi_host="esxi-host.example.com",
                vm_name="vm2",
                cpu_count=4,
                ram_mb=8192,
                storage_gb=100.0,
                power_state="poweredOff",
            ),
        ]

        with (
            unittest.mock.patch(
                "server_list.spec.data_collector.get_all_vm_info",
                return_value={"esxi-host.example.com": vm_list},
            ),
            unittest.mock.patch(
                "server_list.spec.data_collector.get_all_collection_status",
                return_value={
                    "esxi-host.example.com": CollectionStatus(
                        host="esxi-host.example.com",
                        last_fetch="2024-01-01T00:00:00",
                        status="success",
                    )
                },
            ),
        ):
            result = enrich_config_with_vm_data(config)

        assert "vm" in result["machine"][0]
        assert len(result["machine"][0]["vm"]) == 2
        assert result["machine"][0]["vm"][0]["name"] == "vm1"
        assert result["machine"][0]["vm"][0]["power_state"] == "poweredOn"

    def test_enriches_esxi_host_with_unknown_power_state_when_unreachable(self):
        """ESXi ホストに到達できない場合、power_state が unknown になる"""
        from server_list.spec.models import CollectionStatus, VMInfo
        from server_list.spec.webapi.config import enrich_config_with_vm_data

        config = {
            "machine": [
                {
                    "name": "esxi-host.example.com",
                    "os": "ESXi 8.0",
                }
            ]
        }
        vm_list = [
            VMInfo(
                esxi_host="esxi-host.example.com",
                vm_name="vm1",
                cpu_count=2,
                ram_mb=4096,
                storage_gb=50.0,
                power_state="poweredOn",
            ),
        ]

        with (
            unittest.mock.patch(
                "server_list.spec.data_collector.get_all_vm_info",
                return_value={"esxi-host.example.com": vm_list},
            ),
            unittest.mock.patch(
                "server_list.spec.data_collector.get_all_collection_status",
                return_value={
                    "esxi-host.example.com": CollectionStatus(
                        host="esxi-host.example.com",
                        last_fetch="2024-01-01T00:00:00",
                        status="failed",  # ホスト到達不可
                    )
                },
            ),
        ):
            result = enrich_config_with_vm_data(config)

        assert "vm" in result["machine"][0]
        assert result["machine"][0]["vm"][0]["power_state"] == "unknown"

    def test_no_enrichment_for_non_esxi(self):
        """非ESXi ホストはそのまま"""
        from server_list.spec.webapi.config import enrich_config_with_vm_data

        config = {
            "machine": [
                {
                    "name": "ubuntu-host.example.com",
                    "os": "Ubuntu 22.04",
                }
            ]
        }

        result = enrich_config_with_vm_data(config)

        assert "vm" not in result["machine"][0]

    def test_empty_config(self):
        """空の設定でも動作する"""
        from server_list.spec.webapi.config import enrich_config_with_vm_data

        config = {}
        result = enrich_config_with_vm_data(config)

        assert result == {}
