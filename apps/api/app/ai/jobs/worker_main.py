"""CLI entrypoint: ``python -m app.ai.jobs.worker_main``

Runs a Redis-backed AI generation worker until SIGINT/SIGTERM.
"""

from __future__ import annotations

import asyncio
import logging
import signal

from app.ai.jobs.factory import create_job_queue, normalize_queue_backend
from app.ai.jobs.identity import DEFAULT_WORKER_ID, LOCAL_WORKER_ID
from app.ai.jobs.redis_worker import RedisWorker
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.database import create_engine, create_session_factory
from app.dependencies.ai import get_ai_service
from app.services.ai_job_runner import AIJobRunner

logger = logging.getLogger(__name__)


async def _amain() -> None:
    settings = get_settings()
    configure_logging(settings)
    backend = normalize_queue_backend(settings.ai_queue_backend)
    if backend != "redis":
        raise SystemExit(
            "AI worker requires AI_QUEUE_BACKEND=redis "
            f"(got {settings.ai_queue_backend!r})."
        )

    worker_id = f"{LOCAL_WORKER_ID}"
    queue = create_job_queue(settings, worker_id=worker_id)
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    ai_service = get_ai_service()
    runner = AIJobRunner(ai_service, worker_name=worker_id or DEFAULT_WORKER_ID)
    worker = RedisWorker(
        queue,
        runner,
        session_factory,
        worker_id=worker_id,
        poll_interval=settings.ai_worker_poll_interval,
        max_concurrent=settings.ai_max_concurrent_workers,
    )

    loop = asyncio.get_running_loop()

    def _stop() -> None:
        logger.info("shutdown_signal_received")
        worker.request_shutdown()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _stop)
        except NotImplementedError:
            # Windows / limited environments
            signal.signal(sig, lambda *_: _stop())

    try:
        await worker.run_forever()
    finally:
        client = getattr(queue, "_redis", None)
        if client is not None and hasattr(client, "aclose"):
            await client.aclose()
        await engine.dispose()


def main() -> None:
    asyncio.run(_amain())


if __name__ == "__main__":
    main()
