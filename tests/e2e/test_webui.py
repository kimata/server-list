#!/usr/bin/env python3
# ruff: noqa: S101
"""
WebUI E2E テスト

Playwright を使用して WebUI の E2E テストを実行します。
"""

import pathlib
import re

import pytest

# プロジェクトルートの reports/evidence/ に保存
EVIDENCE_DIR = pathlib.Path(__file__).parent.parent.parent / "reports" / "evidence"


def setup_error_handlers(page):
    """ページにエラーハンドラを設定し、エラーリストを返す

    Returns:
        tuple: (js_errors, console_errors) - 発生したエラーを格納するリスト
    """
    js_errors = []
    console_errors = []

    page.on("pageerror", lambda error: js_errors.append(str(error)))
    page.on(
        "console",
        lambda message: (
            console_errors.append(message.text)
            if message.type == "error"
            else None
        ),
    )

    return js_errors, console_errors


def check_no_react_errors(js_errors: list, console_errors: list, context: str = ""):
    """JavaScript/React エラーがないことを確認

    Args:
        js_errors: pageerror イベントでキャプチャしたエラー
        console_errors: console.error でキャプチャしたエラー
        context: エラーメッセージに含めるコンテキスト情報
    """
    # pageerror（未処理例外）のチェック
    assert len(js_errors) == 0, f"JavaScript エラーが発生しました{context}: {js_errors}"

    # React エラーのパターン（minified エラーコードを含む）
    react_error_patterns = [
        r"Minified React error #\d+",  # 本番ビルドの React エラー
        r"Error: Objects are not valid as a React child",
        r"Error: Rendered fewer hooks than expected",
        r"Error: Rendered more hooks than expected",
        r"Invalid hook call",
        r"Rules of Hooks",
    ]

    react_errors = []
    for error in console_errors:
        for pattern in react_error_patterns:
            if re.search(pattern, error, re.IGNORECASE):
                react_errors.append(error)
                break

    assert len(react_errors) == 0, f"React エラーが発生しました{context}: {react_errors}"


def check_page_content_no_error(page, context: str = ""):
    """ページ内容にエラー表示がないことを確認

    React がエラーをキャッチしてフォールバック UI を表示した場合を検出
    """
    # エラー状態を示す可能性のある要素をチェック
    error_indicators = [
        ".notification.is-danger",  # Bulma のエラー通知
        "[data-testid='error-message']",
        ".error-boundary",
    ]

    # テスト環境で許容されるエラーメッセージ
    allowed_errors = [
        "not found",  # Machine not found は正常なケース
        "failed to fetch",  # テスト環境では ESXi に接続できない
        "network error",  # ネットワークエラーはテスト環境で発生しうる
    ]

    for selector in error_indicators:
        error_element = page.locator(selector)
        if error_element.count() > 0:
            error_text = error_element.first.text_content()
            if error_text:
                error_lower = error_text.lower()
                # 許容されるエラーかどうかチェック
                if not any(allowed in error_lower for allowed in allowed_errors):
                    pytest.fail(f"ページにエラーが表示されています{context}: {error_text}")


@pytest.mark.e2e
class TestWebuiE2E:
    """WebUI E2E テスト"""

    def test_index_page_loads(self, page, webserver, base_url):
        """インデックスページ表示の E2E テスト

        1. インデックスページにアクセス
        2. ページが正常にロードされることを確認
        """
        page.set_viewport_size({"width": 1920, "height": 1080})

        js_errors, console_errors = setup_error_handlers(page)

        # インデックスページにアクセス
        page.goto(base_url, wait_until="load")

        # スクリーンショットを保存
        screenshot_path = EVIDENCE_DIR / "e2e_index_page.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot_path), full_page=True)

        # エラーチェック
        check_no_react_errors(js_errors, console_errors, " (インデックスページ)")

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

        js_errors, console_errors = setup_error_handlers(page)

        page.goto(base_url, wait_until="load")

        # JavaScript/React エラーがないこと
        check_no_react_errors(js_errors, console_errors, " (インデックスページ)")


