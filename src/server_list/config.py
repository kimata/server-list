#!/usr/bin/env python3
"""
Configuration dataclasses for server-list.

Provides typed configuration classes that represent config.yaml structure.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class StorageConfig:
    """Storage device configuration."""

    name: str
    model: str | None = None
    volume: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "StorageConfig":
        return cls(
            name=data["name"],
            model=data.get("model"),
            volume=data.get("volume"),
        )


@dataclass
class VmConfig:
    """VM configuration."""

    name: str

    @classmethod
    def from_dict(cls, data: dict) -> "VmConfig":
        return cls(name=data["name"])


@dataclass
class MachineConfig:
    """Machine (server) configuration."""

    name: str
    mode: str | None = None  # Server model name
    cpu: str | None = None
    ram: str | None = None
    storage: list[StorageConfig] | str = field(default_factory=list)
    os: str | None = None
    esxi: str | None = None
    ilo: str | None = None
    vm: list[VmConfig] = field(default_factory=list)
    mount: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "MachineConfig":
        raw_storage = data.get("storage", [])
        # Support both array of storage objects and string 'zfs'
        if isinstance(raw_storage, str):
            storage: list[StorageConfig] | str = raw_storage
        else:
            storage = [StorageConfig.from_dict(s) for s in raw_storage]
        vm = [VmConfig.from_dict(v) for v in data.get("vm", [])]
        mount = data.get("mount", [])
        return cls(
            name=data["name"],
            mode=data.get("mode"),
            cpu=data.get("cpu"),
            ram=data.get("ram"),
            storage=storage,
            os=data.get("os"),
            esxi=data.get("esxi"),
            ilo=data.get("ilo"),
            vm=vm,
            mount=mount,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        result: dict = {"name": self.name}
        if self.mode:
            result["mode"] = self.mode
        if self.cpu:
            result["cpu"] = self.cpu
        if self.ram:
            result["ram"] = self.ram
        if self.storage:
            if isinstance(self.storage, str):
                result["storage"] = self.storage
            else:
                result["storage"] = [
                    {"name": s.name, "model": s.model, "volume": s.volume}
                    for s in self.storage
                ]
        if self.os:
            result["os"] = self.os
        if self.esxi:
            result["esxi"] = self.esxi
        if self.ilo:
            result["ilo"] = self.ilo
        if self.vm:
            result["vm"] = [{"name": v.name} for v in self.vm]
        if self.mount:
            result["mount"] = self.mount
        return result


@dataclass
class WebappConfig:
    """Web application configuration."""

    static_dir_path: str
    image_dir_path: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "WebappConfig":
        return cls(
            static_dir_path=data["static_dir_path"],
            image_dir_path=data.get("image_dir_path"),
        )

    def get_static_dir(self, base_dir: Path) -> Path:
        """Get absolute path to static directory."""
        path = Path(self.static_dir_path)
        if not path.is_absolute():
            path = base_dir / path
        return path

    def get_image_dir(self, base_dir: Path) -> Path:
        """Get absolute path to image directory."""
        if self.image_dir_path:
            path = Path(self.image_dir_path)
            if not path.is_absolute():
                path = base_dir / path
            return path
        return base_dir / "img"


@dataclass
class DataConfig:
    """Data/cache directory configuration."""

    cache: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "DataConfig":
        return cls(cache=data.get("cache"))

    def get_cache_dir(self, base_dir: Path) -> Path:
        """Get absolute path to cache directory."""
        if self.cache:
            path = Path(self.cache)
            if not path.is_absolute():
                path = base_dir / path
            return path
        return base_dir / "data"


@dataclass
class Config:
    """Main configuration class representing config.yaml."""

    webapp: WebappConfig
    machine: list[MachineConfig]
    data: DataConfig = field(default_factory=DataConfig)

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """Create Config from dictionary (parsed YAML)."""
        webapp = WebappConfig.from_dict(data["webapp"])
        machines = [MachineConfig.from_dict(m) for m in data.get("machine", [])]
        data_config = DataConfig.from_dict(data.get("data", {}))
        return cls(
            webapp=webapp,
            machine=machines,
            data=data_config,
        )

    @classmethod
    def load(cls, config_path: Path, schema_path: Path) -> "Config":
        """Load config from YAML file with schema validation."""
        import my_lib.config

        data = my_lib.config.load(config_path, schema_path)
        return cls.from_dict(data)

    def get_machine_by_name(self, name: str) -> MachineConfig | None:
        """Find machine by name."""
        for machine in self.machine:
            if machine.name == name:
                return machine
        return None

    def get_esxi_hosts(self) -> list[str]:
        """Get list of ESXi host names."""
        return [m.name for m in self.machine if m.esxi]

    def is_esxi_host(self, name: str) -> bool:
        """Check if a machine is an ESXi host."""
        machine = self.get_machine_by_name(name)
        return machine is not None and machine.esxi is not None

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "webapp": {
                "static_dir_path": self.webapp.static_dir_path,
                "image_dir_path": self.webapp.image_dir_path,
            },
            "data": {
                "cache": self.data.cache,
            },
            "machine": [m.to_dict() for m in self.machine],
        }
