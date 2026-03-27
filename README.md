# Logic Fingerprint

> Turn any function into a **safe, controllable execution unit**.

---

## ⚡ Quick Start (30 seconds)

### 1. Install

```bash
pip install -r requirements.txt
pip install -e .
```

---

### 2. Add protection to any function

```python
from logic_fingerprint import protect


@protect()
def hello(request):
    return {"msg": "hello world"}
```

---

### 3. Call it like a normal function

```python
print(hello({}))
```

Output:

```python
{'msg': 'hello world'}
```

---

### 4. Errors are automatically controlled

```python
@protect()
def broken(request):
    return 1 / 0


broken({})
```

Output:

```text
ProtectRuntimeError: division by zero
```

---

## 🧠 What just happened?

You just added:

* Circuit breaker (prevents repeated failures)
* Safe recovery (HALF_OPEN probing)
* Controlled execution (no retry storm)
* Optional schema validation
* Auto context (request_id, trace_id, etc.)
* Unified error handling

👉 Without changing your function logic

---

## 🔁 Advanced Mode (Engineering)

If you need full observability:

```python
@protect(simple=False)
def hello(request):
    return {"msg": "hello world"}
```

Return format:

```python
{
  "ok": True,
  "result": {...},
  "context": {...}
}
```

Use this for:

* APIs
* services
* metrics & monitoring
* structured error analysis

---

## 🧩 Input / Output Validation

```python
from pydantic import BaseModel


class Input(BaseModel):
    numbers: list[int]


class Output(BaseModel):
    sum: int


@protect(input_model=Input, output_model=Output)
def sum_numbers(request):
    return {"sum": sum(request.payload["numbers"])}
```

---

## 💡 One-line Mental Model

```text
@protect = "add a safety layer to any function"
```

---

## 🚀 What is this?

Logic Fingerprint is an **execution control layer**.

It sits between your application and your handlers:

```text
Function → Logic Fingerprint → Safe Execution
```

---

## ⚠️ Why this exists

Real-world systems are unstable:

* APIs timeout
* LLM outputs are unpredictable
* retries cause cascading failures
* outputs are inconsistent
* errors are hard to manage

---

## ✅ What it solves

| Problem         | Result               |
| --------------- | -------------------- |
| Retry storms    | Controlled probing   |
| System crashes  | Circuit breaker      |
| Unstable output | Schema validation    |
| Messy errors    | Unified protocol     |
| Hidden failures | Observable execution |

---

## 🧠 Positioning

```text
LangChain = "How to call"
Logic Fingerprint = "Should we call + Is it safe"
```

👉 This is not a replacement
👉 It is a **stability layer under your execution**

---

## 🧪 Built-in Capabilities

* Circuit Breaker (CLOSED / OPEN / HALF_OPEN)
* Time-driven probe (no low-QPS deadlock)
* Consecutive success recovery
* Global failure awareness (anti-cascade)
* Context auto injection
* Unified error protocol

---

## 🔗 Use Cases

### 1. LLM Safety Layer

```text
LangChain → LogicFingerprint → LLM API
```

---

### 2. API Protection Layer

```text
Client → LogicFingerprint → Service
```

---

### 3. Workflow Execution

```text
Task → Protected Function → Safe Execution
```

---

## 🆚 vs LangChain

| Capability         | LangChain  | Logic Fingerprint |
| ------------------ | ---------- | ----------------- |
| Prompt / Agent     | ✅          | ❌                 |
| Execution Safety   | ❌          | ✅                 |
| Circuit Breaker    | ❌          | ✅                 |
| Failure Control    | ❌          | ✅                 |
| Schema Enforcement | ⚠️ Partial | ✅                 |
| Error Protocol     | ❌          | ✅                 |

---

## 🧭 Philosophy

> Don't make systems smarter.
> Make execution safer.

---

## 📌 Roadmap

* v1.1 → config-based protection
* v1.2 → distributed consensus (Redis / etcd)
* v1.3 → rate limiting & auth
* v2.0 → execution runtime system

---

## ⭐ If useful

Give a star ⭐ — this project focuses on real-world system stability.