@pytest.mark.e2e
class TestMachinePageE2E:
    """マシンページ E2E テスト"""

    def test_machine_page_loads(self, page, webserver, base_url):
        """マシンページ表示の E2E テスト"""
        page.set_viewport_size({"width": 1920, "height": 1080})

        js_errors, console_errors = setup_error_handlers(page)

        # マシンページにアクセス
        page.goto(f"{base_url}/machine/test-server", wait_until="load")

        # スクリーンショットを保存
        screenshot_path = EVIDENCE_DIR / "e2e_machine_page.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot_path), full_page=True)

        # エラーチェック
        check_no_react_errors(js_errors, console_errors, " (マシンページ)")

    def test_machine_page_no_js_errors(self, page, webserver, base_url):
        """マシンページで JavaScript エラーがないことを確認"""
        page.set_viewport_size({"width": 1920, "height": 1080})

        js_errors, console_errors = setup_error_handlers(page)

        page.goto(f"{base_url}/machine/test-server", wait_until="load")

        # JavaScript/React エラーがないこと
        check_no_react_errors(js_errors, console_errors, " (マシンページ)")
        check_page_content_no_error(page, " (マシンページ)")

    def test_navigate_to_machine_page(self, page, webserver, base_url):
        """ホームページからマシンページへのナビゲーションをテスト

        実際のユーザー操作（カードをクリック）をシミュレートして、
        ページ遷移時のエラーを検出する
        """
        page.set_viewport_size({"width": 1920, "height": 1080})

        js_errors, console_errors = setup_error_handlers(page)

        # ホームページにアクセス
        page.goto(base_url, wait_until="load")

        # サーバーカードが表示されるまで待機（ない場合はスキップ）
        card_selector = ".card"
        try:
            page.wait_for_selector(card_selector, timeout=10000)
        except Exception:
            pytest.skip("サーバーカードが表示されませんでした（テスト環境の制限）")

        # 最初のカードをクリック
        first_card = page.locator(card_selector).first
        if first_card.count() > 0:
            first_card.click()

            # ページ遷移を待機
            page.wait_for_load_state("load")

            # URL がマシンページに変わったことを確認
            assert "/machine/" in page.url, f"マシンページに遷移していません: {page.url}"

            # スクリーンショットを保存
            screenshot_path = EVIDENCE_DIR / "e2e_machine_page_navigation.png"
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshot_path), full_page=True)

            # エラーチェック
            check_no_react_errors(js_errors, console_errors, " (ナビゲーション後)")
            check_page_content_no_error(page, " (ナビゲーション後)")


@pytest.mark.e2e
class TestAllMachinesE2E:
    """全マシンページの E2E テスト

    テスト用マシンにアクセスしてエラーがないことを確認
    """

    def test_all_machines_no_errors(self, page, webserver, base_url, host, port):  # noqa: ARG002
        """テスト用マシンページでエラーがないことを確認"""
        page.set_viewport_size({"width": 1920, "height": 1080})

        # テスト用マシンのリスト（conftest.py で定義されているもの）
        machines = [{"name": "test-server"}]

        if not machines:
            pytest.skip("マシンが設定されていません")

        errors_found = []

        for machine in machines:
            machine_name = machine.get("name")
            if not machine_name:
                continue

            js_errors, console_errors = setup_error_handlers(page)

            # マシンページにアクセス
            machine_url = f"{base_url}/machine/{machine_name}"
            page.goto(machine_url, wait_until="load")

            # エラーをチェック
            try:
                check_no_react_errors(js_errors, console_errors, f" ({machine_name})")
                check_page_content_no_error(page, f" ({machine_name})")
            except AssertionError as e:
                errors_found.append(f"{machine_name}: {e}")

                # エラー時のスクリーンショット
                safe_name = machine_name.replace("/", "_").replace(".", "_")
                screenshot_path = EVIDENCE_DIR / f"e2e_error_{safe_name}.png"
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(screenshot_path), full_page=True)

        if errors_found:
            pytest.fail(f"以下のマシンページでエラーが発生しました:\n" + "\n".join(errors_found))
