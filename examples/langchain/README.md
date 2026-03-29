# LangChain User Mode

This example shows the recommended user-facing pattern:

- keep `@protect()` as the main entrypoint
- wrap a LangChain `invoke()` or `ainvoke()` boundary
- validate both request and structured output with Pydantic models

## Files

- `user_mode.py`
- `config.yaml.example`

## What It Demonstrates

- `build_review_guard(agent)`
  wraps a sync LangChain agent or runnable using `@protect()`
- `build_async_review_guard(agent)`
  wraps an async LangChain agent or runnable using `@protect()`
- `build_langchain_agent()`
  shows a real LangChain `create_agent(...)` shape with structured output

## Install

If you want to run the real LangChain example, install LangChain and a provider package.
For example:

```powershell
uv add langchain langchain-openai
```

Then set a provider-specific key such as `OPENAI_API_KEY`.

Optional model override:

```powershell
$env:LANGCHAIN_MODEL="gpt-5"
```

## User Project Config

If you use `@protect()` inside your own project, put logicfp config here:

```text
your_project/config/config.yaml
```

Template:

- `config/config.yaml.example`
- `examples/langchain/config.yaml.example`

## Run

From the repository root:

```powershell
$env:PYTHONPATH=".;src"
uv run python examples/langchain/user_mode.py
```

## Why This Is User Mode

如果你想先看“用户模式示例”总览，再回到这个文件，先看：

- `documents/Tutorial/用户模式示例.md`

In this pattern, the caller only thinks about:

- the LangChain agent or runnable
- the input model
- the output model
- the `@protect()` decorator

They do not need to manage runtime assembly, registrars, or HTTP wiring.
