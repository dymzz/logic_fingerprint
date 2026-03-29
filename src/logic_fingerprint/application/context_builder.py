from datetime import datetime, timezone
from uuid import uuid4
from ..domain.models import HandlerRequest, RequestContext

class ContextBuilder:
    def __init__(self, default_source: str = "api") -> None:
        self.default_source = default_source
    def build_context(self, context: RequestContext | None = None) -> RequestContext:
        context = context or RequestContext()
        return RequestContext(
            request_id=context.request_id or f"req-{uuid4().hex}",
            trace_id=context.trace_id or f"trace-{uuid4().hex}",
            user_id=context.user_id,
            source=context.source or self.default_source,
            timestamp=context.timestamp or datetime.now(timezone.utc).isoformat(),
            headers=dict(context.headers),
            metadata=dict(context.metadata),
        )
    def build_request(self, request: HandlerRequest | None = None) -> HandlerRequest:
        request = request or HandlerRequest()
        return HandlerRequest(payload=dict(request.payload), context=self.build_context(request.context))

