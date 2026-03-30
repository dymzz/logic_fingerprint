# logicfp Developer README

这份文档面向仓库开发者，不是最终用户说明。

## 项目定位

- 用户模式入口：`from logicfp import protect, create_protector`
- 工程模式入口：`from logicfp.engineering import create_http_app, build_production_runtime`
- CLI 入口：`logicfp start --config config/config.yaml`

## 仓库结构

```text
src/logicfp/                核心源码包
documents/Tutorial/         用户教程
examples/                   示例项目和示例配置
scripts/                    开发和发布脚本
tests/                      测试
config/                     仓库内配置模板
design/                     设计文档
```

## 本地开发

先安装项目本体：

```bash
pip install -e .
```

如果要做发布相关操作，再安装发布依赖：

```bash
pip install -e .[release]
```

## 本地缓存与临时目录

推荐先启用仓库内缓存和临时目录，避免 `uv` 或 `pytest` 落到系统目录后遇到 Windows ACL/清理问题。

PowerShell:

```powershell
. .\scripts\dev_env.ps1
```

启用后会统一使用：

- `UV_CACHE_DIR=.uv-cache`
- `TMP=.tmp`
- `TEMP=.tmp`
- `pytest --basetemp=.pytest_tmp/basetemp`

其中：

- `uv` 缓存目录通过 [`pyproject.toml`](D:/workspace/python/logic_fingerprint_ai/pyproject.toml) 的 `tool.uv.cache-dir` 固定到项目内
- `pytest` 临时目录通过 [`pyproject.toml`](D:/workspace/python/logic_fingerprint_ai/pyproject.toml) 的 `tool.pytest.ini_options.addopts` 固定到项目内
- [`dev_env.ps1`](D:/workspace/python/logic_fingerprint_ai/scripts/dev_env.ps1) 主要负责把系统级 `TMP/TEMP` 也切到仓库内

如果当前终端里已经有全局 `UV_CACHE_DIR`，脚本会覆盖它，避免继续写到类似 `D:\uv-cache` 这种高风险目录。

## 常用命令

运行测试：

```bash
uv run pytest tests -q
```

启动本地 HTTP 服务：

```bash
logicfp start --config config/config.yaml
```

构建发布包：

```bash
python scripts/release_package.py build
python scripts/release_package.py check
python scripts/release_package.py release
```

发布到 PyPI：

```bash
python scripts/release_package.py publish --repository pypi
```

先发到 TestPyPI：

```bash
python scripts/release_package.py release --publish --testpypi
```

## 配置约定

- 用户项目标准配置路径：`your_project/config/config.yaml`
- 主 section：`logicfp:`
- 兼容旧 section：`logic_fingerprint:`
- 环境变量前缀：`LOGICFP_`
- 兼容旧环境变量前缀：`LOGIC_FINGERPRINT_`
- 用户模式默认建议 `backend_type=memory`
  对 `LangChain / OpenClaw / HTTP / DB / LLM` 这类调用，优先做本地保护；不要把 Redis 群体熔断当成默认方案

详细配置说明见 [config 参数说明.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/config%20参数说明.md)。

## 文档分工

- [README.md](D:/workspace/python/logic_fingerprint_ai/README.md)：用户入口说明
- [logicfp v3 roadmap.md](D:/workspace/python/logic_fingerprint_ai/documents/Product/logicfp%20v3%20roadmap.md)：下个大版本方向
- [protect 的用户模式与工程模式.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/protect%20的用户模式与工程模式.md)：入口模型说明
- [从 demo 到生产接入.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/从%20demo%20到生产接入.md)：接入路径
- [用户模式返回结构说明.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/用户模式返回结构说明.md)：`simple=False` 的 envelope contract
- [用户模式示例.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/用户模式示例.md)：用户模式示例
- [用户模式错误码说明.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/用户模式错误码说明.md)：用户模式错误码与失败语义
- [工程模式示例.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/工程模式示例.md)：工程模式示例

