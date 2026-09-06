# WP007 final corrective evidence

Validated 2026-09-06 on existing PR #15 / `ai/p2-wp007-vidu-job-queue`.
The final evidence describes the committed source accompanying this document;
fetch the live PR HEAD rather than treating a handoff SHA as the current HEAD.

## Executed checks

| Check | Result |
| --- | --- |
| `python -m pytest -q --disable-warnings` | 101 passed, 2 warnings, 11.72 seconds |
| `python -m pytest tests/test_generation_queue.py -q --disable-warnings` with `WP007_TEST_DATABASE_URL` | 53 passed, 1 warning, 8.75 seconds |
| SQLite: `python -m alembic upgrade head` | PASS, revision `007_queue_safety` |
| SQLite: `python -m alembic downgrade -1` | PASS, revision `006_vidu_queue` |
| SQLite: `python -m alembic upgrade head` | PASS, revision `007_queue_safety` |
| PostgreSQL 16.11: same upgrade / downgrade -1 / upgrade sequence | PASS, all three commands |
| `git diff --check` | PASS |

The normal full backend fixtures use SQLite. In the second run, the durable
queue fixtures use independent PostgreSQL connections in isolated schemas;
other API/unit fixtures still use SQLite. These fixtures exercise simultaneous
claim/dispatch, simultaneous idempotent creation, concurrent polling and cancel,
process-death recovery, stale completion fencing and worker restart. PostgreSQL
was initialized in a temporary directory, bound only to loopback and stopped
after validation. No production database or provider was used.

All WP007 HTTP calls are mocked. An autouse guard rejects unmocked async HTTP.
Tests also cover current Vidu request/header mapping, submit/status/cancel,
configuration/rejection failures, 400/401/403, transient 429/eligible 5xx and
network/timeout handling, retry exhaustion, timing eligibility, nested secret
rejection, API output, unlabelled provider exceptions, output URL metadata and
absence of fabricated Asset records. Migration data tests check clean-payload
preservation and unsafe/ambiguous legacy quarantine.

## Safety behavior and limits

- Submission requires an unexpired persisted claim token and atomic
  `CLAIMED -> SUBMITTING` transition. An attempt marker is committed before HTTP.
- A lost response or process death cannot requeue the chargeable operation.
  Ambiguous submissions/cancels enter `RECONCILIATION_REQUIRED`; no automated
  reset/requeue path is provided. A known provider ID is only polled, never
  submitted again. Late results cannot overwrite a recovered lease.
- Safe pre-send connection failures and 429 can retry with persisted bounded
  backoff. Eligible 5xx are transient, but ambiguous submission 5xx are
  quarantined; safe status GETs can retry them. This deliberately favors avoiding
  duplicate charges over automatic recovery of an unknown submission.
- Polls have a persisted 10-second minimum interval and atomic ownership.
  Retry schedules start after the response; terminal/exhausted work cannot be
  submitted again. Poll exhaustion requires reconciliation.
- Arbitrary raw provider results and errors are not persisted. The allowlist
  stores status, safe output URLs and bounded numeric progress. Job errors use
  fixed messages. Nested secret-like parameters and configured secret values
  are rejected without echoing the input. Ordinary API responses omit claim tokens.
- Cancel is provider-neutral and only calls the adapter for known active jobs;
  pending work cancels locally and terminal calls are idempotent. Busy operations
  are not concurrently cancelled. Provider rejection/failure does not claim a
  successful cancellation and is safely rescheduled for status observation.
- Migration 007 preserves clean request payloads, removes legacy untrusted
  result/error data and quarantines unsafe or ambiguous work. Downgrade does not
  restore discarded untrusted data or reverse quarantine. Migration 006 is unchanged.
- Output URLs remain job metadata. No object-storage ingestion or fake Asset
  checksum/size is introduced.

## Vidu contract references

Checked against official documentation on 2026-09-06:

- [Text to Video](https://platform.vidu.com/docs/text-to-video)
- [Reference to Video](https://platform.vidu.com/docs/reference-to-video)
- [Get Generation](https://platform.vidu.com/docs/get-generation)
- [Cancel Generation](https://platform.vidu.com/docs/cancel-generation)

Token authentication, explicit text2video/reference2video requests, task creations
polling and cancel path/body are covered by mocked tests. The server-configured
`viduq2` default supports both implemented paths. No live paid generation was
performed; live provider acceptance is not claimed.

No WP008, multi-mode, frontend, timeline, audio, Redis/Celery, cost ledger,
selective regeneration or deployment work was performed. Independent review and
Owner merge approval remain outstanding; no implementation blocker is known.
