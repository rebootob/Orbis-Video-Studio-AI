"""Enrich an R4 STOP artifact with sanitized durable creative audit metadata.

Runs only after the bounded R4 runner has already stopped. It performs no provider
I/O and copies no prompt, response body, error text, header, credential, or media
content. The ephemeral PostgreSQL service is still available at this point.
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from app.db.session import SessionLocal
from app.models.generation_audit import GenerationAuditLog
from wp020_live_r4_contract import R4_EXECUTION_ID, sanitize_creative_audit


def main() -> None:
    evidence_dir = Path(os.environ.get("WP020_LIVE_EVIDENCE_DIR", "live_evidence"))
    summary_path = evidence_dir / "summary.json"
    if not summary_path.exists():
        print("R4 failure export: summary.json not present; nothing to enrich")
        return

    state = json.loads(summary_path.read_text(encoding="utf-8"))
    if state.get("execution_id") != R4_EXECUTION_ID:
        raise RuntimeError("R4 failure export execution identity mismatch")
    if state.get("status") != "STOPPED":
        print("R4 failure export: state is not STOPPED; no enrichment required")
        return

    project_id_raw = state.get("project_id")
    if not project_id_raw:
        print("R4 failure export: no project_id persisted before STOP")
        return
    project_id = uuid.UUID(str(project_id_raw))

    with SessionLocal() as db:
        audit = (
            db.query(GenerationAuditLog)
            .filter(GenerationAuditLog.project_id == project_id)
            .order_by(GenerationAuditLog.created_at.desc())
            .first()
        )
        creative = sanitize_creative_audit(audit)

    if creative:
        failure_evidence = state.get("failure_evidence")
        if not isinstance(failure_evidence, dict):
            failure_evidence = {}
        failure_evidence["creative_audit"] = creative
        state["failure_evidence"] = failure_evidence
        summary_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        print("R4 failure export: sanitized creative audit retained")
    else:
        print("R4 failure export: no creative audit available")


if __name__ == "__main__":
    main()
