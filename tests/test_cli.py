"""CLI smoke tests."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from aie_echo_bridge import cli


def test_version(capsys):
    rc = cli.main(["version"])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    from aie_echo_bridge import __version__
    assert out == __version__


def test_send_offline_uses_file_only(tmp_path, monkeypatch, capsys):
    """Without MATTERMOST_TOKEN env, send falls back to file_only."""
    monkeypatch.delenv("MATTERMOST_TOKEN", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    rc = cli.main(["send", "--type=test", "--content=hello-cli"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["transport"] == "file_only"
    assert out["content"] == "hello-cli"


def test_parse_since_relative():
    import datetime as dt
    val = cli._parse_since("2h")
    now = dt.datetime.now(dt.timezone.utc)
    delta = now - val
    assert 1.9 * 3600 < delta.total_seconds() < 2.1 * 3600
