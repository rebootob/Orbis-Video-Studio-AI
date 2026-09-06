"""Provider-neutral usage and cost ledger service."""
import uuid
from typing import Optional, List, Dict, Any
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.shot import Shot
from app.models.generation_job import GenerationJob
from app.models.usage_ledger import UsageLedger, LedgerAdjustment
from app.services.pricing import CostStatus
from app.providers.safety import contains_secret


class CostLedgerService:
    @staticmethod
    def _sanitize_string(val: Optional[str], field_name: str) -> Optional[str]:
        if val is None:
            return None
        if contains_secret(val):
            raise HTTPException(
                status_code=400, detail=f"Secret-like data not permitted in {field_name}"
            )
        return val

    @classmethod
    def record_entry(
        cls,
        db: Session,
        project_id: uuid.UUID,
        provider: str,
        operation: str,
        shot_id: Optional[uuid.UUID] = None,
        job_id: Optional[uuid.UUID] = None,
        model: Optional[str] = None,
        usage_units: Optional[Dict[str, Any]] = None,
        estimated_cost: Optional[float] = None,
        actual_cost: Optional[float] = None,
        currency: str = "USD",
        cost_status: str = CostStatus.ESTIMATED,
        provider_event_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        description: Optional[str] = None,
    ) -> UsageLedger:
        # 1. Project existence check
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # 2. Shot ownership check (if provided)
        if shot_id:
            shot = db.get(Shot, shot_id)
            if not shot:
                raise HTTPException(status_code=404, detail="Shot not found")
            from app.services.lock_machine import LockMachineService

            shot_project_id = LockMachineService._resolve_entity_project_id(shot)
            if shot_project_id != project_id:
                raise HTTPException(
                    status_code=400, detail="Shot does not belong to specified project"
                )

        # 3. Job ownership check (if provided)
        if job_id:
            job = db.get(GenerationJob, job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Generation job not found")
            from app.services.lock_machine import LockMachineService

            job_project_id = LockMachineService._resolve_entity_project_id(job.shot)
            if job_project_id != project_id:
                raise HTTPException(
                    status_code=400, detail="Generation job does not belong to specified project"
                )

        # 4. Secret-safety validation
        cls._sanitize_string(provider, "provider")
        cls._sanitize_string(operation, "operation")
        cls._sanitize_string(model, "model")
        cls._sanitize_string(provider_event_id, "provider_event_id")
        cls._sanitize_string(idempotency_key, "idempotency_key")
        cls._sanitize_string(description, "description")
        if usage_units and contains_secret(usage_units):
            raise HTTPException(
                status_code=400, detail="Secret-like data not permitted in usage_units"
            )

        # 5. Idempotency & Deduplication check
        if idempotency_key:
            existing = (
                db.query(UsageLedger)
                .filter(
                    UsageLedger.project_id == project_id,
                    UsageLedger.idempotency_key == idempotency_key,
                )
                .first()
            )
            if existing:
                if actual_cost is not None and existing.cost_status in (
                    CostStatus.ESTIMATED,
                    CostStatus.UNKNOWN,
                ):
                    existing.actual_cost = round(actual_cost, 4)
                    existing.cost_status = CostStatus.CONFIRMED
                    db.commit()
                    db.refresh(existing)
                return existing

        if job_id:
            existing = (
                db.query(UsageLedger)
                .filter(UsageLedger.job_id == job_id, UsageLedger.operation == operation)
                .first()
            )
            if existing:
                if actual_cost is not None and existing.cost_status in (
                    CostStatus.ESTIMATED,
                    CostStatus.UNKNOWN,
                ):
                    existing.actual_cost = round(actual_cost, 4)
                    existing.cost_status = CostStatus.CONFIRMED
                    db.commit()
                    db.refresh(existing)
                return existing

        if provider_event_id:
            existing = (
                db.query(UsageLedger)
                .filter(
                    UsageLedger.provider == provider,
                    UsageLedger.provider_event_id == provider_event_id,
                )
                .first()
            )
            if existing:
                return existing

        # 6. Normalize status
        if cost_status not in (
            CostStatus.ESTIMATED,
            CostStatus.CONFIRMED,
            CostStatus.ADJUSTED,
            CostStatus.UNKNOWN,
        ):
            cost_status = CostStatus.ESTIMATED

        if estimated_cost is None and actual_cost is None and cost_status != CostStatus.ADJUSTED:
            cost_status = CostStatus.UNKNOWN

        entry = UsageLedger(
            id=uuid.uuid4(),
            project_id=project_id,
            shot_id=shot_id,
            job_id=job_id,
            provider=provider,
            operation=operation,
            model=model,
            usage_units=usage_units,
            estimated_cost=round(estimated_cost, 4) if estimated_cost is not None else None,
            actual_cost=round(actual_cost, 4) if actual_cost is not None else None,
            currency=currency.upper(),
            cost_status=cost_status,
            provider_event_id=provider_event_id,
            idempotency_key=idempotency_key,
            description=description,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    @classmethod
    def confirm_job_cost(
        cls,
        db: Session,
        job_id: uuid.UUID,
        actual_cost: Optional[float] = None,
        provider_event_id: Optional[str] = None,
    ) -> Optional[UsageLedger]:
        """Transition ledger entry for a job to CONFIRMED when actual usage/cost is known."""
        entry = db.query(UsageLedger).filter(UsageLedger.job_id == job_id).first()
        if not entry:
            return None

        if actual_cost is not None:
            entry.actual_cost = round(actual_cost, 4)
            entry.cost_status = CostStatus.CONFIRMED
        elif entry.estimated_cost is not None and entry.cost_status == CostStatus.ESTIMATED:
            entry.actual_cost = entry.estimated_cost
            entry.cost_status = CostStatus.CONFIRMED

        if provider_event_id:
            cls._sanitize_string(provider_event_id, "provider_event_id")
            entry.provider_event_id = provider_event_id

        db.commit()
        db.refresh(entry)
        return entry

    @classmethod
    def record_adjustment(
        cls,
        db: Session,
        project_id: uuid.UUID,
        ledger_id: uuid.UUID,
        actor: str,
        reason: str,
        adjusted_cost: float,
    ) -> LedgerAdjustment:
        # 1. Project existence check
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # 2. Ledger entry existence and project ownership check
        entry = db.get(UsageLedger, ledger_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Ledger entry not found")
        if entry.project_id != project_id:
            raise HTTPException(
                status_code=400, detail="Ledger entry does not belong to specified project"
            )

        # 3. Input validation & secret checking
        if not actor or not actor.strip():
            raise HTTPException(status_code=400, detail="Actor is required")
        if not reason or not reason.strip():
            raise HTTPException(status_code=400, detail="Reason is required")
        if contains_secret(actor) or contains_secret(reason):
            raise HTTPException(
                status_code=400, detail="Secret-like data not permitted in adjustment"
            )
        if adjusted_cost < 0:
            raise HTTPException(status_code=400, detail="Adjusted cost must be non-negative")

        previous_cost = (
            entry.actual_cost if entry.actual_cost is not None else entry.estimated_cost
        )

        adjustment = LedgerAdjustment(
            id=uuid.uuid4(),
            ledger_id=ledger_id,
            actor=actor.strip(),
            reason=reason.strip(),
            previous_cost=previous_cost,
            adjusted_cost=round(adjusted_cost, 4),
        )
        db.add(adjustment)

        # Update parent ledger entry while preserving audit history
        entry.actual_cost = round(adjusted_cost, 4)
        entry.cost_status = CostStatus.ADJUSTED

        db.commit()
        db.refresh(adjustment)
        return adjustment

    @classmethod
    def get_project_summary(cls, db: Session, project_id: uuid.UUID) -> Dict[str, Any]:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        from app.services.budget import BudgetService

        budget_info = BudgetService.get_budget_status(db, project_id)

        entries = (
            db.query(UsageLedger)
            .filter(UsageLedger.project_id == project_id)
            .order_by(UsageLedger.created_at.desc())
            .all()
        )

        total_estimated = 0.0
        total_confirmed = 0.0
        total_adjusted = 0.0
        unknown_count = 0

        by_provider: Dict[str, Dict[str, Any]] = {}
        by_operation: Dict[str, Dict[str, Any]] = {}

        for e in entries:
            cost = 0.0
            if e.cost_status == CostStatus.CONFIRMED:
                cost = e.actual_cost or 0.0
                total_confirmed += cost
            elif e.cost_status == CostStatus.ADJUSTED:
                cost = e.actual_cost or 0.0
                total_adjusted += cost
            elif e.cost_status == CostStatus.ESTIMATED:
                cost = e.estimated_cost or 0.0
                total_estimated += cost
            elif e.cost_status == CostStatus.UNKNOWN:
                unknown_count += 1

            prov = e.provider
            if prov not in by_provider:
                by_provider[prov] = {"provider": prov, "total_cost": 0.0, "event_count": 0}
            by_provider[prov]["total_cost"] = round(by_provider[prov]["total_cost"] + cost, 4)
            by_provider[prov]["event_count"] += 1

            op = e.operation
            if op not in by_operation:
                by_operation[op] = {"operation": op, "total_cost": 0.0, "event_count": 0}
            by_operation[op]["total_cost"] = round(by_operation[op]["total_cost"] + cost, 4)
            by_operation[op]["event_count"] += 1

        total_actual = round(total_confirmed + total_adjusted, 4)
        total_committed = round(total_actual + total_estimated, 4)

        return {
            "project_id": project_id,
            "total_estimated_cost": round(total_estimated, 4),
            "total_confirmed_cost": round(total_confirmed, 4),
            "total_adjusted_cost": round(total_adjusted, 4),
            "total_actual_cost": total_actual,
            "total_committed_cost": total_committed,
            "unknown_cost_count": unknown_count,
            "currency": project.budget_currency or "USD",
            "budget": budget_info,
            "by_provider": list(by_provider.values()),
            "by_operation": list(by_operation.values()),
        }

    @classmethod
    def list_entries(
        cls,
        db: Session,
        project_id: uuid.UUID,
        provider: Optional[str] = None,
        operation: Optional[str] = None,
        cost_status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[UsageLedger]:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        query = db.query(UsageLedger).filter(UsageLedger.project_id == project_id)
        if provider:
            query = query.filter(UsageLedger.provider == provider)
        if operation:
            query = query.filter(UsageLedger.operation == operation)
        if cost_status:
            query = query.filter(UsageLedger.cost_status == cost_status)

        return query.order_by(UsageLedger.created_at.desc()).offset(offset).limit(limit).all()
