import asyncio
import time

import httpx

from .config import CatalogueClientConfig
from .errors import CatalogueAuthenticationError


class ClientCredentialsTokenProvider:
    def __init__(self, config: CatalogueClientConfig, http_client: httpx.AsyncClient):
        self._config = config
        self._http_client = http_client
        self._access_token: str | None = None
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    def invalidate(self):
        self._access_token = None
        self._expires_at = 0.0

    async def get_token(self) -> str:
        if self._access_token is not None and time.monotonic() < self._expires_at:
            return self._access_token

        async with self._lock:
            if self._access_token is not None and time.monotonic() < self._expires_at:
                return self._access_token
            return await self._request_token()

    async def _request_token(self) -> str:
        form = {"grant_type": "client_credentials"}
        if self._config.scope:
            form["scope"] = self._config.scope
        try:
            response = await self._http_client.post(
                self._config.token_url,
                data=form,
                auth=(self._config.client_id, self._config.client_secret),
            )
        except httpx.HTTPError as error:
            raise CatalogueAuthenticationError(f"Token request failed: {error}") from error

        if not response.is_success:
            raise CatalogueAuthenticationError(f"Token endpoint returned HTTP {response.status_code}")
        try:
            body = response.json()
            access_token = body["access_token"]
            expires_in = float(body.get("expires_in", 60))
        except (KeyError, TypeError, ValueError) as error:
            raise CatalogueAuthenticationError(
                "Token response is missing valid access_token metadata"
            ) from error
        if not isinstance(access_token, str) or not access_token:
            raise CatalogueAuthenticationError("Token response contains an invalid access_token")

        self._access_token = access_token
        self._expires_at = time.monotonic() + max(0, expires_in - min(30, expires_in * 0.1))
        return access_token
