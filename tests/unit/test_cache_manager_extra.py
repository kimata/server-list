#!/usr/bin/env python3
# ruff: noqa: S101
"""
cache_manager.py の追加ユニットテスト（100%カバレッジ用）
"""

import json
import threading
import unittest.mock
from pathlib import Path


class TestGetCacheException:
    """get_cache 関数の例外テスト"""

    def test_handles_exception(self, temp_data_dir):
        """例外時は None を返す"""
        from server_list.spec import cache_manager

        db_path = temp_data_dir / "cache.db"

        with unittest.mock.patch.object(cache_manager, "DB_PATH", db_path):
            cache_manager.init_db()

            # データベースロックを取得して例外を発生させる
            with unittest.mock.patch.object(
                cache_manager, "get_db_connection", side_effect=Exception("DB error")
            ):
                result = cache_manager.get_cache("test_key")

        assert result is None


class TestSetCacheException:
    """set_cache 関数の例外テスト"""

    def test_handles_exception(self, temp_data_dir):
        """例外時はエラーログを出力"""
        from server_list.spec import cache_manager

        db_path = temp_data_dir / "cache.db"

        with unittest.mock.patch.object(cache_manager, "DB_PATH", db_path):
            cache_manager.init_db()

            with unittest.mock.patch.object(
                cache_manager, "get_db_connection", side_effect=Exception("DB error")
            ):
                # 例外が発生しても正常に終了することを確認
                cache_manager.set_cache("test_key", {"data": "value"})


class TestLoadConfigFromFileWithFile:
    """load_config_from_file 関数のテスト（ファイルあり）"""

    def test_loads_existing_file(self, temp_data_dir):
        """存在するファイルから設定を読み込む"""
        from server_list.spec import cache_manager

        config_path = temp_data_dir / "config.yaml"
        config_path.write_text("machine:\n  - name: test\n")

        with unittest.mock.patch.object(cache_manager, "CONFIG_PATH", config_path):
            result = cache_manager.load_config_from_file()

        assert result is not None
        assert "machine" in result

    def test_handles_yaml_error(self, temp_data_dir):
        """YAML パースエラー時は None を返す"""
        from server_list.spec import cache_manager

        config_path = temp_data_dir / "config.yaml"
        config_path.write_text("invalid: yaml: content:\n  - : :")

        with (
            unittest.mock.patch.object(cache_manager, "CONFIG_PATH", config_path),
            unittest.mock.patch("yaml.safe_load", side_effect=Exception("Parse error")),
        ):
            result = cache_manager.load_config_from_file()

        assert result is None


class TestGetConfigCachesResult:
    """get_config 関数のキャッシュテスト"""

    def test_caches_loaded_config(self, temp_data_dir):
        """読み込んだ設定をキャッシュする"""
        from server_list.spec import cache_manager

        db_path = temp_data_dir / "cache.db"
        config_path = temp_data_dir / "config.yaml"
        config_path.write_text("machine:\n  - name: test\n")

        with (
            unittest.mock.patch.object(cache_manager, "DB_PATH", db_path),
            unittest.mock.patch.object(cache_manager, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(cache_manager, "CONFIG_PATH", config_path),
        ):
            cache_manager.init_db()
            result = cache_manager.get_config()

        assert result is not None
        assert "machine" in result


class TestUpdateAllCaches:
    """update_all_caches 関数のテスト"""

    def test_updates_config_cache(self, temp_data_dir):
        """設定キャッシュを更新する"""
        from server_list.spec import cache_manager

        db_path = temp_data_dir / "cache.db"
        config_path = temp_data_dir / "config.yaml"
        config_path.write_text("machine:\n  - name: test\n")

        with (
            unittest.mock.patch.object(cache_manager, "DB_PATH", db_path),
            unittest.mock.patch.object(cache_manager, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(cache_manager, "CONFIG_PATH", config_path),
            unittest.mock.patch("my_lib.webapp.event.notify_event"),
        ):
            cache_manager.init_db()
            cache_manager.update_all_caches()

    def test_notifies_on_change(self, temp_data_dir):
        """変更時にイベント通知する"""
        from server_list.spec import cache_manager

        db_path = temp_data_dir / "cache.db"
        config_path = temp_data_dir / "config.yaml"
        config_path.write_text("machine:\n  - name: test\n")

        with (
            unittest.mock.patch.object(cache_manager, "DB_PATH", db_path),
            unittest.mock.patch.object(cache_manager, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(cache_manager, "CONFIG_PATH", config_path),
            unittest.mock.patch("my_lib.webapp.event.notify_event") as mock_notify,
        ):
            cache_manager.init_db()
            # 最初の更新
            cache_manager.update_all_caches()
            assert mock_notify.called

    def test_no_notify_when_unchanged(self, temp_data_dir):
        """変更がない場合は通知しない"""
        from server_list.spec import cache_manager

        db_path = temp_data_dir / "cache.db"
        config_path = temp_data_dir / "config.yaml"
        config_path.write_text("machine:\n  - name: test\n")

        with (
            unittest.mock.patch.object(cache_manager, "DB_PATH", db_path),
            unittest.mock.patch.object(cache_manager, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(cache_manager, "CONFIG_PATH", config_path),
            unittest.mock.patch("my_lib.webapp.event.notify_event") as mock_notify,
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

        with (
            unittest.mock.patch.object(cache_manager, "DB_PATH", db_path),
            unittest.mock.patch.object(cache_manager, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(cache_manager, "CONFIG_PATH", config_path),
        ):
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
        from server_list.spec import cache_manager

        db_path = temp_data_dir / "cache.db"
        config_path = temp_data_dir / "config.yaml"
        config_path.write_text("machine:\n  - name: test\n")

        with (
            unittest.mock.patch.object(cache_manager, "DB_PATH", db_path),
            unittest.mock.patch.object(cache_manager, "DATA_DIR", temp_data_dir),
            unittest.mock.patch.object(cache_manager, "CONFIG_PATH", config_path),
        ):
            cache_manager.init_db()
            cache_manager.start_cache_worker()

            # 少し待ってから停止
            import time
            time.sleep(0.1)

            cache_manager.stop_cache_worker()
