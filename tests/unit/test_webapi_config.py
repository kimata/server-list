#!/usr/bin/env python3
# ruff: noqa: S101
"""
webapi/config.py のユニットテスト
"""

import unittest.mock


class TestConfigApi:
    """config API のテスト"""

    def test_get_config_success(self, client, sample_config):
        """GET /api/config が正常に動作する"""
        with (
            unittest.mock.patch(
                "server_list.spec.webapi.config.get_config",
                return_value=sample_config,
            ),
            unittest.mock.patch(
                "server_list.spec.webapi.config.get_all_vm_info_for_host",
                return_value=[],
            ),
        ):
            response = client.get("/server-list/api/config")

        assert response.status_code == 200
        data = response.get_json()
        assert "machine" in data
        assert len(data["machine"]) == 1
        assert data["machine"][0]["name"] == "test-server-1.example.com"

    def test_get_config_not_available(self, client):
        """設定が取得できない場合に503を返す"""
        with unittest.mock.patch(
            "server_list.spec.webapi.config.get_config",
            return_value=None,
        ):
            response = client.get("/server-list/api/config")

        assert response.status_code == 503
        data = response.get_json()
        assert "error" in data


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
            {"vm_name": "vm1"},
            {"vm_name": "vm2"},
        ]

        with unittest.mock.patch(
            "server_list.spec.webapi.config.get_all_vm_info_for_host",
            return_value=vm_list,
        ):
            result = enrich_config_with_vm_data(config)

        assert "vm" in result["machine"][0]
        assert len(result["machine"][0]["vm"]) == 2
        assert result["machine"][0]["vm"][0]["name"] == "vm1"

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
