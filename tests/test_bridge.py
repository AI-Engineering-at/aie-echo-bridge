"""Tests for the high-level EchoBridge orchestrator."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import httpx
import pytest

from aie_echo_bridge.bridge import BridgeMessage, EchoBridge
from aie_echo_bridge.file_mirror import FileMirror
from aie_echo_bridge.honcho_note import HonchoConfig
from aie_echo_bridge.mm_dm import MMConfig


def _mm_success_handler(captured):
    def handler(request: httpx.Request) -> httpx.Response:
        captured["last_url"] = str(request.url)
        captured["last_body"] = request.content.decode() if request.content else ""
        if request.method == "POST" and "/api/v4/posts" in str(request.url):
            return httpx.Response(
                201,
                json={
                    "id": "post-1",
                    "channel_id": "uqpf345hnp8688mm85ddkm8q4y",
                    "user_id": "brain",
                    "create_at": 1700000000000,
                    "message": "hi",
                },
            )
        if request.method == "GET" and "/posts" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "order": ["p1"],
                    "posts": {
                        "p1": {
                            "id": "p1",
                            "user_id": "rbuq48qpr7b6ff88cuiugaz7jh",
                            "create_at": 1700000001000,
                            "message": "echo_log reply",
                        }
                    },
                },
            )
        return httpx.Response(405)

    return handler


def test_send_writes_file_mirror_even_without_transports(tmp_path: Path):
    bridge = EchoBridge(file_mirror=FileMirror(base_dir=tmp_path))
    msg = BridgeMessage(
        type="anweisung",
        content="hello",
        direction="brain->echo_log",
    )
    out = bridge.send(msg)
    assert out.transport == "file_only"
    assert out.id is not None
    files = list(tmp_path.glob("*-bridge.jsonl"))
    assert len(files) == 1


def test_send_rejects_wrong_direction(tmp_path: Path):
    bridge = EchoBridge(file_mirror=FileMirror(base_dir=tmp_path))
    msg = BridgeMessage(
        type="antwort",
        content="x",
        direction="echo_log->brain",
    )
    with pytest.raises(ValueError):
        bridge.send(msg)


class _MMSuccessBridge(EchoBridge):
    """EchoBridge that injects a MockTransport into its MM-client."""

    def __init__(self, transport, **kwargs):
        super().__init__(**kwargs)
        self._mock_transport = transport

    def _build_mm(self):
        from aie_echo_bridge.mm_dm import MattermostDMClient
        if not self.mm_config or not self.mm_config.api_token:
            return None
        return MattermostDMClient(self.mm_config, transport=self._mock_transport)


def test_send_via_mm_when_token_set(tmp_path: Path):
    captured = {}
    transport = httpx.MockTransport(_mm_success_handler(captured))
    bridge = _MMSuccessBridge(
        transport=transport,
        mm_config=MMConfig(api_token="t1"),
        file_mirror=FileMirror(base_dir=tmp_path),
    )
    msg = BridgeMessage(
        type="anweisung",
        content="check status",
        direction="brain->echo_log",
    )
    out = bridge.send(msg)
    assert out.transport == "mm"
    assert "brain-bridge" in captured["last_body"]
    assert "check status" in captured["last_body"]


def test_read_returns_echo_log_replies(tmp_path: Path):
    captured = {}
    transport = httpx.MockTransport(_mm_success_handler(captured))
    bridge = _MMSuccessBridge(
        transport=transport,
        mm_config=MMConfig(api_token="t1"),
        file_mirror=FileMirror(base_dir=tmp_path),
    )
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
    replies = bridge.read(since=since)
    assert len(replies) == 1
    assert replies[0].content == "echo_log reply"
    assert replies[0].direction == "echo_log->brain"
    assert replies[0].transport == "mm"
    # File-mirror should have received the reply too
    log_files = list(tmp_path.glob("*-bridge.jsonl"))
    body = "\n".join(p.read_text(encoding="utf-8") for p in log_files)
    assert "echo_log reply" in body


def test_round_trip_audit(tmp_path: Path):
    """Send + read round-trip results in 2 file-mirror entries."""
    captured = {}
    transport = httpx.MockTransport(_mm_success_handler(captured))
    bridge = _MMSuccessBridge(
        transport=transport,
        mm_config=MMConfig(api_token="t1"),
        file_mirror=FileMirror(base_dir=tmp_path),
    )
    bridge.send(BridgeMessage(
        type="anweisung",
        content="please summarize",
        direction="brain->echo_log",
    ))
    bridge.read(since=dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1))
    log_files = list(tmp_path.glob("*-bridge.jsonl"))
    body = "\n".join(p.read_text(encoding="utf-8") for p in log_files).strip()
    lines = [l for l in body.split("\n") if l.strip()]
    assert len(lines) >= 2
    # One brain->echo_log, one echo_log->brain
    dirs = sorted(set(json.loads(l)["direction"] for l in lines))
    assert dirs == ["brain->echo_log", "echo_log->brain"]


def test_bridge_message_to_record_drops_none():
    msg = BridgeMessage(
        type="x",
        content="y",
        direction="brain->echo_log",
    )
    rec = msg.to_record()
    assert "id" not in rec
    assert rec["type"] == "x"
