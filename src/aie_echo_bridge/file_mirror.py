"""File-substrate-mirror: jede Bridge-Operation wird zusätzlich in
``~/kb/raw/echo-bridge/YYYY-MM-DD-<id>.jsonl`` gespiegelt.

Zweck:
- GAP-Backstop wenn MM oder Honcho transient ausfällt
- Audit-Trail für Joe (alle Brain-Anweisungen sind nachlesbar)
- Substrat-Eintrag für späteres echo_log-Fine-Tuning (Joe-Strategie
  „project_echolog_evolution": eigene Action-Traces = Trainings-Korpus)
"""
from __future__ import annotations

import datetime as dt
import json
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class FileMirror:
    base_dir: Path = field(
        default_factory=lambda: Path.home() / "kb" / "raw" / "echo-bridge"
    )

    def __post_init__(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _log_path(self, day: Optional[dt.date] = None) -> Path:
        d = day or dt.date.today()
        return self.base_dir / f"{d.isoformat()}-bridge.jsonl"

    def append(self, record: dict) -> str:
        """Append ``record`` (with auto-id + auto-ts) as one JSON line.

        Returns the assigned ``id`` for caller's reference.
        """
        rec = dict(record)
        rec.setdefault("id", uuid.uuid4().hex[:12])
        rec.setdefault(
            "ts",
            dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        )
        path = self._log_path()
        line = json.dumps(rec, ensure_ascii=False, sort_keys=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return rec["id"]

    def read_since(self, since: Optional[dt.datetime] = None) -> list[dict]:
        """Read all bridge-records >= ``since`` (default: today only)."""
        if since is None:
            since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=24)
        records: list[dict] = []
        # Walk all log-files in base_dir
        for path in sorted(self.base_dir.glob("*-bridge.jsonl")):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    ts_str = rec.get("ts")
                    if not ts_str:
                        continue
                    try:
                        ts = dt.datetime.fromisoformat(ts_str)
                    except ValueError:
                        continue
                    if ts >= since:
                        records.append(rec)
        return records
