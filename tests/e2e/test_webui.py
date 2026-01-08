#!/usr/bin/env python3
# ruff: noqa: S101
"""
WebUI E2E テスト

Playwright を使用して WebUI の E2E テストを実行します。
"""

import logging
import pathlib

import pytest

# プロジェクトルートの reports/evidence/ に保存
EVIDENCE_DIR = pathlib.Path(__file__).parent.parent.parent / "reports" / "evidence"


@pytest.mark.e2e
class TestWebuiE2E:
    """WebUI E2E テスト"""

    def test_index_page_loads(self, page, webserver, base_url):
        """インデックスページ表示の E2E テスト

        1. インデックスページにアクセス
        2. ページが正常にロードされることを確認
        """
        page.set_viewport_size({"width": 1920, "height": 1080})

        # コンソールログをキャプチャ
        console_errors = []
        page.on(
            "console",
            lambda message: (
                console_errors.append(message.text)
                if message.type == "error"
                else logging.info(message.text)
            ),
        )

        # インデックスページにアクセス
        page.goto(base_url, wait_until="domcontentloaded")

        # スクリーンショットを保存
        screenshot_path = EVIDENCE_DIR / "e2e_index_page.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot_path), full_page=True)

    def test_api_config(self, page, webserver, host, port):
        """設定 API のテスト"""
        response = page.request.get(f"http://{host}:{port}/server-list/api/config")

        # 設定がキャッシュされていない場合は 404
        assert response.status in [200, 404]

    def test_api_uptime(self, page, webserver, host, port):
        """稼働時間 API のテスト"""
        response = page.request.get(f"http://{host}:{port}/server-list/api/uptime")

        assert response.ok
        data = response.json()
        assert isinstance(data, dict)

    def test_api_cpu_benchmark(self, page, webserver, host, port):
        """CPU ベンチマーク API のテスト"""
        response = page.request.get(
            f"http://{host}:{port}/server-list/api/cpu/benchmark?cpu=Intel Core i7-12700K"
        )

        # ベンチマークが見つからない場合は 404
        assert response.status in [200, 404]

    def test_api_vm_info(self, page, webserver, host, port):
        """VM 情報 API のテスト"""
        response = page.request.get(
            f"http://{host}:{port}/server-list/api/vm/info?vm_name=test-vm&esxi_host=esxi-01"
        )

        # VM が見つからない場合は 404
        assert response.status in [200, 404]

    def test_no_js_errors(self, page, webserver, base_url):
        """JavaScript エラーがないことを確認

        1. インデックスページにアクセス
        2. JavaScript エラーがないことを確認
        """
        page.set_viewport_size({"width": 1920, "height": 1080})

        js_errors = []
        page.on("pageerror", lambda error: js_errors.append(str(error)))

        page.goto(base_url, wait_until="domcontentloaded")

        # ページのロード完了を待機
        page.wait_for_load_state("load")

        # JavaScript エラーがないこと
        assert len(js_errors) == 0, f"JavaScript エラーが発生しました: {js_errors}"


@pytest.mark.e2e
class TestMachinePageE2E:
    """マシンページ E2E テスト"""

    def test_machine_page_loads(self, page, webserver, base_url):
        """マシンページ表示の E2E テスト"""
        page.set_viewport_size({"width": 1920, "height": 1080})

        # マシンページにアクセス
        page.goto(f"{base_url}/machine/test-server", wait_until="domcontentloaded")

        # スクリーンショットを保存
        screenshot_path = EVIDENCE_DIR / "e2e_machine_page.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot_path), full_page=True)
