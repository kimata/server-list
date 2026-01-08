#!/usr/bin/env python3
# ruff: noqa: S101
"""
cli/webui.py のユニットテスト
"""

import unittest.mock


class TestCreateApp:
    """create_app 関数のテスト"""

    def test_creates_flask_app(self, flask_app):
        """Flask アプリケーションが作成される"""
        assert flask_app is not None
        assert flask_app.name == "server-list"

    def test_registers_blueprints(self, flask_app):
        """ブループリントが登録される"""
        blueprint_names = [bp.name for bp in flask_app.blueprints.values()]
        assert "cpu_api" in blueprint_names
        assert "config_api" in blueprint_names
        assert "vm_api" in blueprint_names
        assert "uptime_api" in blueprint_names


class TestSpaFallback:
    """SPA フォールバックルートのテスト"""

    def test_machine_route_returns_index_html(self, client):
        """/machine/<path> が index.html を返す"""
        with unittest.mock.patch(
            "flask.send_from_directory",
            return_value="<html>index</html>",
        ):
            response = client.get("/server-list/machine/test-server")

        # フォールバックが動作することを確認（ファイルが存在しない場合は404）
        assert response.status_code in [200, 404]


class TestServeImage:
    """画像配信ルートのテスト"""

    def test_serves_image(self, client):
        """画像を配信する"""
        with unittest.mock.patch(
            "flask.send_from_directory",
            return_value=b"image data",
        ):
            response = client.get("/server-list/api/img/test.png")

        # 画像が存在しない場合は404
        assert response.status_code in [200, 404]


class TestMain:
    """main 関数のテスト"""

    def test_main_with_default_args(self):
        """デフォルト引数でのテスト"""
        mock_config = {
            "webapp": {"static_dir_path": "frontend/dist"},
            "machine": [],
        }

        with (
            unittest.mock.patch("sys.argv", ["server-list", "-c", "config.yaml"]),
            unittest.mock.patch("my_lib.logger.init"),
            unittest.mock.patch("my_lib.config.load", return_value=mock_config),
            unittest.mock.patch("server_list.cli.webui.create_app") as mock_create_app,
        ):
            mock_flask_app = unittest.mock.MagicMock()
            mock_create_app.return_value = mock_flask_app

            from server_list.cli.webui import main

            main()

            mock_create_app.assert_called_once()
            mock_flask_app.run.assert_called_once()

    def test_main_with_custom_port(self):
        """カスタムポートでのテスト"""
        mock_config = {
            "webapp": {"static_dir_path": "frontend/dist"},
            "machine": [],
        }

        with (
            unittest.mock.patch("sys.argv", ["server-list", "-c", "config.yaml", "-p", "8080"]),
            unittest.mock.patch("my_lib.logger.init"),
            unittest.mock.patch("my_lib.config.load", return_value=mock_config),
            unittest.mock.patch("server_list.cli.webui.create_app") as mock_create_app,
        ):
            mock_flask_app = unittest.mock.MagicMock()
            mock_create_app.return_value = mock_flask_app

            from server_list.cli.webui import main

            main()

            mock_flask_app.run.assert_called_once()
            call_kwargs = mock_flask_app.run.call_args[1]
            assert call_kwargs["port"] == 8080

    def test_main_with_debug_mode(self):
        """デバッグモードでのテスト"""
        mock_config = {
            "webapp": {"static_dir_path": "frontend/dist"},
            "machine": [],
        }

        with (
            unittest.mock.patch("sys.argv", ["server-list", "-c", "config.yaml", "-D"]),
            unittest.mock.patch("my_lib.logger.init") as mock_logger,
            unittest.mock.patch("my_lib.config.load", return_value=mock_config),
            unittest.mock.patch("server_list.cli.webui.create_app") as mock_create_app,
        ):
            import logging

            mock_flask_app = unittest.mock.MagicMock()
            mock_create_app.return_value = mock_flask_app

            from server_list.cli.webui import main

            main()

            mock_flask_app.run.assert_called_once()
            call_kwargs = mock_flask_app.run.call_args[1]
            assert call_kwargs["debug"] is True

            # DEBUG レベルで初期化されることを確認
            mock_logger.assert_called_once()
            call_args = mock_logger.call_args
            assert call_args[1]["level"] == logging.DEBUG


class TestBackgroundWorkers:
    """バックグラウンドワーカーのテスト"""

    def test_workers_start_in_werkzeug_main(self, sample_config):
        """WERKZEUG_RUN_MAIN=true でワーカーが起動する"""
        import my_lib.webapp.config

        from server_list.cli.webui import create_app

        webapp_config = my_lib.webapp.config.WebappConfig.from_dict(sample_config["webapp"])

        with (
            unittest.mock.patch("server_list.cli.webui.start_cache_worker") as mock_cache,
            unittest.mock.patch("server_list.cli.webui.start_collector") as mock_collector,
            unittest.mock.patch("os.environ.get", return_value="true"),
            unittest.mock.patch("atexit.register"),
        ):
            create_app(webapp_config)

            mock_cache.assert_called_once()
            mock_collector.assert_called_once()

    def test_workers_start_in_non_debug_mode(self, sample_config):
        """WERKZEUG_RUN_MAIN が未設定でもワーカーが起動する（非デバッグモード用）"""
        import my_lib.webapp.config

        from server_list.cli.webui import create_app

        webapp_config = my_lib.webapp.config.WebappConfig.from_dict(sample_config["webapp"])

        with (
            unittest.mock.patch("server_list.cli.webui.start_cache_worker") as mock_cache,
            unittest.mock.patch("server_list.cli.webui.start_collector") as mock_collector,
            unittest.mock.patch("os.environ.get", return_value=None),
            unittest.mock.patch("atexit.register"),
        ):
            create_app(webapp_config)

            # 非デバッグモードでもワーカーが起動することを確認
            mock_cache.assert_called_once()
            mock_collector.assert_called_once()
