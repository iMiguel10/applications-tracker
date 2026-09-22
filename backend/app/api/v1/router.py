from fastapi import APIRouter

from app.api.v1.endpoints import applications, health

router = APIRouter()

router.include_router(health.router)
router.include_router(applications.router)
