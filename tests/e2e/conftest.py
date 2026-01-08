#!/usr/bin/env python3
# ruff: noqa: S101
"""
E2E テスト用の pytest フィクスチャ
"""

import os
import subprocess
import tempfile
import threading
import time

import pytest


@pytest.fixture(scope="session")
def host():
    """テストサーバーのホスト"""
    return os.environ.get("TEST_HOST", "localhost")


@pytest.fixture(scope="session")
def port():
    """テストサーバーのポート"""
    return int(os.environ.get("TEST_PORT", "15000"))


@pytest.fixture(scope="session")
def base_url(host, port):
    """テストサーバーのベース URL"""
    return f"http://{host}:{port}/server-list"


@pytest.fixture(scope="module")
def webserver(host, port):
    """E2E テスト用の Web サーバー

    テストモジュール単位でサーバーを起動・停止します。
    環境変数 E2E_SERVER_RUNNING=1 が設定されている場合は
    外部で起動されたサーバーを使用します。
    """
    if os.environ.get("E2E_SERVER_RUNNING"):
        yield
        return

    # テスト用の一時ディレクトリを作成
    temp_dir = tempfile.mkdtemp()
    config_path = os.path.join(temp_dir, "config.yaml")

    # 最小限のテスト用設定を作成
    with open(config_path, "w") as f:
        f.write("""
webapp:
  static_dir_path: frontend/dist
  title: Server List (Test)
machine:
  - name: test-server
    host: test.example.com
    os: Linux
    cpu: Intel Core i7-12700K
    ram_gb: 64
    storage_gb: 1000
""")

    # サーバーをバックグラウンドで起動
    env = os.environ.copy()
    env["FLASK_DEBUG"] = "0"

    server_process = subprocess.Popen(
        ["uv", "run", "server-list", "-c", config_path, "-p", str(port)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # サーバーが起動するまで待機
    time.sleep(3)

    yield

    # サーバーを停止
    server_process.terminate()
    try:
        server_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_process.kill()

    # 一時ディレクトリを削除
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
