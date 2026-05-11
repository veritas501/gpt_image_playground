from pathlib import Path

from fastapi.testclient import TestClient

from app.config import load_config
from app.main import create_app


def write_config(path: Path) -> None:
    path.write_text(
        """
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
supported_sizes = ["1024x1024", "1536x1024"]

[app.default_params]
size = "1024x1024"
quality = "auto"

[images]
storage_dir = "images"
""".strip(),
        encoding="utf-8",
    )


def test_health_does_not_require_token(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    write_config(config_path)
    client = TestClient(create_app(load_config(config_path)))

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_app_config_requires_token(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    write_config(config_path)
    client = TestClient(create_app(load_config(config_path)))

    response = client.get("/api/app/config")

    assert response.status_code == 403
    assert response.json() == {"detail": "invalid access token"}


def test_app_config_returns_only_public_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    write_config(config_path)
    client = TestClient(create_app(load_config(config_path)))

    response = client.get("/api/app/config", headers={"X-Access-Token": "secret-token"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["app_name"] == "Image Gen"
    assert payload["default_model"] == "gpt-image-2"
    assert payload["api_mode"] == "images"
    assert payload["supported_sizes"] == ["1024x1024", "1536x1024"]
    assert "api_key" not in payload
    assert "access_token" not in payload
    assert "base_url" not in payload
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["expires"] == "0"


def test_static_index_is_served_when_dist_exists(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    write_config(config_path)
    static_dir = tmp_path.parent / "frontend" / "dist"
    static_dir.mkdir(parents=True)
    (static_dir / "index.html").write_text("<html>spa</html>", encoding="utf-8")
    client = TestClient(create_app(load_config(config_path)))

    response = client.get("/")

    assert response.status_code == 200
    assert "spa" in response.text


def test_app_startup_creates_image_storage_dir(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    write_config(config_path)
    storage_dir = tmp_path / "images"

    assert not storage_dir.exists()

    create_app(load_config(config_path))

    assert storage_dir.exists()
    assert storage_dir.is_dir()
