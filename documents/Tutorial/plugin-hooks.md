# Plugin Hooks

`logicfp.plugins` 提供给插件仓库使用的最小公开契约。

当前只开放一个成功后 hook：

- `SuccessHook.after_success(request, result)`

设计边界：

- 默认 `fail_open`
- 插件只允许补充 `result.meta`
- 插件不直接操作 FSM、Executor、Router
- 契约版本由 `SUPPORTED_HOOK_CONTRACT_VERSION` 管理

## Public API

从 `logicfp.plugins` 可直接导入：

- `SuccessHook`
- `HookRequest`
- `HookResult`
- `HookDecision`
- `CredibilityResult`
- `ActionRisk`
- `DecisionType`
- `FinalDecision`
- `SUPPORTED_HOOK_CONTRACT_VERSION`

## Hook Request

`HookRequest` 给插件的输入字段尽量保持稳定：

- `request_id`
- `prompt`
- `raw_output`
- `reference_materials`
- `action_risk`
- `decision_type`
- `metadata`

如果业务 handler 自己的 input schema 会过滤 payload 字段，插件仍然会读取原始构建请求里的这些插件提示字段，不依赖 handler 的校验后 payload。

## Hook Result

`HookResult` 表示成功执行后的结果快照：

- `ok`
- `output`
- `meta`

插件应只向 `meta` 写入附加信息。

推荐写入：

- `meta["credibility"]`
- `meta["decision"]`
- `meta["plugin_decisions"]`

## Runtime Integration

HTTP / runtime 模式：

```python
from logicfp.runtime import build_demo_runtime
from logicfp.plugins import SuccessHook


class MyHook(SuccessHook):
    def after_success(self, request, result):
        ...


runtime = build_demo_runtime(success_hooks=[MyHook()])
```

用户模式 / decorator 模式：

```python
from logicfp import create_protector

protector = create_protector(
    advanced={
        "success_hooks": [MyHook()],
        "plugin_failure_mode": "fail_open",
    }
)
```

## Failure Mode

支持两种插件失败策略：

- `fail_open`
  插件异常被吞掉，主流程继续成功返回
- `fail_closed`
  插件异常进入错误返回，错误 stage 为 `plugin`

默认值是 `fail_open`。

## Example

```python
from logicfp.plugins import (
    CredibilityResult,
    FinalDecision,
    HookDecision,
    SuccessHook,
)


class CredibilityHook(SuccessHook):
    def after_success(self, request, result):
        return HookDecision(
            credibility=CredibilityResult(
                confidence=0.82,
                risk_level="low",
                verdict="allow",
                reasons=["reference coverage is sufficient"],
            ),
            final_decision=FinalDecision.ALLOW,
            plugin_meta={"plugin_version": "0.1.0"},
        )
```

## Output Shape

当 hook 生效后，结果里通常会多出：

```python
{
    "meta": {
        "credibility": {
            "confidence": 0.82,
            "risk_level": "low",
            "verdict": "allow",
            "reasons": ["reference coverage is sufficient"],
        },
        "decision": "allow",
        "plugin_decisions": [
            {
                "hook": "CredibilityHook",
                "final_decision": "allow",
                "plugin_meta": {"plugin_version": "0.1.0"},
            }
        ],
    }
}
```

## Reference

- Runtime hook tests: `D:\workspace\python\logic_fingerprint\tests\test_plugin_hooks.py`
- Contracts: `D:\workspace\python\logic_fingerprint\src\logicfp\plugins\contracts.py`
- Runner: `D:\workspace\python\logic_fingerprint\src\logicfp\plugins\runner.py`
- External repo template: `D:\workspace\python\logic_fingerprint\examples\plugins\template_repo`
