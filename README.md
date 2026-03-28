
Add a safety layer to any function.

Logic Fingerprint protects your function/LLM/API calls with:

circuit breaker (no retry storms)
safe recovery (HALF_OPEN probing)
schema validation (stable outputs)
unified error handling

Works with a single decorator: @protect()

## 🧭 How it works

```text
Your Function
      ↓
   @protect
      ↓
Logic Fingerprint
  ├─ Circuit Breaker
  ├─ Probe Recovery
  ├─ Validation Layer
  ├─ Error Control
      ↓
 Safe Execution
      ↓
   Result / Error
```

## ⚡ Quick Start

### Install

```bash
pip install logic-fingerprint

```bash
pip install -r requirements.txt
pip install -e .
```

### Protect a real local LLM call

```python
from logic_fingerprint import protect


@protect()
def ask_local_llm(request):
    import json
    import urllib.request

    payload = {
        "model": "llama3.2",
        "prompt": request.payload["prompt"],
        "stream": False,
    }

    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    return {"answer": body["response"].strip()}
```

### Call it like a normal function

```python
result = ask_local_llm({
    "prompt": "Explain circuit breaker in one sentence."
})

print(result)
```

Output:

```python
{'answer': 'A circuit breaker is a safety device that automatically stops an overcurrent flow in an electrical circuit to prevent damage to equipment and potential hazards.'}
```

### What you get automatically

* circuit breaker protection
* safe recovery probing
* controlled failure handling
* optional schema validation
* auto request context



```md
## 🎬 Demos

Run real examples locally:

### 1. Simple mode (like a normal function)

```bash
python demo/demo_protect_simple.py
```

---

### 2. Full mode (engineering output)

```bash
python demo/demo_protect_full.py
```

---

### 3. Error handling (simple mode)

```bash
python demo/demo_error_simple.py
```

---

### 4. Error handling (full mode)

```bash
python demo/demo_error_full.py
```

---

### 5. Real LLM demo (Ollama)

```bash
python demo/demo_protect_ollama_simple.py
```

👉 Make sure Ollama is running locally before running this demo.

------------------------------------------------------------------------

**Logic Fingerprint — Execution Safety Layer (Python)**

* Designed and implemented a decorator-based execution control layer for functions, APIs, and LLM calls
* Built circuit breaker with HALF_OPEN recovery, time-driven probing, and consecutive-success gating
* Added schema validation (Pydantic) and unified error protocol for stable, observable outputs
* Delivered dual-mode API (`simple` vs `full`) to support both developer-friendly usage and production observability
* Integrated with local LLM (Ollama) to demonstrate real-world stability against timeouts and malformed outputs
* Structured demos and documentation to enable 30-second onboarding and clear behavior comparison


Logic Fingerprint — 执行安全层（Python）

设计并实现基于装饰器的执行控制层，用于函数 / API / LLM 调用的稳定性保护
实现熔断机制（CLOSED / OPEN / HALF_OPEN）及时间驱动探测恢复与连续成功判定
引入输入输出 Schema 校验（Pydantic）与统一错误协议，保证结果结构稳定、可观测
设计双模式接口（simple / full），兼顾易用性与工程可观测性
集成本地 LLM（Ollama）进行真实场景验证，解决 timeout、异常输出等问题
构建分层 demo 与文档体系，实现 30 秒上手与行为对照演示

---
“I built a decorator-based execution safety layer for LLM and API calls.”

