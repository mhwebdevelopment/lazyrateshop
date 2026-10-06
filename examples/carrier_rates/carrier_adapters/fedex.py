import os
import httpx
from lazyrate import Provider

FEDEX_OAUTH_URL = "https://apis-sandbox.fedex.com/oauth/token"
FEDEX_RATE_URL = "https://apis-sandbox.fedex.com/rate/v1/rates/quotes"


class FedExProvider(Provider):
    name = "FedEx"
    timeout_seconds = 6.0

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        resp = await client.post(
            FEDEX_OAUTH_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": os.environ["FEDEX_CLIENT_ID"],
                "client_secret": os.environ["FEDEX_CLIENT_SECRET"],
            },
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    async def fetch(self, shipment: dict):
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            token = await self._get_token(client)
            payload = {
                "accountNumber": {"value": os.environ["FEDEX_ACCOUNT_NUMBER"]},
                "requestedShipment": {
                    "shipper": {"address": shipment["origin"]},
                    "recipient": {"address": shipment["destination"]},
                    "pickupType": "DROPOFF_AT_FEDEX_LOCATION",
                    "rateRequestType": ["ACCOUNT", "LIST"],
                    "requestedPackageLineItems": shipment["packages"],
                },
            }
            resp = await client.post(
                FEDEX_RATE_URL,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        results = []
        for rd in data.get("output", {}).get("rateReplyDetails", []):
            svc = rd.get("serviceType", "UNKNOWN")
            amount = None
            for detail in rd.get("ratedShipmentDetails", []):
                amount = detail.get("totalNetCharge")
                break
            results.append({"service": svc, "cost": amount, "transit_days": None})
        return results
