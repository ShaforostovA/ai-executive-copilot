from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr


class LoginRequest(BaseModel):
    organization_slug: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=320)
    password: SecretStr


class Principal(BaseModel):
    user_id: UUID
    organization_id: UUID
    organization_slug: str
    email: str


class AuthenticatedSession(BaseModel):
    principal: Principal
    token: str
    expires_at: datetime
