#!/usr/bin/env python3
"""
共通テストフィクスチャ

テスト全体で使用する共通のフィクスチャとヘルパーを定義します。
"""

import logging
import tempfile
import unittest.mock
from pathlib import Path

import pytest

# === 定数 ===
CONFIG_FILE = "config.yaml"


# === 環境モック ===
@pytest.fixture(scope="session", autouse=True)
def env_mock():
    """テスト環境用の環境変数モック"""
    with unittest.mock.patch.dict(
        "os.environ",
        {
            "TEST": "true",
            "NO_COLORED_LOGS": "true",
        },
    ) as fixture:
        yield fixture


# === テスト用設定 ===
@pytest.fixture
def sample_config():
    """サンプル設定を返す"""
    return {
        "webapp": {
            "static_dir_path": "frontend/dist",
            "image_dir_path": "img",
        },
        "data": {
            "cache": "./data",
        },
        "machine": [
            {
                "name": "test-server-1.example.com",
                "mode": "Test Server Model",
                "cpu": "Intel Core i7-12700K",
                "ram": "64 GB",
                "os": "ESXi 8.0",
                "storage": [
                    {"name": "Test SSD", "model": "TEST-SSD-001", "volume": "1 TB"},
                ],
                "esxi": "https://test-server-1.example.com/",
            },
        ],
    }


@pytest.fixture
def sample_secret():
    """サンプルシークレットを返す"""
    return {
        "esxi_auth": {
            "test-server-1.example.com": {
                "host": "test-server-1.example.com",
                "username": "root",
                "password": "testpassword",
            },
        },
    }


# === データベースフィクスチャ ===
@pytest.fixture
def temp_db_path():
    """一時データベースパスを返す"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.db"


@pytest.fixture
def temp_data_dir():
    """一時データディレクトリを返す"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# === Flask テストクライアント ===
@pytest.fixture
def flask_app(sample_config):
    """Flask テストアプリケーション"""
    import my_lib.webapp.config

    from server_list.cli.webui import create_app

    webapp_config = my_lib.webapp.config.WebappConfig.from_dict(sample_config["webapp"])

    # バックグラウンドワーカーを起動しないようにモック
    with (
        unittest.mock.patch("server_list.cli.webui.start_cache_worker"),
        unittest.mock.patch("server_list.cli.webui.start_collector"),
        unittest.mock.patch("os.environ.get", return_value=None),
    ):
        app = create_app(webapp_config)
        app.config["TESTING"] = True
        app.config["CONFIG"] = sample_config
        yield app


@pytest.fixture
def client(flask_app):
    """Flask テストクライアント"""
    return flask_app.test_client()


# === VM情報フィクスチャ ===
@pytest.fixture
def sample_vm_info():
    """サンプルVM情報（dataclass）"""
    from server_list.spec.models import VMInfo

    return VMInfo(
        vm_name="test-vm-1",
        cpu_count=4,
        ram_mb=8192,
        storage_gb=100.0,
        power_state="poweredOn",
        esxi_host="test-server-1.example.com",
        collected_at="2024-01-01T00:00:00",
    )


@pytest.fixture
def sample_uptime_info():
    """サンプル稼働時間情報（dataclass）"""
    from server_list.spec.models import HostInfo

    return HostInfo(
        host="test-server-1.example.com",
        boot_time="2024-01-01T00:00:00",
        uptime_seconds=86400.0,
        status="running",
        cpu_threads=16,
        cpu_cores=8,
        collected_at="2024-01-02T00:00:00",
    )


# === データベースパス管理 ===
@pytest.fixture(autouse=True)
def reset_db_paths():
    """各テスト後に db_config のパスをリセット"""
    from server_list.spec import db_config

    yield
    db_config.reset_all_paths()


# === ロギング設定 ===
logging.getLogger("werkzeug").setLevel(logging.WARNING)
