"""Project budget control service."""
import uuid
from typing import Optional, Dict, Any
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.usage_ledger import UsageLedger
from app.services.pricing import CostStatus


class BudgetService:
    @staticmethod
    def get_project_or_404(db: Session, project_id: uuid.UUID) -> Project:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project

    @classmethod
    def get_project_committed_cost(cls, db: Session, project_id: uuid.UUID) -> float:
        """Calculate total committed cost: confirmed actuals + manual adjustments + active estimates."""
        entries = db.query(UsageLedger).filter(UsageLedger.project_id == project_id).all()
        total = 0.0
        for e in entries:
            if e.cost_status in (CostStatus.CONFIRMED, CostStatus.ADJUSTED):
                total += (e.actual_cost or 0.0)
            elif e.cost_status == CostStatus.ESTIMATED:
                total += (e.estimated_cost or 0.0)
        return round(total, 4)

    @classmethod
    def get_budget_status(cls, db: Session, project_id: uuid.UUID) -> Dict[str, Any]:
        project = cls.get_project_or_404(db, project_id)
        committed = cls.get_project_committed_cost(db, project_id)
        limit = project.budget_limit
        currency = project.budget_currency or "USD"
        threshold_pct = (
            project.budget_threshold_percentage
            if project.budget_threshold_percentage is not None
            else 80.0
        )

        remaining = round(limit - committed, 4) if limit is not None else None
        soft_threshold_amount = (
            round(limit * (threshold_pct / 100.0), 4) if limit is not None else None
        )

        is_soft_exceeded = bool(
            limit is not None
            and soft_threshold_amount is not None
            and committed >= soft_threshold_amount
        )
        is_hard_exceeded = bool(limit is not None and committed >= limit)

        return {
            "project_id": project.id,
            "budget_limit": limit,
            "budget_currency": currency,
            "budget_threshold_percentage": threshold_pct,
            "soft_limit_threshold_amount": soft_threshold_amount,
            "total_committed_cost": committed,
            "remaining_budget": remaining,
            "is_soft_limit_exceeded": is_soft_exceeded,
            "is_hard_limit_exceeded": is_hard_exceeded,
        }

    @classmethod
    def update_budget(
        cls,
        db: Session,
        project_id: uuid.UUID,
        budget_limit: Optional[float] = None,
        budget_currency: Optional[str] = None,
        budget_threshold_percentage: Optional[float] = None,
    ) -> Dict[str, Any]:
        project = cls.get_project_or_404(db, project_id)
        if budget_limit is not None and budget_limit < 0:
            raise HTTPException(status_code=400, detail="budget_limit must be non-negative")
        if budget_threshold_percentage is not None and not (0 <= budget_threshold_percentage <= 100):
            raise HTTPException(
                status_code=400, detail="budget_threshold_percentage must be between 0 and 100"
            )

        if budget_limit is not None:
            project.budget_limit = budget_limit
        if budget_currency is not None:
            if not budget_currency.strip() or len(budget_currency) > 10:
                raise HTTPException(status_code=400, detail="Invalid budget_currency")
            project.budget_currency = budget_currency.strip().upper()
        if budget_threshold_percentage is not None:
            project.budget_threshold_percentage = budget_threshold_percentage

        db.commit()
        db.refresh(project)
        return cls.get_budget_status(db, project_id)

    @classmethod
    def check_budget_before_dispatch(
        cls,
        db: Session,
        project_id: uuid.UUID,
        estimated_cost: Optional[float] = None,
        lock_row: bool = False,
    ):
        """Fail closed when a known estimated charge would exceed hard budget,

        or when project budget is already exhausted.
        """
        query = db.query(Project).filter(Project.id == project_id)
        if lock_row:
            query = query.with_for_update()
        project = query.first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project.budget_limit is None:
            return

        committed = cls.get_project_committed_cost(db, project_id)
        limit = project.budget_limit
        currency = project.budget_currency or "USD"

        # If already at or exceeding hard budget, block dispatch
        if committed >= limit:
            raise HTTPException(
                status_code=400,
                detail=f"Project budget limit reached: committed {committed:.2f} {currency} has reached or exceeded the budget limit of {limit:.2f} {currency}",
            )

        # If estimated cost is known and would breach the limit, fail closed
        if estimated_cost is not None and estimated_cost > 0:
            if round(committed + estimated_cost, 4) > limit:
                remaining = max(0.0, round(limit - committed, 4))
                raise HTTPException(
                    status_code=400,
                    detail=f"Project budget exceeded: dispatch requires estimated {estimated_cost:.2f} {currency}, but remaining budget is {remaining:.2f} {currency} (limit: {limit:.2f} {currency})",
                )
