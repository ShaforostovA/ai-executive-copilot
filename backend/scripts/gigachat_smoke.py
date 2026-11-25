import asyncio
import sys
from datetime import UTC, datetime
from uuid import uuid4

from copilot_api.core.config import Settings
from copilot_api.infrastructure.gigachat import GigaChatError, GigaChatProvider
from copilot_api.schemas.common import DataOrigin
from copilot_api.schemas.dashboard import SourceDetail


async def run_smoke() -> None:
    settings = Settings()
    source = SourceDetail(
        source_id=uuid4(),
        tenant_id=uuid4(),
        owner_id=uuid4(),
        external_id="synthetic-smoke-001",
        source_type="synthetic",
        title="Synthetic smoke: budget approval",
        content=(
            "Synthetic test message only. Review the demo budget proposal "
            "and prepare a recommendation by Friday."
        ),
        source_timestamp=datetime.now(UTC),
        source_url=None,
        data_origin=DataOrigin.DEMO,
    )
    try:
        async with GigaChatProvider(settings) as provider:
            result = await provider.analyze(source)
    except GigaChatError as exc:
        print(f"GigaChat smoke failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(run_smoke())
