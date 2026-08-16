import sys
from pathlib import Path

import httpx
import pytest

CLIENT_SRC = Path(__file__).resolve().parents[2] / "catalogue-client" / "src"
sys.path.insert(0, str(CLIENT_SRC))

from openg2p_catalogue_client import (
    CatalogueClient,
    CatalogueClientConfig,
    CatalogueProtocolError,
    CatalogueResponseError,
    CatalogueValue,
    SyncState,
)


def config(**overrides):
    values = {
        "base_url": "https://catalogue.test/",
        "token_url": "https://iam.test/token",
        "client_id": "registry",
        "client_secret": "secret",
        "country_code": "eth",
        "max_attempts": 3,
        "retry_backoff_seconds": 0,
    }
    values.update(overrides)
    return CatalogueClientConfig(**values)


def snapshot(version="v1", checksum="checksum-v1"):
    return {
        "release": {
            "country_code": "ETH",
            "version": version,
            "schema_version": "005",
            "checksum": checksum,
            "status": "ACTIVE",
        },
        "catalogues": [],
        "geography": {"levels": [], "units": []},
        "agriculture_statistics": {
            "livestock_population": [],
            "seed_demand_summary": [],
            "seed_demand_trends": [],
            "seed_demand_by_crop": [],
        },
    }


def response_snapshot(request, *, version="v1", checksum="checksum-v1"):
    return httpx.Response(
        200,
        request=request,
        headers={"ETag": f'"{checksum}"', "X-Catalogue-Release": version},
        json=snapshot(version, checksum),
    )


@pytest.mark.asyncio
async def test_fetch_snapshot_uses_client_credentials_and_validates_release_integrity():
    seen = []

    def handler(request):
        seen.append(request)
        if request.url.host == "iam.test":
            assert request.headers["authorization"].startswith("Basic ")
            assert b"grant_type=client_credentials" in request.content
            return httpx.Response(200, request=request, json={"access_token": "token", "expires_in": 300})
        assert request.headers["authorization"] == "Bearer token"
        assert request.url.params["country_code"] == "ETH"
        return response_snapshot(request)

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = CatalogueClient(config(), http_client=http_client)
    result = await client.fetch_snapshot()
    await http_client.aclose()

    assert result.changed is True
    assert result.etag == '"checksum-v1"'
    assert result.snapshot.release.version == "v1"
    assert len(seen) == 2


@pytest.mark.asyncio
async def test_unchanged_snapshot_returns_state_without_invoking_apply_callback():
    applied = False

    def handler(request):
        if request.url.host == "iam.test":
            return httpx.Response(200, request=request, json={"access_token": "token", "expires_in": 300})
        assert request.headers["if-none-match"] == '"checksum-v1"'
        return httpx.Response(304, request=request, headers={"ETag": '"checksum-v1"'})

    async def apply_snapshot(_snapshot):
        nonlocal applied
        applied = True

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = CatalogueClient(config(), http_client=http_client)
    state = SyncState(country_code="ETH", release_version="v1", etag='"checksum-v1"')
    result = await client.sync_snapshot(state, apply_snapshot)
    await http_client.aclose()

    assert result.changed is False
    assert result.state is state
    assert applied is False


@pytest.mark.asyncio
async def test_changed_snapshot_is_applied_before_new_sync_state_is_returned():
    applied_versions = []

    def handler(request):
        if request.url.host == "iam.test":
            return httpx.Response(200, request=request, json={"access_token": "token", "expires_in": 300})
        return response_snapshot(request, version="v2", checksum="checksum-v2")

    async def apply_snapshot(value):
        applied_versions.append(value.release.version)

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = CatalogueClient(config(), http_client=http_client)
    result = await client.sync_snapshot(SyncState(country_code="ETH"), apply_snapshot)
    await http_client.aclose()

    assert applied_versions == ["v2"]
    assert result.changed is True
    assert result.state.release_version == "v2"
    assert result.state.etag == '"checksum-v2"'


