"""aie-echo-bridge — Brain <-> echo_log bidirectional bridge.

Komponente 1: mm_dm        — Mattermost-DM Send/Read (primary transport)
Komponente 2: honcho_note  — Honcho-peer-metadata Send/Read (backup transport)
Komponente 3: file_mirror  — Substrate-mirror to ~/kb/raw/echo-bridge/ (audit)
Komponente 4: cli          — `aie-echo-bridge send|read|ping`
"""

from .mm_dm import MattermostDMClient, MMConfig
from .honcho_note import HonchoNoteClient, HonchoConfig
from .file_mirror import FileMirror
from .bridge import EchoBridge, BridgeMessage

__all__ = [
    "MattermostDMClient",
    "MMConfig",
    "HonchoNoteClient",
    "HonchoConfig",
    "FileMirror",
    "EchoBridge",
    "BridgeMessage",
]

__version__ = "0.1.0"
