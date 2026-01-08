#!/usr/bin/env python3
# ruff: noqa: S101
"""
webapi/vm.py のユニットテスト
"""

import unittest.mock


class TestVmInfoApi:
    """VM情報 API のテスト"""

    def test_get_vm_info_success(self, client, sample_vm_info):
        """GET /api/vm/info が正常に動作する"""
        with unittest.mock.patch(
            "server_list.spec.webapi.vm.get_vm_info",
            return_value=sample_vm_info,
        ):
            response = client.get("/server-list/api/vm/info?vm_name=test-vm-1")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["vm_name"] == "test-vm-1"
        assert data["data"]["cpu_count"] == 4

    def test_get_vm_info_with_esxi_host(self, client, sample_vm_info):
        """esxi_host パラメータ付きで正常に動作する"""
        with unittest.mock.patch(
            "server_list.spec.webapi.vm.get_vm_info",
            return_value=sample_vm_info,
        ) as mock_get:
            response = client.get(
                "/server-list/api/vm/info?vm_name=test-vm-1&esxi_host=test-server-1.example.com"
            )

        assert response.status_code == 200
        mock_get.assert_called_once_with("test-vm-1", "test-server-1.example.com")

    def test_get_vm_info_missing_param(self, client):
        """vm_name パラメータがない場合に400を返す"""
        response = client.get("/server-list/api/vm/info")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_get_vm_info_not_found(self, client):
        """VMが見つからない場合に404を返す"""
        with unittest.mock.patch(
            "server_list.spec.webapi.vm.get_vm_info",
            return_value=None,
        ):
            response = client.get("/server-list/api/vm/info?vm_name=nonexistent")

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False


class TestVmInfoBatchApi:
    """VM情報 バッチ API のテスト"""

    def test_batch_success(self, client, sample_vm_info):
        """POST /api/vm/info/batch が正常に動作する"""
        with unittest.mock.patch(
            "server_list.spec.webapi.vm.get_vm_info",
            return_value=sample_vm_info,
        ):
            response = client.post(
                "/server-list/api/vm/info/batch",
                json={"vms": ["test-vm-1"]},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "test-vm-1" in data["results"]

    def test_batch_missing_vms(self, client):
        """vms パラメータがない場合に400を返す"""
        response = client.post("/server-list/api/vm/info/batch", json={})

        assert response.status_code == 400


class TestVmsForHostApi:
    """ホスト別VM一覧 API のテスト"""

    def test_get_vms_for_host(self, client):
        """GET /api/vm/host/<host> が正常に動作する"""
        vm_list = [
            {"vm_name": "vm1", "cpu_count": 2},
            {"vm_name": "vm2", "cpu_count": 4},
        ]

        with unittest.mock.patch(
            "server_list.spec.webapi.vm.get_all_vm_info_for_host",
            return_value=vm_list,
        ):
            response = client.get("/server-list/api/vm/host/test-server-1.example.com")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["esxi_host"] == "test-server-1.example.com"
        assert len(data["vms"]) == 2
