# User Mode Envelope Reference

This page explains the return structure when using `simple=False` in user mode.

If you want `logicfp` to return a unified envelope on both success and failure instead of raising `ProtectRuntimeError` on failure, use:

```python
@protect(simple=False)
```

## 1. Success Structure

On success:

```python
{
    "ok": True,
    "result": ...,
    "context": {...},
}
```

Fields:

- **`ok`** — always `True`
- **`result`** — your function's return value
- **`context`** — call context information

`context` always contains these keys:

- `request_id`
- `trace_id`
- `user_id`
- `source`
- `timestamp`
- `headers`
- `metadata`

Example:

```python
{
    "ok": True,
    "result": {"value": 2},
    "context": {
        "request_id": "req-...",
        "trace_id": "trace-...",
        "user_id": None,
        "source": "decorator",
        "timestamp": "2026-03-30T12:00:00+00:00",
        "headers": {},
        "metadata": {},
    },
}
```

## 2. Failure Structure

On failure:

```python
{
    "ok": False,
    "error": {
        "code": ...,
        "message": ...,
        "ai_error_code": ...,
        "retryable": ...,
        "provider": ...,
        "severity": ...,
        "details": {...},
    },
    "context": {...},
}
```

Fields:

- **`ok`** — always `False`
- **`error.code`** — error code, e.g. `ERR_VALIDATION`, `ERR_LOGIC`
- **`error.message`** — error message
- **`error.ai_error_code`** — AI error code if recognized (e.g. `RATE_LIMIT_TOKEN`), otherwise `None`
- **`error.retryable`** — `True` / `False` / `None` based on AI error recognition
- **`error.provider`** — provider name if recognized (e.g. `openai`, `anthropic`, `google`), otherwise `None`
- **`error.severity`** — severity level if recognized (e.g. `warn`, `block`), otherwise `None`
- **`error.details`** — detailed error information, empty dict if none
- **`context`** — same context structure as success

Example:

```python
{
    "ok": False,
    "error": {
        "code": "ERR_LOGIC",
        "message": "manual review required",
        "ai_error_code": None,
        "retryable": None,
        "provider": None,
        "severity": None,
        "details": {
            "error_fact": {
                "stage": "execute",
                "source": "system",
                "recoverability": "non_recoverable",
                "code": "ERR_LOGIC",
                "message": "manual review required",
                "details": {
                    "certainty": "deterministic",
                    "impact": "fatal",
                },
            },
            "error_policy": {
                "action": "block",
                "details": {
                    "user_effect": "hard_error",
                    "observability": "alert",
                },
            },
        },
    },
    "context": {
        "request_id": "req-...",
        "trace_id": "trace-...",
        "user_id": None,
        "source": "decorator",
        "timestamp": "2026-03-30T12:00:00+00:00",
        "headers": {},
        "metadata": {},
    },
}
```

The most useful fields to rely on:

- `error.details["error_fact"]["stage"]`
- `error.details["error_fact"]["source"]`
- `error.details["error_fact"]["recoverability"]`
- `error.details["error_policy"]["action"]`

These 4 fields answer:

- Where did the error occur?
- Whose fault is it?
- Is it recoverable?
- What should the system do by default?

Helper functions to avoid deep indexing:

- `logicfp.user_mode.get_error_fact(...)`
- `logicfp.user_mode.get_error_policy(...)`
- `logicfp.user_mode.get_error_action(...)`

## 3. When to Use simple=False

Suitable when:

- You want to pass results upstream for unified handling
- You do not want to write `try/except` at every call site
- You want both success and failure to use the same dict structure

Not suitable when:

- You prefer Python exception style
- You want failures to immediately interrupt without passing an envelope upstream

## 4. Difference Between simple=True and simple=False

- **`simple=True`** — success returns the result directly, failure raises `ProtectRuntimeError`
- **`simple=False`** — success returns a success envelope, failure returns an error envelope

## 5. Stability Advice

If you plan to rely on the return structure long-term, depend only on these top-level contracts:

- Success: `ok / result / context`
- Failure: `ok / error / context`
- Error object: `code / message / ai_error_code / retryable / provider / severity / details`
- Error normalization: `error_fact(stage/source/recoverability)` and `error_policy(action)`

Do not depend on internal implementation details — only depend on these public fields.
