# Demo Guide

This folder contains runnable examples of Logic Fingerprint.

---

## 1. Simple mode

```bash
python demo/demo_protect_simple.py
```

Behavior:

* works like a normal function
* returns plain result

---

## 2. Full mode

```bash
python demo/demo_protect_full.py
```

Behavior:

* returns structured output
* includes context and metadata

---

## 3. Error handling (simple mode)

```bash
python demo/demo_error_simple.py
```

Behavior:

* raises exception directly
* same as normal Python function

---

## 4. Error handling (full mode)

```bash
python demo/demo_error_full.py
```

Behavior:

* returns structured error
* includes error code + context

---

## 5. Local LLM demo (Ollama)

```bash
python demo/demo_protect_ollama_simple.py
```

Requirements:

* Ollama running locally
* model available (e.g. llama3.2)

---

## Summary

| Mode   | Behavior                              |
| ------ | ------------------------------------- |
| simple | behaves like normal function          |
| full   | returns structured engineering output |

Logic Fingerprint lets you choose between:

* developer-friendly usage (simple)
* production-ready execution (full)
