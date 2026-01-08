#!/usr/bin/env python3
# ruff: noqa: S101
"""
cpu_benchmark.py の追加ユニットテスト（100%カバレッジ用）
"""

import unittest.mock


class TestCalculateMatchScoreVersions:
    """calculate_match_score 関数のバージョン比較テスト"""

    def test_version_in_model_partial_match(self):
        """モデル番号の部分一致とバージョン違い"""
        from server_list.spec.cpu_benchmark import calculate_match_score

        # バージョンが異なる場合は低スコア
        score = calculate_match_score("Intel Xeon E5-2699 v3", "Intel Xeon E5-2699 v4")
        assert score < 0.5

    def test_version_match_partial_model(self):
        """部分一致でバージョンも一致"""
        from server_list.spec.cpu_benchmark import calculate_match_score

        score = calculate_match_score("E5-2699v4", "Intel Xeon E5-2699 v4")
        assert score > 0.8

    def test_partial_model_match_with_different_version(self):
        """部分一致でバージョン違い（lines 93-98 カバレッジ）"""
        from server_list.spec.cpu_benchmark import calculate_match_score

        # search_model が candidate_model に含まれる、かつバージョン違い
        score = calculate_match_score("i7-1270 v3", "Intel Core i7-12700K v4")
        assert 0.2 < score < 0.5

    def test_partial_model_match_same_version(self):
        """部分一致でバージョン同じ（line 98 カバレッジ）"""
        from server_list.spec.cpu_benchmark import calculate_match_score

        # search_model が candidate_model に含まれる、かつバージョン同じ
        score = calculate_match_score("i7-1270 v4", "Intel Core i7-12700K v4")
        assert score >= 0.9


class TestCalculateMatchScoreExact:
    """calculate_match_score 関数の完全一致テスト"""

    def test_exact_lowercase_match(self):
        """小文字で完全一致"""
        from server_list.spec.cpu_benchmark import calculate_match_score

        score = calculate_match_score("intel core i7", "Intel Core i7")
        assert score == 1.0


class TestCalculateMatchScoreE5Pattern:
    """calculate_match_score 関数の E5 パターンテスト"""

    def test_e5_same_model_same_version(self):
        """E5 同一モデル・同一バージョン（line 110 カバレッジ）"""
        from server_list.spec.cpu_benchmark import calculate_match_score

        # E5 パターンで同一モデル・同一バージョン
        score = calculate_match_score("E5-2699 v4", "E5-2699 v4")
        assert score >= 0.95

    def test_e5_same_model_no_version(self):
        """E5 同一モデル・バージョンなし（line 112 カバレッジ）"""
        from server_list.spec.cpu_benchmark import calculate_match_score

        # E5 パターンで同一モデル・バージョンなし
        score = calculate_match_score("E5-2699", "E5-2699")
        assert score >= 0.95

    def test_e5_different_model(self):
        """E5 異なるモデル"""
        from server_list.spec.cpu_benchmark import calculate_match_score

        score = calculate_match_score("E5-2680 v4", "E5-2699 v4")
        assert score < 0.5

    def test_e5_same_model_different_version(self):
        """E5 同一モデル・異なるバージョン"""
        from server_list.spec.cpu_benchmark import calculate_match_score

        # E5 パターンで同一モデル・バージョン違い
        score = calculate_match_score("E5-2699 v3", "E5-2699 v4")
        assert score < 0.95


class TestCalculateMatchScoreCorePattern:
    """calculate_match_score 関数の Core i パターンテスト"""

    def test_core_same_model(self):
        """Core i 同一モデル（line 119 カバレッジ）"""
        from server_list.spec.cpu_benchmark import calculate_match_score

        # Core i パターンで同一モデル
        score = calculate_match_score("i7-12700", "i7-12700")
        assert score >= 0.95

    def test_core_different_model(self):
        """Core i 異なるモデル"""
        from server_list.spec.cpu_benchmark import calculate_match_score

        # Core i パターンで異なるモデル
        score = calculate_match_score("i7-12700", "i5-12600")
        assert score < 0.5

    def test_core_different_series(self):
        """Core i 異なるシリーズ"""
        from server_list.spec.cpu_benchmark import calculate_match_score

        # Core i パターンで異なるシリーズ（i7 vs i5）
        score = calculate_match_score("i7-12700K", "i5-12700K")
        assert score < 0.5


class TestSearchChartPageEdgeCases:
    """search_chart_page 関数のエッジケーステスト"""

    def test_entry_without_link(self):
        """リンクがないエントリをスキップ"""
        from server_list.spec.cpu_benchmark import search_chart_page

        html = """
        <html>
        <body>
        <ul class="chartlist">
            <li>No link entry</li>
            <li><a href="/cpu.html">Intel Core i7-12700K</a>(95%)30,000$500</li>
        </ul>
        </body>
        </html>
        """

        mock_response = unittest.mock.MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = unittest.mock.MagicMock()

        with unittest.mock.patch("requests.get", return_value=mock_response):
            name, score = search_chart_page("https://example.com", "Intel Core i7-12700K")

        assert name == "Intel Core i7-12700K"
        assert score == 30000

    def test_invalid_score_value(self):
        """無効なスコア値のエントリをスキップ"""
        from server_list.spec.cpu_benchmark import search_chart_page

        html = """
        <html>
        <body>
        <ul class="chartlist">
            <li><a href="/cpu.html">Intel Core i7-12700K</a>(95%)invalid$500</li>
        </ul>
        </body>
        </html>
        """

        mock_response = unittest.mock.MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = unittest.mock.MagicMock()

        with unittest.mock.patch("requests.get", return_value=mock_response):
            name, score = search_chart_page("https://example.com", "Intel Core i7-12700K")

        assert name is None
        assert score is None