## v3 用户模式 API freeze 清单

`3.0` 前建议冻结这些用户模式入口：

- `from logicfp.user_mode import ErrorCode`
- `from logicfp.user_mode import NormalizationError`
- `from logicfp.user_mode import LogicExecutionError`
- `from logicfp import protect`
- `from logicfp import create_protector`
- `from logicfp.user_mode import protect`
- `from logicfp.user_mode import create_protector`
- `from logicfp.user_mode import Protector`
- `from logicfp.user_mode import ProtectRuntimeError`
- `from logicfp.config import describe_effective_config`

`protect(...)` 在 `3.0` 前要固定的语义：

- 默认是用户模式主入口
- 默认每个装饰器实例拥有独立保护器
- 默认 logger 保持静默
- `simple=True` 和 `simple=False` 的语义保持稳定
- sync / async 路径行为一致
- `simple=False` 的 envelope 结构保持稳定：
  success=`ok/result/context`，failure=`ok/error/context`

`create_protector(...)` 在 `3.0` 前建议分层：

- 用户模式正式参数：
  `config_file`、`probe_rate`、`probe_interval_seconds`、`consecutive_success_threshold`、`total_nodes`、`global_fail_threshold`、`default_source`、`backend_type`、`event_logger`
- 高级/可选参数：
  `instance_id`、`redis_url`、`redis_decode_responses`、`redis_key`、`redis_key_prefix`、`redis_ttl_seconds`、`redis_client`、`backend`、`config`、`settings`

高级控制优先建议：

- 直接用 `Protector(...)`
- 或 `create_protector(advanced={...})`

错误与配置心智在 `3.0` 前也建议锁定：

- `ProtectRuntimeError` 的 `message / code / details / context`
- 用户项目配置路径：`config/config.yaml`
- 主 section：`logicfp:`
- 默认 backend：`memory`
- 环境变量前缀：`LOGICFP_`

## 发布前检查

- 确认版本号已更新：[`src/logicfp/_version.py`](D:/workspace/python/logic_fingerprint_ai/src/logicfp/_version.py)
- 确认 `README.md` 面向用户，`README.developer.md` 面向开发者
- 运行测试
- 构建 `sdist` 和 `wheel`
- 先发 `TestPyPI`，再发正式 `PyPI`
- 发布后补 Git tag

## 3.0 更新说明

这轮 `3.0` 方向上的主要收口点是：

- 用户模式 contract 开始冻结，公开入口收敛到 `protect / create_protector / ErrorCode / NormalizationError / LogicExecutionError / ProtectRuntimeError / describe_effective_config`
- `create_protector(...)` 参数面开始收口，正式参数和高级参数开始分层
- `simple=True` 的失败语义进一步统一，输入校验失败和输出校验失败也统一收进 `ProtectRuntimeError`
- `simple=False` 的 envelope contract 已锁定为：
  success=`ok/result/context`，failure=`ok/error/context`
- 用户模式错误码说明和返回结构说明已经成文档

这意味着当前阶段已经进入：

`3.0 用户模式 contract 收口阶段`

## 3.0.0 发布说明

`3.0.0` 的核心变化，不是继续扩工程模式，而是把用户模式的长期 contract 开始定下来。

本次版本重点包括：

- 用户模式公开入口收敛到：
  `protect / create_protector / ErrorCode / NormalizationError / LogicExecutionError / ProtectRuntimeError / describe_effective_config`
- `create_protector(...)` 正式参数与高级参数开始分层
- `simple=True` 的失败语义进一步统一，输入校验和输出校验失败也统一收进 `ProtectRuntimeError`
- `simple=False` 的 envelope contract 已固定为：
  success=`ok/result/context`，failure=`ok/error/context`
- 用户模式错误码说明与返回结构说明已成文档

发布定位：

- `3.0.0` 是“用户模式 contract 基本成型”的版本
- 后续 `3.x` 继续以用户模式性能、体验、示例和文档打磨为主
