<!-- W41-DOC-SWEEP-FRONTMATTER
---
title: aie-echo-bridge — FALLBACK-Chain
stand: 2026-05-26
gelockt-am: mutable
mutability: mutable-mit-stand
hash-chain: nein
review-due: 2026-08-26
quelle: W11-D + DEC-A30/A31 + ~/kb/ops/FALLBACK-CHAINS.md
operationalisiert: A30/A31 (Fallback-Chain-Doku-Pflicht) · Regel 16 (Fallback-Chain-Pflicht)
cross-ref: ~/kb/ops/FALLBACK-CHAINS.md (Master) · BAUTEILE-INVENTAR.md #17
---
-->

# FALLBACK — aie-echo-bridge

> **Domäne:** Substrat-Bridge / MM-Send
> **Welle:** W11-D
> **Master-SSOT:** `~/kb/ops/FALLBACK-CHAINS.md` (kanonisch).
> Dieses File ist Bauteil-lokale Spiegelung für schnellen Inzident-Lookup.

## Chain-Zusammenfassung

Vault-Token + MM-API (Primary) -> Token-Refresh-Loop (F1) -> File-Queue (F2)

## Trigger-Bedingungen

| Trigger | Bedeutung | Beispiel |
|---------|-----------|----------|
| **HTTP 401** | Unauthorized | Token abgelaufen / nicht im Vault |
| **HTTP 429** | Rate-Limit | Account-Quota erschöpft |
| **HTTP 5xx** | Server-Error | Upstream-Outage |
| **timeout >Ns** | Connect/Read-Timeout | Network-down |
| **FileNotFoundError** | File missing | Pfad falsch / nicht synced |
| **ImportError** | Library missing | venv / pip install fehlt |

## Rollback-Pattern

1. **Auto-Heal:** Health-Probe erkennt Recovery → automatisch Primary.
2. **Service-Restart:** launchd/systemd Restart on failure.
3. **Manual-Intervention:** Joe-DM via aie-echo-bridge.
4. **Last-Resort-Joe-Physisch:** Power-Cycle, Console-Login.

## A33-Anti-Slop-Garantie

**KEIN MOCK** in Production-Pfad. Bei Endpoint-down / Vault-fail:
- UI/Caller bekommt **strukturierten Error** (`—`, leeres JSONL, oder
  Banner „Quelle nicht erreichbar").
- **NIE** erfundene Daten, Phantom-Counts oder Hardcoded-Stub-Response.

## Cross-References

- **Master-Inventar:** `~/kb/ops/FALLBACK-CHAINS.md`
- **Anti-Pattern A30/A31:** `~/kb/ops/META-LEARNINGS.md`
- **CLAUDE.md Regel 16:** Fallback-Chain-Pflicht pro Bauteil
- **CLAUDE.md Regel 19:** KEIN-MOCK-ABSOLUT (A33)

---

*Erstellt 2026-05-26 W41-DOC-SWEEP · Idempotent · Master = FALLBACK-CHAINS.md*
