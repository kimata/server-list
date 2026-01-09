#!/usr/bin/env python3
"""
CPU Benchmark scraper from cpubenchmark.net
Fetches multi-thread and single-thread performance scores and stores them in SQLite database.
"""

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from server_list.spec.db import CPU_SPEC_DB, get_connection

# Re-export for backward compatibility with tests
DB_PATH = CPU_SPEC_DB

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
    with get_connection(DB_PATH) as conn:
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


def calculate_match_score(search_name: str, candidate_name: str) -> float:
    """Calculate how well the candidate matches the search name."""
    # Normalize both names before comparing
    search_lower = normalize_cpu_name(search_name).lower()
    candidate_lower = normalize_cpu_name(candidate_name).lower()

    search_model = extract_model_number(search_name)
    candidate_model = extract_model_number(candidate_name)

    if search_model and candidate_model:
        if search_model == candidate_model:
            return 1.0
        if search_model in candidate_model or candidate_model in search_model:
            search_version = re.search(r"v(\d)", search_lower)
            candidate_version = re.search(r"v(\d)", candidate_lower)
            if search_version and candidate_version:
                if search_version.group(1) != candidate_version.group(1):
                    return 0.3
            return 0.9

    if search_lower == candidate_lower:
        return 1.0

    search_id_match = re.search(r"e5-(\d{4})", search_lower)
    candidate_id_match = re.search(r"e5-(\d{4})", candidate_lower)
    if search_id_match and candidate_id_match:
        if search_id_match.group(1) == candidate_id_match.group(1):
            search_v = re.search(r"v(\d)", search_lower)
            candidate_v = re.search(r"v(\d)", candidate_lower)
            if search_v and candidate_v and search_v.group(1) == candidate_v.group(1):
                return 0.95
            elif not search_v and not candidate_v:
                return 0.95
        return 0.2

    search_core = re.search(r"i([3579])-(\d{4,5})", search_lower)
    candidate_core = re.search(r"i([3579])-(\d{4,5})", candidate_lower)
    if search_core and candidate_core:
        if search_core.group(1) == candidate_core.group(1) and search_core.group(2) == candidate_core.group(2):
            return 0.95
        return 0.2

    search_words = set(re.findall(r"\w+", search_lower))
    candidate_words = set(re.findall(r"\w+", candidate_lower))

    if not search_words:
        return 0.0

    common_words = search_words & candidate_words
    return len(common_words) / len(search_words) * 0.5


def search_chart_page(url: str, cpu_name: str) -> tuple[str | None, int | None]:
    """Search for CPU on a chart page (multithread or singlethread)."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
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

            if match_score > best_score and match_score > 0.5:
                entry_text = entry.get_text()
                # Format: "CPU Name(XX%)12,345$XXX" or "CPU Name(XX%)12,345NA"
                score_match = re.search(r"\)\s*([\d,]+)", entry_text)
                if score_match:
                    try:
                        benchmark_score = int(score_match.group(1).replace(",", ""))
                        best_match_name = entry_cpu_name
                        best_match_score_value = benchmark_score
                        best_score = match_score
                    except ValueError:
                        pass

        return best_match_name, best_match_score_value

    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None, None


def search_cpu_list(cpu_name: str) -> tuple[str | None, int | None]:
    """Search for CPU on the CPU list page (for multi-thread score)."""
    try:
        response = requests.get(CPU_LIST_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
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

            if match_score > best_score and match_score > 0.5:
                try:
                    score_text = cells[1].get_text(strip=True)
                    benchmark_score = int(re.sub(r"[^\d]", "", score_text))
                    best_match_name = entry_cpu_name
                    best_match_score_value = benchmark_score
                    best_score = match_score
                except ValueError:
                    pass

        return best_match_name, best_match_score_value

    except requests.RequestException as e:
        print(f"Error fetching CPU list page: {e}")
        return None, None


def search_cpu_benchmark(cpu_name: str) -> dict | None:
    """
    Search for CPU benchmark scores on cpubenchmark.net.

    Fetches both multi-thread and single-thread scores.

    Returns dict with multi_thread_score and single_thread_score, or None if not found.
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

    return {
        "cpu_name": result_name,
        "multi_thread_score": multi_score,
        "single_thread_score": single_score,
    }


def save_benchmark(cpu_name: str, multi_thread: int | None, single_thread: int | None):
    """Save benchmark data to database."""
    with get_connection(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO cpu_benchmark (cpu_name, multi_thread_score, single_thread_score, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (cpu_name, multi_thread, single_thread))
        conn.commit()


def get_benchmark(cpu_name: str) -> dict | None:
    """Get benchmark data from database."""
    normalized_name = normalize_cpu_name(cpu_name)
    logging.debug("Looking up CPU benchmark for: %s (normalized: %s)", cpu_name, normalized_name)

    with get_connection(DB_PATH) as conn:
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
            return {
                "cpu_name": row[0],
                "multi_thread_score": row[1],
                "single_thread_score": row[2],
            }

    logging.debug("No benchmark found for: %s", cpu_name)
    return None


def clear_benchmark(cpu_name: str):
    """Clear benchmark data from database."""
    with get_connection(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cpu_benchmark WHERE cpu_name = ?", (cpu_name,))
        conn.commit()


def fetch_and_save_benchmark(cpu_name: str) -> dict | None:
    """Fetch benchmark from web and save to database."""
    logging.info("Fetching CPU benchmark from web for: %s", cpu_name)
    result = search_cpu_benchmark(cpu_name)

    if result:
        logging.info("Found benchmark for %s: multi=%s, single=%s",
                     cpu_name, result.get("multi_thread_score"), result.get("single_thread_score"))
        save_benchmark(
            cpu_name,
            result.get("multi_thread_score"),
            result.get("single_thread_score")
        )
        return result

    logging.warning("Could not find benchmark data for: %s", cpu_name)
    return None


def main():
    """Main function to test the scraper."""
    init_db()

    test_cpus = [
        "Core i5-1135G7",
        "Intel Xeon E5-2699 v4",
    ]

    for cpu in test_cpus:
        print(f"\nSearching for: {cpu}")

        # Clear existing cache to re-fetch
        clear_benchmark(cpu)

        # Fetch from web
        result = fetch_and_save_benchmark(cpu)
        if result:
            print(f"  Found: {result}")
        else:
            print("  Not found")

        # Be nice to the server
        time.sleep(2)


if __name__ == "__main__":
    main()
