# Plugin Examples

这里放的是 `logicfp.plugins` 的最小插件示例。

适合两个场景：

- 你要在主项目里挂一个本地 hook
- 你准备把 hook 抽成独立插件仓库

建议先看：

- `documents/Tutorial/plugin-hooks.md`
- `examples/plugins/basic_success_hook.py`
- `examples/plugins/template_repo`

## 最小目标

插件默认只做一件事：

- 在成功结果上追加 `meta`

当前不建议插件：

- 修改 FSM 状态
- 直接改 Router / Executor
- 依赖 `logicfp` 私有模块

## 运行方式

这个示例本身是普通 Python 文件，展示的是接线方式，不依赖单独 CLI。

你可以直接照着把 `BasicCredibilityHook` 接到：

- `build_demo_runtime(success_hooks=[...])`
- `create_protector(advanced={"success_hooks": [...]})`

## 独立仓库模板

如果你准备把 hook 独立成单独插件仓库，可以直接从这里开始：

- `examples/plugins/template_repo/README.md`
- `examples/plugins/template_repo/pyproject.toml`
- `examples/plugins/template_repo/src/logicfp_credibility_plugin/plugin.py`
- `examples/plugins/template_repo/smoke_demo.py`
