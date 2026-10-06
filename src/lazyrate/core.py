"""
lazyrate: generic async fan-out / lazy-load orchestration for aggregating
results from multiple independent, slow, or unreliable backends (carrier
rate APIs, third-party pricing feeds, multi-vendor search, etc.) without
letting the slowest one block everything else.

Core idea: dispatch N async calls concurrently, give each an independent
timeout, and yield results as they complete instead of waiting for all N.

This module contains no mock, simulated, or synthetic data generation.
Providers must implement fetch() against a real backend (HTTP API,
database, queue, etc.). Tests exercise this logic against a local test
HTTP server (see tests/), not against fabricated response payloads.
"""
import asyncio
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional


@dataclass
class TaskResult:
    source: str
    data: Any
    latency_ms: int
    status: str  # "ok" | "error" | "timeout"
    error: Optional[str] = None


class Provider:
    """
    Base class for any async data source you want to fan out to. Subclass
    and implement fetch() with a real network/database/queue call. Give
    each provider its own timeout so it can never stall the rest of the
    batch.
    """
    name: str = "provider"
    timeout_seconds: float = 6.0

    async def fetch(self, request: Any) -> Any:
        raise NotImplementedError

    async def safe_fetch(self, request: Any) -> TaskResult:
        start = time.perf_counter()
        try:
            data = await asyncio.wait_for(self.fetch(request), timeout=self.timeout_seconds)
            elapsed = int((time.perf_counter() - start) * 1000)
            return TaskResult(self.name, data, elapsed, "ok")
        except asyncio.TimeoutError:
            elapsed = int((time.perf_counter() - start) * 1000)
            return TaskResult(self.name, None, elapsed, "timeout", "Provider timed out")
        except Exception as exc:  # noqa: BLE001
            elapsed = int((time.perf_counter() - start) * 1000)
            return TaskResult(self.name, None, elapsed, "error", str(exc))


async def fan_out_stream(providers: list[Provider], request: Any) -> AsyncIterator[TaskResult]:
    """
    Dispatch all providers concurrently and yield each TaskResult the
    instant it resolves, in completion order (not input order). This is
    the lazy-loading primitive: callers can render/consume each result as
    it arrives instead of waiting for the whole batch.
    """
    tasks = [asyncio.create_task(p.safe_fetch(request)) for p in providers]
    for coro in asyncio.as_completed(tasks):
        yield await coro


async def fan_out_blocking(providers: list[Provider], request: Any) -> list[TaskResult]:
    """
    The naive comparison case: waits for every provider before returning
    anything. Total latency = the slowest provider. Included so consumers
    can benchmark against it directly, e.g. in demos or regression tests.
    """
    return await asyncio.gather(*[p.safe_fetch(request) for p in providers])
