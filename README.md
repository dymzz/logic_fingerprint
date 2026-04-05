# Logic Fingerprint (logicfp)

```mermaid
graph TD
    subgraph Input ["输入层"]
        A[用户提问] --> B[上下文池 Context Pool]
        B -->|带指纹的 Evidence| C[LLM 大模型]
    end

    subgraph LLM_Output ["大模型输出 (概率性)"]
        C --> D{生成内容}
        D -->|Claim A| E[断言 A]
        D -->|Claim B| F[断言 B]
    end

    subgraph Logic_FP ["Logic Fingerprint 拦截层 (确定性)"]
        E --> G{指纹比对}
        F --> G
        B -.->|校验| G
        
        G -->|验证通过| H[✅ 确定的逻辑链路]
        G -->|引用缺失/伪造| I[🚫 物理阻断/熔断]
    end

    H --> Output[最终安全输出]
    I --> Error[错误降级/人工审核]

    style Logic_FP fill:#f9f,stroke:#333,stroke-width:2px
    style I fill:#ff9999,stroke:#cc0000
    style H fill:#99ff99,stroke:#006600
```

`logicfp` is an AI-era call protection layer.

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

- User-mode cheatsheet: [documents/Tutorial/user-mode-cheatsheet.md](documents/Tutorial/user-mode-cheatsheet.md)
- Quick user-mode guide: [documents/Tutorial/user-mode-quickstart.md](documents/Tutorial/user-mode-quickstart.md)
- User-mode examples: [documents/Tutorial/user-mode-examples.md](documents/Tutorial/user-mode-examples.md)
- User-mode error codes: [documents/Tutorial/user-mode-error-codes.md](documents/Tutorial/user-mode-error-codes.md)
- User-mode envelope contract: [documents/Tutorial/user-mode-envelope.md](documents/Tutorial/user-mode-envelope.md)
- User mode vs engineering mode: [documents/Tutorial/user-mode-vs-engineering.md](documents/Tutorial/user-mode-vs-engineering.md)
- Config reference: [documents/Tutorial/config-reference.md](documents/Tutorial/config-reference.md)
- Plugin hook guide: [documents/Tutorial/plugin-hooks.md](documents/Tutorial/plugin-hooks.md)


