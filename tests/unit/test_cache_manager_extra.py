#!/usr/bin/env python3
# ruff: noqa: S101
"""
cache_manager.py の追加ユニットテスト（100%カバレッジ用）
"""

import unittest.mock

from server_list.spec import db_config


class TestGetCacheException:
    """_get_cache 関数の例外テスト"""

    def test_handles_exception(self, temp_data_dir):
        """sqlite3.Error 時は None を返す"""
        import sqlite3

        import server_list.spec.db
        from server_list.spec import cache_manager

        db_path = temp_data_dir / "cache.db"
        db_config.set_cache_db_path(db_path)

        cache_manager.init_db()

        # データベースエラーを発生させる
        with unittest.mock.patch.object(
            server_list.spec.db, "get_connection", side_effect=sqlite3.Error("DB error")
        ):
            result = cache_manager._get_cache("test_key")

        assert result is None


class TestSetCacheException:
    """_set_cache 関数の例外テスト"""

    def test_handles_exception(self, temp_data_dir):
        """sqlite3.Error 時はエラーログを出力"""
        import sqlite3

        import server_list.spec.db
        from server_list.spec import cache_manager

        db_path = temp_data_dir / "cache.db"
        db_config.set_cache_db_path(db_path)

        cache_manager.init_db()

        with unittest.mock.patch.object(
            server_list.spec.db, "get_connection", side_effect=sqlite3.Error("DB error")
        ):
            # 例外が発生しても正常に終了することを確認
            cache_manager._set_cache("test_key", {"data": "value"})


class TestLoadConfigFromFileWithFile:
    """load_config_from_file 関数のテスト（ファイルあり）"""

    def test_loads_existing_file(self, temp_data_dir):
        """存在するファイルから設定を読み込む（スキーマをモック）"""
        import server_list.spec.db

        from server_list.spec import cache_manager

        config_path = temp_data_dir / "config.yaml"
        config_path.write_text("machine:\n  - name: test\n")

        db_config.set_config_path(config_path)

        # スキーマパスを存在しないパスに設定して yaml.safe_load フォールバックを使用
        with unittest.mock.patch.object(
            server_list.spec.db, "CONFIG_SCHEMA_PATH", temp_data_dir / "nonexistent.schema"
        ):
            result = cache_manager.load_config_from_file()

        assert result is not None
        assert "machine" in result

    def test_handles_yaml_error(self, temp_data_dir):
        """YAML パースエラー時は None を返す"""
        from server_list.spec import cache_manager

        config_path = temp_data_dir / "config.yaml"
        config_path.write_text("invalid: yaml: content:\n  - : :")

        db_config.set_config_path(config_path)
        with unittest.mock.patch("yaml.safe_load", side_effect=Exception("Parse error")):
            result = cache_manager.load_config_from_file()

        assert result is None


class TestGetConfigCachesResult:
    """get_config 関数のキャッシュテスト"""

    def test_caches_loaded_config(self, temp_data_dir):
        """読み込んだ設定をキャッシュする（スキーマをモック）"""
        import server_list.spec.db

        from server_list.spec import cache_manager

        db_path = temp_data_dir / "cache.db"
        config_path = temp_data_dir / "config.yaml"
        config_path.write_text("machine:\n  - name: test\n")
        db_config.set_cache_db_path(db_path)
        db_config.set_config_path(config_path)

        cache_manager.init_db()

        # スキーマパスを存在しないパスに設定して yaml.safe_load フォールバックを使用
        with unittest.mock.patch.object(
            server_list.spec.db, "CONFIG_SCHEMA_PATH", temp_data_dir / "nonexistent.schema"
        ):
            result = cache_manager.get_config()

        assert result is not None
        assert "machine" in result


