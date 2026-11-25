from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from copilot_api.schemas.common import DataOrigin
from copilot_api.schemas.dashboard import AttentionItem


def attention_item_payload() -> dict[str, object]:
    return {
        "item_id": UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
        "tenant_id": UUID("11111111-1111-4111-8111-111111111111"),
        "owner_id": UUID("22222222-2222-4222-8222-222222222222"),
        "source_id": UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        "score": 50,
        "summary": "Synthetic summary",
        "importance_reason": "Synthetic importance reason",
        "next_step": "Synthetic next step",
        "source_timestamp": datetime(2026, 11, 25, 12, 0, tzinfo=UTC),
        "data_origin": DataOrigin.DEMO,
    }


@pytest.mark.parametrize("score", [-1, 101])
def test_attention_item_rejects_out_of_range_score(score: int) -> None:
    with pytest.raises(ValidationError):
        AttentionItem.model_validate({**attention_item_payload(), "score": score})


def test_attention_item_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError):
        AttentionItem.model_validate(
            {
                **attention_item_payload(),
                "source_timestamp": datetime(2026, 11, 25, 12, 0),
            }
        )
