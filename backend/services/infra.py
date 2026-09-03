"""Single-node infrastructure behind abstract interfaces (Section 12.2).

Rate limiting and job state are in-memory and fine for one machine. When the app is
later split across machines these two classes get a Redis implementation and nothing
else changes - callers only see ``RateLimiter`` / ``JobStore``.
"""

from __future__ import annotations

import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any


class RateLimiter(ABC):
    @abstractmethod
    def allow(self, key: str, limit_per_minute: int) -> bool:
        """True if the action for ``key`` is within ``limit_per_minute``."""


class InMemoryRateLimiter(RateLimiter):
    """Sliding-window counter keyed by e.g. ``"login:1.2.3.4"``."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit_per_minute: int) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > 60.0:
                q.popleft()
            if len(q) >= limit_per_minute:
                return False
            q.append(now)
            return True


@dataclass
class Job:
    id: str
    status: str = "pending"          # pending|running|done|failed
    result: Any = None
    error: str = ""
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None


class JobStore(ABC):
    @abstractmethod
    def create(self, request: dict) -> str: ...

    @abstractmethod
    def get(self, job_id: str) -> Job | None: ...

    @abstractmethod
    def mark_running(self, job_id: str) -> None: ...

    @abstractmethod
    def mark_done(self, job_id: str, result: Any) -> None: ...

    @abstractmethod
    def mark_failed(self, job_id: str, error: str) -> None: ...

    @abstractmethod
    def counts(self) -> dict[str, int]: ...


class InMemoryJobStore(JobStore):
    def __init__(self, ttl_seconds: float = 3600.0) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds

    def _gc(self) -> None:
        now = time.time()
        drop = [j.id for j in self._jobs.values()
                if j.finished_at and now - j.finished_at > self._ttl]
        for jid in drop:
            self._jobs.pop(jid, None)

    def create(self, request: dict) -> str:
        jid = uuid.uuid4().hex
        with self._lock:
            self._gc()
            self._jobs[jid] = Job(id=jid)
        return jid

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def mark_running(self, job_id: str) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].status = "running"

    def mark_done(self, job_id: str, result: Any) -> None:
        with self._lock:
            j = self._jobs.get(job_id)
            if j:
                j.status, j.result, j.finished_at = "done", result, time.time()

    def mark_failed(self, job_id: str, error: str) -> None:
        with self._lock:
            j = self._jobs.get(job_id)
            if j:
                j.status, j.error, j.finished_at = "failed", error, time.time()

    def counts(self) -> dict[str, int]:
        with self._lock:
            out = {"pending": 0, "running": 0, "done": 0, "failed": 0}
            for j in self._jobs.values():
                out[j.status] = out.get(j.status, 0) + 1
            return out


# process-wide singletons (one uvicorn worker == one process)
rate_limiter: RateLimiter = InMemoryRateLimiter()
job_store: JobStore = InMemoryJobStore()
