# WP007 final corrective handoff

- Repository: `rebootob/Orbis-Video-Studio-AI`
- Canonical branch: `main`; verified base `6469e2390fea96a8c2693f4eb838c5903d333c45`
- Existing feature branch: `ai/p2-wp007-vidu-job-queue`
- Existing PR: #15; no replacement PR, merge, force push or direct main write.
- HANDOFF_BASE_SHA: `ed2cd596e3d794a56e2e2526fc3f94b76737f5de` (historical commit before this handoff update; always fetch live HEAD).
- WP006: PASS / CLOSED / MERGED.
- WP007: FINAL CORRECTIVE IMPLEMENTED / WAITING CHATGPT INDEPENDENT REVIEW.
- WP008: PROPOSED / NOT AUTHORIZED. Multi-mode changes remain outside WP007.
- Codex: Owner-authorized bounded final corrective complete; STOP after delivery.
- Antigravity / Claude Code: no further execution authorized by this handoff.

The final corrective adds durable claim ownership and fencing before provider
submission, safe quarantine for ambiguous outcomes, deterministic retry and poll
scheduling, strict secret/result persistence boundaries and provider-neutral
cancellation. An explicit DB worker drives due jobs without Redis/Celery.

Validation: full backend 101 passed; WP007 suite with isolated PostgreSQL
concurrency/recovery fixtures 53 passed; migration upgrade head / downgrade -1 /
upgrade head passed on SQLite and PostgreSQL 16.11. No live provider HTTP or
credits used. The temporary PostgreSQL validation server was stopped.

Read [the evidence and operational limits](../40_DELIVERY/WP007_FINAL_CORRECTIVE_EVIDENCE.md)
and `backend/README.md` for worker/API use and reconciliation behavior.

Next allowed action: independent review of the current PR HEAD, followed by
Owner approval. No automatic merge, deployment, WP008, multi-mode, frontend,
media generation, cost ledger or selective-regeneration expansion is authorized.
