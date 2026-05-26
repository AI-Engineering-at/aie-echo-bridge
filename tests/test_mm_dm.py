"""Tests for the Mattermost-v4 DM-Client."""
from __future__ import annotations

import httpx
import pytest

from aie_echo_bridge.mm_dm import MMConfig, MattermostDMClient


def test_config_requires_token():
    with pytest.raises(ValueError):
        MattermostDMClient(MMConfig(api_token=None))


def test_send_dm_uses_bearer_token_and_channel(monkeypatch):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["body"] = request.content.decode()
        return httpx.Response(
            201,
            json={
                "id": "post1",
                "channel_id": "uqpf345hnp8688mm85ddkm8q4y",
                "message": "hi",
                "create_at": 1234567890123,
                "user_id": "brain-mac",
            },
        )

    transport = httpx.MockTransport(handler)
    cfg = MMConfig(api_token="t1")
    client = MattermostDMClient(cfg, transport=transport)
    out = client.send_dm("hi")
    assert out["id"] == "post1"
    assert "Bearer t1" == captured["auth"]
    assert "uqpf345hnp8688mm85ddkm8q4y" in captured["body"]
    assert "/api/v4/posts" in captured["url"]
    client.close()


def test_read_dm_passes_since_param():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            json={
                "order": ["p1"],
                "posts": {
                    "p1": {
                        "id": "p1",
                        "user_id": "rbuq48qpr7b6ff88cuiugaz7jh",
                        "message": "antwort",
                        "create_at": 9999,
                    }
                },
            },
        )

    transport = httpx.MockTransport(handler)
    cfg = MMConfig(api_token="t1")
    client = MattermostDMClient(cfg, transport=transport)
    data = client.read_dm(since_ms=1234)
    assert "since=1234" in captured["url"]
    assert "p1" in data["posts"]
    client.close()


def test_echo_log_replies_filters_by_user():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "order": ["p1", "p2"],
                "posts": {
                    "p1": {
                        "id": "p1",
                        "user_id": "rbuq48qpr7b6ff88cuiugaz7jh",
                        "message": "echo_log msg",
                        "create_at": 1,
                    },
                    "p2": {
                        "id": "p2",
                        "user_id": "other",
                        "message": "other msg",
                        "create_at": 2,
                    },
                },
            },
        )

    transport = httpx.MockTransport(handler)
    client = MattermostDMClient(MMConfig(api_token="t1"), transport=transport)
    replies = client.echo_log_replies(since_ms=0)
    assert len(replies) == 1
    assert replies[0]["message"] == "echo_log msg"
    client.close()


def test_ping_returns_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "OK"})

    transport = httpx.MockTransport(handler)
    client = MattermostDMClient(MMConfig(api_token="t1"), transport=transport)
    out = client.ping()
    assert out["status"] == "OK"
    client.close()


def test_token_is_not_hardcoded():
    """Regression: ensure no token literal is hardcoded in mm_dm.py."""
    import pathlib
    src = (
        pathlib.Path(__file__).parent.parent / "src" / "aie_echo_bridge" / "mm_dm.py"
    ).read_text(encoding="utf-8")
    # No token-like uppercase chars-long literals beyond placeholder names
    assert "api_token=" not in src.replace("api_token=None", "")
    assert "Bearer t1" not in src
