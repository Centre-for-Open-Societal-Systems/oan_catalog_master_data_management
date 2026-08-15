# OpenG2P Catalogue Client

Async Python client for registry services consuming an immutable Catalogue
Service snapshot. It supports OAuth client credentials, conditional ETag
polling, bounded transient-error retries, and typed response validation.

See [`../docs/registry-integration.md`](../docs/registry-integration.md) for a
complete synchronization example.

Registry services can also fetch one typed crop variety, including its crop
type, category, source rows, agronomic ranges, and source characteristics:

```python
result = await client.fetch_crop_variety_detail("maize-melkassa-1-q")
if result.changed:
    variety = result.detail.variety
    print(variety.crop_type.display_name, variety.category.display_name)
```

Pass `release_version` to pin the lookup to an immutable release, or pass a
previous `etag` to receive an inexpensive `304 Not Modified` result.

Registry services can discover and inspect Ethio-Seed varieties through the
same typed client:

```python
page = await client.fetch_seed_varieties(
    crop_type_code="maize",
    match_status="MATCHED",
    page_size=100,
)
for variety in page.listing.varieties:
    print(variety.code, variety.seed_crop.display_name)

detail = await client.fetch_seed_variety_detail("ethioseed-20")
print(detail.detail.variety.details_url)
```

The list method supports every server-side seed-variety filter plus pagination,
release pinning, and conditional ETags. Unresolved listings validate normally
with null crop-variety, crop-type, and category references.

Livestock registries can consume species, filtered breeds, and the supporting
reference sets without interpreting generic catalogue metadata:

```python
species = await client.fetch_livestock_species()
breeds = await client.fetch_livestock_breeds(
    species_code="cattle",
    breed_type="Indigenous",
    in_national_standard=True,
)
reference_data = await client.fetch_livestock_reference_data()
registry = await client.fetch_livestock_registry_entries(species_code="cattle")
issues = await client.fetch_livestock_registry_validation(has_issues=True)

for breed in breeds.listing.breeds:
    print(breed.code, breed.display_name, breed.species.display_name)
```

All five methods support immutable release pinning and conditional ETags.
Species and breed reads are paginated; breed reads also support national
standard and ET-LITS membership filters.
