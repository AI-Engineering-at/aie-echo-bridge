"""Mattermost-DM transport for Brain <-> echo_log bridge.

Wire-Format aligned with Mattermost v4 API
(https://api.mattermost.com/#tag/posts).

Send-Pattern:
  POST /api/v4/posts  body={channel_id, message, props}

Read-Pattern (poll):
  GET /api/v4/channels/{channel_id}/posts?since={ms_ts}&per_page=N

Echo_log User-ID + DM-Channel-ID are configurable; defaults from
substrate raw/2026-05-25-welle-9-brain-fragen-an-echo-log.md §0:
  echo_log MM-User id: rbuq48qpr7b6ff88cuiugaz7jh
  DM-Channel hermes<->echo_log: uqpf345hnp8688mm85ddkm8q4y
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

DEFAULT_BASE_URL = "http://10.40.10.83:8065"
DEFAULT_ECHO_LOG_DM_CHANNEL = "uqpf345hnp8688mm85ddkm8q4y"
DEFAULT_ECHO_LOG_USER_ID = "rbuq48qpr7b6ff88cuiugaz7jh"


@dataclass
class MMConfig:
    base_url: str = DEFAULT_BASE_URL
    dm_channel_id: str = DEFAULT_ECHO_LOG_DM_CHANNEL
    echo_log_user_id: str = DEFAULT_ECHO_LOG_USER_ID
    api_token: Optional[str] = None  # NEVER hardcoded — read from env
    timeout: float = 8.0


class MattermostDMClient:
    """Minimal Mattermost-v4 client for DM-send + DM-read.

    The client is intentionally narrow — only the 3 endpoints we need
    for the bridge are wrapped. Real-token validation happens by the
    Mattermost server returning 401, not by client-side guesswork.
    """

    def __init__(self, config: MMConfig, transport: Optional[httpx.BaseTransport] = None):
        if not config.api_token:
            raise ValueError(
                "MMConfig.api_token is required — pass it from MATTERMOST_TOKEN env"
            )
        self.config = config
        self._client = httpx.Client(
            base_url=config.base_url,
            headers={"Authorization": f"Bearer {config.api_token}"},
            timeout=config.timeout,
            transport=transport,
        )

    def ping(self) -> dict:
        """Hit /api/v4/system/ping — used by `aie-echo-bridge ping`."""
        resp = self._client.get("/api/v4/system/ping")
        resp.raise_for_status()
        return resp.json()

    def send_dm(self, message: str, props: Optional[dict] = None) -> dict:
        """POST a message to the configured DM-channel.

        Returns the created post (incl. id + create_at) for caller's
        audit-trail.
        """
        payload: dict = {
            "channel_id": self.config.dm_channel_id,
            "message": message,
        }
        if props:
            payload["props"] = props
        resp = self._client.post("/api/v4/posts", json=payload)
        resp.raise_for_status()
        return resp.json()

    def read_dm(self, since_ms: Optional[int] = None, per_page: int = 30) -> dict:
        """Read recent posts from the DM-channel.

        ``since_ms`` is a Mattermost-style unix-ms timestamp. If None,
        returns the most recent ``per_page`` posts.
        """
        params: dict = {"per_page": per_page}
        if since_ms is not None:
            params["since"] = since_ms
        resp = self._client.get(
            f"/api/v4/channels/{self.config.dm_channel_id}/posts",
            params=params,
        )
        resp.raise_for_status()
        return resp.json()

    def echo_log_replies(self, since_ms: int) -> list[dict]:
        """Filter read_dm()-output to posts authored by echo_log only."""
        data = self.read_dm(since_ms=since_ms)
        posts = data.get("posts", {})
        return [
            p for p in posts.values()
            if p.get("user_id") == self.config.echo_log_user_id
        ]

    @staticmethod
    def now_ms() -> int:
        return int(time.time() * 1000)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "MattermostDMClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
