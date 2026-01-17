#!/usr/bin/env python3
"""
統合テスト用フィクスチャ

ユニットテストとは異なり、データベース初期化はモックしません。
各テストが自分でデータベースを設定・初期化します。
"""

import unittest.mock

import pytest


@pytest.fixture
def flask_app(sample_config):
    """Flask テストアプリケーション（統合テスト用）

    データベース初期化はモックせず、バックグラウンドワーカーのみモックします。
    """
    import my_lib.webapp.config

    from server_list.cli.webui import create_app

    webapp_config = my_lib.webapp.config.WebappConfig.parse(sample_config["webapp"])

    # バックグラウンドワーカーのみモック（データベース初期化は実行する）
    with (
        unittest.mock.patch("server_list.cli.webui.start_cache_worker"),
        unittest.mock.patch("server_list.cli.webui.start_collector"),
        unittest.mock.patch("atexit.register"),
    ):
        app = create_app(webapp_config)
        app.config["TESTING"] = True
        app.config["CONFIG"] = sample_config
        yield app


@pytest.fixture
def client(flask_app):
    """Flask テストクライアント"""
    return flask_app.test_client()
