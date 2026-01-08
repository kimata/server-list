#!/usr/bin/env python3
"""
E2E テスト用の pytest フィクスチャ
"""

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pytest


def pytest_addoption(parser):
    """pytest のコマンドラインオプションを追加"""
    parser.addoption(
        "--host",
        action="store",
        default=None,
        help="テストサーバーのホスト",
    )
    parser.addoption(
        "--port",
        action="store",
        default=None,
        type=int,
        help="テストサーバーのポート",
    )


@pytest.fixture(scope="session")
def host(request):
    """テストサーバーのホスト"""
    # コマンドライン引数 > 環境変数 > デフォルト値
    cli_host = request.config.getoption("--host")
    if cli_host:
        return cli_host
    return os.environ.get("TEST_HOST", "localhost")


@pytest.fixture(scope="session")
def port(request):
    """テストサーバーのポート"""
    # コマンドライン引数 > 環境変数 > デフォルト値
    cli_port = request.config.getoption("--port")
    if cli_port:
        return cli_port
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
    temp_dir = Path(tempfile.mkdtemp())
    config_path = temp_dir / "config.yaml"

    # 最小限のテスト用設定を作成
    config_path.write_text("""
webapp:
  static_dir_path: frontend/dist
  title: Server List (Test)
machine:
  - name: test-server
    mode: Test Server
    os: Linux
    cpu: Intel Core i7-12700K
    ram: 64 GB
    storage:
      - name: Main Storage
        model: Test SSD
        volume: 1 TB
""")

    # サーバーをバックグラウンドで起動
    env = os.environ.copy()
    env["FLASK_DEBUG"] = "0"

    server_process = subprocess.Popen(  # noqa: S603
        ["uv", "run", "server-list", "-c", str(config_path), "-p", str(port)],  # noqa: S607
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
    shutil.rmtree(temp_dir, ignore_errors=True)
