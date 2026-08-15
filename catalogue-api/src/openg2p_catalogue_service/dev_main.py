"""Local-only application entry point without external IAM dependencies."""

import os

if os.environ.get("CATALOGUE_API_DEV_MODE", "").lower() != "true":
    raise RuntimeError(
        "The unauthenticated development app requires CATALOGUE_API_DEV_MODE=true. "
        "Use openg2p_catalogue_service.main for every shared environment."
    )

from openg2p_catalogue_service.config import Settings

Settings.get_config()

from openg2p_fastapi_common.ping import PingInitializer

from openg2p_catalogue_service.app import Initializer
from openg2p_catalogue_service.observability import ObservabilityMiddleware

initializer = Initializer()
PingInitializer()
app = initializer.return_app()
app.add_middleware(ObservabilityMiddleware)

if __name__ == "__main__":
    initializer.main()
