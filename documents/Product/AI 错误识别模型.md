# AI 错误识别模型

这页定义 `logicfp` 下一阶段最值得做的识别能力：

- 哪些 AI 调用错误可以直接识别
- 推荐的错误类别表
- 推荐字段
- 第一版优先实现什么

它的目标不是做“更多错误包装”，而是让 `logicfp` 从“稍微阻挡崩溃”升级成“知道失败是什么、值不值得重试、风险有多高”。

## 0. 当前推荐抽象

当前更推荐把错误模型压成 4 个核心问题：

- 它在哪出错
  - `input`
  - `execute`
  - `dependency`
  - `output`
- 它是谁的错
  - `caller`
  - `system`
  - `dependency`
  - `environment`
- 它有多确定
  - `deterministic`
  - `heuristic`
- 系统默认怎么做
  - `allow`
  - `warn`
  - `block`
  - `retry`
  - `fallback`
  - `trip`

也就是：

- `ErrorFact`
  只保留 `stage / source / recoverability / code / message`
- `ErrorPolicy`
  只保留 `action`

像 `certainty`、`impact`、`user_effect`、`observability` 这类信息，不再当成第一层公开抽象，而是作为派生信息留在 `details` 里，供内部策略和诊断使用。

这样做的好处是：

- 对外心智明显更轻
- 失败分类和策略动作能分开演进
- 模糊判断可以按需丢给外部 AI，但不会污染基础事实层

## 1. 可以直接识别的错误

下面这些错误，大多不需要再跑一个模型判断。

只靠异常类型、HTTP 状态、响应体字段、流事件、schema 校验、tool 执行结果，就可以做第一层识别。

### 传输层

- 连接失败
- 连接超时
- 读取超时
- 断流
- 客户端取消

### 限流与配额

- 请求限流
- token 限流
- 并发限流
- 配额耗尽

### 鉴权与权限

- API key 无效
- API key 缺失
- 无权限访问模型或接口
- 组织/项目权限不足

### 请求参数

- 模型不存在
- 请求参数非法
- 上下文过长
- 输入体过大
- tool 定义非法
- 响应格式参数非法

### 上游服务

- 上游 5xx
- 上游过载
- 上游暂时不可用
- 网关错误

### AI 输出

- 明确拒答
- 输出被截断
- JSON 解析失败
- 结构化输出 schema 校验失败
- 结果为空但不允许为空

### Tool / Agent

- tool 名称不存在
- tool 参数不合法
- tool 执行超时
- tool 执行异常
- tool 返回结果不合法

## 2. 第一层不直接识别的错误

下面这些不适合放到第一版核心：

- 幻觉
- 答非所问
- 语义不完整
- 质量差但形式合法
- 推理路径错误但结果看起来正常

这些更适合后面做“规则识别”或“二次判定”，而不是混进最底层异常识别。

## 3. 推荐错误类别表

