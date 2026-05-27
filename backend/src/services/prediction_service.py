"""
Thin httpx wrapper around the ML prediction service.

The backend acts as a proxy so:
  * the frontend keeps talking to `/api/...` (nginx/auth/rate-limit stay in
    one place)
  * the ML service URL is internal config, never exposed to the browser
  * the HttpOnly access_token cookie gets translated into an Authorization
    header for the ML service, which verifies it against the same Redis
    JWKS the backend uses.
"""

import httpx
from fastapi import HTTPException, Request


class PredictionService:
    def __init__(self, http_client: httpx.AsyncClient, base_url: str):
        self._http = http_client
        self._base_url = base_url.rstrip("/")

    @staticmethod
    def _extract_token(request: Request) -> str | None:
        # Cookie (web) takes precedence; bearer header is the API-client path.
        token = request.cookies.get("access_token")
        if token:
            return token
        auth = request.headers.get("authorization") or request.headers.get("Authorization")
        if auth and auth.lower().startswith("bearer "):
            return auth.split(" ", 1)[1].strip()
        return None

    async def _forward(self, path: str, body: dict, request: Request) -> dict:
        token = self._extract_token(request)
        if not token:
            raise HTTPException(status_code=401, detail="not_authenticated")

        url = f"{self._base_url}{path}"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = await self._http.post(url, json=body, headers=headers, timeout=10.0)
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"ml_service_unreachable: {exc}")

        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise HTTPException(status_code=response.status_code, detail=detail)

        return response.json()

    async def predict(self, features: dict, request: Request) -> dict:
        return await self._forward("/api/v1/predict", {"features": features}, request)

    async def predict_batch(self, instances: list[dict], request: Request) -> dict:
        return await self._forward("/api/v1/predict/batch", {"instances": instances}, request)
