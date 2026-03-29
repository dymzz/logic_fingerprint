# Logic Fingerprint (logicfp)

`logicfp` is a Python protection library for wrapping function boundaries with circuit-breaker style control.

Developer documentation lives in [README.developer.md](D:/workspace/python/logic_fingerprint_ai/README.developer.md).

## Install

```bash
pip install logicfp
```

## Quick Start

```python
from logicfp import protect


@protect(simple=False)
def call_model(request):
    return {"answer": request.payload["text"].upper()}


result = call_model(payload={"text": "hello"})
```

Use `@protect()` when you want the simplest user-mode entrypoint.
Use `create_protector()` when you need more than one protector instance.
Use `logicfp.user_mode` when you want explicit user-mode types like `ProtectRuntimeError`.

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

## Learn More

- Quick user-mode guide: [documents/Tutorial/用户模式快速接入.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/用户模式快速接入.md)
- User mode: [documents/Tutorial/用户模式示例.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/用户模式示例.md)
- Mode guide: [documents/Tutorial/protect 的用户模式与工程模式.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/protect%20的用户模式与工程模式.md)
- Optional engineering mode: [documents/Tutorial/工程模式示例.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/工程模式示例.md)
