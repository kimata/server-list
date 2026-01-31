#!/usr/bin/env python3
"""
CPU Benchmark scraper from cpubenchmark.net
Fetches multi-thread and single-thread performance scores and stores them in SQLite database.
"""

import logging
import re
import threading
import time
from typing import Any

import bs4
import requests

from server_list.spec.db import get_connection
from server_list.spec.db_config import get_cpu_spec_db_path
from server_list.spec.models import CPUBenchmark


# =============================================================================
# In-memory cache with TTL for benchmark data
# =============================================================================

class BenchmarkCache:
    """Thread-safe in-memory cache with TTL for benchmark data."""

    def __init__(self, ttl_seconds: int = 3600):
        self._cache: dict[str, Any] = {}
        self._timestamps: dict[str, float] = {}
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        """Get cached value if not expired."""
        with self._lock:
            if key not in self._cache:
                return None
            if time.time() - self._timestamps[key] > self._ttl:
                del self._cache[key]
                del self._timestamps[key]
                return None
            return self._cache[key]

    def set(self, key: str, value: Any) -> None:
        """Set cache value with current timestamp."""
        with self._lock:
            self._cache[key] = value
            self._timestamps[key] = time.time()

    def invalidate(self, key: str | None = None) -> None:
        """Invalidate specific key or all cache."""
        with self._lock:
            if key is None:
                self._cache.clear()
                self._timestamps.clear()
            elif key in self._cache:
                del self._cache[key]
                del self._timestamps[key]


# Global cache instance (1 hour TTL)
_benchmark_cache = BenchmarkCache(ttl_seconds=3600)


# =============================================================================
# Background fetch queue for on-demand benchmark retrieval
# =============================================================================

class BackgroundFetchQueue:
    """Thread-safe queue for background CPU benchmark fetches.

    Prevents duplicate fetches and provides status tracking.
    """

    def __init__(self):
        self._pending: set[str] = set()
        self._lock = threading.Lock()

    def is_pending(self, cpu_name: str) -> bool:
        """Check if a fetch is already pending for this CPU."""
        with self._lock:
            return cpu_name in self._pending

    def add(self, cpu_name: str) -> bool:
        """Add CPU to pending set. Returns False if already pending."""
        with self._lock:
            if cpu_name in self._pending:
                return False
            self._pending.add(cpu_name)
            return True

    def remove(self, cpu_name: str) -> None:
        """Remove CPU from pending set."""
        with self._lock:
            self._pending.discard(cpu_name)


_fetch_queue = BackgroundFetchQueue()


def queue_background_fetch(cpu_name: str) -> bool:
    """Queue a background fetch for a CPU benchmark.

    If the CPU is already being fetched, returns False.
    Otherwise, starts a background thread to fetch the data
    and returns True.

    When fetch completes, notifies frontend via SSE.
    """
    if not _fetch_queue.add(cpu_name):
        logging.debug("Fetch already pending for: %s", cpu_name)
        return False

    def _fetch_task():
        try:
            result = fetch_and_save_benchmark(cpu_name)
            if result:
                # Import here to avoid circular import
                import my_lib.webapp.event
                my_lib.webapp.event.notify_event(my_lib.webapp.event.EVENT_TYPE.CONTENT)
                logging.info("Background fetch completed for: %s", cpu_name)
        except Exception:
            logging.exception("Background fetch failed for: %s", cpu_name)
        finally:
            _fetch_queue.remove(cpu_name)

    thread = threading.Thread(target=_fetch_task, daemon=True)
    thread.start()
    logging.info("Queued background fetch for: %s", cpu_name)
    return True


def queue_background_fetch_batch(cpu_names: list[str]) -> int:
    """Queue background fetches for multiple CPUs.

    Returns the number of CPUs that were queued (not already pending).
    """
    queued = 0
    for cpu_name in cpu_names:
        if queue_background_fetch(cpu_name):
            queued += 1
    return queued


