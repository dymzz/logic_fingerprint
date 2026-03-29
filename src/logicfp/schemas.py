from pydantic import BaseModel, Field
class ForceFailRequest(BaseModel):
    reason: str = "MANUAL_FAIL"
class ExecuteHandlerContextModel(BaseModel):
    request_id: str | None = None
    trace_id: str | None = None
    user_id: str | None = None
    source: str | None = None
    timestamp: str | None = None
    headers: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
class ExecuteHandlerRequest(BaseModel):
    handler: str
    payload: dict = Field(default_factory=dict)
    context: ExecuteHandlerContextModel = Field(default_factory=ExecuteHandlerContextModel)
    now: float | None = None