@pytest.mark.asyncio
async def test_apply_failure_does_not_produce_advanced_sync_state():
    def handler(request):
        if request.url.host == "iam.test":
            return httpx.Response(200, request=request, json={"access_token": "token", "expires_in": 300})
        return response_snapshot(request)

    async def reject_snapshot(_snapshot):
        raise RuntimeError("local transaction rolled back")

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = CatalogueClient(config(), http_client=http_client)
    with pytest.raises(RuntimeError, match="rolled back"):
        await client.sync_snapshot(SyncState(country_code="ETH"), reject_snapshot)
    await http_client.aclose()


@pytest.mark.asyncio
async def test_transient_retry_preserves_etag_and_honors_retry_after():
    api_attempts = 0
    delays = []

    def handler(request):
        nonlocal api_attempts
        if request.url.host == "iam.test":
            return httpx.Response(200, request=request, json={"access_token": "token", "expires_in": 300})
        api_attempts += 1
        assert request.headers["if-none-match"] == '"old"'
        if api_attempts == 1:
            return httpx.Response(503, request=request, headers={"Retry-After": "2"})
        return response_snapshot(request)

    async def record_sleep(delay):
        delays.append(delay)

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = CatalogueClient(config(), http_client=http_client, sleep=record_sleep)
    result = await client.fetch_snapshot(etag='"old"')
    await http_client.aclose()

    assert result.changed is True
    assert api_attempts == 2
    assert delays == [2.0]


@pytest.mark.asyncio
async def test_unauthorized_response_refreshes_token_once():
    token_requests = 0
    bearer_tokens = []

    def handler(request):
        nonlocal token_requests
        if request.url.host == "iam.test":
            token_requests += 1
            return httpx.Response(
                200,
                request=request,
                json={"access_token": f"token-{token_requests}", "expires_in": 300},
            )
        bearer_tokens.append(request.headers["authorization"])
        if len(bearer_tokens) == 1:
            return httpx.Response(401, request=request)
        return response_snapshot(request)

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = CatalogueClient(config(), http_client=http_client)
    result = await client.fetch_snapshot()
    await http_client.aclose()

    assert result.changed is True
    assert token_requests == 2
    assert bearer_tokens == ["Bearer token-1", "Bearer token-2"]


