# Logic Fingerprint System · v1.0

首个稳定版，补上：
1. 统一错误响应协议
2. handler 输入 schema 校验
3. handler 输出 schema 校验

## v1.0 fixed

- 修复：输入校验异常现在会被统一错误协议捕获，不再直接把异常抛出到测试层。
- 修复：Prometheus 指标恢复输出 `success_requests` / `failed_requests` 等计数器。
