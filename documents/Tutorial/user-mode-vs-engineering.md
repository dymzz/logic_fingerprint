# User Mode vs Engineering Mode

This page keeps the word "mode" only to explain the historical path.

The current public product surface recommends only one mode:

- **User mode**: `@protect()` / `create_protector()`

The repository previously included engineering mode, CLI, and HTTP service entry points. These have been removed from the public product surface and are no longer part of the default documentation or install dependencies.

## 1. How to Use It Now

Use only these two entry points by default:

- `from logicfp import protect`
- `from logicfp import create_protector`

If you need explicit user mode types:

- `from logicfp.user_mode import ErrorCode`
- `from logicfp.user_mode import NormalizationError`
- `from logicfp.user_mode import LogicExecutionError`
- `from logicfp.user_mode import ProtectRuntimeError`
- `from logicfp.user_mode import Protector`

## 2. Why Converge to User Mode

Because the core value of `logicfp` is protecting function boundaries, not building a standalone deployable platform service.

The most suitable scenarios are:

- LangChain `invoke()` / `ainvoke()`
- OpenClaw `agent.run()` / `agent.arun()`
- SDK calls
- Local script tasks
- Tool calls
- LLM request boundaries

All of these are better served by `@protect()` directly at the function boundary.

## 3. How Config Works

Projects should use a unified config location:

```text
your_project/
  config/
    config.yaml
```

Main section:

```yaml
logicfp:
  instance_id: decorator-node
  default_source: user_function
  backend_type: memory
```

Recommendations:

- Use `backend_type: memory`
- Get the local protection chain working first
- Do not use distributed backends as the default path

## 4. What About the Historical Engineering Mode

If you see these names in old docs or old code:

- `logicfp.engineering`
- `create_http_app()`
- `logicfp start`
- `FastAPI` / `uvicorn` entry points

Consider them historical paths.

The current version only documents user mode and no longer presents these as the default product surface.

## 5. What to Read Next

Recommended reading order:

1. [user-mode-quickstart.md](user-mode-quickstart.md)
2. [user-mode-examples.md](user-mode-examples.md)
3. [user-mode-error-codes.md](user-mode-error-codes.md)
4. [user-mode-envelope.md](user-mode-envelope.md)
