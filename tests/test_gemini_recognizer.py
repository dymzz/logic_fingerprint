from __future__ import annotations

from logicfp.domain.ai_error_recognizer import recognize_ai_error


class FakeGeminiAPIError(Exception):
    def __init__(self, message, *, code=None):
        super().__init__(message)
        self.code = code
        self.status_code = code


FakeGeminiAPIError.__module__ = "google.genai.errors"


class FakeGeminiModelNotFound(Exception):
    def __init__(self):
        super().__init__("models/gemini-missing is not found for API version v1beta")
        self.status_code = 404
        self.code = 404
        self.model = "gemini-missing"


FakeGeminiModelNotFound.__module__ = "google.genai.errors"


class FakeGeminiRateLimitToken(Exception):
    def __init__(self):
        super().__init__("Resource exhausted: token throughput limit exceeded")
        self.status_code = 429


FakeGeminiRateLimitToken.__module__ = "google.genai.errors"
FakeGeminiRateLimitToken.__name__ = "ResourceExhausted"


class FakeGeminiRateLimitRequest(Exception):
    def __init__(self):
        super().__init__("Resource exhausted: too many requests")
        self.status_code = 429


FakeGeminiRateLimitRequest.__module__ = "google.genai.errors"
FakeGeminiRateLimitRequest.__name__ = "ResourceExhausted"


class FakeGeminiAuthError(Exception):
    def __init__(self):
        super().__init__("API key not valid. Please pass a valid API key.")
        self.status_code = 401


FakeGeminiAuthError.__module__ = "google.genai.errors"


class FakeGeminiForbiddenError(Exception):
    def __init__(self):
        super().__init__("Permission denied for this project")
        self.status_code = 403


FakeGeminiForbiddenError.__module__ = "google.genai.errors"


class FakeGeminiQuotaError(Exception):
    def __init__(self):
        super().__init__("Quota exceeded for this project")
        self.status_code = 429


FakeGeminiQuotaError.__module__ = "google.genai.errors"


class FakeGeminiSafetyError(Exception):
    def __init__(self):
        super().__init__("Response blocked due to safety settings")
        self.status_code = 400


FakeGeminiSafetyError.__module__ = "google.genai.errors"


class FakeGeminiOverloaded(Exception):
    def __init__(self):
        super().__init__("Service temporarily unavailable")
        self.status_code = 503


FakeGeminiOverloaded.__module__ = "google.genai.errors"


class FakeGemini5xx(Exception):
    def __init__(self):
        super().__init__("Internal server error")
        self.status_code = 500


FakeGemini5xx.__module__ = "google.genai.errors"


class FakeGeminiContextTooLong(Exception):
    def __init__(self):
        super().__init__("Request payload size exceeds the limit: too many tokens")
        self.status_code = 400


FakeGeminiContextTooLong.__module__ = "google.genai.errors"


def test_recognize_gemini_model_not_found():
    r = recognize_ai_error(FakeGeminiModelNotFound())
    assert r is not None
    assert r.code == "MODEL_NOT_FOUND"
    assert r.provider == "google"


def test_recognize_gemini_token_rate_limit():
    r = recognize_ai_error(FakeGeminiRateLimitToken())
    assert r is not None
    assert r.code == "RATE_LIMIT_TOKEN"
    assert r.provider == "google"
    assert r.retryable is True


def test_recognize_gemini_request_rate_limit():
    r = recognize_ai_error(FakeGeminiRateLimitRequest())
    assert r is not None
    assert r.code == "RATE_LIMIT_REQUEST"
    assert r.provider == "google"
    assert r.retryable is True


def test_recognize_gemini_auth_invalid():
    r = recognize_ai_error(FakeGeminiAuthError())
    assert r is not None
    assert r.code == "AUTH_INVALID"
    assert r.provider == "google"
    assert r.retryable is False


def test_recognize_gemini_auth_forbidden():
    r = recognize_ai_error(FakeGeminiForbiddenError())
    assert r is not None
    assert r.code == "AUTH_FORBIDDEN"
    assert r.provider == "google"
    assert r.retryable is False


def test_recognize_gemini_quota_exhausted():
    r = recognize_ai_error(FakeGeminiQuotaError())
    assert r is not None
    assert r.code == "QUOTA_EXHAUSTED"
    assert r.provider == "google"
    assert r.retryable is False


def test_recognize_gemini_safety_blocked():
    r = recognize_ai_error(FakeGeminiSafetyError())
    assert r is not None
    assert r.code == "SAFETY_REFUSAL"
    assert r.provider == "google"


def test_recognize_gemini_overloaded():
    r = recognize_ai_error(FakeGeminiOverloaded())
    assert r is not None
    assert r.code == "UPSTREAM_OVERLOADED"
    assert r.provider == "google"
    assert r.retryable is True


def test_recognize_gemini_5xx():
    r = recognize_ai_error(FakeGemini5xx())
    assert r is not None
    assert r.code == "UPSTREAM_5XX"
    assert r.provider == "google"
    assert r.retryable is True


def test_recognize_gemini_context_too_long():
    r = recognize_ai_error(FakeGeminiContextTooLong())
    assert r is not None
    assert r.code == "CONTEXT_TOO_LONG"
    assert r.provider == "google"
    assert r.retryable is False
