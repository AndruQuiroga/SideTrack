from __future__ import annotations

import math

from fastapi import APIRouter
from rq import Queue
from rq.job import Job
from rq.registry import FailedJobRegistry, FinishedJobRegistry, StartedJobRegistry

from ..config import get_settings as get_api_settings

router = APIRouter(prefix="/ops", tags=["ops"])


def _percentile(sorted_data: list[float], percent: float) -> float:
    """Return the percentile value from a pre-sorted list.

    Args:
        sorted_data: Sequence of numbers sorted in ascending order.
        percent: Desired percentile between 0 and 100.

    Returns:
        The percentile value or ``0.0`` when ``sorted_data`` is empty.
    """
    if not sorted_data:
        return 0.0
    k = (len(sorted_data) - 1) * percent / 100
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    return sorted_data[f] + (sorted_data[c] - sorted_data[f]) * (k - f)


@router.get("/queue")
def queue_metrics() -> dict[str, dict[str, float | int]]:
    """Return basic metrics for all RQ queues.

    The metrics include counts of queued, running and failed jobs as well as
    p50 and p95 execution times (in seconds) for recently finished jobs.
    """
    from ..main import _get_redis_connection

    settings = get_api_settings()
    conn = _get_redis_connection(settings)
    metrics: dict[str, dict[str, float | int]] = {}
    for q in Queue.all(connection=conn):
        started = StartedJobRegistry(q.name, connection=conn)
        failed = FailedJobRegistry(q.name, connection=conn)
        finished = FinishedJobRegistry(q.name, connection=conn)

        durations: list[float] = []
        for job_id in finished.get_job_ids()[:100]:
            job = Job.fetch(job_id, connection=conn)
            if job.started_at and job.ended_at:
                durations.append((job.ended_at - job.started_at).total_seconds())
        durations.sort()
        metrics[q.name] = {
            "queued": q.count,
            "running": started.count,
            "failed": failed.count,
            "p50": _percentile(durations, 50),
            "p95": _percentile(durations, 95),
        }
    return metrics


@router.get("/schedules")
def list_schedules() -> dict[str, list[dict[str, str | None]]]:
    """Return job runner schedule information.

    Reports the next run time and last enqueue status for all scheduled jobs.
    """
    import schedule

    from sidetrack.jobrunner import run as jobrunner_run

    out: list[dict[str, str | None]] = []
    for job in schedule.jobs:
        tag_map: dict[str, str] = {}
        for tag in job.tags:
            if ":" in tag:
                k, v = tag.split(":", 1)
                tag_map[k] = v
        user_id = tag_map.get("user")
        job_type = tag_map.get("job")
        if not user_id or not job_type:
            continue
        state = jobrunner_run.get_job_state(user_id, job_type)
        last_run = state.get("last_run")
        out.append(
            {
                "user_id": user_id,
                "job_type": job_type,
                "next_run": job.next_run.isoformat() if job.next_run else None,
                "last_status": state.get("last_status"),
                "last_run": last_run.isoformat() if last_run else None,
            }
        )
    return {"schedules": out}
