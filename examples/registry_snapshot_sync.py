"""Minimal registry-side scheduled synchronization entry point."""

import asyncio
import os

from openg2p_catalogue_client import CatalogueClient, CatalogueClientConfig, SyncState


async def replace_registry_catalogues(snapshot):
    """Validate and atomically replace registry-local data in one transaction."""
    # async with registry_database.transaction():
    #     await registry_repository.stage(snapshot)
    #     await registry_repository.validate(snapshot.release)
    #     await registry_repository.activate(snapshot.release.version)
    print(f"Apply release {snapshot.release.version} in the registry transaction")


async def main():
    config = CatalogueClientConfig(
        base_url=os.environ["CATALOGUE_SERVICE_URL"],
        token_url=os.environ["IAM_TOKEN_URL"],
        client_id=os.environ["CATALOGUE_CLIENT_ID"],
        client_secret=os.environ["CATALOGUE_CLIENT_SECRET"],
        country_code=os.getenv("CATALOGUE_COUNTRY_CODE", "ETH"),
        scope=os.getenv("CATALOGUE_CLIENT_SCOPE"),
    )

    # Load this state from the registry database in a real implementation.
    state = SyncState(country_code=config.country_code)
    async with CatalogueClient(config) as client:
        result = await client.sync_snapshot(state, replace_registry_catalogues)

    # Persist result.state only after sync_snapshot returns. The apply callback
    # has completed successfully at that point.
    print(f"changed={result.changed}, release={result.state.release_version}")


if __name__ == "__main__":
    asyncio.run(main())
