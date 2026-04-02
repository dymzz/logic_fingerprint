# logicfp Plugin Template

这是一个最小的独立插件仓库模板。

目标：

- 只依赖 `logicfp.plugins` 公共契约
- 不依赖 `logicfp` 私有模块
- 插件输出只补充 `result.meta`

## 目录结构

```text
template_repo/
  pyproject.toml
  README.md
  src/
    logicfp_credibility_plugin/
      __init__.py
      plugin.py
  smoke_demo.py
```

## 安装

```bash
pip install logicfp
pip install -e .
```

## 插件内容

模板里的 `BasicCredibilityPlugin` 做了三件最小事情：

- 读取 `prompt`
- 读取 `reference_materials`
- 产出 `credibility` 和 `decision`

## 在主项目里接入

Runtime 模式：

```python
from logicfp.runtime import build_demo_runtime
from logicfp_credibility_plugin import BasicCredibilityPlugin

runtime = build_demo_runtime(success_hooks=[BasicCredibilityPlugin()])
```

Decorator 模式：

```python
from logicfp import create_protector
from logicfp_credibility_plugin import BasicCredibilityPlugin

protector = create_protector(
    advanced={"success_hooks": [BasicCredibilityPlugin()]}
)
```

## 契约要求

- 只实现 `after_success`
- 返回 `HookDecision | None`
- 默认兼容契约版本 `1.0.0`

更多说明见：

- `D:\workspace\python\logic_fingerprint\documents\Tutorial\plugin-hooks.md`
