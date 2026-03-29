# Examples

这里放的都是可运行示例，不放真实业务代码。

默认推荐先看用户模式。只有当你明确需要服务化、统一注册 handler、或者接平台网关时，再看工程模式。

如果你想先按模式选入口，先看这两页：

- `documents/Tutorial/用户模式快速接入.md`
- `documents/Tutorial/用户模式示例.md`
- `documents/Tutorial/工程模式示例.md`

如果你想先理解模式边界和配置来源，再看：

- `documents/Tutorial/protect 的用户模式与工程模式.md`
- `documents/Tutorial/config 参数说明.md`

## 用户模式

用户模式的主入口是 `@protect()`，重点是“保护函数边界，不手动装 runtime”。

这是默认路线。

从这里开始：

- `examples/langchain/user_mode.py`
- `examples/langchain/README.md`
- `examples/langchain/config.yaml.example`
- `examples/user_mode/README.md`
- `examples/user_mode/basic_function.py`
- `examples/user_mode/tool_call.py`
- `examples/user_mode/exception_handling.py`
- `examples/user_mode/config_diagnostics.py`

这条路径适合：

- LangChain `invoke()` / `ainvoke()`
- SDK 调用
- 本地脚本或工具调用

## 工程模式

工程模式的主入口是 `logicfp.engineering` 和 CLI，重点是“保护服务边界，统一注册 handlers”。

这条路线是高级/可选路线，不是默认接入方式。

### 纯 registrar 模板

- `examples/production_handlers.py`
- `examples/production.config.yaml.example`
- `examples/run_demo.ps1`
- `examples/invoke_demo.ps1`

### 带依赖装配的 registrar 模板

- `examples/production_services.py`
- `examples/services.config.yaml.example`
- `examples/run_services_demo.ps1`
- `examples/invoke_services_demo.ps1`

### OpenClaw 工程接入

- `examples/openclaw/register_handlers.py`
- `examples/openclaw/README.md`
- `examples/openclaw/config.yaml.example`

### 可复制业务骨架

- `examples/business_skeleton/README.md`
- `examples/business_skeleton/config.yaml.example`
- `examples/business_skeleton/handlers/register.py`

## 配置约定

示例现在统一使用 YAML。

推荐做法是把示例模板复制到你的项目里：

```text
your_project/
  config/
    config.yaml
```

`examples/` 里的 `*.config.yaml.example` 或 `config.yaml.example` 只是模板来源，不建议直接在仓库根目录长期改它们。

PowerShell 启动脚本仍然保留，作用是做仓库内快速演示；复制到真实项目时，优先使用你自己的 `config/config.yaml`。

## 生产 Handler Module Contract

如果你要让自己的模块能被 `handler_registrars` 加载，保持这个约定：

1. 把模块放到 `PYTHONPATH` 上。
2. 暴露 `register_handlers(handler_registry)`，或者使用 `module_path:function_name`。
3. 在函数里把 handlers 注册到 `HandlerRegistry`。
4. 如果需要数据库、RPC、HTTP client，就在 registrar 里装配依赖，再绑定给 handler。

最小模板：

```python
from logicfp.handler_registry import HandlerRegistry


def register_handlers(handler_registry: HandlerRegistry) -> None:
    def my_handler(request):
        return {"ok": True}

    handler_registry.register("my_handler", my_handler)
```
