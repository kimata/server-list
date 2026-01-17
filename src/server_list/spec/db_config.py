#!/usr/bin/env python3
"""
Database path management module.

Provides centralized management of database paths with getter/setter pattern
for testability. Each module can import the specific getter/setter it needs.

Example usage:
    from server_list.spec.db_config import (
        get_server_data_db_path,
        set_server_data_db_path,
    )

    # In test
    set_server_data_db_path(temp_path / "test.db")
"""

from dataclasses import dataclass, field
from pathlib import Path

from server_list.spec.db import CACHE_DB, CPU_SPEC_DB, SERVER_DATA_DB


@dataclass
class _DbPaths:
    """Internal container for database paths.

    This class is not exported; use the getter/setter functions instead.
    """

    server_data: Path = field(default_factory=lambda: SERVER_DATA_DB)
    cpu_spec: Path = field(default_factory=lambda: CPU_SPEC_DB)
    cache: Path = field(default_factory=lambda: CACHE_DB)


_paths = _DbPaths()


# Server data database (VM info, host info, etc.)
def get_server_data_db_path() -> Path:
    """Get the server data database path."""
    return _paths.server_data


def set_server_data_db_path(path: Path) -> None:
    """Set the server data database path (for testing)."""
    _paths.server_data = path


# CPU spec database (benchmark scores)
def get_cpu_spec_db_path() -> Path:
    """Get the CPU spec database path."""
    return _paths.cpu_spec


def set_cpu_spec_db_path(path: Path) -> None:
    """Set the CPU spec database path (for testing)."""
    _paths.cpu_spec = path


# Cache database (config cache)
def get_cache_db_path() -> Path:
    """Get the cache database path."""
    return _paths.cache


def set_cache_db_path(path: Path) -> None:
    """Set the cache database path (for testing)."""
    _paths.cache = path


def reset_all_paths() -> None:
    """Reset all paths to defaults (for testing cleanup)."""
    global _paths
    _paths = _DbPaths()
