import threading
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import load_config
from app.main import create_app
from app.services.upstream import UpstreamImage, UpstreamResult


class MockUpstreamClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def run_image_task(self, *, prompt: str, mode: str, params: dict[str, object], input_paths: list[Path], mask_path: Path | None) -> UpstreamResult:
        self.calls.append(
            {
                "prompt": prompt,
                "mode": mode,
                "params": params,
                "input_paths": input_paths,
                "mask_path": mask_path,
            }
        )
        return UpstreamResult(
            images=[UpstreamImage(content=b"fake-output", mime_type="image/png", filename="out.png")],
            actual_params={"size": params.get("size")},
            revised_prompt="revised prompt",
        )


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
supported_sizes = ["1024x1024"]

[app.default_params]
size = "1024x1024"
quality = "auto"

[images]
storage_dir = "images"
""".strip(),
        encoding="utf-8",
    )


def make_client(tmp_path: Path) -> tuple[TestClient, MockUpstreamClient]:
    config_path = tmp_path / "config.toml"
    write_config(config_path)
    upstream = MockUpstreamClient()
    app = create_app(load_config(config_path), upstream_client=upstream, run_tasks_inline=True)
    return TestClient(app), upstream


def make_async_client(tmp_path: Path) -> tuple[TestClient, MockUpstreamClient]:
    config_path = tmp_path / "config.toml"
    write_config(config_path)
    upstream = MockUpstreamClient()
    app = create_app(load_config(config_path), upstream_client=upstream, run_tasks_inline=False)
    return TestClient(app), upstream


def auth_headers() -> dict[str, str]:
    return {"X-Access-Token": "secret-token"}


def test_create_task_runs_upstream_and_persists_output(tmp_path: Path) -> None:
    client, upstream = make_client(tmp_path)

    response = client.post(
        "/api/tasks",
        headers=auth_headers(),
        data={
            "prompt": "draw a cat",
            "mode": "generate",
            "params": '{"size":"1024x1024"}',
            "n": "1",
            "size": "1024x1024",
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["request_id"]
    assert created["status"] == "queued"
    assert len(upstream.calls) == 1

    detail = client.get(f"/api/tasks/{created['request_id']}", headers=auth_headers())
    assert detail.status_code == 200
    assert detail.headers["cache-control"] == "no-store, max-age=0"
    assert detail.headers["pragma"] == "no-cache"
    assert detail.headers["expires"] == "0"
    payload = detail.json()
    assert payload["status"] == "succeeded"
    assert payload["prompt"] == "draw a cat"
    assert payload["output_image_ids"]
    assert payload["actual_params"] == {"size": "1024x1024"}
    assert payload["revised_prompt"] == "revised prompt"

    image_id = payload["output_image_ids"][0]
    image = client.get(f"/api/images/{image_id}", headers=auth_headers())
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert image.content == b"fake-output"

    download = client.get(f"/api/images/{image_id}/download", headers=auth_headers())
    assert download.status_code == 200
    assert "attachment" in download.headers["content-disposition"]


def test_post_task_detail_returns_same_payload_as_get(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    created = client.post(
        "/api/tasks",
        headers=auth_headers(),
        data={"prompt": "post detail", "mode": "generate", "params": "{}"},
    ).json()

    get_detail = client.get(f"/api/tasks/{created['request_id']}", headers=auth_headers())
    post_detail = client.post(f"/api/tasks/{created['request_id']}", headers=auth_headers())

    assert get_detail.status_code == 200
    assert post_detail.status_code == 200
    assert post_detail.headers["cache-control"] == "no-store, max-age=0"
    assert post_detail.json() == get_detail.json()


def test_create_edit_task_persists_input_and_mask(tmp_path: Path) -> None:
    client, upstream = make_client(tmp_path)

    response = client.post(
        "/api/tasks",
        headers=auth_headers(),
        data={"prompt": "edit", "mode": "edit", "params": "{}", "mask_target_index": "0"},
        files={
            "input_images": ("input.png", b"input-bytes", "image/png"),
            "mask": ("mask.png", b"mask-bytes", "image/png"),
        },
    )

    assert response.status_code == 201
    request_id = response.json()["request_id"]
    detail = client.get(f"/api/tasks/{request_id}", headers=auth_headers()).json()
    assert detail["input_image_ids"]
    assert detail["mask_image_id"]
    assert upstream.calls[0]["mode"] == "edit"
    assert len(upstream.calls[0]["input_paths"]) == 1
    assert upstream.calls[0]["mask_path"] is not None


def test_list_tasks_endpoint_is_not_available(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)

    response = client.get("/api/tasks", headers=auth_headers())

    assert response.status_code == 404


def test_create_task_rejects_invalid_params_json(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)

    response = client.post(
        "/api/tasks",
        headers=auth_headers(),
        data={"prompt": "bad", "mode": "generate", "params": "not-json"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "params must be a JSON object"


def test_create_task_spawns_detached_worker_when_not_inline(tmp_path: Path, monkeypatch) -> None:
    client, upstream = make_async_client(tmp_path)
    started: list[threading.Thread] = []

    real_thread = threading.Thread

    class ThreadSpy(real_thread):
        def start(self) -> None:  # type: ignore[override]
            started.append(self)

    monkeypatch.setattr("app.routers.tasks.threading.Thread", ThreadSpy)

    response = client.post(
        "/api/tasks",
        headers=auth_headers(),
        data={"prompt": "async", "mode": "generate", "params": "{}"},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "queued"
    assert len(started) == 1
    assert upstream.calls == []


def test_retry_creates_new_task_from_existing_task(tmp_path: Path) -> None:
    client, upstream = make_client(tmp_path)
    original = client.post(
        "/api/tasks",
        headers=auth_headers(),
        data={"prompt": "retry me", "mode": "generate", "params": '{"size":"1024x1024"}'},
    ).json()

    response = client.post(f"/api/tasks/{original['request_id']}/retry", headers=auth_headers())

    assert response.status_code == 201
    retried = response.json()
    assert retried["request_id"] != original["request_id"]
    assert len(upstream.calls) == 2

    detail = client.get(f"/api/tasks/{retried['request_id']}", headers=auth_headers()).json()
    assert detail["prompt"] == "retry me"
    assert detail["params"] == {"size": "1024x1024"}
    assert detail["status"] == "succeeded"


def test_delete_task_removes_records_and_files_by_default(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    created = client.post(
        "/api/tasks",
        headers=auth_headers(),
        data={"prompt": "delete me", "mode": "generate", "params": "{}"},
    ).json()
    detail = client.get(f"/api/tasks/{created['request_id']}", headers=auth_headers()).json()
    image_id = detail["output_image_ids"][0]
    image_before_delete = client.get(f"/api/images/{image_id}", headers=auth_headers())
    assert image_before_delete.status_code == 200

    response = client.delete(f"/api/tasks/{created['request_id']}", headers=auth_headers())

    assert response.status_code == 200
    assert response.json() == {"deleted": True}
    assert client.get(f"/api/tasks/{created['request_id']}", headers=auth_headers()).status_code == 404
    assert client.get(f"/api/images/{image_id}", headers=auth_headers()).status_code == 404


def test_delete_task_can_keep_image_files(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    created = client.post(
        "/api/tasks",
        headers=auth_headers(),
        data={"prompt": "keep files", "mode": "generate", "params": "{}"},
    ).json()
    detail = client.get(f"/api/tasks/{created['request_id']}", headers=auth_headers()).json()
    image_id = detail["output_image_ids"][0]
    assert client.get(f"/api/images/{image_id}", headers=auth_headers()).status_code == 200

    response = client.delete(
        f"/api/tasks/{created['request_id']}?keep_images=true",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {"deleted": True}
    assert client.get(f"/api/tasks/{created['request_id']}", headers=auth_headers()).status_code == 404
    assert client.get(f"/api/images/{image_id}", headers=auth_headers()).status_code == 404
    assert list((tmp_path / "images" / "outputs").glob("*.png"))
