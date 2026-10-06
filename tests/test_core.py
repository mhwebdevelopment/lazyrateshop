"""
Tests exercise fan_out_stream / fan_out_blocking against a real local
HTTP server (see conftest.py). Providers here make genuine httpx async
requests over loopback -- no in-memory mocks or fabricated payloads.
"""
import httpx
import pytest

from lazyrate import Provider, fan_out_stream, fan_out_blocking


class HTTPDelayProvider(Provider):
    """Calls a real HTTP endpoint that sleeps server-side before responding."""
    def __init__(self, name: str, base_url: str, delay_ms: int, fail: bool = False, timeout_seconds: float = 6.0):
        self.name = name
        self.base_url = base_url
        self.delay_ms = delay_ms
        self.fail = fail
        self.timeout_seconds = timeout_seconds

    async def fetch(self, request):
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/?delay_ms={self.delay_ms}&fail={'1' if self.fail else '0'}"
            )
            resp.raise_for_status()
            return resp.text


@pytest.mark.asyncio
async def test_stream_yields_fast_provider_first(http_server):
    fast = HTTPDelayProvider("fast", http_server, delay_ms=20)
    slow = HTTPDelayProvider("slow", http_server, delay_ms=300)
    order = []
    async for result in fan_out_stream([slow, fast], {}):
        order.append(result.source)
    assert order == ["fast", "slow"]


@pytest.mark.asyncio
async def test_timeout_isolates_hung_provider(http_server):
    hung = HTTPDelayProvider("hung", http_server, delay_ms=2000, timeout_seconds=0.2)
    fast = HTTPDelayProvider("fast", http_server, delay_ms=20)
    results = {r.source: r for r in await fan_out_blocking([hung, fast], {})}
    assert results["fast"].status == "ok"
    assert results["hung"].status == "timeout"


@pytest.mark.asyncio
async def test_failure_isolated_per_provider(http_server):
    failing = HTTPDelayProvider("failing", http_server, delay_ms=10, fail=True)
    ok = HTTPDelayProvider("ok", http_server, delay_ms=10, fail=False)
    results = {r.source: r for r in await fan_out_blocking([failing, ok], {})}
    assert results["failing"].status == "error"
    assert results["ok"].status == "ok"
