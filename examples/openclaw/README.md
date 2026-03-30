# OpenClaw User Mode

This example shows the recommended user-facing pattern:

- keep `@protect()` as the main entrypoint
- wrap an OpenClaw `agent.run()` or `agent.arun()` boundary
- validate both request and structured output with Pydantic models

## Files

- `user_mode.py`
- `config.yaml.example`

## What It Demonstrates

- `build_task_guard(agent)`
  wraps a sync OpenClaw agent using `@protect()`
- `build_async_task_guard(agent)`
  wraps an async OpenClaw agent using `@protect()`
- `build_openclaw_agent()`
  shows a real OpenClaw `Agent(...)` shape

## Install

If you want to run the real OpenClaw example, install the openclaw package.
For example:

```powershell
uv add openclaw
```

Then set an agent ID if needed:

```powershell
$env:OPENCLAW_AGENT_ID="my-agent"
```

## User Project Config

If you use `@protect()` inside your own project, put logicfp config here:

```text
your_project/config/config.yaml
```

Template:

- `config/config.yaml.example`
- `examples/openclaw/config.yaml.example`

## Run

From the repository root:

```powershell
$env:PYTHONPATH=".;src"
uv run python examples/openclaw/user_mode.py
```

## Why This Is User Mode

In this pattern, the caller only thinks about:

- the OpenClaw agent
- the input model
- the output model
- the `@protect()` decorator

They do not need to manage runtime assembly, registrars, or HTTP wiring.

If you want to see the user-mode overview first, start with:

- `documents/Tutorial/用户模式示例.md`
