# config 参数说明

这页单独说明三件事：

- 配置放哪里
- 配置怎么合并
- 每个参数有什么作用

## 1. 默认放哪里

用户项目和工程项目都统一放在：

```text
your_project/
  config/
    config.yaml
```

基础模板：

- `config/config.yaml.example`

示例模板：

- `examples/langchain/config.yaml.example`
- `examples/production.config.yaml.example`
- `examples/services.config.yaml.example`
- `examples/openclaw/config.yaml.example`
- `examples/business_skeleton/config.yaml.example`

## 2. 参数怎么来的

核心合并顺序固定是：

```text
代码默认值 < config/config.yaml < 环境变量 < 显式函数参数
```

也就是说：

1. 先用代码里的默认值
2. 再读项目里的 `config/config.yaml`
3. 再用环境变量覆盖
4. 最后用显式传参覆盖

对应入口是：

- `build_runtime_config()`
- `build_runtime_settings()`

## 3. 配置文件怎么找到

默认查找顺序是：

1. 显式参数 `config_file=...`
2. 环境变量 `LOGICFP_CONFIG_FILE`
3. 从当前工作目录向上查找 `config/config.yaml`

CLI 的 `logicfp start --config ...` 也是同样思路，只是额外支持常见系统目录。

## 4. 推荐的 YAML 结构

```yaml
server:
  host: 0.0.0.0
  port: 8000

app:
  demo: false

logicfp:
  instance_id: api-node-a
  default_source: api
  backend_type: memory
  probe_rate: 0.2
  probe_interval_seconds: 5
  consecutive_success_threshold: 3
  total_nodes: 1
  global_fail_threshold: 1.0
  handler_registrars:
    - your_real_package.handlers.register
```

库核心读取的是 `logicfp:` 这一节。

`server:` 和 `app:` 主要给 CLI 用。

## 5. RuntimeConfig 参数

这些参数控制保护策略本身。

| YAML key | 环境变量覆盖名 | 默认值 | 作用 | 模式 |
| --- | --- | --- | --- | --- |
| `probe_rate` | `LOGICFP_PROBE_RATE` | `0.2` | HALF_OPEN 时允许多少比例的 probe 请求通过 | 用户模式、工程模式 |
| `probe_interval_seconds` | `LOGICFP_PROBE_INTERVAL_SECONDS` | `5.0` | 相邻 probe 的最小时间间隔 | 用户模式、工程模式 |
| `consecutive_success_threshold` | `LOGICFP_CONSECUTIVE_SUCCESS_THRESHOLD` | `3` | HALF_OPEN 恢复到 CLOSED 需要连续成功多少次 | 用户模式、工程模式 |
| `total_nodes` | `LOGICFP_TOTAL_NODES` | `1` | 全局失败判断里的总节点数 | 用户模式、工程模式 |
| `global_fail_threshold` | `LOGICFP_GLOBAL_FAIL_THRESHOLD` | `1.0` | 达到多少全局失败比例后视为失败共识 | 用户模式、工程模式 |

来源：

- 默认值来自 `src/logicfp/config/runtime_config.py`
- 文件、环境变量和显式参数由 `src/logicfp/config/loader.py` 合并

## 6. RuntimeSettings 参数

这些参数控制运行环境、后端和 handler 注册方式。