def is_fetch_pending(cpu_name: str) -> bool:
    """Check if a background fetch is pending for this CPU."""
    return _fetch_queue.is_pending(cpu_name)


MULTITHREAD_URL = "https://www.cpubenchmark.net/multithread/"
SINGLETHREAD_URL = "https://www.cpubenchmark.net/singleThread.html"
CPU_LIST_URL = "https://www.cpubenchmark.net/cpu_list.php"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


CPU_BENCHMARK_SCHEMA = """
CREATE TABLE IF NOT EXISTS cpu_benchmark (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cpu_name TEXT UNIQUE NOT NULL,
    multi_thread_score INTEGER,
    single_thread_score INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


def init_db():
    """Initialize the SQLite database."""
    with get_connection(get_cpu_spec_db_path()) as conn:
        conn.executescript(CPU_BENCHMARK_SCHEMA)
        conn.commit()


def extract_model_number(cpu_name: str) -> str | None:
    """Extract the model number from CPU name for precise matching."""
    patterns = [
        r"(E5-\d{4}\s*v\d)",      # Xeon E5-2699 v4
        r"(i[3579]-\d{4,5}\w*)",   # Core i5-1135G7, i7-12700K
        r"(Ryzen\s+\d+\s+\d{4}\w*)",  # Ryzen 9 5900X
        r"(EPYC\s+\d{4}\w*)",      # EPYC 7742
        r"(\d{4,5}\w*)",           # Generic model number
    ]

    for pattern in patterns:
        match = re.search(pattern, cpu_name, re.IGNORECASE)
        if match:
            return match.group(1).lower().replace(" ", "")

    return None


def normalize_cpu_name(cpu_name: str) -> str:
    """Normalize CPU name for matching."""
    name = " ".join(cpu_name.split())
    # Remove clock speed info
    name = re.sub(r"@.*$", "", name).strip()
    # Remove trademark symbols
    name = name.replace("(R)", "").replace("(TM)", "").replace("®", "").replace("™", "")
    # Normalize whitespace again after removing symbols
    name = " ".join(name.split())
    return name


def _match_by_model_number(
    search_name: str, candidate_name: str, search_lower: str, candidate_lower: str
) -> float | None:
    """モデル番号による精密マッチング."""
    search_model = extract_model_number(search_name)
    candidate_model = extract_model_number(candidate_name)

    if not search_model or not candidate_model:
        return None

    if search_model == candidate_model:
        return 1.0

    if search_model not in candidate_model and candidate_model not in search_model:
        return None

    # 部分一致の場合、バージョンチェック
    search_version = re.search(r"v(\d)", search_lower)
    candidate_version = re.search(r"v(\d)", candidate_lower)
    if search_version and candidate_version:
        if search_version.group(1) != candidate_version.group(1):
            return 0.3
    return 0.9


def _match_xeon_e5(search_lower: str, candidate_lower: str) -> float | None:
    """Xeon E5 シリーズの特別マッチング."""
    search_id = re.search(r"e5-(\d{4})", search_lower)
    candidate_id = re.search(r"e5-(\d{4})", candidate_lower)

    if not search_id or not candidate_id:
        return None

    if search_id.group(1) != candidate_id.group(1):
        return 0.2

    # 同一モデル - バージョンチェック
    search_v = re.search(r"v(\d)", search_lower)
    candidate_v = re.search(r"v(\d)", candidate_lower)

    if search_v and candidate_v and search_v.group(1) == candidate_v.group(1):
        return 0.95
    if not search_v and not candidate_v:
        return 0.95

    return 0.2


def _match_core_i(search_lower: str, candidate_lower: str) -> float | None:
    """Intel Core i シリーズの特別マッチング."""
    search_core = re.search(r"i([3579])-(\d{4,5})", search_lower)
    candidate_core = re.search(r"i([3579])-(\d{4,5})", candidate_lower)

    if not search_core or not candidate_core:
        return None

    if (
        search_core.group(1) == candidate_core.group(1)
        and search_core.group(2) == candidate_core.group(2)
    ):
        return 0.95

    return 0.2


def _match_by_word_overlap(search_lower: str, candidate_lower: str) -> float:
    """単語の重複によるファジーマッチング."""
    search_words = set(re.findall(r"\w+", search_lower))
    candidate_words = set(re.findall(r"\w+", candidate_lower))

    if not search_words:
        return 0.0

    common_words = search_words & candidate_words
    return len(common_words) / len(search_words) * 0.5


def calculate_match_score(search_name: str, candidate_name: str) -> float:
    """Calculate how well the candidate matches the search name."""
    search_lower = normalize_cpu_name(search_name).lower()
    candidate_lower = normalize_cpu_name(candidate_name).lower()

    # 1. モデル番号による精密マッチング
    if (score := _match_by_model_number(search_name, candidate_name, search_lower, candidate_lower)) is not None:
        return score

    # 2. 完全一致
    if search_lower == candidate_lower:
        return 1.0

    # 3. Xeon E5 シリーズ特別処理
    if (score := _match_xeon_e5(search_lower, candidate_lower)) is not None:
        return score

    # 4. Core i シリーズ特別処理
    if (score := _match_core_i(search_lower, candidate_lower)) is not None:
        return score

    # 5. 単語重複によるファジーマッチング
    return _match_by_word_overlap(search_lower, candidate_lower)


def _extract_benchmark_score_from_chart_entry(entry_text: str) -> int | None:
    """チャートエントリからベンチマークスコアを抽出.

    Args:
        entry_text: エントリのテキスト (例: "CPU Name(XX%)12,345$XXX")

    Returns:
        ベンチマークスコア (int) または None
    """
    score_match = re.search(r"\)\s*([\d,]+)", entry_text)
    if not score_match:
        return None

    try:
        return int(score_match.group(1).replace(",", ""))
    except ValueError:
        return None


def _extract_benchmark_score_from_table_cell(cell_text: str) -> int | None:
    """テーブルセルからベンチマークスコアを抽出.

    Args:
        cell_text: セルのテキスト

    Returns:
        ベンチマークスコア (int) または None
    """
    try:
        return int(re.sub(r"[^\d]", "", cell_text))
    except ValueError:
        return None


def search_chart_page(url: str, cpu_name: str) -> tuple[str | None, int | None]:
    """Search for CPU on a chart page (multithread or singlethread)."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.warning("Error fetching %s: %s", url, e)
        return None, None

    soup = bs4.BeautifulSoup(response.text, "html.parser")
    entries = soup.select("ul.chartlist li")

    best_match_name = None
    best_match_score_value = None
    best_score = 0.0

    for entry in entries:
        link = entry.select_one("a")
        if not link:
            continue

        entry_cpu_name = link.get_text(strip=True)
        match_score = calculate_match_score(cpu_name, entry_cpu_name)
        if match_score <= best_score or match_score <= 0.5:
            continue

        benchmark_score = _extract_benchmark_score_from_chart_entry(entry.get_text())
        if benchmark_score is not None:
            best_match_name = entry_cpu_name
            best_match_score_value = benchmark_score
            best_score = match_score

    return best_match_name, best_match_score_value


