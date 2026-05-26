"""Tests for the Honcho-peer-metadata backup transport."""
from __future__ import annotations

import httpx
import pytest

from aie_echo_bridge.honcho_note import BRIDGE_METADATA_KEY, HonchoConfig, HonchoNoteClient


def test_get_notes_empty_when_no_metadata():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "echo_log.80"})

    transport = httpx.MockTransport(handler)
    client = HonchoNoteClient(HonchoConfig(), transport=transport)
    notes = client.get_notes()
    assert notes == []
    client.close()


def test_get_notes_returns_existing():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "echo_log.80",
                "metadata": {
                    BRIDGE_METADATA_KEY: [
                        {"id": "n1", "type": "anweisung", "content": "x"}
                    ]
                },
            },
        )

    transport = httpx.MockTransport(handler)
    client = HonchoNoteClient(HonchoConfig(), transport=transport)
    notes = client.get_notes()
    assert len(notes) == 1
    assert notes[0]["id"] == "n1"
    client.close()


def test_append_note_preserves_other_metadata_keys():
    seen_put_body = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "id": "echo_log.80",
                    "metadata": {
                        "other_key": "keep_me",
                        BRIDGE_METADATA_KEY: [{"id": "n0"}],
                    },
                },
            )
        if request.method == "PUT":
            import json as _json
            seen_put_body.update(_json.loads(request.content.decode()))
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(405)

    transport = httpx.MockTransport(handler)
    client = HonchoNoteClient(HonchoConfig(), transport=transport)
    client.append_note({"id": "n1", "type": "anweisung", "content": "x"})
    assert seen_put_body["metadata"]["other_key"] == "keep_me"
    notes = seen_put_body["metadata"][BRIDGE_METADATA_KEY]
    assert len(notes) == 2
    assert notes[-1]["id"] == "n1"
    client.close()


def test_url_uses_workspace_and_peer_id():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"id": "echo_log.80"})

    transport = httpx.MockTransport(handler)
    cfg = HonchoConfig(workspace="aie", peer_id="echo_log.80")
    client = HonchoNoteClient(cfg, transport=transport)
    client.get_notes()
    assert "/v3/workspaces/aie/peers/echo_log.80" in captured["url"]
    client.close()
