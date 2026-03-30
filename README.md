# Logic Fingerprint (logicfp)

`logicfp` is a Python user-mode protection library for wrapping function boundaries with lightweight circuit-breaker style control.

Developer documentation lives in [README.developer.md](D:/workspace/python/logic_fingerprint_ai/README.developer.md).

## Install

```bash
pip install logicfp
```

## Quick Start

```python
from logicfp import protect


@protect()
def call_model(request):
    return {"answer": request.payload["text"].upper()}


result = call_model(payload={"text": "hello"})
```

Use `@protect()` when you want the default entrypoint.  
Use `create_protector()` when you need more than one protector instance.  
Use `logicfp.user_mode` when you want explicit user-mode types like `ErrorCode`, `NormalizationError`, `LogicExecutionError`, and `ProtectRuntimeError`.

## User Mode Contract

The current public contract centers on:

- `protect`
- `create_protector`
- `logicfp.user_mode.ErrorCode`
- `logicfp.user_mode.NormalizationError`
- `logicfp.user_mode.LogicExecutionError`
- `logicfp.user_mode.ProtectRuntimeError`
- `logicfp.config.describe_effective_config`

`logicfp` now recommends user mode as the only public entry model.

## Minimal Config

Put your project config at:

```text
your_project/config/config.yaml
```

```yaml
logicfp:
  instance_id: decorator-node
  default_source: user_function
  backend_type: memory
```

Use `logicfp:` as the main YAML section name. Older `logic_fingerprint:` configs are still accepted for compatibility.  
For user mode, `backend_type: memory` is still the recommended default.

## Failure Styles

`logicfp` supports two user-mode failure styles:

- `simple=True`
  success returns your result directly, failure raises `ProtectRuntimeError`
- `simple=False`
  success returns `ok/result/context`, failure returns `ok/error/context`

Example:

```python
from logicfp import protect


@protect(simple=False)
def review_text(request):
    return {"summary": request.payload["text"][:20]}
```

## Learn More

- Quick user-mode guide: [documents/Tutorial/用户模式快速接入.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/用户模式快速接入.md)
- User mode: [documents/Tutorial/用户模式示例.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/用户模式示例.md)
- User-mode error codes: [documents/Tutorial/用户模式错误码说明.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/用户模式错误码说明.md)
- User-mode envelope contract: [documents/Tutorial/用户模式返回结构说明.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/用户模式返回结构说明.md)
- Mode guide: [documents/Tutorial/protect 的用户模式与工程模式.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/protect%20的用户模式与工程模式.md)
