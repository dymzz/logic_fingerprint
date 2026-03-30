# protect 的用户模式与工程模式

这页保留“模式”这个词，只是为了说明历史路径。

当前公开产品面只推荐一种模式：

- 用户模式：`@protect()` / `create_protector()`

过去仓库里曾经出现过工程模式、CLI 和 HTTP 服务入口。现在这些入口已经从公开产品面撤下，不再作为默认文档路线，也不再作为安装依赖的一部分。

## 1. 现在应该怎么用

默认只用这两个入口：

- `from logicfp import protect`
- `from logicfp import create_protector`

如果你需要显式的用户模式类型，再用：

- `from logicfp.user_mode import ErrorCode`
- `from logicfp.user_mode import NormalizationError`
- `from logicfp.user_mode import LogicExecutionError`
- `from logicfp.user_mode import ProtectRuntimeError`
- `from logicfp.user_mode import Protector`

## 2. 为什么收口到用户模式

因为 `logicfp` 的核心价值，是保护函数边界，而不是再造一个独立部署的平台服务。

当前最适合它的场景是：

- LangChain `invoke()` / `ainvoke()`
- SDK 调用
- 本地脚本任务
- 工具调用
- LLM 请求边界

这类场景都更适合直接在函数边界使用 `@protect()`。

## 3. 配置怎么理解

用户项目统一使用：

```text
your_project/
  config/
    config.yaml
```

主 section 统一是：

```yaml
logicfp:
  instance_id: decorator-node
  default_source: user_function
  backend_type: memory
```

默认推荐：

- `backend_type: memory`
- 优先先跑通本地保护链
- 不把 Redis 群体熔断当成默认路线

## 4. 历史工程模式怎么处理

如果你在旧文档或旧代码里看到这些名字：

- `logicfp.engineering`
- `create_http_app()`
- `logicfp start`
- `FastAPI` / `uvicorn` 入口

可以把它们视为历史路径。

当前版本对外只讲用户模式，不再把这些作为默认产品面。

## 5. 下一步看哪里

推荐按这个顺序继续：

1. [用户模式快速接入.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/用户模式快速接入.md)
2. [用户模式示例.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/用户模式示例.md)
3. [用户模式错误码说明.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/用户模式错误码说明.md)
4. [用户模式返回结构说明.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/用户模式返回结构说明.md)