class TestUpdateAllCaches:
    """update_all_caches 関数のテスト"""

    def test_updates_config_cache(self, temp_data_dir):
        """設定キャッシュを更新する（スキーマをモック）"""
        import server_list.spec.db

        from server_list.spec import cache_manager

        db_path = temp_data_dir / "cache.db"
        config_path = temp_data_dir / "config.yaml"
        config_path.write_text("machine:\n  - name: test\n")
        db_config.set_cache_db_path(db_path)
        db_config.set_config_path(config_path)

        with (
            unittest.mock.patch("my_lib.webapp.event.notify_event"),
            unittest.mock.patch.object(
                server_list.spec.db, "CONFIG_SCHEMA_PATH", temp_data_dir / "nonexistent.schema"
            ),
        ):
            cache_manager.init_db()
            cache_manager.update_all_caches()

    def test_notifies_on_change(self, temp_data_dir):
        """変更時にイベント通知する（スキーマをモック）"""
        import server_list.spec.db

        from server_list.spec import cache_manager

        db_path = temp_data_dir / "cache.db"
        config_path = temp_data_dir / "config.yaml"
        config_path.write_text("machine:\n  - name: test\n")
        db_config.set_cache_db_path(db_path)
        db_config.set_config_path(config_path)

        with (
            unittest.mock.patch("my_lib.webapp.event.notify_event") as mock_notify,
            unittest.mock.patch.object(
                server_list.spec.db, "CONFIG_SCHEMA_PATH", temp_data_dir / "nonexistent.schema"
            ),
        ):
            cache_manager.init_db()
            # 最初の更新
            cache_manager.update_all_caches()
            assert mock_notify.called

    def test_no_notify_when_unchanged(self, temp_data_dir):
        """変更がない場合は通知しない（スキーマをモック）"""
        import server_list.spec.db

        from server_list.spec import cache_manager

        db_path = temp_data_dir / "cache.db"
        config_path = temp_data_dir / "config.yaml"
        config_path.write_text("machine:\n  - name: test\n")
        db_config.set_cache_db_path(db_path)
        db_config.set_config_path(config_path)

        with (
            unittest.mock.patch("my_lib.webapp.event.notify_event") as mock_notify,
            unittest.mock.patch.object(
                server_list.spec.db, "CONFIG_SCHEMA_PATH", temp_data_dir / "nonexistent.schema"
            ),
        ):
            cache_manager.init_db()
            # 最初の更新
            cache_manager.update_all_caches()
            mock_notify.reset_mock()
            # 2回目の更新（変更なし）
            cache_manager.update_all_caches()
            # 変更がないので通知されない
            assert not mock_notify.called


class TestStartCacheWorkerAlreadyRunning:
    """start_cache_worker 関数の重複起動テスト"""

    def test_skips_if_already_running(self, temp_data_dir):
        """既に実行中の場合はスキップする"""
        from server_list.spec import cache_manager

        db_path = temp_data_dir / "cache.db"
        config_path = temp_data_dir / "config.yaml"
        config_path.write_text("machine:\n  - name: test\n")
        db_config.set_cache_db_path(db_path)
        db_config.set_config_path(config_path)

        cache_manager.init_db()

        # ワーカーを開始
        cache_manager.start_cache_worker()

        # 2回目の呼び出し（スキップされるはず）
        cache_manager.start_cache_worker()

        # 停止
        cache_manager.stop_cache_worker()


class TestStopCacheWorkerJoin:
    """stop_cache_worker 関数のスレッド終了テスト"""

    def test_joins_thread(self, temp_data_dir):
        """スレッドを終了待ちする"""
        import time

        from server_list.spec import cache_manager

        db_path = temp_data_dir / "cache.db"
        config_path = temp_data_dir / "config.yaml"
        config_path.write_text("machine:\n  - name: test\n")
        db_config.set_cache_db_path(db_path)
        db_config.set_config_path(config_path)

        cache_manager.init_db()
        cache_manager.start_cache_worker()

        # 少し待ってから停止
        time.sleep(0.1)

        cache_manager.stop_cache_worker()
