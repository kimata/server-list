#!/usr/bin/env python3
"""
Cache manager for server-list data.
Caches config, VM info, CPU benchmarks to SQLite for fast API responses.
Updates data in background and notifies via SSE.
"""

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import yaml

import my_lib.webapp.event

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "cache.db"
CONFIG_PATH = BASE_DIR / "config.yaml"

UPDATE_INTERVAL_SEC = 300  # 5 minutes

_update_thread: threading.Thread | None = None
_should_stop = threading.Event()
_db_lock = threading.Lock()


@contextmanager
def get_db_connection():
    """Get a database connection with proper cleanup."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize the cache database."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def get_cache(key: str) -> dict | list | None:
    """Get cached value by key."""
    try:
        with _db_lock, get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM cache WHERE key = ?", (key,))
            row = cursor.fetchone()

            if row:
                return json.loads(row[0])
    except Exception as e:
        logging.warning("Failed to get cache for %s: %s", key, e)

    return None


def set_cache(key: str, value: dict | list):
    """Set cache value."""
    try:
        with _db_lock, get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO cache (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, json.dumps(value, ensure_ascii=False), datetime.now().isoformat()))
            conn.commit()
    except Exception as e:
        logging.warning("Failed to set cache for %s: %s", key, e)


def load_config_from_file() -> dict | None:
    """Load config from YAML file."""
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, encoding="utf-8") as f:
                return yaml.safe_load(f)
    except Exception as e:
        logging.warning("Failed to load config: %s", e)
    return None


def get_config() -> dict | None:
    """Get config from cache, or load from file if not cached."""
    cached = get_cache("config")
    if cached and isinstance(cached, dict):
        return cached

    # Load from file and cache
    config = load_config_from_file()
    if config:
        set_cache("config", config)
    return config


def update_all_caches():
    """Update all caches from source data."""
    updated = False

    # Update config cache
    config = load_config_from_file()
    if config:
        old_config = get_cache("config")
        if old_config != config:
            set_cache("config", config)
            updated = True
            logging.info("Config cache updated")

    if updated:
        my_lib.webapp.event.notify_event(my_lib.webapp.event.EVENT_TYPE.DATA)
        logging.info("Cache updated, clients notified")


def _update_worker():
    """Background worker that updates caches periodically."""
    logging.info("Cache update worker started (interval: %d sec)", UPDATE_INTERVAL_SEC)

    # Initial update
    update_all_caches()

    while not _should_stop.wait(UPDATE_INTERVAL_SEC):
        update_all_caches()

    logging.info("Cache update worker stopped")


def start_cache_worker():
    """Start the background cache update worker."""
    global _update_thread

    init_db()

    # Initial cache population
    config = load_config_from_file()
    if config:
        set_cache("config", config)

    if _update_thread and _update_thread.is_alive():
        return

    _should_stop.clear()
    _update_thread = threading.Thread(target=_update_worker, daemon=True)
    _update_thread.start()


def stop_cache_worker():
    """Stop the background cache update worker."""
    _should_stop.set()
    if _update_thread:
        _update_thread.join(timeout=5)
