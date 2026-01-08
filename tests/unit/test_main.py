#!/usr/bin/env python3
# ruff: noqa: S101
"""
__main__.py のユニットテスト
"""

import importlib
import sys
import unittest.mock


class TestMainModule:
    """__main__ モジュールのテスト"""

    def test_main_function_exists(self):
        """main 関数が存在することを確認"""
        from server_list.__main__ import main

        assert callable(main)

    def test_main_calls_webui_main(self):
        """main 関数が webui.main を呼び出すことを確認"""
        # モジュールキャッシュをクリアして新しいインポートを強制
        modules_to_remove = [key for key in sys.modules if key.startswith("server_list")]
        for mod in modules_to_remove:
            del sys.modules[mod]

        with unittest.mock.patch("server_list.cli.webui.main") as mock_webui_main:
            # パッチ適用後にモジュールをインポート
            import server_list.__main__

            importlib.reload(server_list.__main__)
            server_list.__main__.main()

            mock_webui_main.assert_called_once()
