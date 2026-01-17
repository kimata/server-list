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
    model: str
    volume: str

    @classmethod
    def parse(cls, data: dict) -> "StorageConfig":
        """Parse from dictionary."""
        return cls(
            name=data["name"],
            model=data["model"],
            volume=data["volume"],
        )


@dataclass
class VmConfig:
    """VM configuration."""

    name: str

    @classmethod
    def parse(cls, data: dict) -> "VmConfig":
        """Parse from dictionary."""
        return cls(name=data["name"])


@dataclass
class MountConfig:
    """Mount point configuration."""

    label: str
    path: str
    type: str = "filesystem"  # "btrfs", "filesystem", or "windows"

    @classmethod
    def parse(cls, data: dict) -> "MountConfig":
        """Parse from dictionary."""
        label = data["label"]
        # If path is not specified, use label as display path
        path = data.get("path", label)
        return cls(
            label=label,
            path=path,
            type=data.get("type", "filesystem"),
        )


@dataclass
class MachineConfig:
    """Machine (server) configuration."""

    name: str
    mode: str  # Server model name
    cpu: str
    ram: str
    os: str
    storage: list[StorageConfig] = field(default_factory=list)
    filesystem: list[str] = field(default_factory=list)  # e.g., ["zfs"]
    esxi: str | None = None
    ilo: str | None = None
    vm: list[VmConfig] = field(default_factory=list)
    mount: list[MountConfig] = field(default_factory=list)

    @classmethod
    def parse(cls, data: dict) -> "MachineConfig":
        """Parse from dictionary."""
        raw_storage = data.get("storage", [])
        # Parse storage as array of objects
        storage = [StorageConfig.parse(s) for s in raw_storage] if raw_storage else []
        filesystem = data.get("filesystem", [])
        vm = [VmConfig.parse(v) for v in data.get("vm", [])]
        mount = [MountConfig.parse(m) for m in data.get("mount", [])]
        return cls(
            name=data["name"],
            mode=data["mode"],
            cpu=data["cpu"],
            ram=data["ram"],
            os=data["os"],
            storage=storage,
            filesystem=filesystem,
            esxi=data.get("esxi"),
            ilo=data.get("ilo"),
            vm=vm,
            mount=mount,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        result: dict = {
            "name": self.name,
            "mode": self.mode,
            "cpu": self.cpu,
            "ram": self.ram,
            "os": self.os,
        }
        if self.storage:
            result["storage"] = [
                {"name": s.name, "model": s.model, "volume": s.volume}
                for s in self.storage
            ]
        if self.filesystem:
            result["filesystem"] = self.filesystem
        if self.esxi:
            result["esxi"] = self.esxi
        if self.ilo:
            result["ilo"] = self.ilo
        if self.vm:
            result["vm"] = [{"name": v.name} for v in self.vm]
        if self.mount:
            result["mount"] = [
                {"label": m.label, "path": m.path, "type": m.type}
                for m in self.mount
            ]
        return result


@dataclass
class WebappConfig:
    """Web application configuration."""

    static_dir_path: str
    image_dir_path: str

    @classmethod
    def parse(cls, data: dict) -> "WebappConfig":
        """Parse from dictionary."""
        return cls(
            static_dir_path=data["static_dir_path"],
            image_dir_path=data["image_dir_path"],
        )

    def get_static_dir(self, base_dir: Path) -> Path:
        """Get absolute path to static directory."""
        path = Path(self.static_dir_path)
        if not path.is_absolute():
            path = base_dir / path
        return path

    def get_image_dir(self, base_dir: Path) -> Path:
        """Get absolute path to image directory."""
        path = Path(self.image_dir_path)
        if not path.is_absolute():
            path = base_dir / path
        return path


@dataclass
class DataConfig:
    """Data/cache directory configuration."""

    cache: str

    @classmethod
    def parse(cls, data: dict) -> "DataConfig":
        """Parse from dictionary."""
        return cls(cache=data["cache"])

    def get_cache_dir(self, base_dir: Path) -> Path:
        """Get absolute path to cache directory."""
        path = Path(self.cache)
        if not path.is_absolute():
            path = base_dir / path
        return path


@dataclass
class Config:
    """Main configuration class representing config.yaml."""

    webapp: WebappConfig
    data: DataConfig
    machine: list[MachineConfig]

    @classmethod
    def parse(cls, data: dict) -> "Config":
        """Parse from dictionary (parsed YAML)."""
        webapp = WebappConfig.parse(data["webapp"])
        data_config = DataConfig.parse(data["data"])
        machines = [MachineConfig.parse(m) for m in data["machine"]]
        return cls(
            webapp=webapp,
            data=data_config,
            machine=machines,
        )

    @classmethod
    def load(cls, config_path: Path, schema_path: Path) -> "Config":
        """Load config from YAML file with schema validation."""
        import my_lib.config

        data = my_lib.config.load(config_path, schema_path)
        return cls.parse(data)

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
