# logicfp Developer README

This document is for repository developers, not end users.

One-liner:

`logicfp = AI-era call protection layer`


## Project Positioning

- User mode entry: `from logicfp import protect, create_protector`
- No CLI / HTTP service entry points

## Repository Structure

```text
src/logicfp/                Core source package
documents/Tutorial/         User tutorials
documents/Product/          Product roadmap documents
examples/                   Example projects and config templates
scripts/                    Dev and release scripts
tests/                      Tests
config/                     In-repo config templates
design/                     Design docs (not in Git)
```

## Local Development

Install the package in editable mode:

```bash
pip install -e .
```

For release operations, also install release dependencies:

```bash
pip install -e .[release]
```

## Local Cache and Temp Directories

Recommended: enable in-repo cache and temp directories to avoid Windows ACL/cleanup issues when `uv` or `pytest` fall back to system directories.

PowerShell:

```powershell
. .\scripts\dev_env.ps1
```

This sets:

- `UV_CACHE_DIR=.uv-cache`
- `TMP=.tmp`
- `TEMP=.tmp`
- `pytest --basetemp=.pytest_tmp/basetemp`

Details:

- `uv` cache dir is pinned to the project via `tool.uv.cache-dir` in `pyproject.toml`
- `pytest` temp dir is pinned via `tool.pytest.ini_options.addopts` in `pyproject.toml`
- `dev_env.ps1` redirects system-level `TMP/TEMP` into the repo

## Common Commands

Run tests:

```bash
uv run pytest tests -q
```

Build release packages:

```bash
python scripts/release_package.py build
python scripts/release_package.py check
python scripts/release_package.py release
```

Publish to PyPI:

```bash
python scripts/release_package.py publish --repository pypi
```

Publish to TestPyPI first:

```bash
python scripts/release_package.py release --publish --testpypi
```

## GitHub Actions Publishing

This repository includes a GitHub Actions workflow at `.github/workflows/publish.yml`.

- Manual TestPyPI publish:
  run the `Publish Python package` workflow and choose `testpypi`
- Automatic PyPI publish:
  push a Git tag like `v3.3.0`
- Manual PyPI publish:
  run the same workflow and choose `pypi`

The workflow builds and validates the package with the existing release script:

```bash
python scripts/release_package.py build
python scripts/release_package.py check
```

Publishing itself is handled by PyPI Trusted Publishing in GitHub Actions, so you do not need to store a long-lived PyPI API token in GitHub secrets.

Before the workflow can publish, configure trusted publishers on both TestPyPI and PyPI:

1. TestPyPI project:
   add a GitHub Actions trusted publisher for this repository and workflow file `.github/workflows/publish.yml`, and set the environment name to `testpypi`
2. PyPI project:
   add the same trusted publisher for `.github/workflows/publish.yml`, and set the environment name to `pypi`
3. GitHub repository environments:
   create `testpypi` and `pypi`
4. Recommended:
   require manual approval for the `pypi` environment before release jobs can continue

Recommended release flow:

1. Run the workflow manually with `testpypi`
2. Verify installation from TestPyPI
3. Push a version tag like `v3.3.0` to publish to PyPI

## 配置约定

- 用户项目标准配置路径：`your_project/config/config.yaml`
- 主 section：`logicfp:`
- 兼容旧 section：`logic_fingerprint:`
- 环境变量前缀：`LOGICFP_`
- 兼容旧环境变量前缀：`LOGIC_FINGERPRINT_`
- 用户模式默认建议 `backend_type=memory`
  对 `LangChain / OpenClaw / DB / LLM` 这类调用，优先做本地保护；不要把 Redis 群体熔断当成默认方案

详细配置说明见 [config 参数说明.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/config%20参数说明.md)。

## 文档分工

- [README.md](D:/workspace/python/logic_fingerprint_ai/README.md)：用户入口说明
- [AI 错误识别模型.md](D:/workspace/python/logic_fingerprint_ai/documents/Product/AI%20错误识别模型.md)：AI 调用错误识别方向
- [logicfp v3 roadmap.md](D:/workspace/python/logic_fingerprint_ai/documents/Product/logicfp%20v3%20roadmap.md)：下个大版本方向
- [protect 的用户模式与工程模式.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/protect%20的用户模式与工程模式.md)：入口模型说明
- [用户模式返回结构说明.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/用户模式返回结构说明.md)：`simple=False` 的 envelope contract
- [用户模式示例.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/用户模式示例.md)：用户模式示例
- [用户模式错误码说明.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/用户模式错误码说明.md)：用户模式错误码与失败语义

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

- 确认版本号已更新：[src/logicfp/_version.py](D:/workspace/python/logic_fingerprint_ai/src/logicfp/_version.py)
- 确认 `README.md` 面向用户，`README.developer.md` 面向开发者
- 运行测试
- 构建 `sdist` 和 `wheel`
- 先发 `TestPyPI`，再发正式 `PyPI`
- 发布后补 Git tag

## 3.0.0 发布说明

`3.0.0` 的核心变化，是把用户模式的长期 contract 开始定下来。

本次版本重点包括：

- 用户模式公开入口收敛到：
  `protect / create_protector / ErrorCode / NormalizationError / LogicExecutionError / ProtectRuntimeError / describe_effective_config`