| YAML key | 环境变量覆盖名 | 默认值 | 作用 | 模式 |
| --- | --- | --- | --- | --- |
| `instance_id` | `LOGICFP_INSTANCE_ID` | `decorator-node` 或 `node-a` | 当前实例标识 | 用户模式、工程模式 |
| `default_source` | `LOGICFP_DEFAULT_SOURCE` | `decorator` 或 `api` | 请求上下文里的默认来源 | 用户模式、工程模式 |
| `backend_type` | `LOGICFP_BACKEND_TYPE` | `memory` | 状态后端类型：`memory`、`redis`、`redis_ttl` | 用户模式、工程模式 |
| `handler_registrars` | `LOGICFP_HANDLER_REGISTRARS` | 空 | 要加载的 handler registrar 模块列表 | 工程模式 |
| `redis_url` | `LOGICFP_REDIS_URL` | 空 | Redis 连接地址 | 工程模式，或高级用户模式 |
| `redis_decode_responses` | `LOGICFP_REDIS_DECODE_RESPONSES` | `true` | Redis client 是否自动 decode | 工程模式，或高级用户模式 |
| `redis_key` | `LOGICFP_REDIS_KEY` | `logicfp:failed_nodes` | Redis 集合模式使用的 key | 工程模式 |
| `redis_key_prefix` | `LOGICFP_REDIS_KEY_PREFIX` | `logicfp:failed_node` | Redis TTL 模式的 key 前缀 | 工程模式 |
| `redis_ttl_seconds` | `LOGICFP_REDIS_TTL_SECONDS` | `30` | Redis TTL 模式失败记录的过期时间 | 工程模式 |

来源：

- 默认值来自 `src/logicfp/config/runtime_settings.py`
- profile 默认值由 `src/logicfp/config/loader.py` 里的 `_default_runtime_settings()` 补上
- 文件、环境变量和显式参数由 `build_runtime_settings()` 合并

## 7. CLI 参数

这些参数不是 runtime core config，而是启动器参数。

| YAML key | CLI 参数 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `server.host` | `--host` | `0.0.0.0` | HTTP 监听地址 |
| `server.port` | `--port` | `8000` | HTTP 监听端口 |
| `app.demo` | `--demo` | `false` | 是否启动 demo runtime |

CLI 文件路径优先级是：

```text
--config > 项目内 config/config.yaml > 常见系统目录
```

## 8. 示例自己的配置怎么来

下面这些不是 logicfp 核心参数，而是示例自己的 section。

### LangChain 用户模式

- 模板：`examples/langchain/config.yaml.example`
- 主要 section：`logicfp:`
- 外部依赖如 `OPENAI_API_KEY` 仍然由你使用的模型 SDK 自己读取

### Service-Wired 示例

- 模板：`examples/services.config.yaml.example`
- 主要 section：`example_services:`
- 可选环境变量覆盖：
  `EXAMPLE_BASE_STOCK`
  `EXAMPLE_DISCOUNT_RATE`
  `EXAMPLE_TAX_RATE`
  `EXAMPLE_CURRENCY`

### OpenClaw 工程示例

- 模板：`examples/openclaw/config.yaml.example`
- 主要 section：`openclaw:`
- 可选环境变量覆盖：
  `OPENCLAW_GATEWAY_URL`
  `OPENCLAW_AGENT_ID`
  `OPENCLAW_MAIN_KEY`
  `OPENCLAW_SESSION_PREFIX`
  `OPENCLAW_CHANNEL`
  `OPENCLAW_REMOTE_TOKEN_ENV`

### Business Skeleton

- 模板：`examples/business_skeleton/config.yaml.example`
- 主要 section：`business:`
- 可选环境变量覆盖：
  `BUSINESS_INVENTORY_SOURCE`
  `BUSINESS_PRICING_CURRENCY`
  `BUSINESS_STOCK_OFFSET`
  `BUSINESS_DEFAULT_DISCOUNT_RATE`

## 9. 一个最小用户模式配置

```yaml
logicfp:
  instance_id: langchain-node
  default_source: langchain
  backend_type: memory
  probe_rate: 0.2
  probe_interval_seconds: 5
  consecutive_success_threshold: 3
```

## 10. 一个最小工程模式配置

```yaml
server:
  port: 8000

app:
  demo: false

logicfp:
  instance_id: api-node-a
  default_source: api
  backend_type: memory
  handler_registrars:
    - your_real_package.handlers.register
```

如果要切 Redis，再补：

```yaml
logicfp:
  backend_type: redis_ttl
  redis_url: redis://127.0.0.1:6379/0
  redis_ttl_seconds: 30
```
