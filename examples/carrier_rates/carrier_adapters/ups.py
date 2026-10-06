import os
import httpx
from lazyrate import Provider

UPS_OAUTH_URL = "https://wwwcie.ups.com/security/v1/oauth/token"
UPS_RATE_URL = "https://wwwcie.ups.com/api/rating/v2409/Shop"


class UPSProvider(Provider):
    name = "UPS"
    timeout_seconds = 6.0

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        resp = await client.post(
            UPS_OAUTH_URL,
            data={"grant_type": "client_credentials"},
            auth=(os.environ["UPS_CLIENT_ID"], os.environ["UPS_CLIENT_SECRET"]),
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    async def fetch(self, shipment: dict):
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            token = await self._get_token(client)
            payload = {
                "RateRequest": {
                    "Shipment": {
                        "Shipper": {"Address": shipment["origin"]},
                        "ShipTo": {"Address": shipment["destination"]},
                        "Package": shipment["packages"],
                    }
                }
            }
            resp = await client.post(
                UPS_RATE_URL,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        results = []
        for rated in data.get("RateResponse", {}).get("RatedShipment", []):
            svc = rated.get("Service", {}).get("Code", "UNKNOWN")
            amount = rated.get("TotalCharges", {}).get("MonetaryValue")
            results.append({"service": svc, "cost": float(amount) if amount else None, "transit_days": None})
        return results
