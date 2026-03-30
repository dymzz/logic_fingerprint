# User Mode Error Codes

This page explains the most common error codes in user mode — the values that `ProtectRuntimeError.code` can take when `@protect()` or `create_protector()` calls fail.

For explicit error code checking in your code, use:

```python
from logicfp.user_mode import (
    ErrorCode,
    LogicExecutionError,
    NormalizationError,
    ProtectRuntimeError,
    get_error_action,
    get_error_fact,
)
```

## 1. Recommended Pattern

```python
from logicfp import protect
from logicfp.user_mode import ErrorCode, ProtectRuntimeError


@protect(simple=True)
def run_task(request):
    raise ValueError("manual review required")


try:
    run_task(payload={"task_id": "T-1001"})
except ProtectRuntimeError as exc:
    if exc.code == ErrorCode.ERR_NORM.value:
        print("normalization-style failure")
```

## 2. Common Error Codes

### `ERR_VALIDATION`

Input data does not match `input_model`.

Common sources:

- Pydantic input validation failure
- Missing required fields
- Incorrect field types

Typical behavior:

- `ProtectRuntimeError.details["errors"]` contains validation details

### `ERR_OUTPUT_VALIDATION`

Function executed successfully but the return value does not match `output_model`.

Common sources:

- Missing return fields
- Incorrect return field types
- Return structure does not match the declared output model

Typical behavior:

- `ProtectRuntimeError.details["errors"]` contains validation details

### `ERR_NULL`

Function returned `None`.

This usually means:

- Your function has no explicit `return`
- A branch is missing a return value
- Logic should have returned an object but returned empty

### `ERR_NORM`

In the current version, these Python exceptions map to `ERR_NORM`:

- `ValueError`
- `TypeError`
- `KeyError`

Suitable for:

- Manually raising "invalid parameter"
- Business pre-check failures
- Cases requiring human review or input correction

For stable expression of "normalization/input correction" failures, raise:

```python
from logicfp.user_mode import NormalizationError
```

### `ERR_LOGIC`

In the current version, these exceptions map to `ERR_LOGIC`:

- `LogicExecutionError`
- `RuntimeError`
- `AssertionError`

Recommended approach — raise explicitly:

```python
from logicfp.user_mode import LogicExecutionError
```

Suitable for:

- Business rules reject execution
- Requires manual review
- Current state does not allow continued processing

### `ERR_EXECUTION_BLOCKED`

The request was blocked by the current protection state and the business function was never executed.

Common scenarios:

- A hard failure occurred previously
- The state machine is still in a blocked state
- The current request is not an allowed probe request

### `ERR_UNKNOWN`

An exception not recognized by any more specific rule.

Common sources:

- Unclassified Python exceptions
- Exceptions raised directly by third-party libraries
- Error types not yet categorized in the current version

If your code frequently produces `ERR_UNKNOWN`, it usually means you should explicitly classify those exceptions.

## 3. Other Error Codes

These error codes are mostly used in the internal execution chain:

- `ERR_TIMEOUT`
- `ERR_LOGIC`
- `ERR_HANDLER_NOT_FOUND`

They can still appear in user mode, but the ones listed above are the most common for typical function protection.

## 4. Where Error Codes Come From

Error codes originate from 4 layers:

1. **Input/output validation** — `ERR_VALIDATION` / `ERR_OUTPUT_VALIDATION`
2. **Executor guards** — `ERR_NULL` / `ERR_EXECUTION_BLOCKED`
3. **Exception classifier** — e.g. `ValueError/TypeError/KeyError -> ERR_NORM`, `RuntimeError/AssertionError -> ERR_LOGIC`
4. **Unclassified exceptions** — fall through to `ERR_UNKNOWN`

## 5. Stability Advice

In user mode, the most reliable approach is:

- Check `exc.code` first
- Then check `exc.details`
- Use `exc.context` to correlate with the request context

For long-term stable error branching, depend only on:

