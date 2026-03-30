# User Mode Templates

这组模板只面向用户模式，也就是“直接用 `@protect()` 或 `create_protector()` 保护函数边界”。

## 推荐顺序

1. 基础函数模板
   `examples/user_mode/basic_function.py`
2. 工具调用模板
   `examples/user_mode/tool_call.py`
3. 异常处理模板
   `examples/user_mode/exception_handling.py`
4. 配置诊断模板
   `examples/user_mode/config_diagnostics.py`
5. 动作解析模板
   `examples/user_mode/action_resolver.py`
6. 局部识别模板
   `examples/user_mode/custom_recognizer.py`
7. 本地日志模板
   `examples/user_mode/local_logging.py`

## 这些模板分别解决什么问题

- `basic_function.py`
  最小用户模式写法，适合普通 Python 函数。
- `tool_call.py`
  演示 `create_protector()`，适合工具调用、SDK 包装、多个保护实例。
- `exception_handling.py`
  演示 `simple=True` 时如何捕获 `logicfp.user_mode.ProtectRuntimeError`。
- `config_diagnostics.py`
  打印当前实际生效的配置、配置文件路径和环境变量前缀。
- `action_resolver.py`
  演示怎么用 `error_action_resolver` 把未知失败改成 `fallback`，再由调用方走本地备用路径。
- `custom_recognizer.py`
  演示怎么给单个 protector 局部注入 `ai_error_recognizers`，把项目私有 provider 错误映射成标准 AI 错误，再由调用方按 `ai_error` 做本地 fallback。
- `local_logging.py`
  演示怎么用 `JsonlEventLogger + SummaryLogger` 做本地 JSONL 日志和轻量汇总，不需要单独跑服务；示例里也带了按文件大小轮转。

如果你已经把日志写到 `logs/logicfp.jsonl`，也可以直接用：

```bash
python scripts/log_summary.py logs/logicfp.jsonl
```

相关说明：

- `documents/Tutorial/用户模式速查.md`
- `documents/Tutorial/用户模式错误码说明.md`

## 配置放哪里

真实项目里推荐放在：

```text
your_project/config/config.yaml
```

最小模板可以从这里复制：

- `examples/user_mode/config.yaml.example`
- `config/config.yaml.example`
