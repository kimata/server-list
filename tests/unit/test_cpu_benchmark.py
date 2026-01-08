#!/usr/bin/env python3
# ruff: noqa: S101
"""
cpu_benchmark.py のユニットテスト
"""

import sqlite3
import unittest.mock
from pathlib import Path

import pytest


class TestInitDb:
    """init_db 関数のテスト"""

    def test_creates_table(self, temp_data_dir):
        """テーブルが正しく作成される"""
        from server_list.spec import cpu_benchmark

        db_path = temp_data_dir / "cpu_spec.db"

        with unittest.mock.patch.object(cpu_benchmark, "DB_PATH", db_path):
            cpu_benchmark.init_db()

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "cpu_benchmark" in tables


class TestNormalizeCpuName:
    """normalize_cpu_name 関数のテスト"""

    def test_removes_extra_spaces(self):
        """余分なスペースを削除する"""
        from server_list.spec.cpu_benchmark import normalize_cpu_name

        result = normalize_cpu_name("Intel  Core   i7-12700K")
        assert result == "Intel Core i7-12700K"

    def test_removes_clock_speed(self):
        """クロック速度を削除する"""
        from server_list.spec.cpu_benchmark import normalize_cpu_name

        result = normalize_cpu_name("Intel Core i7-12700K @ 3.60GHz")
        assert result == "Intel Core i7-12700K"


class TestExtractModelNumber:
    """extract_model_number 関数のテスト"""

    def test_extracts_xeon_e5(self):
        """Xeon E5 のモデル番号を抽出する"""
        from server_list.spec.cpu_benchmark import extract_model_number

        result = extract_model_number("Intel Xeon E5-2699 v4")
        assert result == "e5-2699v4"

    def test_extracts_core_i7(self):
        """Core i7 のモデル番号を抽出する"""
        from server_list.spec.cpu_benchmark import extract_model_number

        result = extract_model_number("Intel Core i7-12700K")
        assert result == "i7-12700k"

    def test_extracts_core_i5_with_suffix(self):
        """サフィックス付き Core i5 のモデル番号を抽出する"""
        from server_list.spec.cpu_benchmark import extract_model_number

        result = extract_model_number("Intel Core i5-1135G7")
        assert result == "i5-1135g7"

    def test_returns_none_for_unknown(self):
        """未知の形式では None を返す"""
        from server_list.spec.cpu_benchmark import extract_model_number

        result = extract_model_number("Unknown CPU")
        assert result is None


class TestCalculateMatchScore:
    """calculate_match_score 関数のテスト"""

    def test_exact_match(self):
        """完全一致でスコア1.0"""
        from server_list.spec.cpu_benchmark import calculate_match_score

        score = calculate_match_score("Intel Core i7-12700K", "Intel Core i7-12700K")
        assert score == 1.0

    def test_model_number_match(self):
        """モデル番号一致で高スコア"""
        from server_list.spec.cpu_benchmark import calculate_match_score

        score = calculate_match_score("Intel Xeon E5-2699 v4", "Xeon E5-2699 v4 @ 2.20GHz")
        assert score > 0.8

    def test_different_version_low_score(self):
        """異なるバージョンで低スコア"""
        from server_list.spec.cpu_benchmark import calculate_match_score

        score = calculate_match_score("Intel Xeon E5-2699 v4", "Intel Xeon E5-2699 v3")
        assert score < 0.5


class TestSaveAndGetBenchmark:
    """ベンチマークデータの保存・取得テスト"""

    def test_save_and_get_benchmark(self, temp_data_dir):
        """ベンチマークデータの保存と取得が正しく動作する"""
        from server_list.spec import cpu_benchmark

        db_path = temp_data_dir / "cpu_spec.db"

        with unittest.mock.patch.object(cpu_benchmark, "DB_PATH", db_path):
            cpu_benchmark.init_db()

            cpu_benchmark.save_benchmark("Intel Core i7-12700K", 30000, 4000)

            result = cpu_benchmark.get_benchmark("Intel Core i7-12700K")

        assert result is not None
        assert result["cpu_name"] == "Intel Core i7-12700K"
        assert result["multi_thread_score"] == 30000
        assert result["single_thread_score"] == 4000

    def test_get_benchmark_fuzzy_match(self, temp_data_dir):
        """あいまい検索が正しく動作する"""
        from server_list.spec import cpu_benchmark

        db_path = temp_data_dir / "cpu_spec.db"

        with unittest.mock.patch.object(cpu_benchmark, "DB_PATH", db_path):
            cpu_benchmark.init_db()

            cpu_benchmark.save_benchmark("Intel Core i7-12700K @ 3.60GHz", 30000, 4000)

            result = cpu_benchmark.get_benchmark("i7-12700K")

        assert result is not None
        assert "i7-12700K" in result["cpu_name"]

    def test_get_benchmark_not_found(self, temp_data_dir):
        """存在しないCPUでは None を返す"""
        from server_list.spec import cpu_benchmark

        db_path = temp_data_dir / "cpu_spec.db"

        with unittest.mock.patch.object(cpu_benchmark, "DB_PATH", db_path):
            cpu_benchmark.init_db()

            result = cpu_benchmark.get_benchmark("Nonexistent CPU XYZ-9999")

        assert result is None


class TestClearBenchmark:
    """clear_benchmark 関数のテスト"""

    def test_clears_benchmark(self, temp_data_dir):
        """ベンチマークデータを削除する"""
        from server_list.spec import cpu_benchmark

        db_path = temp_data_dir / "cpu_spec.db"

        with unittest.mock.patch.object(cpu_benchmark, "DB_PATH", db_path):
            cpu_benchmark.init_db()

            cpu_benchmark.save_benchmark("Test CPU", 10000, 2000)
            assert cpu_benchmark.get_benchmark("Test CPU") is not None

            cpu_benchmark.clear_benchmark("Test CPU")
            assert cpu_benchmark.get_benchmark("Test CPU") is None
