#!/usr/bin/env python3
# ruff: noqa: S101
"""
webapi/storage.py のユニットテスト
"""

import unittest.mock

import server_list.spec.models as models


class TestStorageZfsApi:
    """ZFS ストレージ API のテスト"""

    def test_get_host_zfs_pools_success(self, client):
        """GET /api/storage/zfs/<host> が正常に動作する"""
        sample_pool = models.ZfsPoolInfo(
            pool_name="rpool",
            size_bytes=1000000000000,
            allocated_bytes=500000000000,
            free_bytes=500000000000,
            health="ONLINE",
            collected_at="2024-01-01T00:00:00",
        )

        with unittest.mock.patch(
            "server_list.spec.data_collector.get_zfs_pool_info",
            return_value=[sample_pool],
        ):
            response = client.get("/server-list/api/storage/zfs/test-server.example.com")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["pool_name"] == "rpool"
        assert data["data"][0]["health"] == "ONLINE"

    def test_get_host_zfs_pools_not_found(self, client):
        """ZFSデータが見つからない場合にエラーを返す"""
        with unittest.mock.patch(
            "server_list.spec.data_collector.get_zfs_pool_info",
            return_value=[],
        ):
            response = client.get("/server-list/api/storage/zfs/nonexistent.example.com")

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert "error" in data


class TestStorageMountApi:
    """マウントポイント API のテスト"""

    def test_get_host_mounts_success(self, client):
        """GET /api/storage/mount/<host> が正常に動作する"""
        sample_mount = models.MountInfo(
            mountpoint="/data",
            size_bytes=2000000000000,
            avail_bytes=1000000000000,
            used_bytes=1000000000000,
            collected_at="2024-01-01T00:00:00",
        )

        with unittest.mock.patch(
            "server_list.spec.data_collector.get_mount_info",
            return_value=[sample_mount],
        ):
            response = client.get("/server-list/api/storage/mount/test-server.example.com")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["mountpoint"] == "/data"

    def test_get_host_mounts_not_found(self, client):
        """マウントデータが見つからない場合にエラーを返す"""
        with unittest.mock.patch(
            "server_list.spec.data_collector.get_mount_info",
            return_value=[],
        ):
            response = client.get("/server-list/api/storage/mount/nonexistent.example.com")

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert "error" in data


class TestStorageBatchApi:
    """ストレージバッチ API のテスト"""

    def test_batch_zfs_only(self, client):
        """POST /api/storage/batch で ZFS のみ取得"""
        sample_pool = models.ZfsPoolInfo(
            pool_name="rpool",
            size_bytes=1000000000000,
            allocated_bytes=500000000000,
            free_bytes=500000000000,
            health="ONLINE",
            collected_at="2024-01-01T00:00:00",
        )

        with unittest.mock.patch(
            "server_list.spec.data_collector.get_zfs_pool_info",
            return_value=[sample_pool],
        ):
            response = client.post(
                "/server-list/api/storage/batch",
                json={"zfs_hosts": ["server1.example.com", "server2.example.com"]},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "server1.example.com" in data["data"]["zfs"]
        assert "server2.example.com" in data["data"]["zfs"]
        assert data["data"]["mount"] == {}

    def test_batch_mount_only(self, client):
        """POST /api/storage/batch でマウントのみ取得"""
        sample_mount = models.MountInfo(
            mountpoint="/data",
            size_bytes=2000000000000,
            avail_bytes=1000000000000,
            used_bytes=1000000000000,
            collected_at="2024-01-01T00:00:00",
        )

        with unittest.mock.patch(
            "server_list.spec.data_collector.get_mount_info",
            return_value=[sample_mount],
        ):
            response = client.post(
                "/server-list/api/storage/batch",
                json={"mount_hosts": ["server1.example.com"]},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "server1.example.com" in data["data"]["mount"]
        assert data["data"]["zfs"] == {}

    def test_batch_combined(self, client):
        """POST /api/storage/batch で ZFS とマウント両方取得"""
        sample_pool = models.ZfsPoolInfo(
            pool_name="rpool",
            size_bytes=1000000000000,
            allocated_bytes=500000000000,
            free_bytes=500000000000,
            health="ONLINE",
            collected_at="2024-01-01T00:00:00",
        )
        sample_mount = models.MountInfo(
            mountpoint="/data",
            size_bytes=2000000000000,
            avail_bytes=1000000000000,
            used_bytes=1000000000000,
            collected_at="2024-01-01T00:00:00",
        )

        with (
            unittest.mock.patch(
                "server_list.spec.data_collector.get_zfs_pool_info",
                return_value=[sample_pool],
            ),
            unittest.mock.patch(
                "server_list.spec.data_collector.get_mount_info",
                return_value=[sample_mount],
            ),
        ):
            response = client.post(
                "/server-list/api/storage/batch",
                json={
                    "zfs_hosts": ["zfs-server.example.com"],
                    "mount_hosts": ["mount-server.example.com"],
                },
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "zfs-server.example.com" in data["data"]["zfs"]
        assert "mount-server.example.com" in data["data"]["mount"]

    def test_batch_empty_body(self, client):
        """リクエストボディがない場合にエラー"""
        response = client.post(
            "/server-list/api/storage/batch",
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_batch_no_hosts(self, client):
        """ホストが指定されていない場合にエラー"""
        response = client.post(
            "/server-list/api/storage/batch",
            json={},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_batch_empty_hosts(self, client):
        """空のホストリストの場合にエラー"""
        response = client.post(
            "/server-list/api/storage/batch",
            json={"zfs_hosts": [], "mount_hosts": []},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_batch_host_not_found(self, client):
        """ホストにデータがない場合も空配列を返す"""
        with unittest.mock.patch(
            "server_list.spec.data_collector.get_zfs_pool_info",
            return_value=[],
        ):
            response = client.post(
                "/server-list/api/storage/batch",
                json={"zfs_hosts": ["nonexistent.example.com"]},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["zfs"]["nonexistent.example.com"] == []
