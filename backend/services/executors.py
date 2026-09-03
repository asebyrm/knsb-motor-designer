"""Executor pools that keep CPU-bound work off the event loop (Section 12.2).

* Forward simulation is fast (<200 ms) but still synchronous -> a **thread pool**
  so a slow request cannot stall the worker's event loop.
* The mission solver can run tens of seconds -> a **ProcessPoolExecutor**, never
  awaited directly.

``run_simulation_async`` / ``solve_mission_async`` are the only entry points the API
uses. The pools are created on app startup and shut down on the lifespan exit.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

from app_config import get_settings

_thread_pool: ThreadPoolExecutor | None = None
_process_pool: ProcessPoolExecutor | None = None


def start_pools() -> None:
    global _thread_pool, _process_pool
    s = get_settings()
    if _thread_pool is None:
        _thread_pool = ThreadPoolExecutor(max_workers=s.sim_thread_workers,
                                          thread_name_prefix="sim")
    if _process_pool is None:
        _process_pool = ProcessPoolExecutor(max_workers=max(1, s.solver_processes))


def shutdown_pools() -> None:
    global _thread_pool, _process_pool
    if _thread_pool is not None:
        _thread_pool.shutdown(wait=False, cancel_futures=True)
        _thread_pool = None
    if _process_pool is not None:
        _process_pool.shutdown(wait=False, cancel_futures=True)
        _process_pool = None


def _ensure() -> None:
    if _thread_pool is None or _process_pool is None:
        start_pools()


# --- module-level workers (must be importable for ProcessPoolExecutor pickling) ---

def _run_simulation_worker(design: dict, downsample: int) -> dict:
    from services.simulation_service import run_simulation

    return run_simulation(design, downsample=downsample)


def _solve_mission_worker(payload: dict) -> dict:
    from core.solver import MissionInput, solve_mission

    cfg = MissionInput(**payload)
    return solve_mission(cfg).to_dict()


async def run_simulation_async(design: dict, *, downsample: int = 500,
                               timeout: float | None = None) -> dict:
    _ensure()
    loop = asyncio.get_running_loop()
    fut = loop.run_in_executor(_thread_pool, _run_simulation_worker, design, downsample)
    return await asyncio.wait_for(fut, timeout=timeout)


async def solve_mission_async(payload: dict, *, timeout: float | None = None) -> dict:
    _ensure()
    loop = asyncio.get_running_loop()
    fut = loop.run_in_executor(_process_pool, _solve_mission_worker, payload)
    return await asyncio.wait_for(fut, timeout=timeout)


def pool_stats() -> dict:
    tp = _thread_pool
    pp = _process_pool
    return {
        "thread_pool_workers": tp._max_workers if tp else 0,
        "thread_pool_queue": tp._work_queue.qsize() if tp else 0,
        "process_pool_workers": pp._max_workers if pp else 0,
        "process_pool_pending": len(getattr(pp, "_pending_work_items", {})) if pp else 0,
    }
