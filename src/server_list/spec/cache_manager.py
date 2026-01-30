#!/usr/bin/env python3
"""
Cache manager for server-list data.
Caches config, VM info, CPU benchmarks to SQLite for fast API responses.
Updates data in background and notifies via SSE.
"""

import json
import logging
import pathlib
import sqlite3
import threading
from datetime import datetime

import my_lib.config
import my_lib.webapp.event

import server_list.spec.db
import server_list.spec.db_config

UPDATE_INTERVAL_SEC = 300  # 5 minutes

_update_thread: threading.Thread | None = None
_should_stop = threading.Event()
_db_lock = threading.Lock()
_watch_thread: threading.Thread | None = None
_watch_stop_event: threading.Event | None = None


CACHE_SCHEMA = """
CREATE TABLE IF NOT EXISTS cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


def init_db():
    """Initialize the cache database."""
    with server_list.spec.db.get_connection(
        server_list.spec.db_config.get_cache_db_path()
    ) as conn:
        conn.executescript(CACHE_SCHEMA)
        conn.commit()


def _get_cache(key: str) -> dict | None:
    """Internal: Get cached value by key.

    For type-safe access, use the specialized getters:
    - get_config() for config cache (returns dict | None)

    Args:
        key: Cache key to retrieve

    Returns:
        Cached value as dict, or None if not found
    """
    try:
        with _db_lock, server_list.spec.db.get_connection(
            server_list.spec.db_config.get_cache_db_path()
        ) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM cache WHERE key = ?", (key,))
            row = cursor.fetchone()

            if row:
                return json.loads(row[0])
    except (sqlite3.Error, json.JSONDecodeError) as e:
        logging.warning("Failed to get cache for %s: %s", key, e)

    return None


def _set_cache(key: str, value: dict):
    """Internal: Set cache value."""
    try:
        with _db_lock, server_list.spec.db.get_connection(
            server_list.spec.db_config.get_cache_db_path()
        ) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO cache (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, json.dumps(value, ensure_ascii=False), datetime.now().isoformat()))
            conn.commit()
    except sqlite3.Error as e:
        logging.warning("Failed to set cache for %s: %s", key, e)


def _get_cache_state(db_path: str | pathlib.Path) -> str | None:
    """キャッシュ DB の状態を取得する."""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT MAX(updated_at) FROM cache")
            row = cursor.fetchone()
            return row[0] if row else None
    except sqlite3.Error:
        logging.exception("Failed to get cache state")
        return None


def load_config_from_file() -> dict | None:
    """Load config from YAML file with schema validation.

    Uses my_lib.config.load() for consistent config loading
    with schema validation across the codebase.
    The config path is obtained from db_config for testability.
    Falls back to yaml.safe_load() if schema file is not available (e.g., in tests).
    """
    import yaml

    try:
        config_path = server_list.spec.db_config.get_config_path()
        if not config_path.exists():
            return None

        # Use centralized schema path from db module
        schema_path = server_list.spec.db.CONFIG_SCHEMA_PATH

        # Use schema validation if available, otherwise fallback to yaml.safe_load
        if schema_path.exists():
            return my_lib.config.load(config_path, schema_path)

        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.warning("Failed to load config: %s", e)
        return None


def get_config() -> dict | None:
    """Get config from cache, or load from file if not cached.

    This is the recommended way to access config data, providing
    type-safe access with dict | None return type.

    Returns:
        Config dictionary or None if not available
    """
    cached = _get_cache("config")
    if cached:
        return cached

    # Load from file and cache
    config = load_config_from_file()
    if config:
        _set_cache("config", config)
    return config


def update_all_caches():
    """Update all caches from source data."""
    updated = False

    # Update config cache
    config = load_config_from_file()
    if config:
        old_config = _get_cache("config")
        if old_config != config:
            _set_cache("config", config)
            updated = True
            logging.info("Config cache updated")

    if updated:
        logging.info("Cache updated")
        my_lib.webapp.event.notify_event(my_lib.webapp.event.EVENT_TYPE.CONTENT)


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
    global _update_thread, _watch_thread, _watch_stop_event

    init_db()

    # Initial cache population
    _watch_stop_event, _watch_thread = my_lib.webapp.event.start_db_state_watcher(
        server_list.spec.db_config.get_cache_db_path(),
        _get_cache_state,
        my_lib.webapp.event.EVENT_TYPE.CONTENT,
        notify_on_first=True,
    )

    update_all_caches()

    if _update_thread and _update_thread.is_alive():
        return

    _should_stop.clear()
    _update_thread = threading.Thread(target=_update_worker, daemon=True)
    _update_thread.start()


def stop_cache_worker():
    """Stop the background cache update worker."""
    global _watch_thread, _watch_stop_event
    _should_stop.set()
    if _update_thread:
        _update_thread.join(timeout=5)

    if _watch_thread is not None and _watch_stop_event is not None:
        my_lib.webapp.event.stop_db_state_watcher(_watch_stop_event, _watch_thread)
        _watch_thread = None
        _watch_stop_event = None
