from pathlib import Path

from app.config import load_config
from app.services.upstream import UpstreamClient


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class FakeHttpClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls: list[tuple[str, str, dict]] = []

    def post(self, url: str, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return FakeResponse(self.payload)

    def get(self, url: str, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return FakeResponse(self.payload)


def write_config(path: Path, api_mode: str = "images") -> None:
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
api_mode = "{api_mode}"
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


def test_responses_generate_builds_request_and_parses_result(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.toml"
    write_config(config_path, api_mode="responses")
    client = UpstreamClient(load_config(config_path))
    fake = FakeHttpClient(
        {
            "output": [
                {
                    "type": "image_generation_call",
                    "result": "ZmFrZS1pbWFnZQ==",
                    "size": "1024x1024",
                    "revised_prompt": "revised prompt",
                }
            ]
        }
    )
    monkeypatch.setattr(client, "_client", lambda: fake)

    result = client.run_image_task(
        prompt="draw a cat",
        mode="generate",
        params={"size": "1024x1024", "output_format": "png", "quality": "auto"},
        input_paths=[],
        mask_path=None,
    )

    method, url, kwargs = fake.calls[0]
    assert method == "POST"
    assert url == "https://internal.example.test/v1/responses"
    assert kwargs["json"]["tools"][0]["action"] == "generate"
    assert kwargs["json"]["tool_choice"] == "required"
    assert kwargs["json"]["input"].startswith("Use the following text as the complete prompt")
    assert result.images[0].content == b"fake-image"
    assert result.revised_prompt == "revised prompt"
    assert result.actual_params == {"size": "1024x1024"}


def test_responses_edit_includes_input_images_and_mask(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.toml"
    write_config(config_path, api_mode="responses")
    input_path = tmp_path / "input.png"
    input_path.write_bytes(b"input")
    mask_path = tmp_path / "mask.png"
    mask_path.write_bytes(b"mask")
    client = UpstreamClient(load_config(config_path))
    fake = FakeHttpClient(
        {
            "output": [
                {
                    "type": "image_generation_call",
                    "result": {"b64_json": "ZmFrZS1pbWFnZQ=="},
                }
            ]
        }
    )
    monkeypatch.setattr(client, "_client", lambda: fake)

    client.run_image_task(
        prompt="edit a cat",
        mode="edit",
        params={"size": "1024x1024", "output_format": "png", "quality": "auto"},
        input_paths=[input_path],
        mask_path=mask_path,
    )

    _, _, kwargs = fake.calls[0]
    payload = kwargs["json"]
    assert payload["tools"][0]["action"] == "edit"
    assert payload["tools"][0]["input_image_mask"]["image_url"].startswith("data:image/png;base64,")
    assert isinstance(payload["input"], list)
    assert payload["input"][0]["content"][1]["type"] == "input_image"


def test_images_edit_uses_real_image_mime_type_for_multipart(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.toml"
    write_config(config_path, api_mode="images")
    input_path = tmp_path / "input.jpeg"
    input_path.write_bytes(b"input")
    client = UpstreamClient(load_config(config_path))
    fake = FakeHttpClient({"data": [{"b64_json": "ZmFrZS1pbWFnZQ=="}]})
    monkeypatch.setattr(client, "_client", lambda: fake)

    client.run_image_task(
        prompt="edit a photo",
        mode="edit",
        params={"size": "1024x1024"},
        input_paths=[input_path],
        mask_path=None,
    )

    _, url, kwargs = fake.calls[0]
    assert url == "https://internal.example.test/v1/images/edits"
    assert kwargs["files"][0][0] == "image"
    assert kwargs["files"][0][1][0] == "input.jpeg"
    assert kwargs["files"][0][1][2] == "image/jpeg"
