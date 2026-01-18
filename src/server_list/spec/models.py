#!/usr/bin/env python3
"""
Data models for server-list.

Provides typed dataclasses for VM info, host info, CPU benchmarks, etc.
Used internally by data_collector.py and cpu_benchmark.py.
"""

from dataclasses import dataclass


@dataclass
class VMInfo:
    """VM information collected from ESXi."""

    esxi_host: str
    vm_name: str
    cpu_count: int | None
    ram_mb: int | None
    storage_gb: float | None
    power_state: str | None
    cpu_usage_mhz: int | None = None
    memory_usage_mb: int | None = None
    collected_at: str | None = None

    @classmethod
    def parse_row(cls, row: tuple, esxi_host: str) -> "VMInfo":
        """Create VMInfo from DB row (without esxi_host column)."""
        return cls(
            esxi_host=esxi_host,
            vm_name=row[0],
            cpu_count=row[1],
            ram_mb=row[2],
            storage_gb=round(row[3], 1) if row[3] else None,
            power_state=row[4],
            cpu_usage_mhz=row[5],
            memory_usage_mb=row[6],
            collected_at=row[7],
        )

    @classmethod
    def parse_row_full(cls, row: tuple) -> "VMInfo":
        """Create VMInfo from DB row (with esxi_host column)."""
        return cls(
            vm_name=row[0],
            cpu_count=row[1],
            ram_mb=row[2],
            storage_gb=round(row[3], 1) if row[3] else None,
            power_state=row[4],
            esxi_host=row[5],
            cpu_usage_mhz=row[6],
            memory_usage_mb=row[7],
            collected_at=row[8],
        )


@dataclass
class HostInfo:
    """Host information collected from ESXi or Prometheus."""

    host: str
    boot_time: str | None
    uptime_seconds: float | None
    status: str
    cpu_threads: int | None = None
    cpu_cores: int | None = None
    os_version: str | None = None
    cpu_usage_percent: float | None = None
    memory_usage_percent: float | None = None
    memory_total_bytes: float | None = None
    memory_used_bytes: float | None = None
    collected_at: str | None = None

    @classmethod
    def parse_row(cls, row: tuple) -> "HostInfo":
        """Create HostInfo from DB row."""
        return cls(
            host=row[0],
            boot_time=row[1],
            uptime_seconds=row[2],
            status=row[3],
            cpu_threads=row[4],
            cpu_cores=row[5],
            os_version=row[6],
            cpu_usage_percent=row[7],
            memory_usage_percent=row[8],
            memory_total_bytes=row[9],
            memory_used_bytes=row[10],
            collected_at=row[11],
        )


@dataclass
class PowerInfo:
    """Power consumption information from iLO."""

    power_watts: int | None
    power_average_watts: int | None
    power_max_watts: int | None
    power_min_watts: int | None
    collected_at: str | None = None

    @classmethod
    def parse_row(cls, row: tuple) -> "PowerInfo":
        """Create PowerInfo from DB row (without host column)."""
        return cls(
            power_watts=row[0],
            power_average_watts=row[1],
            power_max_watts=row[2],
            power_min_watts=row[3],
            collected_at=row[4],
        )

    @classmethod
    def parse_row_with_host(cls, row: tuple) -> tuple[str, "PowerInfo"]:
        """Create (host, PowerInfo) tuple from DB row (with host column)."""
        return (
            row[0],
            cls(
                power_watts=row[1],
                power_average_watts=row[2],
                power_max_watts=row[3],
                power_min_watts=row[4],
                collected_at=row[5],
            ),
        )


@dataclass
class CollectionStatus:
    """Data collection status for a host."""

    host: str
    last_fetch: str | None
    status: str

    @classmethod
    def parse_row(cls, row: tuple) -> "CollectionStatus":
        """Create CollectionStatus from DB row."""
        return cls(
            host=row[0],
            last_fetch=row[1],
            status=row[2],
        )


@dataclass
class ZfsPoolInfo:
    """ZFS pool information from Prometheus."""

    pool_name: str
    size_bytes: float | None
    allocated_bytes: float | None
    free_bytes: float | None
    health: float | None
    collected_at: str | None = None

    @classmethod
    def parse_row(cls, row: tuple) -> "ZfsPoolInfo":
        """Create ZfsPoolInfo from DB row."""
        return cls(
            pool_name=row[0],
            size_bytes=row[1],
            allocated_bytes=row[2],
            free_bytes=row[3],
            health=row[4],
            collected_at=row[5],
        )


@dataclass
class MountInfo:
    """Mount point information from Prometheus."""

    mountpoint: str
    size_bytes: float | None
    avail_bytes: float | None
    used_bytes: float | None
    collected_at: str | None = None

    @classmethod
    def parse_row(cls, row: tuple) -> "MountInfo":
        """Create MountInfo from DB row."""
        return cls(
            mountpoint=row[0],
            size_bytes=row[1],
            avail_bytes=row[2],
            used_bytes=row[3],
            collected_at=row[4],
        )


@dataclass
class CPUBenchmark:
    """CPU benchmark scores from cpubenchmark.net."""

    cpu_name: str
    multi_thread_score: int | None
    single_thread_score: int | None


@dataclass
class UsageMetrics:
    """CPU/メモリ使用率データ (Prometheus から取得)."""

    cpu_usage_percent: float | None = None
    memory_usage_percent: float | None = None
    memory_total_bytes: float | None = None
    memory_used_bytes: float | None = None


@dataclass
class UptimeData:
    """稼働時間データ (Prometheus から取得)."""

    boot_time: str
    uptime_seconds: float
    status: str


@dataclass
class StorageMetrics:
    """ストレージメトリクス (Prometheus から取得)."""

    size_bytes: float
    avail_bytes: float
    used_bytes: float
