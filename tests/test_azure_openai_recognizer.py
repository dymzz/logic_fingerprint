from __future__ import annotations

from logicfp.domain.ai_error_recognizer import recognize_ai_error


class FakeAzureOpenAIContentFilter(Exception):
    def __init__(self):
        super().__init__("Azure OpenAI content_filter triggered by ResponsibleAIPolicy")
        self.status_code = 400
        self.code = "content_filter"


FakeAzureOpenAIContentFilter.__module__ = "openai"


class FakeAzureOpenAIDeploymentNotFound(Exception):
    def __init__(self):
        super().__init__("Azure deployment not found: gpt-4o-mini-eastus")
        self.status_code = 404
        self.model = "gpt-4o-mini-eastus"


FakeAzureOpenAIDeploymentNotFound.__module__ = "openai"


class FakeAzureOpenAITokenRateLimit(Exception):
    def __init__(self):
        super().__init__("Azure rate limit: tokens per minute exceeded for deployment")
        self.status_code = 429


FakeAzureOpenAITokenRateLimit.__module__ = "openai"


class FakeAzureOpenAIRequestRateLimit(Exception):
    def __init__(self):
        super().__init__("Azure rate limit: requests per minute exceeded. Retry after 10 seconds.")
        self.status_code = 429


FakeAzureOpenAIRequestRateLimit.__module__ = "openai"


class FakeAzureOpenAIAuthError(Exception):
    def __init__(self):
        super().__init__("Azure access denied: invalid api key")
        self.status_code = 401


FakeAzureOpenAIAuthError.__module__ = "openai"


class FakeAzureOpenAIOverloaded(Exception):
    def __init__(self):
        super().__init__("Azure server busy, temporarily unavailable")
        self.status_code = 503


FakeAzureOpenAIOverloaded.__module__ = "openai"


class FakeAzureOpenAI5xx(Exception):
    def __init__(self):
        super().__init__("Azure internal server error")
        self.status_code = 500


FakeAzureOpenAI5xx.__module__ = "openai"


class FakeAzureOpenAIContextTooLong(Exception):
    def __init__(self):
        super().__init__("Azure context length exceeded: too many tokens for this deployment")
        self.status_code = 400


FakeAzureOpenAIContextTooLong.__module__ = "openai"


def test_recognize_azure_content_filter():
    r = recognize_ai_error(FakeAzureOpenAIContentFilter())
    assert r is not None
    assert r.code == "SAFETY_REFUSAL"
    assert r.provider == "azure-openai"


def test_recognize_azure_deployment_not_found():
    r = recognize_ai_error(FakeAzureOpenAIDeploymentNotFound())
    assert r is not None
    assert r.code == "MODEL_NOT_FOUND"
    assert r.provider == "azure-openai"


def test_recognize_azure_token_rate_limit():
    r = recognize_ai_error(FakeAzureOpenAITokenRateLimit())
    assert r is not None
    assert r.code == "RATE_LIMIT_TOKEN"
    assert r.provider == "azure-openai"
    assert r.retryable is True


def test_recognize_azure_request_rate_limit():
    r = recognize_ai_error(FakeAzureOpenAIRequestRateLimit())
    assert r is not None
    assert r.code == "RATE_LIMIT_REQUEST"
    assert r.provider == "azure-openai"
    assert r.retryable is True


def test_recognize_azure_auth_error():
    r = recognize_ai_error(FakeAzureOpenAIAuthError())
    assert r is not None
    assert r.code == "AUTH_INVALID"
    assert r.provider == "azure-openai"
    assert r.retryable is False


def test_recognize_azure_overloaded():
    r = recognize_ai_error(FakeAzureOpenAIOverloaded())
    assert r is not None
    assert r.code == "UPSTREAM_OVERLOADED"
    assert r.provider == "azure-openai"
    assert r.retryable is True


def test_recognize_azure_5xx():
    r = recognize_ai_error(FakeAzureOpenAI5xx())
    assert r is not None
    assert r.code == "UPSTREAM_5XX"
    assert r.provider == "azure-openai"
    assert r.retryable is True


def test_recognize_azure_context_too_long():
    r = recognize_ai_error(FakeAzureOpenAIContextTooLong())
    assert r is not None
    assert r.code == "CONTEXT_TOO_LONG"
    assert r.provider == "azure-openai"
    assert r.retryable is False
