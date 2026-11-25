from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadinessChecks(BaseModel):
    application: Literal["ok"] = "ok"
    database: Literal["ok", "disabled", "error"] = "disabled"


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"] = "ready"
    checks: ReadinessChecks = Field(default_factory=ReadinessChecks)
