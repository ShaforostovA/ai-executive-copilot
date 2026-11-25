import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from copilot_api.core.security import (
    generate_session_token,
    hash_session_token,
    verify_password,
)
from copilot_api.infrastructure.database.models import AuthSession, Organization, User
from copilot_api.schemas.auth import AuthenticatedSession, Principal


class AuthService:
    def __init__(self, session: AsyncSession, session_ttl_minutes: int) -> None:
        self.session = session
        self.session_ttl = timedelta(minutes=session_ttl_minutes)

    async def login(
        self,
        organization_slug: str,
        email: str,
        password: str,
    ) -> AuthenticatedSession | None:
        query = (
            select(User, Organization)
            .join(Organization, User.organization_id == Organization.id)
            .where(
                Organization.slug == organization_slug.strip().lower(),
                User.email == email.strip().lower(),
                User.is_active.is_(True),
            )
        )
        row = (await self.session.execute(query)).one_or_none()
        if row is None:
            return None
        user, organization = row
        password_valid = await asyncio.to_thread(
            verify_password,
            password,
            user.password_hash,
        )
        if not password_valid:
            return None
        token = generate_session_token()
        now = datetime.now(UTC)
        expires_at = now + self.session_ttl
        self.session.add(
            AuthSession(
                user_id=user.id,
                token_hash=hash_session_token(token),
                created_at=now,
                expires_at=expires_at,
                last_seen_at=now,
            )
        )
        await self.session.commit()
        return AuthenticatedSession(
            principal=self._principal(user, organization),
            token=token,
            expires_at=expires_at,
        )

    async def get_principal(self, token: str) -> Principal | None:
        now = datetime.now(UTC)
        query = (
            select(User, Organization, AuthSession)
            .join(Organization, User.organization_id == Organization.id)
            .join(AuthSession, AuthSession.user_id == User.id)
            .where(
                AuthSession.token_hash == hash_session_token(token),
                AuthSession.expires_at > now,
                User.is_active.is_(True),
            )
        )
        row = (await self.session.execute(query)).one_or_none()
        if row is None:
            return None
        user, organization, _ = row
        return self._principal(user, organization)

    async def logout(self, token: str) -> None:
        query = select(AuthSession).where(AuthSession.token_hash == hash_session_token(token))
        auth_session = (await self.session.execute(query)).scalar_one_or_none()
        if auth_session is not None:
            await self.session.delete(auth_session)
            await self.session.commit()

    @staticmethod
    def _principal(user: User, organization: Organization) -> Principal:
        return Principal(
            user_id=user.id,
            organization_id=organization.id,
            organization_slug=organization.slug,
            email=user.email,
        )
