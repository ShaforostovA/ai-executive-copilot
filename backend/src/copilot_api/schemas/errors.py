from pydantic import BaseModel


class ValidationIssue(BaseModel):
    field: str
    message: str
    type: str


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    details: list[ValidationIssue] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
