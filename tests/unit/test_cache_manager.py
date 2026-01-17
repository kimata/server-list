#!/usr/bin/env python3
# ruff: noqa: S101
"""
cache_manager.py のユニットテスト
"""

import sqlite3
import unittest.mock

from server_list.spec import db_config


class TestInitDb:
    """init_db 関数のテスト"""

    def test_creates_cache_table(self, temp_data_dir):
        """cache テーブルが正しく作成される"""
        from server_list.spec import cache_manager

        db_path = temp_data_dir / "cache.db"
        db_config.set_cache_db_path(db_path)

        cache_manager.init_db()

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "cache" in tables


class TestCacheOperations:
    """キャッシュ操作のテスト"""

    def test_set_and_get_cache(self, temp_data_dir):
        """キャッシュの設定と取得が正しく動作する"""
        from server_list.spec import cache_manager

        db_path = temp_data_dir / "cache.db"
        db_config.set_cache_db_path(db_path)

        cache_manager.init_db()

        test_data = {"key1": "value1", "key2": 123}
        cache_manager.set_cache("test_key", test_data)

        result = cache_manager.get_cache("test_key")

        assert result == test_data

    def test_get_cache_not_found(self, temp_data_dir):
        """存在しないキーでは None を返す"""
        from server_list.spec import cache_manager

        db_path = temp_data_dir / "cache.db"
        db_config.set_cache_db_path(db_path)

        cache_manager.init_db()

        result = cache_manager.get_cache("nonexistent_key")

        assert result is None

    def test_set_cache_overwrites(self, temp_data_dir):
        """キャッシュの上書きが正しく動作する"""
        from server_list.spec import cache_manager

        db_path = temp_data_dir / "cache.db"
        db_config.set_cache_db_path(db_path)

        cache_manager.init_db()

        cache_manager.set_cache("test_key", {"old": "value"})
        cache_manager.set_cache("test_key", {"new": "value"})

        result = cache_manager.get_cache("test_key")

        assert result == {"new": "value"}

    def test_cache_list(self, temp_data_dir):
        """リストのキャッシュが正しく動作する"""
        from server_list.spec import cache_manager

        db_path = temp_data_dir / "cache.db"
        db_config.set_cache_db_path(db_path)

        cache_manager.init_db()

        test_list = [{"name": "item1"}, {"name": "item2"}]
        cache_manager.set_cache("list_key", test_list)

        result = cache_manager.get_cache("list_key")

        assert result == test_list


class TestLoadConfigFromFile:
    """load_config_from_file 関数のテスト"""

    def test_returns_none_when_file_not_exists(self, temp_data_dir):
        """ファイルが存在しない場合は None を返す"""
        from server_list.spec import cache_manager

        with unittest.mock.patch.object(cache_manager, "CONFIG_PATH", temp_data_dir / "nonexistent.yaml"):
            result = cache_manager.load_config_from_file()

        assert result is None


class TestGetConfig:
    """get_config 関数のテスト"""

    def test_returns_cached_config(self, temp_data_dir, sample_config):
        """キャッシュから設定を返す"""
        from server_list.spec import cache_manager

        db_path = temp_data_dir / "cache.db"
        db_config.set_cache_db_path(db_path)

        cache_manager.init_db()
        cache_manager.set_cache("config", sample_config)

        result = cache_manager.get_config()

        assert result == sample_config

    def test_loads_from_file_when_not_cached(self, temp_data_dir, sample_config):
        """キャッシュがない場合はファイルから読み込む"""
        from server_list.spec import cache_manager

        db_path = temp_data_dir / "cache.db"
        db_config.set_cache_db_path(db_path)

        with unittest.mock.patch.object(cache_manager, "load_config_from_file", return_value=sample_config):
            cache_manager.init_db()

            result = cache_manager.get_config()

        assert result == sample_config


class TestCacheWorker:
    """キャッシュワーカーのテスト"""

    def test_start_and_stop_worker(self, temp_data_dir):
        """ワーカーの開始と停止が正しく動作する"""
        from server_list.spec import cache_manager

        db_path = temp_data_dir / "cache.db"
        db_config.set_cache_db_path(db_path)

        with (
            unittest.mock.patch.object(cache_manager, "load_config_from_file", return_value=None),
            unittest.mock.patch.object(cache_manager, "UPDATE_INTERVAL_SEC", 0.1),
        ):
            cache_manager.start_cache_worker()

            assert cache_manager._update_thread is not None
            assert cache_manager._update_thread.is_alive()

            cache_manager.stop_cache_worker()

            assert not cache_manager._update_thread.is_alive()