@pytest.mark.asyncio
async def test_terminal_response_and_invalid_integrity_are_explicit_errors():
    api_response = "forbidden"

    def handler(request):
        if request.url.host == "iam.test":
            return httpx.Response(200, request=request, json={"access_token": "token", "expires_in": 300})
        if api_response == "forbidden":
            return httpx.Response(403, request=request, json={"detail": "missing snapshot.read"})
        return httpx.Response(
            200,
            request=request,
            headers={"ETag": '"different"', "X-Catalogue-Release": "v1"},
            json=snapshot(),
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = CatalogueClient(config(), http_client=http_client)
    with pytest.raises(CatalogueResponseError, match="missing snapshot.read"):
        await client.fetch_snapshot()

    api_response = "invalid"
    with pytest.raises(CatalogueProtocolError, match="checksum does not match"):
        await client.fetch_snapshot()
    await http_client.aclose()


def test_configuration_normalizes_service_and_country_and_rejects_unbounded_values():
    value = config()
    assert value.base_url == "https://catalogue.test"
    assert value.country_code == "ETH"
    with pytest.raises(ValueError, match="max_attempts"):
        config(max_attempts=0)


def test_client_validates_typed_cross_catalogue_relations():
    value = CatalogueValue.model_validate(
        {
            "code": "1",
            "display_name": "Maize",
            "status": "ACTIVE",
            "relations": [
                {
                    "type": "category",
                    "target_catalogue_code": "crop_category",
                    "target_code": "1",
                    "target_display_name": "Cereal Crops",
                }
            ],
        }
    )

    assert value.relations[0].target_catalogue_code == "crop_category"


@pytest.mark.asyncio
async def test_unsolicited_304_without_an_etag_is_rejected():
    def handler(request):
        if request.url.host == "iam.test":
            return httpx.Response(200, request=request, json={"access_token": "token", "expires_in": 300})
        return httpx.Response(304, request=request)

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = CatalogueClient(config(), http_client=http_client)
    with pytest.raises(CatalogueProtocolError, match="missing the synchronized ETag"):
        await client.fetch_snapshot()
    await http_client.aclose()


def crop_variety_detail():
    return {
        "release": {
            "country_code": "ETH",
            "version": "ETH-crop-taxonomy-v3",
            "schema_version": "008",
            "checksum": "crop-checksum",
            "status": "ACTIVE",
        },
        "variety": {
            "code": "maize-melkassa-1-q",
            "display_name": "Melkassa-1Q",
            "status": "ACTIVE",
            "crop_type": {"code": "maize", "display_name": "Maize"},
            "category": {"code": "cereal", "display_name": "Cereal Crops"},
            "source_records": [
                {
                    "source_record_code": "maize-melkassa-1-q-2013",
                    "centre": "Melkassa",
                    "release_year_raw": "2013",
                    "release_year": 2013,
                    "altitude_min_m": "1000",
                    "characteristics": [
                        {
                            "code": "grain-color",
                            "display_name": "Grain Color",
                            "value_type": "TEXT",
                            "raw_value": "White",
                            "value_text": "White",
                        }
                    ],
                }
            ],
        },
    }


@pytest.mark.asyncio
async def test_fetch_crop_variety_detail_is_typed_and_supports_release_pinning():
    def handler(request):
        if request.url.host == "iam.test":
            return httpx.Response(200, request=request, json={"access_token": "token", "expires_in": 300})
        assert request.url.path == "/v1/crop-varieties/maize-melkassa-1-q"
        assert request.url.params["country_code"] == "ETH"
        assert request.url.params["release_version"] == "ETH-crop-taxonomy-v3"
        return httpx.Response(
            200,
            request=request,
            headers={"ETag": '"crop-checksum"', "X-Catalogue-Release": "ETH-crop-taxonomy-v3"},
            json=crop_variety_detail(),
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = CatalogueClient(config(), http_client=http_client)
    result = await client.fetch_crop_variety_detail(
        "maize-melkassa-1-q",
        release_version="ETH-crop-taxonomy-v3",
    )
    await http_client.aclose()

    assert result.changed is True
    assert result.detail.variety.crop_type.code == "maize"
    assert result.detail.variety.category.code == "cereal"
    assert result.detail.variety.source_records[0].altitude_min_m == 1000
    assert result.detail.variety.source_records[0].characteristics[0].value_text == "White"


@pytest.mark.asyncio
async def test_fetch_crop_variety_detail_handles_conditional_and_terminal_responses():
    api_response = "unchanged"

    def handler(request):
        if request.url.host == "iam.test":
            return httpx.Response(200, request=request, json={"access_token": "token", "expires_in": 300})
        assert request.headers["if-none-match"] == '"crop-checksum"'
        if api_response == "unchanged":
            return httpx.Response(304, request=request)
        return httpx.Response(404, request=request, json={"detail": "Crop variety 'unknown' was not found"})

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = CatalogueClient(config(), http_client=http_client)
    result = await client.fetch_crop_variety_detail("maize", etag='"crop-checksum"')
    assert result.changed is False
    assert result.detail is None

    api_response = "missing"
    with pytest.raises(CatalogueResponseError, match="was not found") as error:
        await client.fetch_crop_variety_detail("unknown", etag='"crop-checksum"')
    assert error.value.status_code == 404
    await http_client.aclose()


@pytest.mark.asyncio
async def test_fetch_crop_variety_detail_rejects_invalid_release_integrity():
    def handler(request):
        if request.url.host == "iam.test":
            return httpx.Response(200, request=request, json={"access_token": "token", "expires_in": 300})
        return httpx.Response(
            200,
            request=request,
            headers={"ETag": '"wrong"', "X-Catalogue-Release": "ETH-crop-taxonomy-v3"},
            json=crop_variety_detail(),
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = CatalogueClient(config(), http_client=http_client)
    with pytest.raises(CatalogueProtocolError, match="checksum does not match"):
        await client.fetch_crop_variety_detail("maize-melkassa-1-q")
    await http_client.aclose()


def seed_variety(code="ethioseed-20", matched=True):
    return {
        "code": code,
        "display_name": "Melkassa-1Q",
        "status": "ACTIVE",
        "source_variety_id": 20,
        "seed_crop": {"code": "1", "display_name": "Maize"},
        "matched_crop_variety": (
            {"code": "maize-melkassa-1-q", "display_name": "Melkassa-1Q"} if matched else None
        ),
        "crop_type": {"code": "maize", "display_name": "Maize"} if matched else None,
        "category": {"code": "cereal", "display_name": "Cereals"} if matched else None,
        "crop_name_raw": "Maize",
        "common_name_raw": "Melkassa-1Q",
        "category_raw": "Cereal",
        "release_year": 2008,
        "release_date": "2008-01-01",
        "release_raw": "2008",
        "maintainer": "EIAR",
        "source_classification": "Domestic",
        "details_url": "https://ethioseed.example/20",
        "match_method": "EXACT_NAME_AND_CROP" if matched else "UNRESOLVED",
        "match_status": "MATCHED" if matched else "UNRESOLVED",
        "review_note": None,
    }


def seed_release():
    return {
        "country_code": "ETH",
        "version": "ETH-crop-taxonomy-v4",
        "schema_version": "009",
        "checksum": "seed-checksum",
        "status": "ACTIVE",
    }


@pytest.mark.asyncio
async def test_fetch_seed_varieties_is_typed_and_sends_filters():
    def handler(request):
        if request.url.host == "iam.test":
            return httpx.Response(200, request=request, json={"access_token": "token", "expires_in": 300})
        assert request.url.path == "/v1/seed-varieties"
        assert request.url.params["country_code"] == "ETH"
        assert request.url.params["crop_type_code"] == "maize"
        assert request.url.params["match_status"] == "MATCHED"
        assert request.url.params["release_year"] == "2008"
        assert request.url.params["page"] == "2"
        assert request.url.params["page_size"] == "25"
        assert request.url.params["release_version"] == "ETH-crop-taxonomy-v4"
        return httpx.Response(
            200,
            request=request,
            headers={
                "ETag": '"seed-checksum"',
                "X-Catalogue-Release": "ETH-crop-taxonomy-v4",
            },
            json={
                "release": seed_release(),
                "varieties": [seed_variety()],
                "total": 309,
                "page": 2,
                "page_size": 25,
            },
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = CatalogueClient(config(), http_client=http_client)
    result = await client.fetch_seed_varieties(
        crop_type_code="maize",
        match_status="MATCHED",
        release_year=2008,
        page=2,
        page_size=25,
        release_version="ETH-crop-taxonomy-v4",
    )
    await http_client.aclose()

    assert result.changed is True
    assert result.listing.total == 309
    assert result.listing.varieties[0].crop_type.code == "maize"
    assert result.listing.varieties[0].release_date.year == 2008


@pytest.mark.asyncio
async def test_fetch_seed_variety_detail_handles_conditional_and_not_found():
    response_kind = "unchanged"

    def handler(request):
        if request.url.host == "iam.test":
            return httpx.Response(200, request=request, json={"access_token": "token", "expires_in": 300})
        assert request.headers["if-none-match"] == '"seed-checksum"'
        if response_kind == "unchanged":
            return httpx.Response(304, request=request)
        return httpx.Response(404, request=request, json={"detail": "Unknown seed variety"})

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = CatalogueClient(config(), http_client=http_client)
    result = await client.fetch_seed_variety_detail("ethioseed-20", etag='"seed-checksum"')
    assert result.changed is False
    assert result.detail is None

    response_kind = "missing"
    with pytest.raises(CatalogueResponseError, match="Unknown seed variety") as error:
        await client.fetch_seed_variety_detail("ethioseed-999999", etag='"seed-checksum"')
    assert error.value.status_code == 404
    await http_client.aclose()


@pytest.mark.asyncio
async def test_fetch_seed_variety_detail_validates_integrity_and_unresolved_shape():
    checksum = "seed-checksum"

    def handler(request):
        if request.url.host == "iam.test":
            return httpx.Response(200, request=request, json={"access_token": "token", "expires_in": 300})
        return httpx.Response(
            200,
            request=request,
            headers={
                "ETag": f'"{checksum}"',
                "X-Catalogue-Release": "ETH-crop-taxonomy-v4",
            },
            json={"release": seed_release(), "variety": seed_variety(matched=False)},
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = CatalogueClient(config(), http_client=http_client)
    result = await client.fetch_seed_variety_detail("ethioseed-20")
    assert result.detail.variety.match_status == "UNRESOLVED"
    assert result.detail.variety.matched_crop_variety is None

    checksum = "wrong"
    with pytest.raises(CatalogueProtocolError, match="checksum does not match"):
        await client.fetch_seed_variety_detail("ethioseed-20")
    await http_client.aclose()


def livestock_release():
    return {
        "country_code": "ETH",
        "version": "ETH-catalogue-v8",
        "schema_version": "1.7",
        "checksum": "livestock-checksum",
        "status": "ACTIVE",
    }


@pytest.mark.asyncio
async def test_fetch_livestock_species_is_typed_and_supports_release_pinning():
    def handler(request):
        if request.url.host == "iam.test":
            return httpx.Response(200, request=request, json={"access_token": "token", "expires_in": 300})
        assert request.url.path == "/v1/livestock/species"
        assert request.url.params["country_code"] == "ETH"
        assert request.url.params["search"] == "cattle"
        assert request.url.params["release_version"] == "ETH-catalogue-v8"
        return httpx.Response(
            200,
            request=request,
            headers={
                "ETag": '"livestock-checksum"',
                "X-Catalogue-Release": "ETH-catalogue-v8",
            },
            json={
                "release": livestock_release(),
                "species": [
                    {
                        "code": "cattle",
                        "display_name": "Cattle",
                        "status": "ACTIVE",
                        "scientific_name": "Bos taurus & Bos indicus",
                        "in_lis_population": True,
                        "in_etlits_registry": True,
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 25,
            },
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = CatalogueClient(config(), http_client=http_client)
    result = await client.fetch_livestock_species(
        search="cattle",
        page_size=25,
        release_version="ETH-catalogue-v8",
    )
    await http_client.aclose()

    assert result.changed is True
    assert result.listing.species[0].code == "cattle"
    assert result.listing.species[0].scientific_name == "Bos taurus & Bos indicus"


@pytest.mark.asyncio
async def test_fetch_livestock_breeds_sends_registry_filters_and_validates_relations():
    def handler(request):
        if request.url.host == "iam.test":
            return httpx.Response(200, request=request, json={"access_token": "token", "expires_in": 300})
        assert request.url.path == "/v1/livestock/breeds"
        assert request.url.params["species_code"] == "cattle"
        assert request.url.params["breed_type"] == "Indigenous"
        assert request.url.params["in_national_standard"] == "true"
        assert request.url.params["in_etlits_registry"] == "true"
        return httpx.Response(
            200,
            request=request,
            headers={
                "ETag": '"livestock-checksum"',
                "X-Catalogue-Release": "ETH-catalogue-v8",
            },
            json={
                "release": livestock_release(),
                "breeds": [
                    {
                        "code": "1.01.10",
                        "display_name": "Boran",
                        "status": "ACTIVE",
                        "species": {"code": "cattle", "display_name": "Cattle"},
                        "source_id": 10,
                        "breed_code": "1.01.10",
                        "abbreviation": "BOR",
                        "breed_type": "Indigenous",
                        "in_national_standard": True,
                        "in_etlits_registry": True,
                        "source": "National Livestock Data Standard (MOA, 2024)",
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 100,
            },
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = CatalogueClient(config(), http_client=http_client)
    result = await client.fetch_livestock_breeds(
        species_code="cattle",
        breed_type="Indigenous",
        in_national_standard=True,
        in_etlits_registry=True,
    )
    await http_client.aclose()

    boran = result.listing.breeds[0]
    assert boran.species.code == "cattle"
    assert boran.breed_type == "Indigenous"
    assert boran.in_etlits_registry is True


@pytest.mark.asyncio
async def test_fetch_livestock_reference_data_supports_conditional_etags():
    response_kind = "changed"

    def handler(request):
        if request.url.host == "iam.test":
            return httpx.Response(200, request=request, json={"access_token": "token", "expires_in": 300})
        assert request.url.path == "/v1/livestock/reference-data"
        if response_kind == "unchanged":
            assert request.headers["if-none-match"] == '"livestock-checksum"'
            return httpx.Response(304, request=request)
        return httpx.Response(
            200,
            request=request,
            headers={
                "ETag": '"livestock-checksum"',
                "X-Catalogue-Release": "ETH-catalogue-v8",
            },
            json={
                "release": livestock_release(),
                "genders": [
                    {
                        "code": "Female",
                        "display_name": "Female",
                        "in_etlits_registry": True,
                    }
                ],
                "location_types": [
                    {
                        "code": "Low Land",
                        "display_name": "Low Land",
                        "ecological_zone": {"code": "1", "display_name": "Kolla"},
                    }
                ],
                "body_conditions": [
                    {
                        "code": "3",
                        "display_name": "Medium",
                        "bcs_score": 3,
                        "condition_label": "Medium",
                        "fatness_label": "Moderate",
                    }
                ],
                "production_types": [
                    {
                        "code": "Milk",
                        "display_name": "Milk",
                        "in_national_standard": True,
                        "in_etlits_registry": True,
                        "valid_species": [{"code": "cattle", "display_name": "Cattle"}],
                    }
                ],
                "record_statuses": [
                    {
                        "code": "PENDING",
                        "display_name": "Pending",
                        "sort_order": 1,
                        "is_live_master_data": True,
                    }
                ],
            },
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = CatalogueClient(config(), http_client=http_client)
    result = await client.fetch_livestock_reference_data()
    assert result.reference_data.production_types[0].valid_species[0].code == "cattle"

    response_kind = "unchanged"
    unchanged = await client.fetch_livestock_reference_data(etag=result.etag)
    await http_client.aclose()
    assert unchanged.changed is False
    assert unchanged.reference_data is None


@pytest.mark.asyncio
async def test_fetch_livestock_registry_entries_is_typed_and_filterable():
    def handler(request):
        if request.url.host == "iam.test":
            return httpx.Response(200, request=request, json={"access_token": "token", "expires_in": 300})
        assert request.url.path == "/v1/livestock/registry-entries"
        assert request.url.params["species_code"] == "cattle"
        assert request.url.params["status"] == "ACTIVE"
        return httpx.Response(
            200,
            request=request,
            headers={
                "ETag": '"livestock-checksum"',
                "X-Catalogue-Release": "ETH-catalogue-v8",
            },
            json={
                "release": livestock_release(),
                "entries": [
                    {
                        "id": "livestock-008569662215",
                        "species_code": "cattle",
                        "breed_name": "Boran",
                        "breed_id": 10,
                        "breed_code": "1.01.10",
                        "breed_species_code": "cattle",
                        "gender_code": "Female",
                        "location_type_code": "Low Land",
                        "body_condition_code": "BCS3",
                        "production_type_code": "Milk",
                        "status": "ACTIVE",
                        "created_on": "2026-08-10T11:28:32.902Z",
                        "updated_on": "2026-08-13T07:49:28.294Z",
                        "validation": {
                            "id": "livestock-008569662215",
                            "status": "ACTIVE",
                            "species_code": "cattle",
                            "breed_name": "Boran",
                            "breed_code": "1.01.10",
                            "breed_species_code": "cattle",
                            "production_type_code": "Milk",
                            "breed_unrecognised": False,
                            "breed_outside_national_standard": False,
                            "breed_species_mismatch": False,
                            "production_type_species_mismatch": False,
                        },
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 100,
            },
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = CatalogueClient(config(), http_client=http_client)
    result = await client.fetch_livestock_registry_entries(species_code="cattle", status="ACTIVE")
    await http_client.aclose()

    assert result.changed is True
    assert result.listing.total == 1
    assert result.listing.entries[0].breed_id == 10
    assert result.listing.entries[0].validation.breed_unrecognised is False