- `create_protector(...)` 正式参数与高级参数开始分层
- `simple=True` 的失败语义进一步统一，输入校验和输出校验失败也统一收进 `ProtectRuntimeError`
- `simple=False` 的 envelope contract 已固定为：
  success=`ok/result/context`，failure=`ok/error/context`
- 用户模式错误码说明与返回结构说明已成文档
- CLI / HTTP 服务入口已从公开产品面收回

发布定位：

- `3.0.0` 是“用户模式 contract 基本成型”的版本
- 后续 `3.x` 继续以用户模式性能、体验、示例和文档打磨为主

## 3.1.0 更新说明

`3.1.0` 的核心变化，是把公开产品面彻底收口到用户模式。

本次版本重点包括：

- 移除 `fastapi` / `uvicorn` 基础依赖
- 删除 CLI 与 HTTP 服务入口
- 删除公开的工程模式文档入口和对应示例
- 根包继续只保留：
  `protect / create_protector`
- README、教程、examples 全部改成围绕 `@protect()` 组织

版本定位：

- `3.1.0` 是“用户模式-only 收口完成”的版本
- 后续 `3.x` 继续专注用户模式性能、体验、错误语义和示例质量

## 3.2.0 更新说明

`3.2.0` 的核心变化，是把用户模式里的错误归一化和动作覆写能力做成稳定的高级接口。

本次版本重点包括：

- 错误结构收口到 4 个核心问题：
  `stage / source / recoverability / action`
- `simple=False` 的失败 envelope 里，现在稳定带出：
  `error_fact` 和 `error_policy`
- 新增用户模式读取接口：
  `get_error_fact / get_error_policy / get_error_action / get_error_details`
- 新增 `error_action_resolver` 高级入口
  - 输入 contract：`fact / default_action`
  - 兼容保留：`default_policy`
  - 最小返回：`{\"action\": \"...\"}`
- `error_policy_resolver` 保留兼容，但进入弃用路径
- 用户模式示例和速查文档补齐：
  - `action_resolver.py`
  - 用户模式速查
  - 错误码说明 / 返回结构 / 快速接入 同步到新 contract

版本定位：

- `3.2.0` 是"用户模式错误模型与动作覆写 contract 基本成型"的版本
- 后续 `3.x` 可以继续围绕 AI 错误识别、轻量策略和用户体验打磨

## 3.3.0 更新说明

`3.3.0` 的核心变化，是把 AI 错误识别测试覆盖补齐、新增 OpenClaw 集成示例、明确 metrics hook 接口、增强配置诊断能力。

本次版本重点包括：

- AI 错误识别 provider 测试全面补齐：
  - Anthropic：`AUTH_INVALID` / `AUTH_FORBIDDEN` / `QUOTA_EXHAUSTED` / `MODEL_NOT_FOUND` / `CONTEXT_TOO_LONG` / `RATE_LIMIT_TOKEN` / `UPSTREAM_5XX`
  - LangChain：`TOOL_NOT_FOUND`
  - Generic transport：`NET_TIMEOUT` / `NET_CONNECT`
  - Generic output：`OUTPUT_SCHEMA_INVALID` / `EMPTY_RESULT`
- Bug fix：`_is_safety_refusal` 排除 `ConnectionError`/`OSError`，防止 "connection refused" 误判为 safety refusal
- 新增 generic recognizer：`_is_output_schema_invalid` / `_is_empty_result`
- 新增 OpenClaw 集成示例：
  - `examples/openclaw/user_mode.py`（sync + async guard）
  - `examples/openclaw/README.md` / `config.yaml.example`
  - `tests/test_openclaw_examples.py`（4 个测试）
- 新增 `MetricsHook` 接口：
  - `logicfp.infra.metrics`：`MetricsHook` / `MetricEvent` / `NullMetricsHook` / `PrintMetricsHook`
  - `Protector` 接受 `metrics_hook` 参数（通过 `advanced={"metrics_hook": ...}`）
  - sync + async 路径均 emit `protect.total` / `protect.success` / `protect.failure` / `protect.blocked`
- 新增 `diagnose_config()`：
  - 检测 `REDIS_URL_IGNORED` / `REDIS_URL_MISSING`
  - 检测 `PROBE_RATE_OUT_OF_RANGE` / `GLOBAL_FAIL_THRESHOLD_OUT_OF_RANGE`
  - 检测 `PROBE_INTERVAL_NON_POSITIVE` / `CONSECUTIVE_SUCCESS_THRESHOLD_NON_POSITIVE`
  - 检测 `LEGACY_ENV_PREFIX` 使用
  - `describe_effective_config()` 输出新增 `diagnostics` 字段
- 热路径微基准测试：
  - 无模型：~11µs/call（p50=10.6µs, p95=16.3µs, 88k ops/sec）
  - 含 pydantic 校验：~16µs/call（p50=15.0µs, p95=25.9µs, 61k ops/sec）
- 开发工具修复：
  - `conftest.py` 增加 robust basetemp cleanup（修复 Windows PermissionError）
  - `pytest` 加入 `dependency-groups.dev`（修复 `uv run pytest`）

版本定位：

- `3.3.0` 是"AI 错误识别全面可测 + 可观测性基础设施就位"的版本
- 后续 `3.x` 可以继续围绕 AI 错误识别策略、metrics 实际接入和用户体验打磨
