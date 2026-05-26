<!-- W41-DOC-SWEEP-FRONTMATTER
---
title: aie-echo-bridge — Substrat-Bridge / MM-Send
stand: 2026-05-26
gelockt-am: mutable
mutability: mutable
hash-chain: nein
review-due: 2026-08-26
quelle: W11-D Build-Beleg + BAUTEILE-INVENTAR.md #17
operationalisiert: M40 (Bauteil-Disziplin) · A30/A31 (Fallback-Chain-Doku) · Regel 17 (Doku-Versionierung)
welle: W41-DOC-SWEEP (2026-05-26)
cross-ref: ~/kb/ops/BAUTEILE-INVENTAR.md #17 · ~/kb/ops/FALLBACK-CHAINS.md · ~/kb/ops/DOCU-VERSIONING-LOCK.md
---
-->

# aie-echo-bridge

Bidirektionale Brücke Brain (Mac-CLI) ↔ echo_log (.80 Voice-Gateway).

## Transports

1. **MM-DM** (primary): Brain sendet via Hermes-Token an Mattermost-DM-Channel
   `@echo_log`. Antworten werden gepollt aus dem gleichen Channel.
2. **Honcho-peer-memory** (backup): Anweisungen werden als
   `peer.metadata`-Note geschrieben + gelesen aus
   `.82:8055/v3/workspaces/{ws}/peers/echo_log.80`.
3. **File-Substrate-Mirror** (audit): jede Anweisung + Antwort wird zusätzlich
   in `~/kb/raw/echo-bridge/YYYY-MM-DD-<id>.jsonl` gespiegelt für GAP-Backstop.

## CLI

```bash
aie-echo-bridge send --type=anweisung --content="Status-Check"
aie-echo-bridge read --since=1h
aie-echo-bridge ping
```

## Tests

```bash
python -m pytest -v
```

## Reach-Status (Stand 2026-05-25)

- MM `.83:8065` -> erreichbar (Hermes-Token in `~/.hermes/.env`)
- Honcho `.82:8055` -> erreichbar (root endpoint)
- `.80` direct SSH -> NICHT erreichbar (Brain hat keinen Jump-Host-Key)

→ Bridge funktioniert read+write von Mac aus über MM + Honcho.
   Deploy auf `.80` erfordert Joe-Step (siehe Build-Report §2).
