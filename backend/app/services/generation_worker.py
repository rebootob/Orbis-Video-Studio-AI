"""Explicitly started DB worker: python -m app.services.generation_worker.

No worker or provider calls are started by importing the API application.
"""
import asyncio
from sqlalchemy import or_
from app.db.session import SessionLocal
from app.models.generation_job import GenerationJob
from app.services.job_dispatch import JobDispatchService, utc_now, ACTIVE


async def run_once(session_factory=SessionLocal):
    with session_factory() as db:
        JobDispatchService.recover_pending_jobs(db)
        job = JobDispatchService.claim_next_job(db)
        if job:
            await JobDispatchService.process_job(db, job.id, claim_token=job.claim_token)
        now = utc_now()
        pending = db.query(GenerationJob.id).filter(
            GenerationJob.status.in_(ACTIVE), GenerationJob.provider_job_id.is_not(None),
            or_(GenerationJob.next_poll_at.is_(None), GenerationJob.next_poll_at <= now),
        ).order_by(GenerationJob.next_poll_at, GenerationJob.created_at).limit(10).all()
        db.commit()
        for (job_id,) in pending:
            await JobDispatchService.poll_job_status(db, job_id)


async def main():
    while True:
        await run_once()
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
