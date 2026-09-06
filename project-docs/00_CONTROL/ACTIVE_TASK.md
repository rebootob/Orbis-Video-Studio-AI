# Active Task Specification

> **Canonical Document Location:** [`project-docs/00_CONTROL/ACTIVE_TASK.md`](project-docs/00_CONTROL/ACTIVE_TASK.md)

---

## Active Work Package

```text
P2-WP010 CORRECTIVE — Mode-Aware Web Workspace & Production UI
```

Status:

```text
IMPLEMENTED / WAITING CHATGPT INDEPENDENT REVIEW
```

Owner Authorization:
Authorized via GitHub Issue #24 on feature branch `ai/p2-wp010-mode-aware-web-workspace` and PR #25.

Execution Engine:
Antigravity (bounded corrective execution complete; STOPPING for ChatGPT review).

### Objective

Deliver production-ready mode-aware web workspace across STORY, SHORT, LOOP, and SCENE modes with full history retention, safe soft archiving, pre-generation cost confirmation gates, staged approval workflow, multi-project management, real document uploads, and honest provider-neutral readiness panels.

Scope Delivered:
1. **Full History Retention & Soft Deletion**: Replaced unsafe hard deletion on Project with soft archiving (`status = "ARCHIVED"`). Projects with recorded jobs/ledger entries cannot be deleted, preserving full auditable provenance. Added explicit archive, unarchive, and duplicate endpoints for projects and scenes.
2. **Deletion Guards on Audit History**: Added conflict guards (HTTP 409) preventing scene or shot deletion if associated with recorded generation jobs or usage ledger records.
3. **Restricted CORS Security**: Configured strict origin whitelist (`http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`, `http://127.0.0.1:3000`) instead of wildcard with credentials.
4. **Staged Workflow & Next Best Action Guidance**: Integrated clear 5-stage progress guidance (`Story` → `Storyboard` → `Shot Plan` → `Images` → `Video`) and Next Recommended Step guidance banner with single primary CTA and plain-language explanation.
5. **Cost Confirmation & Batch Generation**: Built pre-generation `CostConfirmationModal` querying `/projects/{id}/jobs/estimate`, displaying candidate shot count, estimated total cost, explicit `UNKNOWN` pricing warnings when unpriced, and budget hard/soft cap alerts. Added multi-shot selection for "Generate Selected".
6. **Scene & Shot Reordering Controls**: Implemented server-backed reordering endpoints (`PATCH /projects/{id}/scenes/reorder`, `PATCH /scenes/{id}/shots/reorder`) with move up/down controls on UI.
7. **Real File Ingestion**: Replaced placeholder upload alerts with real file inputs calling `POST /api/v1/assets/upload` for both New Project source context and Continuity Reference Documents.
8. **Truthful Audio & QC Panels**: Removed fabricated claims of ElevenLabs/OpenAI TTS, dynamic beat alignment, and specific -14dB auto-ducking. Replaced with honest provider-neutral schema allocation placeholders. Renamed QC audit section to "Generation Dispatch Audit Log & Discovered Assets" and derived checks from real project data.
9. **Zero Live Credits Used**: 100% mocked / zero live provider costs spent.

---

## Current Execution Roles

```text
Owner = final human authority / UAT / merge approval
ChatGPT = Control Plane / Architect / Independent Reviewer
Antigravity = STOP until explicitly authorized for the next bounded task
Codex = STOP
Claude Code = STOP
```

---

## Next Allowed Action

Wait for ChatGPT independent review of PR #25. Do not merge without Owner approval. Do not start WP011.
