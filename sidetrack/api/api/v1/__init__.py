from fastapi import APIRouter

from ...routers import cohorts, daypart, insights, moods, similar
from . import auth, dashboard, listens, musicbrainz, spotify

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(listens.router)
router.include_router(musicbrainz.router)
router.include_router(dashboard.router)
router.include_router(spotify.router)
router.include_router(insights.router)
router.include_router(moods.router)
router.include_router(similar.router)
router.include_router(daypart.router)
router.include_router(cohorts.router)
