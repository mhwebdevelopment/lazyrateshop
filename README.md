# lazyrate

Async fan-out / lazy-load orchestration for aggregating results from
multiple independent, slow, or unreliable backends -- without letting the
slowest one block everything else.

Originated from fixing a multi-carrier freight rate shop (FedEx, UPS,
Dayton Freight, R+L Carriers, Estes) that was taking 5-10s+ per request
because it waited for every carrier before rendering anything. The fix
generalizes to any "call N independent services, show results as they
arrive" problem: multi-vendor price comparison, aggregating search across
providers, dashboard widgets pulling from separate APIs, etc.

## Core idea

1. Dispatch every provider concurrently, never sequentially.
2. Give each provider its own timeout so one hung call can't stall the batch.
3. Stream/yield each result as it completes instead of waiting for all N.

## Install

```bash
pip install -e .
```

## Usage

```python
import asyncio
from lazyrate import Provider, fan_out_stream

class MyAPIProvider(Provider):
    name = "my-api"
    timeout_seconds = 5.0

    async def fetch(self, request):
        # real async HTTP/DB/queue call goes here
        ...

async def main():
    providers = [MyAPIProvider(), AnotherProvider(), ThirdProvider()]
    async for result in fan_out_stream(providers, request={"foo": "bar"}):
        print(result.source, result.status, result.latency_ms, result.data)

asyncio.run(main())
```

`fan_out_stream` yields `TaskResult` objects (`source`, `data`, `latency_ms`,
`status` -- `ok`/`error`/`timeout`, `error`) in completion order, so the
fastest providers render first regardless of input order.

For the naive comparison case (wait for everything, like most codebases
do by default), use `fan_out_blocking`, which returns a list only once
every provider has resolved or timed out.

## Example: multi-carrier rate shopping

See `examples/carrier_rates/` for a complete FastAPI app that fans out to
FedEx, UPS, Dayton Freight, R+L Carriers, and Estes concurrently and
streams results to the browser via Server-Sent Events. This example
calls the real carrier APIs directly:

- `carrier_adapters/` -- HTTP adapters for all 5 carriers (OAuth2
  for FedEx/UPS, API key/basic auth for the LTL carriers) with correct
  production endpoint URLs
- `app.py` -- wires the 5 adapters into lazyrate's fan-out; requires
  live credentials, there is no mock mode

Run it (requires real credentials in `.env`, see `.env.example`):
```bash
pip install -e ".[examples]"
cd examples/carrier_rates
cp .env.example .env   # populate every carrier credential before running
uvicorn app:app --reload
```

## Testing

Tests run against a local HTTP server:
```bash
pip install -e ".[dev]"
pytest
```

## Why not just use asyncio.gather everywhere?

`asyncio.gather` is fine when you only care about the total result and
don't need partial results before everything finishes. `lazyrate` is for
the case where you want to render/consume each result as soon as it's
available (better perceived latency, no head-of-line blocking from one
slow provider) and want per-provider timeout isolation without
hand-rolling it every time.

## License

MIT
