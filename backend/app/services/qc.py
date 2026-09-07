import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException, status

from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.asset import Asset
from app.models.audio_clip import AudioClip
from app.models.assembly import AssemblyTimeline, AssemblyScene, AssemblyShotPlacement
from app.models.reference_library import CharacterBible, LocationBible
from app.models.generation_job import GenerationJob
from app.models.qc import QCRun, QCFinding, WarningDecision, ApprovalRecord
from app.schemas.qc import (
    QCRunRead,
    QCFindingRead,
    WarningDecisionRead,
    SimpleFindingRead,
    QCRunSummaryRead,
    ApprovalRecordRead,
    QCHistoryPagination,
    QCFindingPagination,
)
from app.services.assembly import AssemblyService
from app.services.production_orchestrator import ProductionOrchestrator, OrchestrationActionResult


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class QCService:
    """Service owning quality control evaluation, rule execution, warning decision audit,
    and final production approval gates.
    """

    @classmethod
    def run_qc(cls, db: Session, project_id: uuid.UUID, actor: str = "system") -> QCRun:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        timeline = AssemblyService.get_or_create_active_timeline(db, str(project_id))
        if not timeline:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active timeline assembly available for QC evaluation",
            )

        # Create new QC Run bound to exact current timeline revision
        qc_run = QCRun(
            id=uuid.uuid4(),
            project_id=project_id,
            timeline_id=timeline.id,
            timeline_version=timeline.version,
            status="RUNNING",
            actor=actor,
            created_at=utc_now(),
        )
        db.add(qc_run)
        db.flush()

        findings: List[QCFinding] = []

        # Fetch canonical project state for evaluation
        db_scenes = (
            db.query(Scene)
            .filter(Scene.project_id == project_id)
            .order_by(Scene.scene_number.asc())
            .all()
        )
        scene_ids = [s.id for s in db_scenes]
        db_shots = (
            db.query(Shot)
            .filter(Shot.scene_id.in_(scene_ids))
            .order_by(Shot.shot_number.asc())
            .all()
        ) if scene_ids else []
        shot_map = {s.id: s for s in db_shots}

        assets = db.query(Asset).filter(Asset.project_id == project_id).all()
        asset_map = {a.id: a for a in assets}

        audio_clips = db.query(AudioClip).filter(AudioClip.project_id == project_id).all()

        char_bibles = db.query(CharacterBible).filter(CharacterBible.project_id == project_id).all()
        loc_bibles = db.query(LocationBible).filter(LocationBible.project_id == project_id).all()

        recon_jobs = (
            db.query(GenerationJob)
            .filter(
                GenerationJob.shot_id.in_(shot_map.keys()),
                GenerationJob.status == "RECONCILIATION_REQUIRED",
            )
            .all()
        ) if shot_map else []

        # Rule 1: EMPTY_SCENE (BLOCKER)
        for scene in db_scenes:
            scene_shots = [sh for sh in db_shots if sh.scene_id == scene.id and sh.status != "ARCHIVED"]
            if not scene_shots:
                findings.append(
                    QCFinding(
                        id=uuid.uuid4(),
                        project_id=project_id,
                        qc_run_id=qc_run.id,
                        timeline_id=timeline.id,
                        rule_code="EMPTY_SCENE",
                        severity="BLOCKER",
                        message=f"Scene #{scene.scene_number} has no active camera shots.",
                        why_it_matters="A scene without shots cannot be rendered or assembled into the final cut.",
                        recommended_fix="Generate or add shots to Scene #" + str(scene.scene_number) + ".",
                        target_type="SCENE",
                        target_id=scene.id,
                        target_label=f"Scene #{scene.scene_number}",
                        action_type="GENERATE_SHOT_PLAN",
                    )
                )

        # Rule 2: Timeline Placements Check
        placements = (
            db.query(AssemblyShotPlacement)
            .filter(AssemblyShotPlacement.timeline_id == timeline.id)
            .order_by(AssemblyShotPlacement.shot_order.asc())
            .all()
        )

        for placement in placements:
            shot = shot_map.get(placement.shot_id)
            shot_label = f"Shot S{placement.scene_id.hex[:4]}-#{shot.shot_number}" if shot else f"Placement {placement.id.hex[:6]}"

            # Rule 2a: MISSING_VISUAL (BLOCKER)
            if placement.source_type == "MISSING" or not placement.visual_asset_id:
                findings.append(
                    QCFinding(
                        id=uuid.uuid4(),
                        project_id=project_id,
                        qc_run_id=qc_run.id,
                        timeline_id=timeline.id,
                        rule_code="MISSING_VISUAL",
                        severity="BLOCKER",
                        message=f"Shot '{shot_label}' has no usable video or keyframe asset assigned.",
                        why_it_matters="Every timeline shot placement requires a generated video or reference keyframe.",
                        recommended_fix="Generate or select a visual asset for this shot.",
                        target_type="SHOT",
                        target_id=placement.shot_id,
                        target_label=shot_label,
                        action_type="GENERATE_SHOT",
                    )
                )

            # Rule 2b: INVALID_TRIM_TIMING (BLOCKER)
            if (
                placement.trim_in < 0
                or (placement.trim_out is not None and placement.trim_out <= placement.trim_in)
                or placement.effective_duration <= 0
            ):
                findings.append(
                    QCFinding(
                        id=uuid.uuid4(),
                        project_id=project_id,
                        qc_run_id=qc_run.id,
                        timeline_id=timeline.id,
                        rule_code="INVALID_TRIM_TIMING",
                        severity="BLOCKER",
                        message=f"Shot '{shot_label}' has invalid trim boundaries or non-positive duration.",
                        why_it_matters="Negative trim values or zero duration corrupt timeline playback and assembly rendering.",
                        recommended_fix="Reset trim boundaries to valid non-negative offsets.",
                        target_type="PLACEMENT",
                        target_id=placement.id,
                        target_label=shot_label,
                        action_type="UPDATE_PLACEMENT",
                    )
                )

            # Rule 2c: LOCKED_STATE_CONFLICT (BLOCKER)
            if placement.is_locked and (placement.source_type == "MISSING" or not placement.visual_asset_id):
                findings.append(
                    QCFinding(
                        id=uuid.uuid4(),
                        project_id=project_id,
                        qc_run_id=qc_run.id,
                        timeline_id=timeline.id,
                        rule_code="LOCKED_STATE_CONFLICT",
                        severity="BLOCKER",
                        message=f"Shot '{shot_label}' is locked but lacks a valid visual asset.",
                        why_it_matters="Locked placements cannot be auto-reconciled while unassigned.",
                        recommended_fix="Unlock placement or assign a valid asset.",
                        target_type="PLACEMENT",
                        target_id=placement.id,
                        target_label=shot_label,
                        action_type="UNLOCK_PLACEMENT",
                    )
                )

            # Rule 2d: MISSING_REQUIRED_DIALOGUE (BLOCKER)
            if shot and shot.visual_prompt and ("dialogue:" in shot.visual_prompt.lower() or "speaks" in shot.visual_prompt.lower()):
                has_dialogue_clip = any(
                    ac.shot_id == shot.id or ac.scene_id == shot.scene_id
                    for ac in audio_clips
                    if ac.audio_type in ("VO", "DIALOGUE")
                )
                if not has_dialogue_clip:
                    findings.append(
                        QCFinding(
                            id=uuid.uuid4(),
                            project_id=project_id,
                            qc_run_id=qc_run.id,
                            timeline_id=timeline.id,
                            rule_code="MISSING_REQUIRED_DIALOGUE",
                            severity="BLOCKER",
                            message=f"Shot '{shot_label}' requires spoken dialogue, but no dialogue audio clip is present.",
                            why_it_matters="Dialogue lines indicated in script must have audio assigned before final approval.",
                            recommended_fix="Generate or assign spoken dialogue audio for this shot.",
                            target_type="SHOT",
                            target_id=shot.id,
                            target_label=shot_label,
                            action_type="GENERATE_AUDIO",
                        )
                    )

            # Rule 2e: APPROVED_ASSET_MISMATCH (WARNING)
            if shot and shot.source_asset_id and placement.visual_asset_id and shot.source_asset_id != placement.visual_asset_id:
                findings.append(
                    QCFinding(
                        id=uuid.uuid4(),
                        project_id=project_id,
                        qc_run_id=qc_run.id,
                        timeline_id=timeline.id,
                        rule_code="APPROVED_ASSET_MISMATCH",
                        severity="WARNING",
                        message=f"Shot '{shot_label}' timeline asset differs from the primary approved shot asset.",
                        why_it_matters="The timeline placement uses a different version or fallback image than shot primary.",
                        recommended_fix="Verify if override is intentional or sync with primary shot asset.",
                        target_type="PLACEMENT",
                        target_id=placement.id,
                        target_label=shot_label,
                        action_type="UPDATE_PLACEMENT",
                    )
                )

        # Rule 3: UNRESOLVED_RECONCILIATION (BLOCKER)
        if recon_jobs:
            findings.append(
                QCFinding(
                    id=uuid.uuid4(),
                    project_id=project_id,
                    qc_run_id=qc_run.id,
                    timeline_id=timeline.id,
                    rule_code="UNRESOLVED_RECONCILIATION",
                    severity="BLOCKER",
                    message=f"{len(recon_jobs)} provider job(s) lost synchronization and require reconciliation.",
                    why_it_matters="In-flight generation outcomes must be reconciled before production can be approved.",
                    recommended_fix="Reconcile provider jobs in the job control panel.",
                    target_type="PROJECT",
                    target_id=project_id,
                    target_label="Project Jobs",
                    action_type="RESOLVE_RECONCILIATION",
                )
            )

        # Rule 4: UNVERIFIED_VISUAL_CONTINUITY (WARNING - Deterministic check)
        # Deterministically check if adjacent shots in scene have different visual asset types or missing transition metadata
        for scene in db_scenes:
            scene_placements = [
                p for p in placements if p.scene_id == scene.id
            ]
            if len(scene_placements) > 1:
                for i in range(len(scene_placements) - 1):
                    curr_p = scene_placements[i]
                    next_p = scene_placements[i + 1]
                    if curr_p.source_type != next_p.source_type or (curr_p.source_type == "KEYFRAME" and next_p.source_type == "KEYFRAME"):
                        sh1 = shot_map.get(curr_p.shot_id)
                        sh2 = shot_map.get(next_p.shot_id)
                        lbl1 = f"S{scene.scene_number}-#{sh1.shot_number}" if sh1 else "Shot 1"
                        lbl2 = f"S{scene.scene_number}-#{sh2.shot_number}" if sh2 else "Shot 2"
                        findings.append(
                            QCFinding(
                                id=uuid.uuid4(),
                                project_id=project_id,
                                qc_run_id=qc_run.id,
                                timeline_id=timeline.id,
                                rule_code="UNVERIFIED_VISUAL_CONTINUITY",
                                severity="WARNING",
                                message=f"Visual continuity between adjacent shots '{lbl1}' and '{lbl2}' cannot be deterministically verified.",
                                why_it_matters="Switching between video clips and keyframe stills may cause visual jump cuts.",
                                recommended_fix="Review visual preview transition and accept if acceptable.",
                                target_type="SCENE",
                                target_id=scene.id,
                                target_label=f"Scene #{scene.scene_number} ({lbl1} -> {lbl2})",
                                action_type="REVIEW_CONTINUITY",
                            )
                        )

        # Rule 5: MISSING_PROJECT_AUDIO (WARNING)
        if not audio_clips and len(placements) > 0:
            findings.append(
                QCFinding(
                    id=uuid.uuid4(),
                    project_id=project_id,
                    qc_run_id=qc_run.id,
                    timeline_id=timeline.id,
                    rule_code="MISSING_PROJECT_AUDIO",
                    severity="WARNING",
                    message="No audio clips or background music assigned to the project timeline.",
                    why_it_matters="The final production cut will be completely silent.",
                    recommended_fix="Generate or assign audio tracks or accept silent output.",
                    target_type="PROJECT",
                    target_id=project_id,
                    target_label="Project Audio",
                    action_type="GENERATE_AUDIO_PLAN",
                )
            )

        # Rule 6: CHARACTER_REFERENCE_MISMATCH (WARNING)
        for shot in db_shots:
            if shot.visual_prompt and ("character" in shot.visual_prompt.lower() or "hero" in shot.visual_prompt.lower()):
                if not char_bibles:
                    findings.append(
                        QCFinding(
                            id=uuid.uuid4(),
                            project_id=project_id,
                            qc_run_id=qc_run.id,
                            timeline_id=timeline.id,
                            rule_code="CHARACTER_REFERENCE_MISMATCH",
                            severity="WARNING",
                            message=f"Shot #{shot.shot_number} mentions character in prompt, but no Character Bible reference exists.",
                            why_it_matters="Character consistency across shots cannot be guaranteed without reference bibles.",
                            recommended_fix="Create Character Bible or accept prompt without character lock.",
                            target_type="SHOT",
                            target_id=shot.id,
                            target_label=f"Shot #{shot.shot_number}",
                            action_type="CREATE_REFERENCE",
                        )
                    )

        # Save all findings
        for f in findings:
            db.add(f)

        blocker_cnt = sum(1 for f in findings if f.severity == "BLOCKER")
        warning_cnt = sum(1 for f in findings if f.severity == "WARNING")

        qc_run.blocker_count = blocker_cnt
        qc_run.warning_count = warning_cnt

        if blocker_cnt > 0:
            qc_run.status = "BLOCKED"
        elif warning_cnt > 0:
            qc_run.status = "RUNNING"  # Waiting for warning decisions
        else:
            qc_run.status = "PASSED"

        db.commit()
        db.refresh(qc_run)
        return qc_run

    @classmethod
    def record_warning_decision(
        cls,
        db: Session,
        project_id: uuid.UUID,
        finding_id: uuid.UUID,
        decision: str,
        reason: Optional[str] = None,
        actor: str = "USER",
    ) -> WarningDecision:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        finding = db.get(QCFinding, finding_id)
        if not finding or finding.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="QC finding not found for this project context",
            )

        if finding.severity != "WARNING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Warning decisions can only be recorded for WARNING findings. BLOCKER findings cannot be bypassed.",
            )

        decision_upper = decision.upper()
        if decision_upper not in ("FIX_REQUIRED", "ACCEPTED_WITH_REASON"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Decision must be either FIX_REQUIRED or ACCEPTED_WITH_REASON",
            )

        if decision_upper == "ACCEPTED_WITH_REASON":
            if not reason or not reason.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A non-empty reason is strictly required when accepting a warning without fixing.",
                )
            reason = reason.strip()
        else:
            reason = reason.strip() if reason else None

        # Check existing decision for finding on exact timeline revision
        existing_decision = (
            db.query(WarningDecision)
            .filter(
                WarningDecision.finding_id == finding_id,
                WarningDecision.qc_run_id == finding.qc_run_id,
            )
            .first()
        )

        if existing_decision:
            existing_decision.decision = decision_upper
            existing_decision.reason = reason
            existing_decision.actor = actor
            existing_decision.decided_at = utc_now()
            target_dec = existing_decision
        else:
            target_dec = WarningDecision(
                id=uuid.uuid4(),
                project_id=project_id,
                qc_run_id=finding.qc_run_id,
                finding_id=finding_id,
                timeline_id=finding.timeline_id,
                decision=decision_upper,
                reason=reason,
                actor=actor,
                decided_at=utc_now(),
            )
            db.add(target_dec)

        db.flush()

        # Re-evaluate parent QC run status
        # Re-evaluate parent QC run status
        qc_run = db.get(QCRun, finding.qc_run_id)
        if qc_run and qc_run.blocker_count == 0:
            warning_findings = [f for f in qc_run.findings if f.severity == "WARNING"]
            decided_map = {wd.finding_id: wd.decision for wd in qc_run.decisions}

            has_fix_required = any(decided_map.get(f.id) == "FIX_REQUIRED" for f in warning_findings)
            all_accepted = (
                all(decided_map.get(f.id) == "ACCEPTED_WITH_REASON" for f in warning_findings)
                if warning_findings else True
            )

            if has_fix_required:
                qc_run.status = "BLOCKED"
            elif all_accepted:
                qc_run.status = "PASSED"
            else:
                qc_run.status = "RUNNING"

        db.commit()
        db.refresh(target_dec)
        return target_dec

    @classmethod
    def validate_final_approval(
        cls,
        db: Session,
        project_id: uuid.UUID,
        timeline_id: Optional[uuid.UUID] = None,
        qc_run_id: Optional[uuid.UUID] = None,
    ) -> Tuple[AssemblyTimeline, QCRun]:
        """Validate eligibility for final production approval without mutating project status."""
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        active_timeline = AssemblyService.get_active_timeline(db, str(project_id))
        if not active_timeline:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active timeline assembly available for production approval",
            )

        if timeline_id and timeline_id != active_timeline.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Specified timeline ID '{timeline_id}' does not match the active current timeline revision (v{active_timeline.version}). Stale revisions cannot be approved.",
            )

        latest_qc = (
            db.query(QCRun)
            .filter(
                QCRun.project_id == project_id,
                QCRun.timeline_id == active_timeline.id,
            )
            .order_by(QCRun.created_at.desc())
            .first()
        )

        if not latest_qc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No QC run exists for the current timeline revision. Run QC evaluation before attempting approval.",
            )

        if qc_run_id and qc_run_id != latest_qc.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Specified QC Run ID is not the latest evaluation for the current timeline revision.",
            )

        # 1. Check Blockers: BLOCKER CANNOT BE BYPASSED!
        if latest_qc.blocker_count > 0:
            blocker_messages = [f.message for f in latest_qc.findings if f.severity == "BLOCKER"]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve production while {latest_qc.blocker_count} BLOCKER finding(s) exist: {'; '.join(blocker_messages[:3])}",
            )

        # 2. Check Warning Decisions: EVERY WARNING REQUIRES USER DECISION and FIX_REQUIRED BLOCKS APPROVAL!
        warning_findings = [f for f in latest_qc.findings if f.severity == "WARNING"]
        decided_map = {wd.finding_id: wd for wd in latest_qc.decisions}

        undecided = [f for f in warning_findings if f.id not in decided_map]
        if undecided:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Every warning requires an explicit user decision before final approval. {len(undecided)} warning(s) remain undecided.",
            )

        fix_required = [f for f in warning_findings if decided_map[f.id].decision == "FIX_REQUIRED"]
        if fix_required:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve production: {len(fix_required)} warning(s) are marked FIX_REQUIRED. Resolve these issues and re-evaluate QC before attempting approval.",
            )

        return active_timeline, latest_qc

    @classmethod
    def approve_production(
        cls,
        db: Session,
        project_id: uuid.UUID,
        timeline_id: Optional[uuid.UUID] = None,
        qc_run_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
        actor: str = "USER",
    ) -> ApprovalRecord:
        """Forward final production approval to canonical ProductionOrchestrator workflow owner."""
        return ProductionOrchestrator.approve_final_production(
            db=db,
            project_id=project_id,
            timeline_id=timeline_id,
            qc_run_id=qc_run_id,
            notes=notes,
            actor=actor,
        )

    @classmethod
    def get_simple_summary(cls, db: Session, project_id: uuid.UUID) -> QCRunSummaryRead:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        active_timeline = AssemblyService.get_active_timeline(db, str(project_id))
        if not active_timeline:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active timeline assembly exists for project",
            )

        qc_run = (
            db.query(QCRun)
            .filter(
                QCRun.project_id == project_id,
                QCRun.timeline_id == active_timeline.id,
            )
            .order_by(QCRun.created_at.desc())
            .first()
        )

        if not qc_run:
            # Auto-run QC if no evaluation exists for active timeline
            qc_run = cls.run_qc(db, project_id)

        decisions_map = {wd.finding_id: wd for wd in qc_run.decisions}
        simple_findings: List[SimpleFindingRead] = []
        unresolved_warnings = 0
        fix_required_warnings = 0

        for f in qc_run.findings:
            dec = decisions_map.get(f.id)
            if f.severity == "WARNING":
                if not dec:
                    unresolved_warnings += 1
                elif dec.decision == "FIX_REQUIRED":
                    fix_required_warnings += 1

            simple_findings.append(
                SimpleFindingRead(
                    id=f.id,
                    rule_code=f.rule_code,
                    severity=f.severity,
                    message=f.message,
                    why_it_matters=f.why_it_matters,
                    recommended_fix=f.recommended_fix,
                    target_label=f.target_label,
                    action_type=f.action_type,
                    decision=dec.decision if dec else None,
                    reason=dec.reason if dec else None,
                )
            )

        if qc_run.blocker_count > 0:
            overall_state = "BLOCKED"
            recommended_next_action = "Resolve blocker items before final review"
        elif fix_required_warnings > 0:
            overall_state = "NEEDS_ATTENTION"
            recommended_next_action = f"Fix {fix_required_warnings} warning item(s) marked FIX_REQUIRED and re-evaluate QC"
        elif unresolved_warnings > 0:
            overall_state = "NEEDS_ATTENTION"
            recommended_next_action = f"Make decisions on {unresolved_warnings} warning item(s)"
        else:
            overall_state = "READY_FOR_APPROVAL"
            recommended_next_action = "Approve final video production"

        return QCRunSummaryRead(
            qc_run_id=qc_run.id,
            project_id=project_id,
            timeline_id=active_timeline.id,
            timeline_version=active_timeline.version,
            status=qc_run.status,
            overall_state=overall_state,
            total_blockers=qc_run.blocker_count,
            total_warnings=qc_run.warning_count,
            unresolved_warnings=unresolved_warnings,
            recommended_next_action=recommended_next_action,
            simple_findings=simple_findings,
        )

    @classmethod
    def get_qc_history(
        cls, db: Session, project_id: uuid.UUID, offset: int = 0, limit: int = 20
    ) -> QCHistoryPagination:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        eff_limit = min(max(limit, 1), 100)
        query = (
            db.query(QCRun)
            .filter(QCRun.project_id == project_id)
            .order_by(QCRun.created_at.desc(), QCRun.id.desc())
        )
        total_count = query.count()
        runs = query.offset(offset).limit(eff_limit).all()

        runs_read: List[QCRunRead] = []
        for r in runs:
            # Summary mode: findings list is empty to prevent N+1 loading and heavy payload in history list
            runs_read.append(
                QCRunRead(
                    id=r.id,
                    project_id=r.project_id,
                    timeline_id=r.timeline_id,
                    timeline_version=r.timeline_version,
                    status=r.status,
                    blocker_count=r.blocker_count,
                    warning_count=r.warning_count,
                    actor=r.actor,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                    findings=[],
                )
            )

        return QCHistoryPagination(
            qc_runs=runs_read,
            total_count=total_count,
            offset=offset,
            limit=eff_limit,
        )

    @classmethod
    def get_qc_run_findings(
        cls,
        db: Session,
        project_id: uuid.UUID,
        run_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> QCFindingPagination:
        """Get bounded, paginated list of findings for a specific QC run with set-based decision mapping."""
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        qc_run = db.get(QCRun, run_id)
        if not qc_run or qc_run.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"QC run '{run_id}' not found for project '{project_id}'",
            )

        eff_limit = min(max(limit, 1), 100)
        query = (
            db.query(QCFinding)
            .filter(QCFinding.qc_run_id == run_id)
            .order_by(QCFinding.created_at.asc(), QCFinding.id.asc())
        )
        total_count = query.count()
        findings = query.offset(offset).limit(eff_limit).all()

        finding_ids = [f.id for f in findings]
        decisions = (
            db.query(WarningDecision)
            .filter(WarningDecision.finding_id.in_(finding_ids))
            .all()
        ) if finding_ids else []
        dec_map = {d.finding_id: d for d in decisions}

        findings_read: List[QCFindingRead] = []
        for f in findings:
            dec = dec_map.get(f.id)
            findings_read.append(
                QCFindingRead(
                    id=f.id,
                    project_id=f.project_id,
                    qc_run_id=f.qc_run_id,
                    timeline_id=f.timeline_id,
                    rule_code=f.rule_code,
                    severity=f.severity,
                    message=f.message,
                    why_it_matters=f.why_it_matters,
                    recommended_fix=f.recommended_fix,
                    target_type=f.target_type,
                    target_id=f.target_id,
                    target_label=f.target_label,
                    action_type=f.action_type,
                    created_at=f.created_at,
                    current_decision=WarningDecisionRead.model_validate(dec) if dec else None,
                )
            )

        return QCFindingPagination(
            findings=findings_read,
            total_count=total_count,
            offset=offset,
            limit=eff_limit,
        )
