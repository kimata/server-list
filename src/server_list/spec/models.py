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
    def parse(cls, data: dict) -> "VMInfo":
        """Create VMInfo from dictionary."""
        return cls(
            esxi_host=data["esxi_host"],
            vm_name=data["vm_name"],
            cpu_count=data.get("cpu_count"),
            ram_mb=data.get("ram_mb"),
            storage_gb=data.get("storage_gb"),
            power_state=data.get("power_state"),
            cpu_usage_mhz=data.get("cpu_usage_mhz"),
            memory_usage_mb=data.get("memory_usage_mb"),
            collected_at=data.get("collected_at"),
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
    def parse(cls, data: dict) -> "HostInfo":
        """Create HostInfo from dictionary."""
        return cls(
            host=data["host"],
            boot_time=data.get("boot_time"),
            uptime_seconds=data.get("uptime_seconds"),
            status=data.get("status", "unknown"),
            cpu_threads=data.get("cpu_threads"),
            cpu_cores=data.get("cpu_cores"),
            os_version=data.get("os_version"),
            cpu_usage_percent=data.get("cpu_usage_percent"),
            memory_usage_percent=data.get("memory_usage_percent"),
            memory_total_bytes=data.get("memory_total_bytes"),
            memory_used_bytes=data.get("memory_used_bytes"),
            collected_at=data.get("collected_at"),
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
    def parse(cls, data: dict) -> "PowerInfo":
        """Create PowerInfo from dictionary."""
        return cls(
            power_watts=data.get("power_watts"),
            power_average_watts=data.get("power_average_watts"),
            power_max_watts=data.get("power_max_watts"),
            power_min_watts=data.get("power_min_watts"),
            collected_at=data.get("collected_at"),
        )


@dataclass
class CollectionStatus:
    """Data collection status for a host."""

    host: str
    last_fetch: str | None
    status: str

    @classmethod
    def parse(cls, data: dict) -> "CollectionStatus":
        """Create CollectionStatus from dictionary."""
        return cls(
            host=data["host"],
            last_fetch=data.get("last_fetch"),
            status=data.get("status", "unknown"),
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
    def parse(cls, data: dict) -> "ZfsPoolInfo":
        """Create ZfsPoolInfo from dictionary."""
        return cls(
            pool_name=data.get("pool_name", data.get("pool", "unknown")),
            size_bytes=data.get("size_bytes"),
            allocated_bytes=data.get("allocated_bytes"),
            free_bytes=data.get("free_bytes"),
            health=data.get("health"),
            collected_at=data.get("collected_at"),
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
    def parse(cls, data: dict) -> "MountInfo":
        """Create MountInfo from dictionary."""
        return cls(
            mountpoint=data.get("mountpoint", ""),
            size_bytes=data.get("size_bytes"),
            avail_bytes=data.get("avail_bytes"),
            used_bytes=data.get("used_bytes"),
            collected_at=data.get("collected_at"),
        )


@dataclass
class CPUBenchmark:
    """CPU benchmark scores from cpubenchmark.net."""

    cpu_name: str
    multi_thread_score: int | None
    single_thread_score: int | None

    @classmethod
    def parse(cls, data: dict) -> "CPUBenchmark":
        """Create CPUBenchmark from dictionary."""
        return cls(
            cpu_name=data["cpu_name"],
            multi_thread_score=data.get("multi_thread_score"),
            single_thread_score=data.get("single_thread_score"),
        )


@dataclass
class UsageMetrics:
    """CPU/メモリ使用率データ (Prometheus から取得)."""

    cpu_usage_percent: float | None = None
    memory_usage_percent: float | None = None
    memory_total_bytes: float | None = None
    memory_used_bytes: float | None = None

    @classmethod
    def parse(cls, data: dict) -> "UsageMetrics":
        """Create UsageMetrics from dictionary."""
        return cls(
            cpu_usage_percent=data.get("cpu_usage_percent"),
            memory_usage_percent=data.get("memory_usage_percent"),
            memory_total_bytes=data.get("memory_total_bytes"),
            memory_used_bytes=data.get("memory_used_bytes"),
        )


@dataclass
class UptimeData:
    """稼働時間データ (Prometheus から取得)."""

    boot_time: str
    uptime_seconds: float
    status: str

    @classmethod
    def parse(cls, data: dict) -> "UptimeData":
        """Create UptimeData from dictionary."""
        return cls(
            boot_time=data["boot_time"],
            uptime_seconds=data["uptime_seconds"],
            status=data.get("status", "running"),
        )


@dataclass
class StorageMetrics:
    """ストレージメトリクス (Prometheus から取得)."""

    size_bytes: float
    avail_bytes: float
    used_bytes: float

    @classmethod
    def parse(cls, data: dict) -> "StorageMetrics":
        """Create StorageMetrics from dictionary."""
        return cls(
            size_bytes=data["size_bytes"],
            avail_bytes=data["avail_bytes"],
            used_bytes=data["used_bytes"],
        )