| code | category | 直接识别信号 | retryable | severity |
| --- | --- | --- | --- | --- |
| `NET_CONNECT` | `network` | DNS/TLS/connect/reset 异常 | `true` | `warn` |
| `NET_TIMEOUT` | `network` | connect/read timeout | `true` | `warn` |
| `STREAM_BROKEN` | `stream` | 已收到 chunk，但未正常结束就断开 | `true` | `warn` |
| `CLIENT_CANCELLED` | `client` | 调用方主动取消 | `false` | `noise` |
| `RATE_LIMIT_REQUEST` | `rate_limit` | 429 + request/rpm/rps 语义 | `true` | `warn` |
| `RATE_LIMIT_TOKEN` | `rate_limit` | 429 + token/tpm/throughput 语义 | `true` | `warn` |
| `QUOTA_EXHAUSTED` | `quota` | quota/credits exhausted | `false` | `block` |
| `AUTH_INVALID` | `auth` | 401 / invalid api key | `false` | `block` |
| `AUTH_FORBIDDEN` | `auth` | 403 / no permission | `false` | `block` |
| `MODEL_NOT_FOUND` | `request` | model not found | `false` | `block` |
| `INPUT_INVALID` | `request` | 参数非法 / body 非法 | `false` | `block` |
| `CONTEXT_TOO_LONG` | `request` | context length exceeded | `false` | `block` |
| `UPSTREAM_OVERLOADED` | `upstream` | 503/529/overloaded | `true` | `warn` |
| `UPSTREAM_5XX` | `upstream` | 5xx | `true` | `warn` |
| `SAFETY_REFUSAL` | `safety` | refusal / blocked reason | `false` | `warn` |
| `OUTPUT_TRUNCATED` | `output` | `finish_reason=length` | `null` | `warn` |
| `OUTPUT_PARSE_ERROR` | `output` | JSON parse fail | `false` | `warn` |
| `OUTPUT_SCHEMA_INVALID` | `output` | schema/pydantic 校验失败 | `false` | `warn` |
| `TOOL_NOT_FOUND` | `tool` | tool 名不存在 | `false` | `block` |
| `TOOL_ARGS_INVALID` | `tool` | tool args schema fail | `false` | `warn` |
| `TOOL_TIMEOUT` | `tool` | tool timeout | `true` | `warn` |
| `TOOL_EXEC_ERROR` | `tool` | tool 抛异常 | `null` | `warn` |
| `EMPTY_RESULT` | `output` | 结果为空且不允许为空 | `false` | `warn` |
| `UNKNOWN` | `unknown` | 兜底 | `null` | `warn` |

## 4. 推荐字段

### 公开稳定字段

这些字段适合以后进入 `ProtectRuntimeError` 或统一 envelope：

- `code`
- `category`
- `message`
- `retryable`
- `severity`
- `phase`
- `provider`
- `model`
- `details`

### 诊断字段

这些字段适合放进 `details`：

- `http_status`
- `provider_code`
- `provider_type`
- `provider_request_id`
- `retry_after_s`
- `finish_reason`
- `stream_started`
- `received_chunks`
- `input_tokens`
- `output_tokens`
- `max_output_tokens`
- `tool_name`
- `tool_call_id`
- `schema_name`
- `raw_error_type`
- `raw_error_message`

## 5. 推荐 phase 枚举

- `prepare`
- `request`
- `stream`
- `parse`
- `validate`
- `tool`
- `postprocess`

## 6. 第一版最值得先做的 8 个

第一版优先实现下面这些：

- `NET_TIMEOUT`
- `STREAM_BROKEN`
- `RATE_LIMIT_REQUEST`
- `RATE_LIMIT_TOKEN`
- `AUTH_INVALID`
- `UPSTREAM_OVERLOADED`
- `OUTPUT_SCHEMA_INVALID`
- `TOOL_TIMEOUT`

这 8 个已经足够让 `logicfp` 从“错误包装”变成“AI 调用识别 + 保护层”。

## 7. 当前建议

实现顺序建议是：

1. 先把错误表和字段固定成内部模型
2. 再把 provider 异常映射到这些 code
3. 最后再决定哪些字段进入公开 API

这样可以先增强识别能力，又不会太早把新结构冻成长期包袱。

## 8. 可选 API 模型识别

如果规则识别不够，也可以按需加一层“API 模型识别”。

当前更推荐的接法不是把模型调用硬编码进核心库，而是通过高级参数传一个分类函数：

```python
protector = create_protector(
    advanced={
        "ai_error_classifier": my_classifier,
    }
)
```

这个分类函数会收到一份标准化输入，例如：

- `exception_type`
- `exception_module`
- `message`
- `provider`
- `http_status`
- `provider_code`
- `tool_name`

它返回的结果只需要给出：

- `code`
- 可选的 `provider`
- 可选的 `model`
- 可选的 `details`

当前行为是：

- 规则识别优先
- 只有规则识别失败时，才会调用 `ai_error_classifier`
- 分类结果会进入 `details["ai_error"]`

这样能保留默认轻量路径，同时允许用户按需接入 API 模型做更细的识别。


