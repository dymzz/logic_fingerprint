# OpenClaw Engineering Mode

这个示例只讲工程模式，不讲 `@protect()` 的用户模式。

配套总览看这里：

- `documents/Tutorial/工程模式示例.md`
- `documents/Tutorial/protect 的用户模式与工程模式.md`

## Files

- `register_handlers.py`
- `config.yaml.example`

## What It Demonstrates

- `openclaw_agent_turn`
  保护 Gateway 入站 turn 边界
- `openclaw_tool_dispatch`
  保护 session 内的 tool dispatch 边界

## Config

把模板复制到你的项目：

```text
your_project/config/config.yaml
```

模板文件：

- `examples/openclaw/config.yaml.example`

其中包含两类配置：

- `logicfp:`：运行时、backend、registrar
- `openclaw:`：Gateway URL、agent/session 约定、远端 token 环境变量名

## Start

推荐用 CLI：

```powershell
logicfp start --config config/config.yaml
```

如果只是仓库内调试，也可以继续参考：

- `examples/run_demo.ps1`

## Why This Is Engineering Mode

在这条路径里，你需要自己负责：

- registrar wiring
- runtime/backend 选择
- session key 约定
- Gateway 部署和凭据约定

所以它属于平台/服务接入，而不是“装饰器包一个函数”。
