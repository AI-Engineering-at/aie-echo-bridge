"""High-level orchestrator combining mm_dm + honcho_note + file_mirror.

Public API for CLI + tests.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import os
from dataclasses import dataclass, field
from typing import Optional

from .file_mirror import FileMirror
from .honcho_note import HonchoConfig, HonchoNoteClient
from .mm_dm import MMConfig, MattermostDMClient


@dataclass
class BridgeMessage:
    """One bridge unit: an instruction from Brain or a reply from echo_log."""

    type: str            # "anweisung" | "frage" | "antwort" | "test" | ...
    content: str
    direction: str       # "brain->echo_log" or "echo_log->brain"
    id: Optional[str] = None
    ts: Optional[str] = None
    transport: Optional[str] = None   # "mm" | "honcho" | "file_only"

    def to_record(self) -> dict:
        rec = dataclasses.asdict(self)
        return {k: v for k, v in rec.items() if v is not None}


@dataclass
class EchoBridge:
    """High-level Brain <-> echo_log bridge.

    All operations write to the file-mirror first (so even if MM and
    Honcho both fail, the audit-record exists). MM is tried as primary
    transport. Honcho is tried as backup. ``transport`` in the response
    tells the caller which transport actually succeeded.
    """

    mm_config: Optional[MMConfig] = None
    honcho_config: Optional[HonchoConfig] = None
    file_mirror: FileMirror = field(default_factory=FileMirror)

    def _build_mm(self) -> Optional[MattermostDMClient]:
        if not self.mm_config or not self.mm_config.api_token:
            return None
        try:
            return MattermostDMClient(self.mm_config)
        except Exception:
            return None

    def _build_honcho(self) -> Optional[HonchoNoteClient]:
        if not self.honcho_config:
            return None
        try:
            return HonchoNoteClient(self.honcho_config)
        except Exception:
            return None

    def send(self, msg: BridgeMessage) -> BridgeMessage:
        """Send Brain->echo_log instruction.

        Order: file-mirror (always) -> MM (primary) -> Honcho (backup).
        """
        if msg.direction != "brain->echo_log":
            raise ValueError("send() expects direction='brain->echo_log'")
        record = msg.to_record()
        msg.id = self.file_mirror.append(record)
        msg.transport = "file_only"

        mm = self._build_mm()
        if mm is not None:
            try:
                body = self._format_dm(msg)
                mm.send_dm(body)
                msg.transport = "mm"
            except Exception:
                pass
            finally:
                mm.close()

        if msg.transport == "file_only":
            honcho = self._build_honcho()
            if honcho is not None:
                try:
                    honcho.append_note({
                        "id": msg.id,
                        "type": msg.type,
                        "content": msg.content,
                        "from": "brain",
                    })
                    msg.transport = "honcho"
                except Exception:
                    pass
                finally:
                    honcho.close()

        return msg

    def read(self, since: Optional[dt.datetime] = None) -> list[BridgeMessage]:
        """Read echo_log->Brain replies via MM + file-mirror.

        File-mirror is the union — every reply also gets mirrored when
        observed. This makes ``read()`` idempotent for the local audit
        even across restarts.
        """
        replies: list[BridgeMessage] = []

        mm = self._build_mm()
        if mm is not None:
            try:
                since_ms = (
                    int(since.timestamp() * 1000)
                    if since is not None
                    else mm.now_ms() - 24 * 3600 * 1000
                )
                posts = mm.echo_log_replies(since_ms=since_ms)
                for p in posts:
                    bm = BridgeMessage(
                        type="antwort",
                        content=p.get("message", ""),
                        direction="echo_log->brain",
                        id=p.get("id"),
                        ts=dt.datetime.fromtimestamp(
                            p.get("create_at", 0) / 1000,
                            tz=dt.timezone.utc,
                        ).isoformat(timespec="seconds"),
                        transport="mm",
                    )
                    replies.append(bm)
                    self.file_mirror.append(bm.to_record())
            except Exception:
                pass
            finally:
                mm.close()

        return replies

    @staticmethod
    def _format_dm(msg: BridgeMessage) -> str:
        return (
            f"[brain-bridge {msg.type} {msg.id}]\n"
            f"{msg.content}"
        )


def make_default_bridge() -> EchoBridge:
    """Construct an EchoBridge with env-vars wired in.

    Reads MATTERMOST_URL, MATTERMOST_TOKEN, ECHO_LOG_DM_CHANNEL,
    ECHO_LOG_USER_ID, HONCHO_BASE_URL, HONCHO_API_TOKEN from environment.
    """
    mm_cfg = None
    if os.environ.get("MATTERMOST_TOKEN"):
        mm_cfg = MMConfig(
            base_url=os.environ.get("MATTERMOST_URL", MMConfig.base_url),
            dm_channel_id=os.environ.get(
                "ECHO_LOG_DM_CHANNEL", MMConfig.dm_channel_id
            ),
            echo_log_user_id=os.environ.get(
                "ECHO_LOG_USER_ID", MMConfig.echo_log_user_id
            ),
            api_token=os.environ["MATTERMOST_TOKEN"],
        )

    honcho_cfg = HonchoConfig(
        base_url=os.environ.get("HONCHO_BASE_URL", HonchoConfig.base_url),
        api_token=os.environ.get("HONCHO_API_TOKEN"),
    )

    return EchoBridge(mm_config=mm_cfg, honcho_config=honcho_cfg)
