from fastapi import APIRouter

from copilot_api.routers.dashboard import router as dashboard_router

api_v1_router = APIRouter()
api_v1_router.include_router(dashboard_router)
