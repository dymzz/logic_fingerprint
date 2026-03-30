from logicfp.domain.errors import (
    ErrorCode,
    LogicExecutionError,
    NormalizationError,
    classify_exception,
)


def test_classify_exception_maps_user_mode_normalization_error():
    assert classify_exception(NormalizationError("bad input")) == ErrorCode.ERR_NORM


def test_classify_exception_maps_user_mode_logic_error():
    assert classify_exception(LogicExecutionError("manual review")) == ErrorCode.ERR_LOGIC


def test_classify_exception_maps_builtin_normalization_style_errors():
    assert classify_exception(ValueError("bad value")) == ErrorCode.ERR_NORM
    assert classify_exception(TypeError("bad type")) == ErrorCode.ERR_NORM
    assert classify_exception(KeyError("missing")) == ErrorCode.ERR_NORM


def test_classify_exception_maps_builtin_logic_style_errors():
    assert classify_exception(RuntimeError("bad state")) == ErrorCode.ERR_LOGIC
    assert classify_exception(AssertionError("assertion failed")) == ErrorCode.ERR_LOGIC
