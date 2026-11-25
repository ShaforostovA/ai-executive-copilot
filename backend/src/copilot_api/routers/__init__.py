from fastapi import APIRouter

from copilot_api.routers.auth import router as auth_router
from copilot_api.routers.dashboard import router as dashboard_router
from copilot_api.routers.workflow import router as workflow_router
from copilot_api.routers.yandex import router as yandex_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(dashboard_router)
api_v1_router.include_router(workflow_router)
api_v1_router.include_router(yandex_router)
