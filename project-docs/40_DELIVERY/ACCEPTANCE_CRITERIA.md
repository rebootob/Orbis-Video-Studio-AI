# Acceptance Criteria & V1 Pass Verification

> **Canonical Document Location:** [`project-docs/40_DELIVERY/ACCEPTANCE_CRITERIA.md`](project-docs/40_DELIVERY/ACCEPTANCE_CRITERIA.md)

---

## 1. Work Package P0-WP001 Acceptance Criteria

To achieve acceptance for **P0-WP001**, the following criteria MUST be met 100%:

- [x] **Documentation Completeness:** All 26 canonical documents across `00_CONTROL`, `10_GOVERNANCE`, `20_ARCHITECTURE`, `30_PRODUCT`, and `40_DELIVERY`, plus root `README.md`, exist and contain thorough specifications.
- [x] **No Machine-Specific Local Links:** Zero workstation paths (`file:///c:/...`) exist in any documentation file; all links use repository-relative Markdown paths.
- [x] **No Application Code:** Zero application source code, frontend components, backend endpoints, database scripts, or cloud deployments exist in the repository.
- [x] **No Provider Credentials / API Calls:** Zero API keys or live provider API calls (Vidu, etc.) were initiated.
- [x] **Git Branch Standard:** Changes committed to branch `ai/p0-wp001-doc-foundation`.
- [x] **Git Commit Message Standard:** Commit message matches `docs: establish Orbis Video Studio AI governance and architecture foundation`.
- [x] **Pull Request Opened:** Pull Request `#1` opened targeting `main`.
- [x] **Stop Condition Honored:** Execution stopped immediately after pushing corrective commit to PR `#1` without merging or starting P0-WP002.

---

## 2. V1 Release PASS Verification Checklist

For the overall system to achieve **V1 PASS** status, the following workflow capabilities must pass empirical UAT verification:

| Step | User / System Action | Verification Standard | Status |
| :--- | :--- | :--- | :--- |
| **1** | Open Web Application | Workspace loads cleanly in browser without local software installation. | PENDING |
| **2** | Create Project & Ingest Docs | Uploads PDF/Word/PPTX brief; system parses text into story context cleanly. | PENDING |
| **3** | Create & Edit Story/Script | Generates logline, synopsis, formatted script, scenes, and shots editable in UI. | PENDING |
| **4** | Reference Library Setup | Character Bibles and Location Bibles created and tagged to scenes. | PENDING |
| **5** | Shot Generation via Vidu | AI video generated via Vidu provider adapter with reference payloads. | PENDING |
| **6** | Hybrid Shot Import | User successfully uploads external video/image asset to shot timeline. | PENDING |
| **7** | Granular Asset Lock | User locks approved script/shots; system protects them from overwrite during regen. | PENDING |
| **8** | Audio & Subtitle Setup | Configures VO stems, BGM, SFX; auto-ducking attenuates music during dialogue. | PENDING |
| **9** | Timeline Preview & Edit | Trims shots, aligns audio tracks, previews sequence in browser player. | PENDING |
| **10**| Selective Regeneration | Regenerates ONLY target missing/failed unlocked shot; locked shots untouched. | PENDING |
| **11**| Cloud Master Render | Cloud video compositing worker renders master sequence into high-res MP4 file. | PENDING |
| **12**| Multi-Output Export | Renders 16:9 YouTube master and 9:16 TikTok Reels output cleanly without re-gen. | PENDING |
