#!/usr/bin/env python3

from openg2p_catalogue_service.config import Settings

Settings.get_config()

from iam_core.user_auth.app import Initializer as IAMInitializer
from iam_core.user_auth.config import Settings as IAMAuthSettings
from iam_core.user_auth.middleware import ValidateAndRefreshTokenMiddleware
from openg2p_fastapi_common.ping import PingInitializer

from openg2p_catalogue_service.app import Initializer
from openg2p_catalogue_service.observability import ObservabilityMiddleware
from openg2p_catalogue_service.security import CataloguePermissionMiddleware

IAMInitializer()
initializer = Initializer()
PingInitializer()

app = initializer.return_app()
iam_config = IAMAuthSettings.get_config()
app.add_middleware(
    CataloguePermissionMiddleware,
    client_id=iam_config.keycloak_client_id,
)
app.add_middleware(ValidateAndRefreshTokenMiddleware)
# Added last so authentication failures and all application responses are also
# represented in request metrics and correlated logs.
app.add_middleware(ObservabilityMiddleware)

if __name__ == "__main__":
    initializer.main()
