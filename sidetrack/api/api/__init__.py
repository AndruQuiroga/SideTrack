from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from .v1 import router as v1_router
from .v1 import auth as auth_v1

router = APIRouter()
router.include_router(v1_router)
router.include_router(auth_v1.router)


@router.get("/", include_in_schema=False)
async def redirect_to_latest() -> RedirectResponse:
    """Redirect root requests to the latest API version."""
    return RedirectResponse(url="/api/v1")
