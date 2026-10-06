import os
import httpx
from lazyrate import Provider

DAYTON_RATE_URL = "https://api.daytonfreight.com/rates"


class DaytonFreightProvider(Provider):
    name = "Dayton Freight"
    timeout_seconds = 6.0

    async def fetch(self, shipment: dict):
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.post(
                DAYTON_RATE_URL,
                auth=(os.environ["DAYTON_API_USERNAME"], os.environ["DAYTON_API_PASSWORD"]),
                json={
                    "customerNumber": os.environ["DAYTON_CUSTOMER_NUMBER"],
                    "origin": shipment["origin"],
                    "destination": shipment["destination"],
                    "items": shipment["packages"],
                },
            )
            resp.raise_for_status()
            data = resp.json()
        amount = data.get("totalCharge")
        transit = data.get("transitDays")
        return [{"service": "LTL", "cost": amount, "transit_days": transit}]
