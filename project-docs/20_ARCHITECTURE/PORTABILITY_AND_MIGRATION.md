# Portability, Migration & Disaster Recovery

> **Canonical Document Location:** [`project-docs/20_ARCHITECTURE/PORTABILITY_AND_MIGRATION.md`](file:///c:/Users/allda/Desktop/Dev/git/Orbis%20Video%20Studio%20AI/project-docs/20_ARCHITECTURE/PORTABILITY_AND_MIGRATION.md)

---

## 1. Cloud Portability Architecture

To ensure zero machine lock-in and seamless deployment across cloud infrastructure providers (AWS, GCP, Azure, DigitalOcean, or private cloud), the platform relies on containerization and standard interface abstractions.

```mermaid
graph TD
    AppCode["Application Backend & UI"] --> Docker["Docker Containerization (OCI Compliant)"]
    Docker --> Orchestrator["Kubernetes / AWS ECS / Cloud Run"]
    
    AppCode --> DBAbstraction["PostgreSQL Adapter"]
    AppCode --> StorageAbstraction["S3 Object Storage Adapter"]
    AppCode --> SecretAbstraction["Environment & Secrets Vault"]
    
    DBAbstraction --> RDS[(Managed Postgres / Aurora / GCP Cloud SQL)]
    StorageAbstraction --> CloudS3[(AWS S3 / Cloudflare R2 / MinIO)]
    SecretAbstraction --> Vault[(AWS Secrets Manager / HashiCorp Vault / .env)]
```

---

## 2. Configuration & Secret Externalization

- **Zero Hardcoded Secrets:** Provider API keys (Vidu keys), database credentials, and storage tokens MUST be injected via environment variables or secret managers.
- **Environment Parity:** Identical container images are used across Local Development, Staging, and Production environments.

---

## 3. Project Export / Import Package Schema

To prevent platform lock-in and facilitate backup, project migration, or offline archiving, projects can be exported as a portable `.orbis` package (ZIP format containing JSON manifest + media assets).

### Package Directory Structure
```
project_export_12345.orbis (ZIP Archive)
├── project.json              # Full project domain schema & locks
├── story_script.json         # Story, Script, Scene, Shot metadata
├── references/
│   ├── char_hero.png
│   └── location_lab.jpg
├── shots/
│   ├── shot_001_v1.mp4
│   └── shot_002_imported.mp4
├── audio/
│   ├── vo_en.wav
│   └── bgm_main.mp3
└── manifests/
    └── export_manifest.json  # Checksums, version, timestamp
```

---

## 4. Disaster Recovery & Backup Strategy

1. **Database Backups:** Daily automated PostgreSQL snapshot backups with point-in-time recovery (PITR) retention for 30 days.
2. **Object Storage Replication:** Cross-region versioned S3 buckets to prevent data loss.
3. **Restoration Protocol:** Standardized automated recovery script re-populates PostgreSQL schema and re-attaches Object Storage assets within 15 minutes.
