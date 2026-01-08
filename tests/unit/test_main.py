#!/usr/bin/env python3
# ruff: noqa: S101
"""
__main__.py のユニットテスト
"""

import unittest.mock


class TestMainModule:
    """__main__ モジュールのテスト"""

    def test_main_function_exists(self):
        """main 関数が存在することを確認"""
        from server_list.__main__ import main

        assert callable(main)

    def test_main_calls_webui_main(self):
        """main 関数が webui.main を呼び出すことを確認"""
        with unittest.mock.patch("server_list.cli.webui.main") as mock_webui_main:
            from server_list.__main__ import main

            main()

            mock_webui_main.assert_called_once()
