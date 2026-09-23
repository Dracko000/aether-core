import asyncio
import logging
from typing import Callable, Dict, Any, Optional
from dataclasses import dataclass
from aether.orchestration.events import bus, Event

logger = logging.getLogger("aether.orchestration.scheduler")

@dataclass
class ScheduledJob:
    id: str
    callback: Callable
    interval: float
    last_run: float = 0.0
    enabled: bool = True

class Scheduler:
    """
    Ticker-based scheduler for recurring system tasks and agent wake-up cycles.
    """
    def __init__(self):
        self._jobs: Dict[str, ScheduledJob] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def schedule(self, job_id: str, interval: float, callback: Callable):
        """Schedule a recurring task."""
        self._jobs[job_id] = ScheduledJob(id=job_id, interval=interval, callback=callback)
        logger.debug(f"Scheduled job {job_id} every {interval}s")

    def unschedule(self, job_id: str):
        """Remove a scheduled task."""
        if job_id in self._jobs:
            del self._jobs[job_id]

    async def start(self):
        """Start the scheduler loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Scheduler started")

    async def stop(self):
        """Stop the scheduler loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler stopped")

    async def _run_loop(self):
        """Internal tick loop."""
        while self._running:
            now = asyncio.get_event_loop().time()
            for job_id, job in self._jobs.items():
                if job.enabled and (now - job.last_run) >= job.interval:
                    try:
                        logger.debug(f"Executing scheduled job: {job_id}")
                        if asyncio.iscoroutinefunction(job.callback):
                            await job.callback()
                        else:
                            job.callback()
                        job.last_run = now
                    except Exception as e:
                        logger.error(f"Error in scheduled job {job_id}: {e}")
                        await bus.publish(Event(
                            type="SYSTEM_ALERT",
                            payload={"job_id": job_id, "error": str(e)}
                        ))

            # Tick every 10ms for higher precision
            await asyncio.sleep(0.01)
