from pathlib import Path

import pytest

from app.config import ConfigError, load_config


def write_config(path: Path, storage_dir: str = "../data/images") -> None:
    path.write_text(
        f"""
[server]
host = "127.0.0.1"
port = 8000

[security]
access_token = "secret-token"

[upstream]
base_url = "https://internal.example.test/v1"
api_key = "sk-test"
default_model = "gpt-image-2"
timeout_seconds = 120

[app]
app_name = "Image Gen"
api_mode = "images"
static_dir = "../frontend/dist"
supported_sizes = ["1024x1024"]

[app.default_params]
size = "1024x1024"
quality = "auto"

[images]
storage_dir = "{storage_dir}"
""".strip(),
        encoding="utf-8",
    )


def test_load_config_resolves_relative_paths(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    write_config(config_path, "images")

    config = load_config(config_path)

    assert config.security.access_token == "secret-token"
    assert config.upstream.default_model == "gpt-image-2"
    assert config.images.storage_dir == tmp_path / "images"
    assert config.app.static_dir == tmp_path.parent / "frontend" / "dist"


def test_load_config_rejects_missing_required_section(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text("[server]\nport = 8000\n", encoding="utf-8")

    with pytest.raises(ConfigError):
        load_config(config_path)
