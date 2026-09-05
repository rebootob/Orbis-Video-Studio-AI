# Quality, Security & Cost Release Gates

> **Canonical Document Location:** [`project-docs/40_DELIVERY/RELEASE_GATES.md`](project-docs/40_DELIVERY/RELEASE_GATES.md)

---

## 1. Release Gate Architecture

Prior to merging any Work Package or cutting a release tag, the submission MUST pass four sequential release gates.

```mermaid
graph LR
    Sub[WP Submission / PR] --> Gate1{Gate 1: Architectural Compliance}
    Gate1 -- Pass --> Gate2{Gate 2: Quality & Test Pass}
    Gate2 -- Pass --> Gate3{Gate 3: Security & Cost Guard}
    Gate3 -- Pass --> Gate4{Gate 4: ChatGPT Review & Owner Sign-off}
    Gate4 -- Pass --> Merge[Merge PR into main]
    
    Gate1 -- Fail --> Reject[Reject Submission & Request Revisions]
    Gate2 -- Fail --> Reject
    Gate3 -- Fail --> Reject
    Gate4 -- Fail --> Reject
```

---

## 2. Release Gate Checklist Specs

### Gate 1: Architectural & Governance Compliance
- [ ] Code/docs strictly conform to locked architectural principles in [`project-docs/10_GOVERNANCE/SCOPE_LOCK.md`](project-docs/10_GOVERNANCE/SCOPE_LOCK.md).
- [ ] Zero workstation-specific absolute file paths (`file:///c:/...`) exist in documentation.
- [ ] No unauthorized out-of-scope features introduced.
- [ ] All new topics or schema modifications updated in canonical documentation files.

### Gate 2: Quality & Automated Test Pass
- [ ] 100% pass rate on unit test suite.
- [ ] 100% pass rate on provider adapter mock tests (zero live billing).
- [ ] Zero linting errors or build warnings.

### Gate 3: Security & Financial Guard
- [ ] Zero hardcoded API keys, secrets, or passwords in repository code or documentation.
- [ ] Idempotency key validation enforced on all new external integration endpoints.
- [ ] Cost audit logging verified for all provider API call sites.

### Gate 4: Independent Review & Human Sign-off
- [ ] ChatGPT Independent Review completed with recommendation to merge.
- [ ] Project Owner approval received and documented in PR discussion.
