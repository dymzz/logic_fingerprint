## ⚡ Quick Start

### Install

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