def search_cpu_list(cpu_name: str) -> tuple[str | None, int | None]:
    """Search for CPU on the CPU list page (for multi-thread score)."""
    try:
        response = requests.get(CPU_LIST_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.warning("Error fetching CPU list page: %s", e)
        return None, None

    soup = bs4.BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", id="cputable")
    if not table:
        return None, None

    tbody = table.find("tbody")
    if not tbody:
        return None, None

    best_match_name = None
    best_match_score_value = None
    best_score = 0.0

    for row in tbody.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        name_link = cells[0].find("a")
        if not name_link:
            continue

        entry_cpu_name = name_link.get_text(strip=True)
        match_score = calculate_match_score(cpu_name, entry_cpu_name)
        if match_score <= best_score or match_score <= 0.5:
            continue

        benchmark_score = _extract_benchmark_score_from_table_cell(cells[1].get_text(strip=True))
        if benchmark_score is not None:
            best_match_name = entry_cpu_name
            best_match_score_value = benchmark_score
            best_score = match_score

    return best_match_name, best_match_score_value


def search_cpu_benchmark(cpu_name: str) -> CPUBenchmark | None:
    """
    Search for CPU benchmark scores on cpubenchmark.net.

    Fetches both multi-thread and single-thread scores.

    Returns CPUBenchmark with multi_thread_score and single_thread_score, or None if not found.
    """
    normalized_name = normalize_cpu_name(cpu_name)

    # Get multi-thread score (try multithread page first, then CPU list)
    multi_name, multi_score = search_chart_page(MULTITHREAD_URL, normalized_name)
    if not multi_score:
        multi_name, multi_score = search_cpu_list(normalized_name)

    # Get single-thread score
    single_name, single_score = search_chart_page(SINGLETHREAD_URL, normalized_name)

    # Use the best matched name
    result_name = multi_name or single_name

    if not result_name:
        return None

    return CPUBenchmark(
        cpu_name=result_name,
        multi_thread_score=multi_score,
        single_thread_score=single_score,
    )


def save_benchmark(cpu_name: str, multi_thread: int | None, single_thread: int | None):
    """Save benchmark data to database."""
    with get_connection(get_cpu_spec_db_path()) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO cpu_benchmark (cpu_name, multi_thread_score, single_thread_score, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (cpu_name, multi_thread, single_thread))
        conn.commit()

    # Invalidate cache when new data is saved
    _benchmark_cache.invalidate("all_benchmarks")


def get_benchmark(cpu_name: str) -> CPUBenchmark | None:
    """Get benchmark data from database."""
    normalized_name = normalize_cpu_name(cpu_name)
    logging.debug("Looking up CPU benchmark for: %s (normalized: %s)", cpu_name, normalized_name)

    with get_connection(get_cpu_spec_db_path()) as conn:
        cursor = conn.cursor()

        # First try exact match
        cursor.execute("""
            SELECT cpu_name, multi_thread_score, single_thread_score
            FROM cpu_benchmark
            WHERE cpu_name = ?
        """, (cpu_name,))

        row = cursor.fetchone()

        if not row:
            # Try fuzzy match with LIKE using original name
            cursor.execute("""
                SELECT cpu_name, multi_thread_score, single_thread_score
                FROM cpu_benchmark
                WHERE cpu_name LIKE ?
            """, (f"%{cpu_name}%",))
            row = cursor.fetchone()

        if not row:
            # Try fuzzy match with LIKE using normalized name
            cursor.execute("""
                SELECT cpu_name, multi_thread_score, single_thread_score
                FROM cpu_benchmark
                WHERE cpu_name LIKE ?
            """, (f"%{normalized_name}%",))
            row = cursor.fetchone()

        if not row:
            # Try model number based matching
            model = extract_model_number(cpu_name)
            if model:
                cursor.execute("""
                    SELECT cpu_name, multi_thread_score, single_thread_score
                    FROM cpu_benchmark
                """)
                all_rows = cursor.fetchall()
                for r in all_rows:
                    db_model = extract_model_number(r[0])
                    if db_model and db_model == model:
                        row = r
                        break

        if row:
            logging.debug("Found benchmark for %s: multi=%s, single=%s", cpu_name, row[1], row[2])
            return CPUBenchmark(
                cpu_name=row[0],
                multi_thread_score=row[1],
                single_thread_score=row[2],
            )

    logging.debug("No benchmark found for: %s", cpu_name)
    return None


def get_all_benchmarks() -> dict[str, CPUBenchmark]:
    """Get all benchmark data from database in a single query.

    Uses in-memory cache with 1 hour TTL to avoid repeated DB queries.

    Returns:
        Dict mapping CPU name to CPUBenchmark
    """
    cache_key = "all_benchmarks"

    # Try cache first
    cached = _benchmark_cache.get(cache_key)
    if cached is not None:
        return cached

    # Fetch from database
    with get_connection(get_cpu_spec_db_path()) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cpu_name, multi_thread_score, single_thread_score
            FROM cpu_benchmark
        """)

        result = {
            row[0]: CPUBenchmark(
                cpu_name=row[0],
                multi_thread_score=row[1],
                single_thread_score=row[2],
            )
            for row in cursor.fetchall()
        }

    # Cache the result
    _benchmark_cache.set(cache_key, result)
    return result


def _find_benchmark_match(
    cpu_name: str, all_benchmarks: dict[str, CPUBenchmark]
) -> CPUBenchmark | None:
    """Find a matching benchmark for a CPU name using various strategies.

    Matching strategies (in order of priority):
    1. Exact match
    2. Substring match (original name)
    3. Substring match (normalized name)
    4. Model number match

    Args:
        cpu_name: CPU name to look up
        all_benchmarks: Dict of all benchmarks from database

    Returns:
        Matching CPUBenchmark or None if not found
    """
    # Try exact match first
    if cpu_name in all_benchmarks:
        return all_benchmarks[cpu_name]

    # Try fuzzy matching
    normalized_name = normalize_cpu_name(cpu_name)
    for db_name, benchmark in all_benchmarks.items():
        if cpu_name in db_name or normalized_name in db_name:
            return benchmark

    # Try model number matching
    if model := extract_model_number(cpu_name):
        for db_name, benchmark in all_benchmarks.items():
            if (db_model := extract_model_number(db_name)) and db_model == model:
                return benchmark

    return None


def get_benchmarks_batch(cpu_names: list[str]) -> dict[str, CPUBenchmark | None]:
    """Get benchmark data for multiple CPUs efficiently.

    Uses a single DB query to fetch all benchmarks, then matches
    against requested CPU names using various matching strategies.

    Args:
        cpu_names: List of CPU names to look up

    Returns:
        Dict mapping requested CPU name to CPUBenchmark (or None if not found)
    """
    all_benchmarks = get_all_benchmarks()
    return {cpu_name: _find_benchmark_match(cpu_name, all_benchmarks) for cpu_name in cpu_names}


def clear_benchmark(cpu_name: str):
    """Clear benchmark data from database."""
    with get_connection(get_cpu_spec_db_path()) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cpu_benchmark WHERE cpu_name = ?", (cpu_name,))
        conn.commit()

    # Invalidate cache when data is deleted
    _benchmark_cache.invalidate("all_benchmarks")


def fetch_and_save_benchmark(cpu_name: str) -> CPUBenchmark | None:
    """Fetch benchmark from web and save to database."""
    logging.info("Fetching CPU benchmark from web for: %s", cpu_name)
    result = search_cpu_benchmark(cpu_name)

    if result:
        logging.info("Found benchmark for %s: multi=%s, single=%s",
                     cpu_name, result.multi_thread_score, result.single_thread_score)
        save_benchmark(
            cpu_name,
            result.multi_thread_score,
            result.single_thread_score
        )
        return result

    logging.warning("Could not find benchmark data for: %s", cpu_name)
    return None


def main():
    """Main function to test the scraper."""
    logging.basicConfig(level=logging.INFO)
    init_db()

    test_cpus = [
        "Core i5-1135G7",
        "Intel Xeon E5-2699 v4",
    ]

    for cpu in test_cpus:
        logging.info("Searching for: %s", cpu)

        # Clear existing cache to re-fetch
        clear_benchmark(cpu)

        # Fetch from web
        result = fetch_and_save_benchmark(cpu)
        if result:
            logging.info("  Found: %s", result)
        else:
            logging.info("  Not found")

        # Be nice to the server
        time.sleep(2)


if __name__ == "__main__":
    main()
