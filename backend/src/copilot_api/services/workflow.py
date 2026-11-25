from copilot_api.infrastructure.database.repository import PostgresDashboardRepository
from copilot_api.schemas.auth import Principal
from copilot_api.schemas.common import DataOrigin
from copilot_api.schemas.dashboard import SourceDetail
from copilot_api.schemas.workflow import (
    AnalysisWorkflowResponse,
    SyntheticAnalysisRequest,
)
from copilot_api.services.interfaces import AnalysisProvider


class AnalysisWorkflowError(Exception):
    pass


class AnalysisWorkflowService:
    def __init__(
        self,
        repository: PostgresDashboardRepository,
        provider: AnalysisProvider,
        model_name: str,
    ) -> None:
        self.repository = repository
        self.provider = provider
        self.model_name = model_name

    async def run(
        self,
        payload: SyntheticAnalysisRequest,
        principal: Principal,
    ) -> AnalysisWorkflowResponse:
        source = SourceDetail(
            **payload.model_dump(),
            tenant_id=principal.organization_id,
            owner_id=principal.user_id,
            data_origin=DataOrigin.DEMO,
        )
        stored_source = await self.repository.record_source_message(source)
        existing = await self.repository.get_analysis_result(
            stored_source.source_id,
            principal.organization_id,
            principal.user_id,
        )
        if existing is not None:
            return AnalysisWorkflowResponse(
                source=stored_source,
                analysis=existing,
                idempotent_replay=True,
            )
        analysis = await self.provider.analyze(stored_source)
        if analysis.data_origin is not DataOrigin.LIVE:
            raise AnalysisWorkflowError("Analysis provider returned a non-live result.")
        analysis = analysis.model_copy(
            update={
                "tenant_id": principal.organization_id,
                "owner_id": principal.user_id,
                "source_id": stored_source.source_id,
            }
        )
        stored_analysis = await self.repository.record_analysis_result(
            analysis,
            self.model_name,
        )
        return AnalysisWorkflowResponse(
            source=stored_source,
            analysis=stored_analysis,
            idempotent_replay=stored_analysis.item_id != analysis.item_id,
        )
