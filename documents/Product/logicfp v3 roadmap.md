# logicfp v3 roadmap

## 产品定位

`logicfp v3` 的主方向，不是继续扩成一个独立部署的平台服务，而是收敛成一个面向 AI 与工具调用场景的 Python 保护库。

核心判断：

- 主入口是用户模式：`from logicfp import protect, create_protector`
- 默认工作方式是本地保护，不是群体熔断
- 优先服务的场景是 `LangChain / OpenClaw / HTTP / DB / LLM / tool call`
- 工程模式继续保留，但不再作为主叙事和主投入方向

一句话版本：

`logicfp v3 = 面向 AI 调用链的用户模式保护层`

## v3 目标

### 1. 用户模式定型

把以下能力稳定成正式对外 contract：

- `protect`
- `create_protector`
- `ProtectRuntimeError`
- `logicfp.config.describe_effective_config`

要求：

- 导入路径稳定
- 返回和异常语义稳定
- 示例与 README 都优先讲用户模式

### 2. 本地优先

默认配置继续建议：

- `backend_type=memory`

原因：

- 本地保护更符合用户模式心智
- 不引入 Redis 级别的群体熔断风险
- 对单个业务服务、agent、tool call 来说更容易解释和调试

Redis 或其他共识后端：

- 保留为可选扩展
- 不作为默认推荐路径
- 不作为 v3 主要卖点

### 3. 热路径继续收缩

v3 继续优化用户模式调用开销，重点看：

- `ContextBuilder` 的 `request_id / trace_id / timestamp` 是否做懒生成
- 无模型时尽量走最短路径
- 输出封装和异常封装减少不必要对象构造
- async 路径和 sync 路径保持一致、轻量
- 默认行为保持静默，不做高频 `print`

目标不是把它做成零开销，而是让它在毫秒级业务调用里足够轻。

### 4. 可观测但默认安静

默认体验要求：

- 成功路径不刷屏
- 失败路径信息够用
- 日志和指标通过显式接入打开

重点方向：

- logger hook / metrics hook 更明确
- 保持默认静默
- 错误上下文更容易排查

### 5. 真实生态集成优先

示例和文档优先投入在这些集成面：

- LangChain runnable / chain / tool
- OpenClaw handler / agent turn
- 普通 Python 函数保护
- LLM 调用包装

示例目标是“能直接参考接入”，不是玩具业务展示。

## v3 非目标

以下方向不作为 v3 主线：

- 单独部署的 HTTP 平台化服务
- 复杂的 admin 路由和服务化运维体系
- Redis 群体熔断作为默认能力
- 以多节点共识为中心的产品叙事

这些能力可以保留，但不应消耗 v3 的主设计精力。

## 版本节奏

### 2.x 阶段

继续做：

- 用户模式 API 稳定
- 文档和示例收口
- 性能优化
- Windows 开发体验修复
- 发布链路和开发工具收紧

### 3.0 触发条件

满足以下条件后，再发 `3.0`：

- 用户模式 API 不再频繁调整
- 用户模式示例覆盖主场景
- 默认配置和错误语义稳定
- 热路径性能达到可接受水平
- 文档已经完全转为“用户模式优先”

## 建议的 v3 工作流

### P0

- 用户模式 API freeze
- 默认配置 freeze
- LangChain / OpenClaw 示例完善
- 文档结构定稿

### P1

- 用户模式性能第二轮优化
- logger / metrics hook 明确化
- 配置诊断体验继续打磨

### P2

- 工程模式兼容维护
- CLI 和 HTTP 入口维持可用
- 可选共识后端维持可选扩展地位

## 决策原则

后续遇到新需求时，优先问这 3 个问题：

1. 它是否直接提升用户模式体验？
2. 它是否更贴近 AI / tool / LLM 的真实调用链？
3. 它是否会把产品重新拉回“独立服务平台”方向？

如果第 3 条答案是“会”，默认不进 v3 主线。
