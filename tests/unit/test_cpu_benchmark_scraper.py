#!/usr/bin/env python3
# ruff: noqa: S101
"""
cpu_benchmark.py のスクレイピング関連ユニットテスト
"""

import unittest.mock

import requests


class TestSearchChartPage:
    """search_chart_page 関数のテスト"""

    def test_finds_cpu_on_chart(self):
        """チャートページからCPUを見つける"""
        from server_list.spec.cpu_benchmark import search_chart_page

        html = """
        <html>
        <body>
        <ul class="chartlist">
            <li><a href="/cpu.html">Intel Core i7-12700K</a>(95%)30,000$500</li>
            <li><a href="/cpu.html">Intel Core i5-12600K</a>(90%)25,000$400</li>
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

    def test_returns_none_on_request_error(self):
        """リクエストエラー時は None を返す"""
        from server_list.spec.cpu_benchmark import search_chart_page

        with unittest.mock.patch("requests.get", side_effect=requests.RequestException("error")):
            name, score = search_chart_page("https://example.com", "Intel Core i7-12700K")

        assert name is None
        assert score is None

    def test_returns_none_when_no_match(self):
        """一致するCPUがない場合は None を返す"""
        from server_list.spec.cpu_benchmark import search_chart_page

        html = """
        <html>
        <body>
        <ul class="chartlist">
            <li><a href="/cpu.html">AMD Ryzen 9 5900X</a>(95%)30,000$500</li>
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


class TestSearchCpuList:
    """search_cpu_list 関数のテスト"""

    def test_finds_cpu_in_table(self):
        """CPUリストテーブルからCPUを見つける"""
        from server_list.spec.cpu_benchmark import search_cpu_list

        html = """
        <html>
        <body>
        <table id="cputable">
            <tbody>
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

    def test_returns_none_on_request_error(self):
        """リクエストエラー時は None を返す"""
        from server_list.spec.cpu_benchmark import search_cpu_list

        with unittest.mock.patch("requests.get", side_effect=requests.RequestException("error")):
            name, score = search_cpu_list("Intel Core i7-12700K")

        assert name is None
        assert score is None

    def test_returns_none_when_no_table(self):
        """テーブルがない場合は None を返す"""
        from server_list.spec.cpu_benchmark import search_cpu_list

        html = "<html><body></body></html>"

        mock_response = unittest.mock.MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = unittest.mock.MagicMock()

        with unittest.mock.patch("requests.get", return_value=mock_response):
            name, score = search_cpu_list("Intel Core i7-12700K")

        assert name is None
        assert score is None


class TestSearchCpuBenchmark:
    """search_cpu_benchmark 関数のテスト"""

    def test_finds_benchmark(self):
        """ベンチマークを見つける"""
        from server_list.spec.cpu_benchmark import search_cpu_benchmark

        with (
            unittest.mock.patch(
                "server_list.spec.cpu_benchmark.search_chart_page",
                side_effect=[
                    ("Intel Core i7-12700K", 30000),  # multithread
                    ("Intel Core i7-12700K", 4000),   # singlethread
                ],
            ),
        ):
            result = search_cpu_benchmark("Intel Core i7-12700K")

        assert result is not None
        assert result["cpu_name"] == "Intel Core i7-12700K"
        assert result["multi_thread_score"] == 30000
        assert result["single_thread_score"] == 4000

    def test_falls_back_to_cpu_list(self):
        """マルチスレッドチャートで見つからない場合はCPUリストにフォールバック"""
        from server_list.spec.cpu_benchmark import search_cpu_benchmark

        with (
            unittest.mock.patch(
                "server_list.spec.cpu_benchmark.search_chart_page",
                side_effect=[
                    (None, None),  # multithread - not found
                    ("Intel Core i7-12700K", 4000),   # singlethread
                ],
            ),
            unittest.mock.patch(
                "server_list.spec.cpu_benchmark.search_cpu_list",
                return_value=("Intel Core i7-12700K", 30000),
            ),
        ):
            result = search_cpu_benchmark("Intel Core i7-12700K")

        assert result is not None
        assert result["multi_thread_score"] == 30000

    def test_returns_none_when_not_found(self):
        """見つからない場合は None を返す"""
        from server_list.spec.cpu_benchmark import search_cpu_benchmark

        with (
            unittest.mock.patch(
                "server_list.spec.cpu_benchmark.search_chart_page",
                return_value=(None, None),
            ),
            unittest.mock.patch(
                "server_list.spec.cpu_benchmark.search_cpu_list",
                return_value=(None, None),
            ),
        ):
            result = search_cpu_benchmark("Unknown CPU")

        assert result is None


class TestFetchAndSaveBenchmark:
    """fetch_and_save_benchmark 関数のテスト"""

    def test_fetches_and_saves(self, temp_data_dir):
        """ウェブから取得して保存する"""
        from server_list.spec import cpu_benchmark

        db_path = temp_data_dir / "cpu_spec.db"
        benchmark_data = {
            "cpu_name": "Intel Core i7-12700K",
            "multi_thread_score": 30000,
            "single_thread_score": 4000,
        }

        with (
            unittest.mock.patch.object(cpu_benchmark, "DB_PATH", db_path),
            unittest.mock.patch(
                "server_list.spec.cpu_benchmark.search_cpu_benchmark",
                return_value=benchmark_data,
            ),
        ):
            cpu_benchmark.init_db()
            result = cpu_benchmark.fetch_and_save_benchmark("Intel Core i7-12700K")

        assert result is not None
        assert result["cpu_name"] == "Intel Core i7-12700K"

    def test_returns_none_when_not_found(self):
        """見つからない場合は None を返す"""
        from server_list.spec.cpu_benchmark import fetch_and_save_benchmark

        with unittest.mock.patch(
            "server_list.spec.cpu_benchmark.search_cpu_benchmark",
            return_value=None,
        ):
            result = fetch_and_save_benchmark("Unknown CPU")

        assert result is None


class TestCalculateMatchScoreEdgeCases:
    """calculate_match_score 関数のエッジケーステスト"""

    def test_core_i_matching(self):
        """Core i シリーズのマッチング"""
        from server_list.spec.cpu_benchmark import calculate_match_score

        score = calculate_match_score("Intel Core i5-12600K", "Intel Core i5-12600K @ 3.70GHz")
        assert score > 0.8

    def test_xeon_e5_different_model(self):
        """異なる Xeon E5 モデル"""
        from server_list.spec.cpu_benchmark import calculate_match_score

        score = calculate_match_score("Intel Xeon E5-2699 v4", "Intel Xeon E5-2680 v4")
        assert score < 0.5

    def test_partial_word_match(self):
        """部分的な単語一致"""
        from server_list.spec.cpu_benchmark import calculate_match_score

        score = calculate_match_score("Intel Xeon", "Intel Xeon E5-2699 v4")
        assert score > 0

    def test_empty_search_words(self):
        """空の検索語"""
        from server_list.spec.cpu_benchmark import calculate_match_score

        score = calculate_match_score("", "Intel Core i7")
        assert score == 0.0
