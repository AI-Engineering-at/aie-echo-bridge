"""aie-echo-bridge CLI.

Examples:
    aie-echo-bridge ping
    aie-echo-bridge send --type=anweisung --content="Status-Check"
    aie-echo-bridge read --since=1h
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys

from .bridge import BridgeMessage, make_default_bridge


def _parse_since(arg: str) -> dt.datetime:
    """Parse '1h' / '24h' / '30m' / ISO-8601 -> aware datetime UTC."""
    arg = arg.strip()
    now = dt.datetime.now(dt.timezone.utc)
    if arg.endswith("h"):
        return now - dt.timedelta(hours=int(arg[:-1]))
    if arg.endswith("m"):
        return now - dt.timedelta(minutes=int(arg[:-1]))
    if arg.endswith("d"):
        return now - dt.timedelta(days=int(arg[:-1]))
    # ISO
    return dt.datetime.fromisoformat(arg)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aie-echo-bridge")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("version", help="print package version")
    sub.add_parser("ping", help="ping Mattermost + Honcho")

    send_p = sub.add_parser("send", help="send instruction Brain->echo_log")
    send_p.add_argument("--type", default="anweisung")
    send_p.add_argument("--content", required=True)

    read_p = sub.add_parser("read", help="read echo_log->Brain replies")
    read_p.add_argument("--since", default="1h")

    args = parser.parse_args(argv)

    if args.cmd == "version":
        from . import __version__
        print(__version__)
        return 0

    if args.cmd == "ping":
        from .mm_dm import MattermostDMClient
        import os
        ok_mm, ok_honcho = False, False
        if os.environ.get("MATTERMOST_TOKEN"):
            try:
                from .mm_dm import MMConfig
                cfg = MMConfig(
                    base_url=os.environ.get(
                        "MATTERMOST_URL", MMConfig.base_url
                    ),
                    api_token=os.environ["MATTERMOST_TOKEN"],
                )
                with MattermostDMClient(cfg) as c:
                    c.ping()
                ok_mm = True
            except Exception as e:
                print(f"mm ping failed: {e}", file=sys.stderr)
        try:
            import httpx
            from .honcho_note import HonchoConfig
            base = os.environ.get("HONCHO_BASE_URL", HonchoConfig.base_url)
            r = httpx.get(base, timeout=4.0)
            ok_honcho = r.status_code < 500
        except Exception as e:
            print(f"honcho ping failed: {e}", file=sys.stderr)
        print(json.dumps({"mm": ok_mm, "honcho": ok_honcho}))
        return 0 if (ok_mm or ok_honcho) else 2

    if args.cmd == "send":
        msg = BridgeMessage(
            type=args.type,
            content=args.content,
            direction="brain->echo_log",
        )
        bridge = make_default_bridge()
        out = bridge.send(msg)
        print(json.dumps(out.to_record(), ensure_ascii=False, sort_keys=True))
        return 0

    if args.cmd == "read":
        since = _parse_since(args.since)
        bridge = make_default_bridge()
        replies = bridge.read(since=since)
        print(
            json.dumps(
                [m.to_record() for m in replies],
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
