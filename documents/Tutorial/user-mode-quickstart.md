# User Mode Quickstart

This page solves one thing: get `logicfp` attached to a function in 3 minutes.

If you just want the shortest template, go to:

- [user-mode-cheatsheet.md](user-mode-cheatsheet.md)

## 1. When to Use User Mode

Suitable for:

- Protecting a plain Python function
- Wrapping LangChain `invoke()` / `ainvoke()`
- Wrapping OpenClaw `agent.run()` / `agent.arun()`
- Protecting SDK calls, tool calls, or local script tasks
- Not wanting to maintain extra service entries or complex assembly

Default entry points:

- `from logicfp import protect`
- `from logicfp import create_protector`

## 2. 3-Minute Minimal Setup

Install:

```bash
pip install logicfp
```

Wrap your function:

```python
from logicfp import protect


@protect()
def call_model(request):
    return {
        "ok": True,
        "payload": request.payload,
    }
```

Call with `payload`:

```python
result = call_model(payload={"text": "hello"})
```

Add input/output constraints:

```python
from pydantic import BaseModel
from logicfp import protect


class ReviewInput(BaseModel):
    text: str


class ReviewOutput(BaseModel):
    summary: str


@protect(input_model=ReviewInput, output_model=ReviewOutput, simple=False)
def review_text(request):
    return {"summary": request.payload["text"][:20]}
```

## 3. Where to Put Config

Place config in your project:

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

Start with `backend_type: memory` and get the protection chain working first.

## 4. When to Use create_protector()

Start with `@protect()` by default.

Switch to `create_protector()` only when:

- You need two protectors with different strategies
- You want to explicitly set `default_source` or strategy parameters
- You want to reuse the same config across multiple functions
- You want to override the default action based on error facts (e.g. change `warn` to `fallback`)

Most common pattern:

```python
from logicfp import create_protector


tool_guard = create_protector(
    default_source="tool_call",
)


@tool_guard.protect(simple=False)
def run_tool(request):
    return {"ok": True}
```

For advanced control over `instance_id`, `redis_*`, or direct backend injection, use:

```python
from logicfp.user_mode import Protector

guard = Protector(instance_id="tool-guard")
```

To override the default action based on error facts:

```python
tool_guard = create_protector(
    advanced={
        "error_action_resolver": my_action_resolver,
    }
)
```

Minimal reference:

- `examples/user_mode/action_resolver.py`

## 5. Common Issues

### Why isn't the return value the raw result?

With the default `simple=True`, success returns the result directly and failure raises an exception.

For a unified envelope:

```python
@protect(simple=False)
```

See: [user-mode-envelope.md](user-mode-envelope.md)

### Why does failure raise an exception?

This is the default behavior of `simple=True`.

To catch it:

```python
from logicfp.user_mode import ProtectRuntimeError
```

For error code branching, see:

- [user-mode-error-codes.md](user-mode-error-codes.md)
- [user-mode-envelope.md](user-mode-envelope.md)

### Why isn't my config taking effect?

Check two things first:

1. Is the file at `config/config.yaml`?
2. Is the process working directory your project root?

To inspect the effective config:

```python
from logicfp.config import DECORATOR_PROFILE, describe_effective_config

print(describe_effective_config(profile=DECORATOR_PROFILE))
```

With `simple=False`, you can also inspect the 4 normalized fields on failure:

- `error_fact.stage`
- `error_fact.source`
- `error_fact.recoverability`
- `error_policy.action`

Helper functions:

```python
from logicfp.user_mode import get_error_action, get_error_fact

result = guarded(payload={"value": 1})
fact = get_error_fact(result)
action = get_error_action(result)
```

## 6. What to Read Next

After the minimal setup works, continue in this order:

1. `examples/user_mode/basic_function.py`
2. `examples/user_mode/tool_call.py`
3. `examples/user_mode/exception_handling.py`
4. `examples/user_mode/config_diagnostics.py`
5. `examples/langchain/user_mode.py`
6. `examples/openclaw/user_mode.py`
