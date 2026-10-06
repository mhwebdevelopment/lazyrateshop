import os
import httpx
from lazyrate import Provider

RL_RATE_URL = "https://api.rlc.com/RateQuote/GetRateQuote"


class RLCarriersProvider(Provider):
    name = "R+L Carriers"
    timeout_seconds = 6.0

    async def fetch(self, shipment: dict):
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.post(
                RL_RATE_URL,
                json={
                    "APIKey": os.environ["RL_API_KEY"],
                    "QuoteType": "Domestic",
                    "Origin": shipment["origin"],
                    "Destination": shipment["destination"],
                    "Items": shipment["packages"],
                },
            )
            resp.raise_for_status()
            data = resp.json()
        levels = data.get("ServiceLevels", [])
        results = []
        for lvl in levels:
            results.append({"service": lvl.get("Name", "LTL"), "cost": lvl.get("NetCharge"), "transit_days": lvl.get("ServiceDays")})
        if not results:
            raise RuntimeError("No service levels returned")
        return results
