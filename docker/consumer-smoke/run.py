"""Exercise the packaged registry client against the Docker Catalogue API."""

import asyncio
import os

from openg2p_catalogue_client import CatalogueClient, CatalogueClientConfig


async def main():
    config = CatalogueClientConfig(
        base_url=os.getenv("CATALOGUE_SERVICE_URL", "http://api:8000"),
        token_url=os.getenv("IAM_TOKEN_URL", "http://mock-iam:8080/token"),
        client_id="consumer-smoke",
        client_secret="consumer-smoke-secret",
        country_code=os.getenv("CATALOGUE_COUNTRY_CODE", "ETH"),
    )
    async with CatalogueClient(config) as client:
        crop_detail = await client.fetch_crop_variety_detail("maize-melkassa-1-q")
        assert crop_detail.changed and crop_detail.detail is not None
        crop_variety = crop_detail.detail.variety
        assert crop_variety.crop_type.code == "maize"
        assert crop_variety.category.code == "cereal"
        assert {row.release_year for row in crop_variety.source_records} == {
            2001,
            2013,
        }

        matched = await client.fetch_seed_varieties(
            crop_type_code="maize",
            match_status="MATCHED",
            page_size=5,
        )
        assert matched.changed and matched.listing is not None
        assert matched.listing.total > 0
        seed_variety = matched.listing.varieties[0]
        assert seed_variety.match_status == "MATCHED"
        assert seed_variety.seed_crop is not None
        assert seed_variety.matched_crop_variety is not None
        assert seed_variety.crop_type is not None
        assert seed_variety.crop_type.code == "maize"
        assert seed_variety.category is not None

        seed_detail = await client.fetch_seed_variety_detail(seed_variety.code)
        assert seed_detail.changed and seed_detail.detail is not None
        assert seed_detail.detail.variety == seed_variety

        unresolved = await client.fetch_seed_varieties(
            match_status="UNRESOLVED",
            page_size=1,
        )
        assert unresolved.changed and unresolved.listing is not None
        assert unresolved.listing.total == 593
        unresolved_variety = unresolved.listing.varieties[0]
        assert unresolved_variety.seed_crop is not None
        assert unresolved_variety.matched_crop_variety is None
        assert unresolved_variety.crop_type is None
        assert unresolved_variety.category is None

        unchanged = await client.fetch_crop_variety_detail(
            crop_variety.code,
            etag=crop_detail.etag,
            release_version=crop_detail.detail.release.version,
        )
        assert not unchanged.changed and unchanged.detail is None

        unchanged_seed = await client.fetch_seed_variety_detail(
            seed_variety.code,
            etag=seed_detail.etag,
            release_version=seed_detail.detail.release.version,
        )
        assert not unchanged_seed.changed and unchanged_seed.detail is None

        species = await client.fetch_livestock_species()
        assert species.changed and species.listing is not None
        assert species.listing.total == 5

        cattle_breeds = await client.fetch_livestock_breeds(
            species_code="cattle",
            breed_type="Indigenous",
        )
        assert cattle_breeds.changed and cattle_breeds.listing is not None
        assert cattle_breeds.listing.total == 25
        assert all(breed.species.code == "cattle" for breed in cattle_breeds.listing.breeds)

        livestock_reference = await client.fetch_livestock_reference_data()
        assert livestock_reference.changed and livestock_reference.reference_data is not None
        assert len(livestock_reference.reference_data.genders) == 4
        assert len(livestock_reference.reference_data.production_types) == 13

    print(
        "consumer smoke passed: "
        f"release={crop_detail.detail.release.version} "
        f"crop_variety={crop_variety.code} "
        f"source_records={len(crop_variety.source_records)} "
        f"seed_variety={seed_variety.code} "
        f"matched_maize={matched.listing.total} "
        f"unresolved={unresolved.listing.total}"
        f" livestock_species={species.listing.total}"
        f" indigenous_cattle_breeds={cattle_breeds.listing.total}"
    )


if __name__ == "__main__":
    asyncio.run(main())