class TestSearchCpuListEdgeCases:
    """search_cpu_list 関数のエッジケーステスト"""

    def test_no_tbody(self):
        """tbody がない場合は None を返す"""
        from server_list.spec.cpu_benchmark import search_cpu_list

        html = """
        <html>
        <body>
        <table id="cputable"></table>
        </body>
        </html>
        """

        mock_response = unittest.mock.MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = unittest.mock.MagicMock()

        with unittest.mock.patch("requests.get", return_value=mock_response):
            name, score = search_cpu_list("Intel Core i7-12700K")

        assert name is None
        assert score is None

    def test_row_with_few_cells(self):
        """セルが少ない行をスキップ"""
        from server_list.spec.cpu_benchmark import search_cpu_list

        html = """
        <html>
        <body>
        <table id="cputable">
            <tbody>
                <tr><td>Only one cell</td></tr>
                <tr>
                    <td><a href="/cpu.html">Intel Core i7-12700K</a></td>
                    <td>30,000</td>
                    <td>$500</td>
                </tr>
            </tbody>
        </table>
        </body>
        </html>
        """

        mock_response = unittest.mock.MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = unittest.mock.MagicMock()

        with unittest.mock.patch("requests.get", return_value=mock_response):
            name, score = search_cpu_list("Intel Core i7-12700K")

        assert name == "Intel Core i7-12700K"
        assert score == 30000

    def test_row_without_link(self):
        """リンクがない行をスキップ"""
        from server_list.spec.cpu_benchmark import search_cpu_list

        html = """
        <html>
        <body>
        <table id="cputable">
            <tbody>
                <tr><td>No link</td><td>100</td></tr>
                <tr>
                    <td><a href="/cpu.html">Intel Core i7-12700K</a></td>
                    <td>30,000</td>
                </tr>
            </tbody>
        </table>
        </body>
        </html>
        """

        mock_response = unittest.mock.MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = unittest.mock.MagicMock()

        with unittest.mock.patch("requests.get", return_value=mock_response):
            name, score = search_cpu_list("Intel Core i7-12700K")

        assert name == "Intel Core i7-12700K"
        assert score == 30000

    def test_invalid_score_in_table(self):
        """無効なスコア値をスキップ"""
        from server_list.spec.cpu_benchmark import search_cpu_list

        html = """
        <html>
        <body>
        <table id="cputable">
            <tbody>
                <tr>
                    <td><a href="/cpu.html">Intel Core i7-12700K</a></td>
                    <td>invalid</td>
                </tr>
            </tbody>
        </table>
        </body>
        </html>
        """

        mock_response = unittest.mock.MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = unittest.mock.MagicMock()

        with unittest.mock.patch("requests.get", return_value=mock_response):
            name, score = search_cpu_list("Intel Core i7-12700K")

        # スコアがパースできない場合は採用されない
        assert name is None
        assert score is None


class TestSearchCpuBenchmarkSingleThread:
    """search_cpu_benchmark 関数のシングルスレッドテスト"""

    def test_single_thread_only(self):
        """シングルスレッドのみ見つかる場合"""
        from server_list.spec.cpu_benchmark import search_cpu_benchmark

        with (
            unittest.mock.patch(
                "server_list.spec.cpu_benchmark.search_chart_page",
                side_effect=[
                    (None, None),  # multithread
                    ("Intel Core i7-12700K", 4000),  # singlethread
                ],
            ),
            unittest.mock.patch(
                "server_list.spec.cpu_benchmark.search_cpu_list",
                return_value=(None, None),
            ),
        ):
            result = search_cpu_benchmark("Intel Core i7-12700K")

        assert result is not None
        assert result["cpu_name"] == "Intel Core i7-12700K"
        assert result["multi_thread_score"] is None
        assert result["single_thread_score"] == 4000


class TestGetBenchmarkFuzzyMatch:
    """get_benchmark 関数のファジーマッチテスト"""

    def test_like_match(self, temp_data_dir):
        """LIKE 検索でマッチ"""
        from server_list.spec import cpu_benchmark

        db_path = temp_data_dir / "cpu_spec.db"

        with unittest.mock.patch.object(cpu_benchmark, "DB_PATH", db_path):
            cpu_benchmark.init_db()
            cpu_benchmark.save_benchmark("Intel Core i7-12700K @ 3.6GHz", 30000, 4000)

            result = cpu_benchmark.get_benchmark("i7-12700K")

        assert result is not None
        assert "i7-12700K" in result["cpu_name"]

    def test_model_number_match(self, temp_data_dir):
        """モデル番号でマッチ"""
        from server_list.spec import cpu_benchmark

        db_path = temp_data_dir / "cpu_spec.db"

        with unittest.mock.patch.object(cpu_benchmark, "DB_PATH", db_path):
            cpu_benchmark.init_db()
            cpu_benchmark.save_benchmark("Intel Core i7-12700K Full Name", 30000, 4000)

            # モデル番号が一致する場合
            result = cpu_benchmark.get_benchmark("Core i7-12700K")

        assert result is not None


class TestMainFunction:
    """main 関数のテスト"""

    def test_main_runs(self, temp_data_dir):
        """main 関数が実行される"""
        from server_list.spec import cpu_benchmark

        db_path = temp_data_dir / "cpu_spec.db"

        with (
            unittest.mock.patch.object(cpu_benchmark, "DB_PATH", db_path),
            unittest.mock.patch(
                "server_list.spec.cpu_benchmark.search_cpu_benchmark",
                return_value={"cpu_name": "Test", "multi_thread_score": 1000, "single_thread_score": 500},
            ),
            unittest.mock.patch("time.sleep"),
            unittest.mock.patch("builtins.print"),
        ):
            cpu_benchmark.main()
