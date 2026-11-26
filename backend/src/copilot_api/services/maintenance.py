from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker

from copilot_api.infrastructure.database.models import AuthSession


async def cleanup_expired_sessions(session_factory: async_sessionmaker) -> int:
    async with session_factory() as session:
        result = await session.execute(
            delete(AuthSession).where(AuthSession.expires_at <= datetime.now(UTC))
        )
        await session.commit()
        return int(result.rowcount or 0)
