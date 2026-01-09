#!/usr/bin/env python3
"""
Shared database utilities for server-list.

Provides common path definitions and database connection utilities
using my_lib.sqlite_util for Kubernetes-optimized SQLite operations.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import my_lib.sqlite_util

if TYPE_CHECKING:
    from server_list.config import Config

# Base directory paths (defaults, can be overridden by config)
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
SCHEMA_DIR = BASE_DIR / "schema"

# Data directory (default, can be overridden by init_from_config)
DATA_DIR = BASE_DIR / "data"

# Database paths (default, updated by init_from_config)
SERVER_DATA_DB = DATA_DIR / "server_data.db"
CACHE_DB = DATA_DIR / "cache.db"
CPU_SPEC_DB = DATA_DIR / "cpu_spec.db"

# Image directory (default, can be overridden by init_from_config)
IMAGE_DIR = BASE_DIR / "img"

# Schema paths
SQLITE_SCHEMA_PATH = SCHEMA_DIR / "sqlite.schema"
SECRET_SCHEMA_PATH = SCHEMA_DIR / "secret.schema"
CONFIG_SCHEMA_PATH = SCHEMA_DIR / "config.schema"

# Config file paths
CONFIG_PATH = BASE_DIR / "config.yaml"
SECRET_PATH = BASE_DIR / "secret.yaml"


def init_from_config(config: Config) -> None:
    """Initialize paths from Config object.

    Updates module-level path variables based on config values.

    Args:
        config: Config object with data and webapp settings.
    """
    global DATA_DIR, SERVER_DATA_DB, CACHE_DB, CPU_SPEC_DB, IMAGE_DIR

    # Update data directory from config
    DATA_DIR = config.data.get_cache_dir(BASE_DIR)
    SERVER_DATA_DB = DATA_DIR / "server_data.db"
    CACHE_DB = DATA_DIR / "cache.db"
    CPU_SPEC_DB = DATA_DIR / "cpu_spec.db"

    # Update image directory from config
    IMAGE_DIR = config.webapp.get_image_dir(BASE_DIR)


def ensure_data_dir() -> None:
    """Ensure the data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection(db_path: Path, timeout: float = 10.0):
    """
    Get a database connection with proper cleanup.

    Uses my_lib.sqlite_util for Kubernetes-optimized SQLite settings.

    Args:
        db_path: Path to the database file
        timeout: Connection timeout in seconds

    Yields:
        sqlite3.Connection: Database connection
    """
    ensure_data_dir()
    with my_lib.sqlite_util.connect(db_path, timeout=timeout) as conn:
        yield conn


def init_schema(db_path: Path, schema_sql: str) -> None:
    """
    Initialize database with given schema SQL.

    Args:
        db_path: Path to the database file
        schema_sql: SQL script to execute for schema creation
    """
    with get_connection(db_path) as conn:
        conn.executescript(schema_sql)
        conn.commit()


def init_schema_from_file(db_path: Path, schema_path: Path) -> None:
    """
    Initialize database with schema from a file.

    Args:
        db_path: Path to the database file
        schema_path: Path to the schema SQL file
    """
    with schema_path.open(encoding="utf-8") as f:
        schema_sql = f.read()
    init_schema(db_path, schema_sql)
    # Run migrations after schema initialization
    migrate_schema(db_path)


def migrate_schema(db_path: Path) -> None:
    """
    Run schema migrations to add new columns to existing tables.

    This handles adding columns that were added after the initial schema.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # Check if esxi_version column exists in uptime_info
        cursor.execute("PRAGMA table_info(uptime_info)")
        columns = [row[1] for row in cursor.fetchall()]

        if "esxi_version" not in columns:
            cursor.execute("ALTER TABLE uptime_info ADD COLUMN esxi_version TEXT")
            conn.commit()
