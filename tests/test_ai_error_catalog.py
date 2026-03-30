from logicfp.domain.ai_error_catalog import (
    AI_ERROR_CATALOG,
    AIErrorCategory,
    AIErrorPhase,
    AIErrorSeverity,
    FIRST_WAVE_AI_ERROR_CODES,
    get_ai_error_descriptor,
)


def test_first_wave_codes_exist_in_catalog() -> None:
    for code in FIRST_WAVE_AI_ERROR_CODES:
        assert code in AI_ERROR_CATALOG


def test_rate_limit_token_descriptor_shape() -> None:
    descriptor = get_ai_error_descriptor("RATE_LIMIT_TOKEN")

    assert descriptor is not None
    assert descriptor.category is AIErrorCategory.RATE_LIMIT
    assert descriptor.retryable is True
    assert descriptor.severity is AIErrorSeverity.WARN
    assert descriptor.phase is AIErrorPhase.REQUEST
    assert "token_rate_limit" in descriptor.recognition_signals


def test_stream_broken_descriptor_shape() -> None:
    descriptor = get_ai_error_descriptor("STREAM_BROKEN")

    assert descriptor is not None
    assert descriptor.category is AIErrorCategory.STREAM
    assert descriptor.retryable is True
    assert descriptor.phase is AIErrorPhase.STREAM
    assert "connection_lost_mid_stream" in descriptor.recognition_signals


def test_unknown_descriptor_is_defined() -> None:
    descriptor = get_ai_error_descriptor("UNKNOWN")

    assert descriptor is not None
    assert descriptor.category is AIErrorCategory.UNKNOWN
    assert descriptor.retryable is None
    assert descriptor.severity is AIErrorSeverity.WARN
