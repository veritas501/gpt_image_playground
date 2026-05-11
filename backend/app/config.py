from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ServerConfig:
    host: str
    port: int


@dataclass(frozen=True)
class SecurityConfig:
    access_token: str


@dataclass(frozen=True)
class UpstreamConfig:
    base_url: str
    api_key: str
    default_model: str
    timeout_seconds: int


@dataclass(frozen=True)
class AppConfig:
    app_name: str
    api_mode: str
    static_dir: Path
    supported_sizes: list[str] = field(default_factory=list)
    default_params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ImagesConfig:
    storage_dir: Path


@dataclass(frozen=True)
class Settings:
    project_root: Path
    server: ServerConfig
    security: SecurityConfig
    upstream: UpstreamConfig
    app: AppConfig
    images: ImagesConfig


def default_config_path() -> Path:
    env_path = os.getenv("IMAGE2_GEN_CONFIG")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return Path(__file__).resolve().parents[1] / "config.toml"


def load_config(path: str | Path | None = None) -> Settings:
    config_path = Path(path).expanduser().resolve() if path else default_config_path()
    if not config_path.exists():
        raise ConfigError(f"config file not found: {config_path}")

    try:
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid config file: {exc}") from exc

    root = config_path.parent
    return Settings(
        project_root=root,
        server=ServerConfig(
            host=_required(data, "server", "host"),
            port=int(_required(data, "server", "port")),
        ),
        security=SecurityConfig(
            access_token=_required(data, "security", "access_token"),
        ),
        upstream=UpstreamConfig(
            base_url=_required(data, "upstream", "base_url").rstrip("/"),
            api_key=_required(data, "upstream", "api_key"),
            default_model=_required(data, "upstream", "default_model"),
            timeout_seconds=int(_required(data, "upstream", "timeout_seconds")),
        ),
        app=AppConfig(
            app_name=_required(data, "app", "app_name"),
            api_mode=_required(data, "app", "api_mode"),
            static_dir=_resolve_path(root, _required(data, "app", "static_dir")),
            supported_sizes=list(data.get("app", {}).get("supported_sizes", [])),
            default_params=dict(data.get("app", {}).get("default_params", {})),
        ),
        images=ImagesConfig(
            storage_dir=_resolve_path(root, _required(data, "images", "storage_dir")),
        ),
    )


def _required(data: dict[str, Any], section: str, key: str) -> Any:
    section_data = data.get(section)
    if not isinstance(section_data, dict) or key not in section_data:
        raise ConfigError(f"missing required config: {section}.{key}")
    value = section_data[key]
    if isinstance(value, str) and not value:
        raise ConfigError(f"empty required config: {section}.{key}")
    return value


def _resolve_path(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (root / path).resolve()
