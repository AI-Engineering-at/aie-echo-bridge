"""Tests for the file-substrate mirror."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from aie_echo_bridge.file_mirror import FileMirror


def test_append_writes_jsonl(tmp_path: Path):
    fm = FileMirror(base_dir=tmp_path)
    rec_id = fm.append({"type": "anweisung", "content": "x"})
    assert isinstance(rec_id, str) and len(rec_id) > 0
    log_file = next(tmp_path.glob("*-bridge.jsonl"))
    line = log_file.read_text(encoding="utf-8").strip()
    rec = json.loads(line)
    assert rec["id"] == rec_id
    assert rec["content"] == "x"
    assert "ts" in rec


def test_append_uses_supplied_id(tmp_path: Path):
    fm = FileMirror(base_dir=tmp_path)
    rec_id = fm.append({"id": "fixed1", "type": "x", "content": "y"})
    assert rec_id == "fixed1"


def test_read_since_filters(tmp_path: Path):
    fm = FileMirror(base_dir=tmp_path)
    fm.append({"id": "a", "type": "x", "content": "y"})
    fm.append({"id": "b", "type": "x", "content": "z"})
    now = dt.datetime.now(dt.timezone.utc)
    recs = fm.read_since(since=now - dt.timedelta(minutes=1))
    ids = sorted([r["id"] for r in recs])
    assert ids == ["a", "b"]


def test_read_since_excludes_old(tmp_path: Path):
    fm = FileMirror(base_dir=tmp_path)
    # Inject an old record manually
    old_path = tmp_path / "2025-01-01-bridge.jsonl"
    old_path.write_text(
        json.dumps({"id": "old", "ts": "2025-01-01T00:00:00+00:00", "content": "x"})
        + "\n",
        encoding="utf-8",
    )
    recs = fm.read_since(since=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc))
    assert all(r["id"] != "old" for r in recs)


def test_read_since_default_is_24h(tmp_path: Path):
    fm = FileMirror(base_dir=tmp_path)
    fm.append({"type": "anweisung", "content": "fresh"})
    recs = fm.read_since()
    assert len(recs) >= 1
    assert any(r.get("content") == "fresh" for r in recs)
