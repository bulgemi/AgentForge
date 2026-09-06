"""REST API Routes aggregation."""

from fastapi import APIRouter

from ._admin_user_routes import router as admin_user_router
from ._auth_routes import router as auth_router
from ._chat_routes import router as chat_router
from ._ldap_routes import router as ldap_router
from ._sso_routes import router as sso_router


def get_all_routers() -> list[APIRouter]:
    """Return all modular routers for application assembly."""
    return [
        auth_router,
        ldap_router,
        sso_router,
        admin_user_router,
        chat_router,
    ]
