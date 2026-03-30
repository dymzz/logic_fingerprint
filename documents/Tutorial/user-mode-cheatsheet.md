# User Mode Cheatsheet

This page contains the most common user mode templates, ready to copy.

## 1. Minimal Setup

```python
from logicfp import protect


@protect()
def call_model(request):
    return {"answer": request.payload["text"].upper()}


result = call_model(payload={"text": "hello"})
```

## 2. Unified Envelope

```python
from logicfp import protect


@protect(simple=False)
def review_text(request):
    return {"summary": request.payload["text"][:20]}


result = review_text(payload={"text": "hello"})
```

Success structure:

- `ok / result / context`

Failure structure:

- `ok / error / context`

## 3. Reading Errors

```python
from logicfp.user_mode import ProtectRuntimeError, get_error_action, get_error_fact


try:
    call_model(payload={"text": "hello"})
except ProtectRuntimeError as exc:
    fact = get_error_fact(exc)
    action = get_error_action(exc)
    if fact is not None:
        print(fact["stage"], fact["source"], fact["recoverability"])
    print(action)
```

For `simple=False`:

```python
result = review_text(payload={"text": "hello"})
fact = get_error_fact(result)
action = get_error_action(result)
```

## 4. The 4 Core Fields

- `error_fact.stage`
  - `input`
  - `execute`
  - `dependency`
  - `output`
- `error_fact.source`
  - `caller`
  - `system`
  - `dependency`
  - `environment`
  - `unknown`
- `error_fact.recoverability`
  - `retryable`
  - `degradable`
  - `non_recoverable`
  - `unknown`
- `error_policy.action`
  - `allow`
  - `warn`
  - `block`
  - `retry`
  - `fallback`
  - `trip`

## 5. Overriding the Default Action

```python
from logicfp import create_protector


def my_action_resolver(payload):
    fact = payload["fact"]
    if fact["source"] == "unknown" and fact["recoverability"] == "unknown":
        return {"action": "fallback"}
    return None


guard = create_protector(
    advanced={"error_action_resolver": my_action_resolver},
)
```

The resolver currently receives:

- `fact`
- `default_action`

Kept for compatibility:

- `default_policy`

For static type hints, import from:

- `logicfp.user_mode.ErrorActionResolverPayload`
- `logicfp.user_mode.ErrorActionResolverResult`

Recommended return values:

- `None`
- `{"action": "fallback"}`

Optional extra fields:

- `user_effect`
- `observability`
- `details`

## 6. Config Location

```text
your_project/
  config/
    config.yaml
```

Minimal config:

```yaml
logicfp:
  instance_id: decorator-node
  default_source: user_function
  backend_type: memory
```
