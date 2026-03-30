# User Mode Examples

This page collects user mode examples — those using `@protect()` as the main entry point.

If you just want to protect function boundaries without assembling a complex runtime, this is the page for you.

This is the current default recommended path.

For the shortest setup path, start with:

- [user-mode-quickstart.md](user-mode-quickstart.md)

## When to Read This Page

Suitable for:

- LangChain `invoke()` / `ainvoke()`
- OpenClaw `agent.run()` / `agent.arun()`
- SDK calls
- Tool function calls
- Local script tasks

This page does not cover internal runtime assembly details.

## Current Examples

### Plain Function / Tool Call / Exception Handling / Config Diagnostics

- `examples/user_mode/README.md`
- `examples/user_mode/basic_function.py`
- `examples/user_mode/tool_call.py`
- `examples/user_mode/exception_handling.py`
- `examples/user_mode/config_diagnostics.py`
- `examples/user_mode/config.yaml.example`

These templates demonstrate:

- Minimal `@protect()` usage
- `create_protector()` multi-instance pattern
- How to catch `logicfp.user_mode.ProtectRuntimeError` with `simple=True`
- What the success / error envelope looks like with `simple=False`
- How to print the effective config

### LangChain

- `examples/langchain/user_mode.py`
- `examples/langchain/README.md`
- `examples/langchain/config.yaml.example`

These examples demonstrate:

- Wrapping a sync `invoke()` with `@protect()`
- Wrapping an async `ainvoke()` with `@protect()`
- Using Pydantic for input/output validation
- Hiding runtime details inside the library

### OpenClaw

- `examples/openclaw/user_mode.py`
- `examples/openclaw/README.md`
- `examples/openclaw/config.yaml.example`

These examples demonstrate:

- Wrapping a sync `agent.run()` with `@protect()`
- Wrapping an async `agent.arun()` with `@protect()`
- Using Pydantic for input/output validation

## Config Placement

Place config in your project:

```text
your_project/config/config.yaml
```

Minimal template sources:

- `examples/langchain/config.yaml.example`
- `examples/openclaw/config.yaml.example`
- `config/config.yaml.example`

User mode typically only requires:

- `instance_id`
- `default_source`
- `backend_type`
- probe-related parameters

## Entry Points

User mode recommends only these two entry points:

- `from logicfp import protect`
- `from logicfp import create_protector`

To troubleshoot config issues, start with:

- `examples/user_mode/config_diagnostics.py`
- `logicfp.config.describe_effective_config(...)`
