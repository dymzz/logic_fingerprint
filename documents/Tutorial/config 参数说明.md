# config 参数说明

这页单独说明三件事：

- 配置放哪里
- 配置怎么合并
- 每个参数有什么作用

## 1. 默认放哪里

用户项目统一放在：

```text
your_project/
  config/
    config.yaml
```

基础模板：

- `config/config.yaml.example`

示例模板：

- `examples/langchain/config.yaml.example`
- `examples/user_mode/config.yaml.example`

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

## 4. 推荐的 YAML 结构

```yaml
logicfp:
  instance_id: decorator-node
  default_source: user_function
  backend_type: memory
  probe_rate: 0.2
  probe_interval_seconds: 5
  consecutive_success_threshold: 3
  total_nodes: 1
  global_fail_threshold: 1.0
```

库核心读取的是 `logicfp:` 这一节。

## 5. RuntimeConfig 参数

这些参数控制保护策略本身。

| YAML key | 环境变量覆盖名 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `probe_rate` | `LOGICFP_PROBE_RATE` | `0.2` | HALF_OPEN 时允许多少比例的 probe 请求通过 |
| `probe_interval_seconds` | `LOGICFP_PROBE_INTERVAL_SECONDS` | `5.0` | 相邻 probe 的最小时间间隔 |
| `consecutive_success_threshold` | `LOGICFP_CONSECUTIVE_SUCCESS_THRESHOLD` | `3` | HALF_OPEN 恢复到 CLOSED 需要连续成功多少次 |
| `total_nodes` | `LOGICFP_TOTAL_NODES` | `1` | 全局失败判断里的总节点数 |
| `global_fail_threshold` | `LOGICFP_GLOBAL_FAIL_THRESHOLD` | `1.0` | 达到多少全局失败比例后视为失败共识 |

来源：

- 默认值来自 `src/logicfp/config/runtime_config.py`
- 文件、环境变量和显式参数由 `src/logicfp/config/loader.py` 合并

## 6. RuntimeSettings 参数

这些参数控制运行环境和状态后端。

| YAML key | 环境变量覆盖名 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `instance_id` | `LOGICFP_INSTANCE_ID` | `decorator-node` 或 `node-a` | 当前实例标识 |
| `default_source` | `LOGICFP_DEFAULT_SOURCE` | `decorator` 或 `api` | 请求上下文里的默认来源 |
| `backend_type` | `LOGICFP_BACKEND_TYPE` | `memory` | 状态后端类型：`memory`、`redis`、`redis_ttl` |
| `redis_url` | `LOGICFP_REDIS_URL` | 空 | Redis 连接地址，高级用法 |
| `redis_decode_responses` | `LOGICFP_REDIS_DECODE_RESPONSES` | `true` | Redis client 是否自动 decode |
| `redis_key` | `LOGICFP_REDIS_KEY` | `logicfp:failed_nodes` | Redis 集合模式使用的 key |
| `redis_key_prefix` | `LOGICFP_REDIS_KEY_PREFIX` | `logicfp:failed_node` | Redis TTL 模式的 key 前缀 |
| `redis_ttl_seconds` | `LOGICFP_REDIS_TTL_SECONDS` | `30` | Redis TTL 模式失败记录的过期时间 |

来源：

- 默认值来自 `src/logicfp/config/runtime_settings.py`
- profile 默认值由 `src/logicfp/config/loader.py` 里的 `_default_runtime_settings()` 补上
- 文件、环境变量和显式参数由 `build_runtime_settings()` 合并

## 7. 示例自己的配置怎么来

下面这些不是 `logicfp` 核心参数，而是示例自己的 section。

### LangChain 用户模式

- 模板：`examples/langchain/config.yaml.example`
- 主要 section：`logicfp:`
- 外部依赖如 `OPENAI_API_KEY` 仍然由你使用的模型 SDK 自己读取

## 8. 一个最小用户模式配置

```yaml
logicfp:
  instance_id: langchain-node
  default_source: langchain
  backend_type: memory
  probe_rate: 0.2
  probe_interval_seconds: 5
  consecutive_success_threshold: 3
```
