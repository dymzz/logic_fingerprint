from logic_fingerprint.core.context_builder import ContextBuilder
from logic_fingerprint.core.models import HandlerRequest, RequestContext

def test_context_builder_autofills_missing_fields():
    builder = ContextBuilder(default_source="api")
    built = builder.build_request(HandlerRequest(payload={"x": 1}))
    assert built.context.request_id is not None
    assert built.context.trace_id is not None
    assert built.context.timestamp is not None
    assert built.context.source == "api"

def test_context_builder_preserves_explicit_fields():
    builder = ContextBuilder(default_source="api")
    built = builder.build_request(HandlerRequest(payload={"x": 1}, context=RequestContext(request_id="r-1", trace_id="t-1", source="worker")))
    assert built.context.request_id == "r-1"
    assert built.context.trace_id == "t-1"
    assert built.context.source == "worker"
