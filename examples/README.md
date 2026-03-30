# Examples

这里放的都是可运行示例，不放真实业务代码。

现在默认只推荐用户模式，也就是 `@protect()`。

如果你想先按入口看，先看这两页：

- `documents/Tutorial/用户模式速查.md`
- `documents/Tutorial/用户模式快速接入.md`
- `documents/Tutorial/用户模式示例.md`

如果你想先理解配置来源，再看：

- `documents/Tutorial/protect 的用户模式与工程模式.md`
- `documents/Tutorial/config 参数说明.md`

## 用户模式

用户模式的主入口是 `@protect()`，重点是“保护函数边界，不手动装复杂运行时”。

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
- `examples/user_mode/action_resolver.py`
- `examples/user_mode/custom_recognizer.py`
- `examples/user_mode/local_logging.py`

这条路径适合：

- LangChain `invoke()` / `ainvoke()`
- SDK 调用
- 本地脚本或工具调用

## 配置约定

示例统一使用 YAML。

推荐做法是把示例模板复制到你的项目里：

```text
your_project/
  config/
    config.yaml
```

`examples/` 里的 `config.yaml.example` 只是模板来源，不建议直接在仓库根目录长期改它们。

其他偏工程化的示例会逐步迁出公开入口说明，不再作为默认接入路径。
