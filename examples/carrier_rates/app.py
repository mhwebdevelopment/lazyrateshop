"""
Multi-carrier LTL/parcel rate shopping example using lazyrate.

This app calls the real FedEx, UPS, Dayton Freight, R+L Carriers, and
Estes APIs concurrently and streams each carrier's result to the browser
via Server-Sent Events as soon as it resolves, instead of blocking the
whole page on the slowest carrier.

Requires real credentials in .env (see .env.example). There is no mock
mode -- populate every credential below before running.

Run:
    uvicorn app:app --reload
"""
import json
import os
from dataclasses import asdict

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, FileResponse

from lazyrate import fan_out_stream, fan_out_blocking
from carrier_adapters.fedex import FedExProvider
from carrier_adapters.ups import UPSProvider
#from carrier_adapters.dayton import DaytonFreightProvider
#from carrier_adapters.rl_carriers import RLCarriersProvider
#from carrier_adapters.estes import EstesProvider

load_dotenv()

app = FastAPI(title="lazyrate carrier rates example")

PROVIDERS = [
    FedExProvider(),
    UPSProvider(),
#    DaytonFreightProvider(),
#    RLCarriersProvider(),
#    EstesProvider(),
]

# Populate with a real shipment; origin/destination/packages must match
# each carrier's expected address and package schema (see adapter files).
SAMPLE_SHIPMENT = {
    "origin": {"city": "Hickory Hills", "state": "IL", "postalCode": "60457", "country": "US"},
    "destination": {"city": "Columbus", "state": "OH", "postalCode": "43004", "country": "US"},
    "packages": [{"weight": 150, "length": 48, "width": 40, "height": 36, "class": 70}],
}


@app.get("/")
async def index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static_index.html"))


@app.get("/api/rates/stream")
async def stream_rates(request: Request):
    async def event_gen():
        yield f"event: start\ndata: {json.dumps({'providers': [p.name for p in PROVIDERS]})}\n\n"
        async for result in fan_out_stream(PROVIDERS, SAMPLE_SHIPMENT):
            if await request.is_disconnected():
                break
            yield f"event: rate\ndata: {json.dumps(asdict(result))}\n\n"
        yield "event: done\ndata: {}\n\n"
    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.get("/api/rates/blocking")
async def blocking_rates():
    results = await fan_out_blocking(PROVIDERS, SAMPLE_SHIPMENT)
    return {"results": [asdict(r) for r in results]}
