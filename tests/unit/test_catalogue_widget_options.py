import pytest
from fastapi import Response
from openg2p_catalogue_service.controllers import CatalogueController
from openg2p_catalogue_service.schemas import CatalogueValuesResponse, catalogue_options


def catalogue_response(values):
    return CatalogueValuesResponse.model_validate(
        {
            "release": {
                "country_code": "ETH",
                "version": "ETH-catalogue-v9",
                "schema_version": "1.8",
                "checksum": "abc123",
                "status": "ACTIVE",
            },
            "catalogue": {
                "code": "crop_category",
                "domain": "crop",
                "display_name": "Crop category",
                "status": "ACTIVE",
            },
            "values": values,
            "total": len(values),
            "page": 1,
            "page_size": 100,
        }
    )


def test_catalogue_options_expose_only_normalized_widget_fields():
    values = catalogue_response(
        [
            {
                "code": " 1 ",
                "display_name": " Cereal Crops ",
                "status": "ACTIVE",
                "metadata": {"source": "SQL"},
                "relations": [
                    {
                        "type": "example",
                        "target_catalogue_code": "other",
                        "target_code": "x",
                        "target_display_name": "Other",
                    }
                ],
            }
        ]
    )

    response = catalogue_options(values)

    assert response.options[0].model_dump() == {
        "code": "1",
        "display_name": "Cereal Crops",
    }
    assert response.release.version == "ETH-catalogue-v9"
    assert response.total == 1


@pytest.mark.parametrize(
    ("code", "display_name"),
    [("", "Cereal Crops"), (" ", "Cereal Crops"), ("1", ""), ("1", "   ")],
)
def test_catalogue_options_reject_blank_required_fields(code, display_name):
    values = catalogue_response(
        [{"code": code, "display_name": display_name, "status": "ACTIVE"}]
    )

    with pytest.raises(ValueError, match="non-empty code and display_name"):
        catalogue_options(values)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("catalogue_code", "relation_type", "related_catalogue_code", "related_value_code"),
    [
        ("crop", "category", "crop_category", "1"),
        ("crop_variety", "crop", "crop", "1"),
    ],
)
async def test_widget_resolver_forwards_cascade_relation_filters(
    catalogue_code,
    relation_type,
    related_catalogue_code,
    related_value_code,
):
    class CatalogueServiceStub:
        def __init__(self):
            self.parameters = None

        async def get_values(self, **parameters):
            self.parameters = parameters
            return catalogue_response(
                [{"code": "result", "display_name": "Result", "status": "ACTIVE"}]
            )

    service = CatalogueServiceStub()
    controller = object.__new__(CatalogueController)
    controller.catalogue_service = service

    response = await controller.get_catalogue_options(
        response=Response(),
        catalogue_code=catalogue_code,
        country_code="ETH",
        release_version=None,
        status="ACTIVE",
        parent_code=None,
        relation_type=relation_type,
        related_catalogue_code=related_catalogue_code,
        related_value_code=related_value_code,
        search=None,
        page=1,
        page_size=100,
        if_none_match=None,
    )

    assert service.parameters["catalogue_code"] == catalogue_code
    assert service.parameters["relation_type"] == relation_type
    assert service.parameters["related_catalogue_code"] == related_catalogue_code
    assert service.parameters["related_value_code"] == related_value_code
    assert response.options[0].code == "result"


@pytest.mark.asyncio
async def test_widget_resolver_sets_release_cache_headers():
    class CatalogueServiceStub:
        async def get_values(self, **_parameters):
            return catalogue_response(
                [{"code": "1", "display_name": "Cereal Crops", "status": "ACTIVE"}]
            )

    controller = object.__new__(CatalogueController)
    controller.catalogue_service = CatalogueServiceStub()
    http_response = Response()

    result = await controller.get_catalogue_options(
        response=http_response,
        catalogue_code="crop_category",
        country_code="ETH",
        release_version=None,
        status="ACTIVE",
        parent_code=None,
        relation_type=None,
        related_catalogue_code=None,
        related_value_code=None,
        search=None,
        page=1,
        page_size=100,
        if_none_match=None,
    )

    assert result.options[0].code == "1"
    assert http_response.headers["etag"] == '"abc123"'
    assert http_response.headers["x-catalogue-release"] == "ETH-catalogue-v9"
    assert http_response.headers["cache-control"].startswith("public, max-age=")


@pytest.mark.asyncio
async def test_widget_resolver_returns_not_modified_for_current_release():
    class CatalogueServiceStub:
        async def get_values(self, **_parameters):
            return catalogue_response(
                [{"code": "1", "display_name": "Cereal Crops", "status": "ACTIVE"}]
            )

    controller = object.__new__(CatalogueController)
    controller.catalogue_service = CatalogueServiceStub()

    result = await controller.get_catalogue_options(
        response=Response(),
        catalogue_code="crop_category",
        country_code="ETH",
        release_version=None,
        status="ACTIVE",
        parent_code=None,
        relation_type=None,
        related_catalogue_code=None,
        related_value_code=None,
        search=None,
        page=1,
        page_size=100,
        if_none_match='"abc123"',
    )

    assert result.status_code == 304
    assert result.body == b""
    assert result.headers["etag"] == '"abc123"'
    assert result.headers["x-catalogue-release"] == "ETH-catalogue-v9"
    assert result.headers["cache-control"].startswith("public, max-age=")
