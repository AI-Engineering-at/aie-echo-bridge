"""Honcho-peer-memory backup transport for the bridge.

Pattern: Brain schreibt eine Note in echo_log's peer.metadata.
Echo_log liest beim nächsten Refresh seine eigene metadata und reagiert
darauf. Diese Bridge-Variante ist **Backup**, weil Honcho-Polling
asynchron + nicht durch User-Aktion gesteuert ist.

Wire-Format folgt v3 peers (analog zu echo-log-rework/honcho_peer):
  GET    /v3/workspaces/{ws}/peers/{peer_id}
  PUT    /v3/workspaces/{ws}/peers/{peer_id}  body={metadata: {...}}
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx

DEFAULT_BASE_URL = "http://10.40.10.82:8055"
DEFAULT_WORKSPACE = "aie"
DEFAULT_PEER_ID = "echo_log.80"
BRIDGE_METADATA_KEY = "brain_bridge_notes"


@dataclass
class HonchoConfig:
    base_url: str = DEFAULT_BASE_URL
    workspace: str = DEFAULT_WORKSPACE
    peer_id: str = DEFAULT_PEER_ID
    api_token: Optional[str] = None
    timeout: float = 8.0


class HonchoNoteClient:
    """Read + Write notes into echo_log's peer.metadata as bridge transport.

    Notes are stored under ``metadata[BRIDGE_METADATA_KEY]`` as a list of
    ``{ts, type, content}``-dicts. The list is the wire-format; the
    client knows nothing else about Honcho-internals.
    """

    def __init__(self, config: HonchoConfig, transport: Optional[httpx.BaseTransport] = None):
        self.config = config
        headers = {}
        if config.api_token:
            headers["Authorization"] = f"Bearer {config.api_token}"
        self._client = httpx.Client(
            base_url=config.base_url,
            headers=headers,
            timeout=config.timeout,
            transport=transport,
        )

    @property
    def _peer_url(self) -> str:
        return (
            f"/v3/workspaces/{self.config.workspace}"
            f"/peers/{self.config.peer_id}"
        )

    def get_notes(self) -> list[dict]:
        resp = self._client.get(self._peer_url)
        resp.raise_for_status()
        peer = resp.json()
        metadata = peer.get("metadata", {}) or {}
        notes = metadata.get(BRIDGE_METADATA_KEY, [])
        return list(notes)

    def append_note(self, note: dict) -> dict:
        """Append ``note`` to peer.metadata[BRIDGE_METADATA_KEY]."""
        # 1. Read current metadata
        resp = self._client.get(self._peer_url)
        resp.raise_for_status()
        peer = resp.json()
        metadata = peer.get("metadata", {}) or {}
        notes = metadata.get(BRIDGE_METADATA_KEY, [])
        notes.append(note)
        metadata[BRIDGE_METADATA_KEY] = notes

        # 2. PUT the updated metadata back
        put_resp = self._client.put(
            self._peer_url,
            json={"metadata": metadata},
        )
        put_resp.raise_for_status()
        return put_resp.json()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HonchoNoteClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