- `ErrorCode`
- `ProtectRuntimeError.code`
- `ProtectRuntimeError.details`
- `ProtectRuntimeError.context`

## 6. The 4 Core Questions in Failure Structure

With `simple=False`, the current version normalizes failures into two layers:

- `error.details["error_fact"]`
- `error.details["error_policy"]`

The most useful fields:

- **`error_fact.stage`** — `input` / `execute` / `dependency` / `output`
- **`error_fact.source`** — `caller` / `system` / `dependency` / `environment` / `unknown`
- **`error_fact.recoverability`** — `retryable` / `degradable` / `non_recoverable` / `unknown`
- **`error_policy.action`** — `allow` / `warn` / `block` / `retry` / `fallback` / `trip`

In other words:

- `error_fact` answers "what kind of thing happened"
- `error_policy` answers "what should the system do about it"

Fields like `certainty`, `impact`, `user_effect`, `observability` are in `details` and are better suited for diagnostics or internal strategy — not recommended as first-layer long-term contracts.

Helper functions:

- `logicfp.user_mode.get_error_fact(...)`
- `logicfp.user_mode.get_error_policy(...)`
- `logicfp.user_mode.get_error_action(...)`

Example:

```python
from logicfp.user_mode import ProtectRuntimeError, get_error_action, get_error_fact

try:
    run_task(payload={"task_id": "T-1001"})
except ProtectRuntimeError as exc:
    fact = get_error_fact(exc)
    action = get_error_action(exc)
    if fact is not None:
        print(fact["stage"], fact["source"], fact["recoverability"])
    print(action)
```

To override the default action based on error facts:

- `create_protector(advanced={"error_action_resolver": ...})`

The resolver receives:

- `fact`
- `default_action`

Compatibility field (kept but deprecated):

- `default_policy`

Recommended return:

- `None` — use the default action
- `{"action": "..."}` — override the default action

Optional extra fields: `user_effect`, `observability`, `details`

For type hints, import from `logicfp.user_mode`:

- `ErrorActionResolverPayload`
- `ErrorActionResolverResult`
- `ErrorFactData`
- `ErrorPolicyData`
- `AIErrorRecognizer`
- `RecognitionContext`
- `build_ai_error_recognition`

Minimal reference: `examples/user_mode/action_resolver.py`

## 7. AI Error Recognition Details

When a failure comes from an AI / tool / external dependency call, the current version may include an additional recognition layer at:

- `ProtectRuntimeError.details["ai_error"]`

Since v3.4.0, the key AI error fields are also promoted to first-class attributes:

- `ProtectRuntimeError.ai_error_code`
- `ProtectRuntimeError.retryable`
- `ProtectRuntimeError.provider`
- `ProtectRuntimeError.severity`

With `simple=False`, these are also at `error.ai_error_code`, `error.retryable`, `error.provider`, `error.severity`.

These help distinguish:

- `RATE_LIMIT_TOKEN`
- `RATE_LIMIT_REQUEST`
- `STREAM_BROKEN`
- `AUTH_INVALID`
- `AUTH_FORBIDDEN`
- `UPSTREAM_OVERLOADED`
- `UPSTREAM_5XX`
- `OUTPUT_SCHEMA_INVALID`
- `TOOL_TIMEOUT`
- `MODEL_NOT_FOUND`
- `CONTEXT_TOO_LONG`
- `SAFETY_REFUSAL`
- and more

Supported providers: OpenAI, Anthropic, Google Gemini, Azure OpenAI, LangChain.

For custom on-demand recognition, pass a classifier:

- `create_protector(advanced={"ai_error_classifier": ...})`

It only runs when rule-based recognition does not match.

To add local recognizers to a specific protector:

- `create_protector(advanced={"ai_error_recognizers": [my_recognizer]})`

These run before the global registered chain, suitable for project-specific providers or business-specific exceptions.

Minimal reference: `examples/user_mode/custom_recognizer.py`
