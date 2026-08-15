import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any, Literal
from urllib.parse import quote

import httpx
from pydantic import ValidationError

from .auth import ClientCredentialsTokenProvider
from .config import CatalogueClientConfig
from .errors import CatalogueProtocolError, CatalogueResponseError
from .models import (
    CropVarietyDetailFetch,
    CropVarietyDetailResponse,
    LivestockBreedListFetch,
    LivestockBreedListResponse,
    LivestockReferenceDataFetch,
    LivestockReferenceDataResponse,
    LivestockRegistryEntryListFetch,
    LivestockRegistryEntryListResponse,
    LivestockRegistryValidationFetch,
    LivestockRegistryValidationResponse,
    LivestockSpeciesListFetch,
    LivestockSpeciesListResponse,
    MasterDataSnapshot,
    SeedVarietyDetailFetch,
    SeedVarietyDetailResponse,
    SeedVarietyListFetch,
    SeedVarietyListResponse,
    SnapshotFetch,
    SyncResult,
    SyncState,
)

TRANSIENT_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class CatalogueClient:
    def __init__(
        self,
        config: CatalogueClientConfig,
        *,
        http_client: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
    ):
        self.config = config
        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.AsyncClient(timeout=config.timeout_seconds)
        self._token_provider = ClientCredentialsTokenProvider(config, self._http_client)
        self._sleep = sleep

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.aclose()

    async def aclose(self):
        if self._owns_http_client:
            await self._http_client.aclose()

    async def fetch_snapshot(
        self,
        *,
        etag: str | None = None,
        release_version: str | None = None,
    ) -> SnapshotFetch:
        headers = {"Accept": "application/json"}
        if etag:
            headers["If-None-Match"] = etag
        params = {"country_code": self.config.country_code}
        if release_version:
            params["release_version"] = release_version

        response = await self._request("GET", "/v1/snapshots/current", headers=headers, params=params)
        if response.status_code == 304:
            unchanged_etag = response.headers.get("ETag") or etag
            if not unchanged_etag:
                raise CatalogueProtocolError("304 response is missing the synchronized ETag")
            return SnapshotFetch(changed=False, etag=unchanged_etag, snapshot=None)
        if not response.is_success:
            raise CatalogueResponseError(response.status_code, _response_message(response))

        response_etag = response.headers.get("ETag")
        release_header = response.headers.get("X-Catalogue-Release")
        if not response_etag or not release_header:
            raise CatalogueProtocolError("Snapshot response is missing ETag or X-Catalogue-Release")
        try:
            snapshot = MasterDataSnapshot.model_validate(response.json())
        except (ValueError, ValidationError) as error:
            raise CatalogueProtocolError(f"Snapshot response is invalid: {error}") from error
        if snapshot.release.version != release_header:
            raise CatalogueProtocolError("Snapshot release does not match X-Catalogue-Release")
        if _unquote_etag(response_etag) != snapshot.release.checksum:
            raise CatalogueProtocolError("Snapshot checksum does not match ETag")
        return SnapshotFetch(changed=True, etag=response_etag, snapshot=snapshot)

    async def sync_snapshot(
        self,
        state: SyncState,
        apply_snapshot: Callable[[MasterDataSnapshot], Awaitable[None]],
    ) -> SyncResult:
        if state.country_code.upper() != self.config.country_code:
            raise ValueError("Sync state country_code does not match client configuration")
        fetched = await self.fetch_snapshot(etag=state.etag)
        if not fetched.changed:
            return SyncResult(changed=False, state=state)

        assert fetched.snapshot is not None
        await apply_snapshot(fetched.snapshot)
        return SyncResult(
            changed=True,
            state=SyncState(
                country_code=self.config.country_code,
                release_version=fetched.snapshot.release.version,
                etag=fetched.etag,
            ),
        )

    async def fetch_crop_variety_detail(
        self,
        variety_code: str,
        *,
        etag: str | None = None,
        release_version: str | None = None,
    ) -> CropVarietyDetailFetch:
        """Fetch one canonical crop variety and its source characteristics."""
        headers = {"Accept": "application/json"}
        if etag:
            headers["If-None-Match"] = etag
        params = {"country_code": self.config.country_code}
        if release_version:
            params["release_version"] = release_version

        response = await self._request(
            "GET",
            f"/v1/crop-varieties/{quote(variety_code, safe='')}",
            headers=headers,
            params=params,
        )
        if response.status_code == 304:
            unchanged_etag = response.headers.get("ETag") or etag
            if not unchanged_etag:
                raise CatalogueProtocolError("304 response is missing the synchronized ETag")
            return CropVarietyDetailFetch(changed=False, etag=unchanged_etag, detail=None)
        if not response.is_success:
            raise CatalogueResponseError(response.status_code, _response_message(response))

        response_etag = response.headers.get("ETag")
        release_header = response.headers.get("X-Catalogue-Release")
        if not response_etag or not release_header:
            raise CatalogueProtocolError("Crop variety response is missing ETag or X-Catalogue-Release")
        try:
            detail = CropVarietyDetailResponse.model_validate(response.json())
        except (ValueError, ValidationError) as error:
            raise CatalogueProtocolError(f"Crop variety response is invalid: {error}") from error
        if detail.release.version != release_header:
            raise CatalogueProtocolError("Crop variety release does not match X-Catalogue-Release")
        if _unquote_etag(response_etag) != detail.release.checksum:
            raise CatalogueProtocolError("Crop variety checksum does not match ETag")
        return CropVarietyDetailFetch(changed=True, etag=response_etag, detail=detail)

    async def fetch_seed_varieties(
        self,
        *,
        seed_crop_code: str | None = None,
        crop_variety_code: str | None = None,
        crop_type_code: str | None = None,
        category_code: str | None = None,
        match_status: str | None = None,
        release_year: int | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 100,
        etag: str | None = None,
        release_version: str | None = None,
    ) -> SeedVarietyListFetch:
        """Fetch a filtered page of seed varieties and source provenance."""
        headers = {"Accept": "application/json"}
        if etag:
            headers["If-None-Match"] = etag
        params = {
            "country_code": self.config.country_code,
            "seed_crop_code": seed_crop_code,
            "crop_variety_code": crop_variety_code,
            "crop_type_code": crop_type_code,
            "category_code": category_code,
            "match_status": match_status,
            "release_year": release_year,
            "search": search,
            "page": page,
            "page_size": page_size,
            "release_version": release_version,
        }
        response = await self._request(
            "GET",
            "/v1/seed-varieties",
            headers=headers,
            params={key: value for key, value in params.items() if value is not None},
        )
        if response.status_code == 304:
            unchanged_etag = response.headers.get("ETag") or etag
            if not unchanged_etag:
                raise CatalogueProtocolError("304 response is missing the synchronized ETag")
            return SeedVarietyListFetch(changed=False, etag=unchanged_etag, listing=None)
        if not response.is_success:
            raise CatalogueResponseError(response.status_code, _response_message(response))

        response_etag = response.headers.get("ETag")
        release_header = response.headers.get("X-Catalogue-Release")
        if not response_etag or not release_header:
            raise CatalogueProtocolError("Seed variety response is missing ETag or X-Catalogue-Release")
        try:
            listing = SeedVarietyListResponse.model_validate(response.json())
        except (ValueError, ValidationError) as error:
            raise CatalogueProtocolError(f"Seed variety response is invalid: {error}") from error
        _validate_seed_variety_integrity(listing.release, response_etag, release_header)
        return SeedVarietyListFetch(changed=True, etag=response_etag, listing=listing)

    async def fetch_seed_variety_detail(
        self,
        seed_variety_code: str,
        *,
        etag: str | None = None,
        release_version: str | None = None,
    ) -> SeedVarietyDetailFetch:
        """Fetch one seed variety with source and reviewed match details."""
        headers = {"Accept": "application/json"}
        if etag:
            headers["If-None-Match"] = etag
        params = {"country_code": self.config.country_code}
        if release_version:
            params["release_version"] = release_version
        response = await self._request(
            "GET",
            f"/v1/seed-varieties/{quote(seed_variety_code, safe='')}",
            headers=headers,
            params=params,
        )
        if response.status_code == 304:
            unchanged_etag = response.headers.get("ETag") or etag
            if not unchanged_etag:
                raise CatalogueProtocolError("304 response is missing the synchronized ETag")
            return SeedVarietyDetailFetch(changed=False, etag=unchanged_etag, detail=None)
        if not response.is_success:
            raise CatalogueResponseError(response.status_code, _response_message(response))

        response_etag = response.headers.get("ETag")
        release_header = response.headers.get("X-Catalogue-Release")
        if not response_etag or not release_header:
            raise CatalogueProtocolError("Seed variety response is missing ETag or X-Catalogue-Release")
        try:
            detail = SeedVarietyDetailResponse.model_validate(response.json())
        except (ValueError, ValidationError) as error:
            raise CatalogueProtocolError(f"Seed variety response is invalid: {error}") from error
        _validate_seed_variety_integrity(detail.release, response_etag, release_header)
        return SeedVarietyDetailFetch(changed=True, etag=response_etag, detail=detail)

    async def fetch_livestock_species(
        self,
        *,
        search: str | None = None,
        page: int = 1,
        page_size: int = 100,
        etag: str | None = None,
        release_version: str | None = None,
    ) -> LivestockSpeciesListFetch:
        """Fetch a typed page of livestock species."""
        return await self._fetch_livestock_resource(
            path="/v1/livestock/species",
            response_model=LivestockSpeciesListResponse,
            fetch_model=LivestockSpeciesListFetch,
            payload_field="listing",
            params={"search": search, "page": page, "page_size": page_size},
            etag=etag,
            release_version=release_version,
            label="Livestock species",
        )

    async def fetch_livestock_breeds(
        self,
        *,
        species_code: str | None = None,
        breed_type: Literal["Indigenous", "Exotic", "Cross"] | None = None,
        in_national_standard: bool | None = None,
        in_etlits_registry: bool | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 100,
        etag: str | None = None,
        release_version: str | None = None,
    ) -> LivestockBreedListFetch:
        """Fetch and filter a typed page of livestock breeds."""
        return await self._fetch_livestock_resource(
            path="/v1/livestock/breeds",
            response_model=LivestockBreedListResponse,
            fetch_model=LivestockBreedListFetch,
            payload_field="listing",
            params={
                "species_code": species_code,
                "breed_type": breed_type,
                "in_national_standard": in_national_standard,
                "in_etlits_registry": in_etlits_registry,
                "search": search,
                "page": page,
                "page_size": page_size,
            },
            etag=etag,
            release_version=release_version,
            label="Livestock breed",
        )

    async def fetch_livestock_reference_data(
        self,
        *,
        etag: str | None = None,
        release_version: str | None = None,
    ) -> LivestockReferenceDataFetch:
        """Fetch livestock gender, location, condition, production, and status values."""
        return await self._fetch_livestock_resource(
            path="/v1/livestock/reference-data",
            response_model=LivestockReferenceDataResponse,
            fetch_model=LivestockReferenceDataFetch,
            payload_field="reference_data",
            params={},
            etag=etag,
            release_version=release_version,
            label="Livestock reference data",
        )

    async def fetch_livestock_registry_entries(
        self,
        *,
        species_code: str | None = None,
        status: str | None = None,
        breed_id: int | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 100,
        etag: str | None = None,
        release_version: str | None = None,
    ) -> LivestockRegistryEntryListFetch:
        """Fetch the release-scoped ET-LITS registry snapshot."""
        return await self._fetch_livestock_resource(
            path="/v1/livestock/registry-entries",
            response_model=LivestockRegistryEntryListResponse,
            fetch_model=LivestockRegistryEntryListFetch,
            payload_field="listing",
            params={
                "species_code": species_code,
                "status": status,
                "breed_id": breed_id,
                "search": search,
                "page": page,
                "page_size": page_size,
            },
            etag=etag,
            release_version=release_version,
            label="Livestock registry",
        )

    async def fetch_livestock_registry_validation(
        self,
        *,
        species_code: str | None = None,
        status: str | None = None,
        has_issues: bool | None = None,
        page: int = 1,
        page_size: int = 100,
        etag: str | None = None,
        release_version: str | None = None,
    ) -> LivestockRegistryValidationFetch:
        """Fetch registry rows with derived catalogue-validation flags."""
        return await self._fetch_livestock_resource(
            path="/v1/livestock/registry-validation",
            response_model=LivestockRegistryValidationResponse,
            fetch_model=LivestockRegistryValidationFetch,
            payload_field="listing",
            params={
                "species_code": species_code,
                "status": status,
                "has_issues": has_issues,
                "page": page,
                "page_size": page_size,
            },
            etag=etag,
            release_version=release_version,
            label="Livestock registry validation",
        )

    async def _fetch_livestock_resource(
        self,
        *,
        path: str,
        response_model,
        fetch_model,
        payload_field: str,
        params: dict[str, Any],
        etag: str | None,
        release_version: str | None,
        label: str,
    ):
        headers = {"Accept": "application/json"}
        if etag:
            headers["If-None-Match"] = etag
        params.update(
            country_code=self.config.country_code,
            release_version=release_version,
        )
        response = await self._request(
            "GET",
            path,
            headers=headers,
            params={key: value for key, value in params.items() if value is not None},
        )
        if response.status_code == 304:
            unchanged_etag = response.headers.get("ETag") or etag
            if not unchanged_etag:
                raise CatalogueProtocolError("304 response is missing the synchronized ETag")
            return fetch_model(changed=False, etag=unchanged_etag, **{payload_field: None})
        if not response.is_success:
            raise CatalogueResponseError(response.status_code, _response_message(response))

        response_etag = response.headers.get("ETag")
        release_header = response.headers.get("X-Catalogue-Release")
        if not response_etag or not release_header:
            raise CatalogueProtocolError(f"{label} response is missing ETag or X-Catalogue-Release")
        try:
            payload = response_model.model_validate(response.json())
        except (ValueError, ValidationError) as error:
            raise CatalogueProtocolError(f"{label} response is invalid: {error}") from error
        _validate_release_integrity(payload.release, response_etag, release_header, label)
        return fetch_model(changed=True, etag=response_etag, **{payload_field: payload})

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        refreshed_after_unauthorized = False
        base_headers = dict(kwargs.pop("headers", {}))
        for attempt in range(1, self.config.max_attempts + 1):
            token = await self._token_provider.get_token()
            headers = dict(base_headers)
            headers["Authorization"] = f"Bearer {token}"
            try:
                response = await self._http_client.request(
                    method,
                    f"{self.config.base_url}{path}",
                    headers=headers,
                    **kwargs,
                )
            except httpx.TransportError:
                if attempt == self.config.max_attempts:
                    raise
                await self._sleep(self._retry_delay(attempt, None))
                continue

            if response.status_code == 401 and not refreshed_after_unauthorized:
                self._token_provider.invalidate()
                refreshed_after_unauthorized = True
                if attempt == self.config.max_attempts:
                    return response
                continue
            if response.status_code not in TRANSIENT_STATUS_CODES or attempt == self.config.max_attempts:
                return response
            await self._sleep(self._retry_delay(attempt, response))
        raise AssertionError("request retry loop exited unexpectedly")

    def _retry_delay(self, attempt: int, response: httpx.Response | None) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return max(0.0, float(retry_after))
                except ValueError:
                    try:
                        parsed = parsedate_to_datetime(retry_after)
                        return max(0.0, parsed.timestamp() - datetime.now(parsed.tzinfo).timestamp())
                    except (TypeError, ValueError, OverflowError):
                        pass
        return self.config.retry_backoff_seconds * (2 ** (attempt - 1))


def _unquote_etag(value: str) -> str:
    value = value.strip()
    if value.startswith("W/"):
        value = value[2:].strip()
    return value[1:-1] if len(value) >= 2 and value[0] == value[-1] == '"' else value


def _validate_seed_variety_integrity(release, response_etag: str, release_header: str) -> None:
    if release.version != release_header:
        raise CatalogueProtocolError("Seed variety release does not match X-Catalogue-Release")
    if _unquote_etag(response_etag) != release.checksum:
        raise CatalogueProtocolError("Seed variety checksum does not match ETag")


def _validate_release_integrity(release, response_etag: str, release_header: str, label: str) -> None:
    if release.version != release_header:
        raise CatalogueProtocolError(f"{label} release does not match X-Catalogue-Release")
    if _unquote_etag(response_etag) != release.checksum:
        raise CatalogueProtocolError(f"{label} checksum does not match ETag")


def _response_message(response: httpx.Response) -> str:
    try:
        body = response.json()
        if isinstance(body, dict) and "detail" in body:
            return str(body["detail"])
    except ValueError:
        pass
    return response.text[:500] or response.reason_phrase
