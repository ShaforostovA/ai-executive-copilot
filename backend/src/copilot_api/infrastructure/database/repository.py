from datetime import UTC, datetime
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from copilot_api.infrastructure.database.models import (
    AnalysisResult,
    Connection,
    SourceMessage,
)
from copilot_api.schemas.common import DataOrigin, IntegrationState
from copilot_api.schemas.dashboard import (
    AttentionItem,
    Digest,
    IntegrationStatus,
    SourceDetail,
)


class PostgresDashboardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_current_digest(
        self,
        organization_id: UUID,
        owner_id: UUID,
    ) -> Digest:
        analysis_query = (
            select(AnalysisResult, SourceMessage)
            .join(SourceMessage, AnalysisResult.source_message_id == SourceMessage.id)
            .where(
                AnalysisResult.organization_id == organization_id,
                AnalysisResult.owner_id == owner_id,
                SourceMessage.organization_id == organization_id,
                SourceMessage.owner_id == owner_id,
            )
            .order_by(AnalysisResult.score.desc(), AnalysisResult.created_at.desc())
        )
        rows = (await self.session.execute(analysis_query)).all()
        items = [
            AttentionItem(
                item_id=analysis.id,
                tenant_id=analysis.organization_id,
                owner_id=analysis.owner_id,
                source_id=source.id,
                score=analysis.score,
                summary=analysis.summary,
                importance_reason=analysis.importance_reason,
                next_step=analysis.next_step,
                source_timestamp=source.source_timestamp,
                data_origin=DataOrigin(analysis.data_origin),
            )
            for analysis, source in rows
        ]
        integrations = await self.list_integrations(organization_id, owner_id)
        origins = [item.data_origin for item in items]
        origins.extend(integration.data_origin for integration in integrations)
        return Digest(
            digest_id=uuid5(
                UUID("44444444-4444-4444-8444-444444444444"),
                f"{organization_id}:{owner_id}",
            ),
            generated_at=datetime.now(UTC),
            attention_items=items,
            integrations=integrations,
            data_origin=(
                DataOrigin.DEMO
                if origins and all(origin is DataOrigin.DEMO for origin in origins)
                else DataOrigin.LIVE
            ),
        )

    async def list_integrations(
        self,
        organization_id: UUID,
        owner_id: UUID,
    ) -> list[IntegrationStatus]:
        query = (
            select(Connection)
            .where(
                Connection.organization_id == organization_id,
                Connection.owner_id == owner_id,
            )
            .order_by(Connection.provider)
        )
        connections = (await self.session.execute(query)).scalars().all()
        return [
            IntegrationStatus(
                integration_id=connection.id,
                provider=connection.provider,
                status=IntegrationState(connection.status),
                last_sync_at=connection.last_sync_at,
                detail=connection.detail,
                data_origin=DataOrigin(connection.data_origin),
            )
            for connection in connections
        ]

    async def get_source_by_id(
        self,
        source_id: UUID,
        organization_id: UUID,
        owner_id: UUID,
    ) -> SourceDetail | None:
        query = select(SourceMessage).where(
            SourceMessage.id == source_id,
            SourceMessage.organization_id == organization_id,
            SourceMessage.owner_id == owner_id,
        )
        source = (await self.session.execute(query)).scalar_one_or_none()
        return self._to_source_detail(source) if source is not None else None

    async def record_source_message(self, source: SourceDetail) -> SourceDetail:
        statement = (
            insert(SourceMessage)
            .values(
                id=source.source_id,
                organization_id=source.tenant_id,
                owner_id=source.owner_id,
                external_id=source.external_id,
                source_type=source.source_type,
                title=source.title,
                content=source.content,
                source_timestamp=source.source_timestamp,
                source_url=str(source.source_url) if source.source_url else None,
                data_origin=source.data_origin.value,
            )
            .on_conflict_do_nothing(constraint="uq_source_messages_owner_external")
            .returning(SourceMessage.id)
        )
        inserted_id = (await self.session.execute(statement)).scalar_one_or_none()
        if inserted_id is None:
            existing = (
                await self.session.execute(
                    select(SourceMessage).where(
                        SourceMessage.organization_id == source.tenant_id,
                        SourceMessage.owner_id == source.owner_id,
                        SourceMessage.source_type == source.source_type,
                        SourceMessage.external_id == source.external_id,
                    )
                )
            ).scalar_one()
            await self.session.commit()
            return self._to_source_detail(existing)
        await self.session.commit()
        stored = await self.session.get(SourceMessage, inserted_id)
        if stored is None:
            raise RuntimeError("Inserted source message could not be loaded.")
        return self._to_source_detail(stored)

    async def get_analysis_result(
        self,
        source_id: UUID,
        organization_id: UUID,
        owner_id: UUID,
    ) -> AttentionItem | None:
        query = (
            select(AnalysisResult, SourceMessage)
            .join(SourceMessage, AnalysisResult.source_message_id == SourceMessage.id)
            .where(
                AnalysisResult.source_message_id == source_id,
                AnalysisResult.organization_id == organization_id,
                AnalysisResult.owner_id == owner_id,
                SourceMessage.organization_id == organization_id,
                SourceMessage.owner_id == owner_id,
            )
        )
        row = (await self.session.execute(query)).one_or_none()
        if row is None:
            return None
        analysis, source = row
        return self._to_attention_item(analysis, source)

    async def record_analysis_result(
        self,
        analysis: AttentionItem,
        model_name: str,
    ) -> AttentionItem:
        statement = (
            insert(AnalysisResult)
            .values(
                id=analysis.item_id,
                organization_id=analysis.tenant_id,
                owner_id=analysis.owner_id,
                source_message_id=analysis.source_id,
                score=analysis.score,
                summary=analysis.summary,
                importance_reason=analysis.importance_reason,
                next_step=analysis.next_step,
                model=model_name,
                data_origin=analysis.data_origin.value,
            )
            .on_conflict_do_nothing(constraint="uq_analysis_results_source_message_id")
        )
        await self.session.execute(statement)
        await self.session.commit()
        stored = await self.get_analysis_result(
            analysis.source_id,
            analysis.tenant_id,
            analysis.owner_id,
        )
        if stored is None:
            raise RuntimeError("Stored analysis result could not be loaded.")
        return stored

    @staticmethod
    def _to_attention_item(
        analysis: AnalysisResult,
        source: SourceMessage,
    ) -> AttentionItem:
        return AttentionItem(
            item_id=analysis.id,
            tenant_id=analysis.organization_id,
            owner_id=analysis.owner_id,
            source_id=source.id,
            score=analysis.score,
            summary=analysis.summary,
            importance_reason=analysis.importance_reason,
            next_step=analysis.next_step,
            source_timestamp=source.source_timestamp,
            data_origin=DataOrigin(analysis.data_origin),
        )

    @staticmethod
    def _to_source_detail(source: SourceMessage) -> SourceDetail:
        return SourceDetail(
            source_id=source.id,
            tenant_id=source.organization_id,
            owner_id=source.owner_id,
            external_id=source.external_id,
            source_type=source.source_type,
            title=source.title,
            content=source.content,
            source_timestamp=source.source_timestamp,
            source_url=source.source_url,
            data_origin=DataOrigin(source.data_origin),
        )
