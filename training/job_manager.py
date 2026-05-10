from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from training.config import MAX_CONCURRENT_TRAINING, MAX_QUEUED_JOBS
from training.progress_tracker import init_job, list_jobs, update_job, reconcile_incomplete_jobs
from training.trainer import run_training_job

_executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_TRAINING)
_lock = threading.Lock()


def _active_job_count() -> int:
    jobs = list_jobs()
    return sum(1 for job in jobs if job.get("status") in {"queued", "running"})


def submit_training_job(dataset_id: str, dataset_dir: str, config: dict[str, Any], owner: str | None = None) -> dict[str, Any]:
    with _lock:
        active = _active_job_count()
        if active >= MAX_CONCURRENT_TRAINING + MAX_QUEUED_JOBS:
            raise RuntimeError("Training queue is full. Try again later.")

        job_id = uuid.uuid4().hex
        job = init_job(job_id, dataset_id, config, owner=owner)

        def _runner():
            update_job(job_id, status="running")
            run_training_job(job_id, dataset_dir, config, owner=owner)

        _executor.submit(_runner)
        return job


def bootstrap_job_manager() -> None:
    reconcile_incomplete_jobs()
