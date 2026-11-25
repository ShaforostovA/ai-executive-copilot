from pydantic import BaseModel, ConfigDict, Field, SecretStr


class OAuthTokenResponse(BaseModel):
    access_token: SecretStr
    expires_at: int = Field(gt=0)


class GigaChatAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(ge=0, le=100)
    summary: str = Field(min_length=1)
    importance_reason: str = Field(min_length=1)
    next_step: str = Field(min_length=1)


class CompletionMessage(BaseModel):
    content: str


class CompletionChoice(BaseModel):
    message: CompletionMessage


class CompletionResponse(BaseModel):
    choices: list[CompletionChoice] = Field(min_length=1)
