import os
import httpx
from lazyrate import Provider

ESTES_RATE_URL = "https://apiproxy.estes-express.com/v4/rate-quotes"


class EstesProvider(Provider):
    """
    Estes is rarely used by this 3PL. Give it the same (or a shorter)
    timeout as the others so a stalled/rare-use carrier never becomes the
    bottleneck for the whole rate shop.
    """
    name = "Estes"
    timeout_seconds = 5.0

    async def fetch(self, shipment: dict):
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.post(
                ESTES_RATE_URL,
                headers={"apikey": os.environ["ESTES_API_KEY"]},
                auth=(os.environ["ESTES_USERNAME"], os.environ["ESTES_PASSWORD"]),
                json={
                    "origin": shipment["origin"],
                    "destination": shipment["destination"],
                    "commodities": shipment["packages"],
                },
            )
            resp.raise_for_status()
            data = resp.json()
        amount = data.get("rateQuote", {}).get("totalCharges")
        transit = data.get("rateQuote", {}).get("transitDays")
        return [{"service": "LTL", "cost": amount, "transit_days": transit}]
