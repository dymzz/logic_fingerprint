# Business Skeleton

这是一个可复制的高级骨架，不是默认入口，也不是最终包目录。

默认公开入口仍然是：

- `from logicfp import protect`
- `from logicfp import create_protector`

如果你只是想接入 `logicfp`，优先先看：

- [documents/Tutorial/用户模式快速接入.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/用户模式快速接入.md)
- [documents/Tutorial/用户模式示例.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/用户模式示例.md)

## Included Files

- `settings.py`
- `repositories/`
- `services/`
- `handlers/register.py`
- `config.yaml.example`

logicfp 会加载的 registrar 是：

```text
examples.business_skeleton.handlers.register
```

## Config

复制模板到你的项目：

```text
your_project/config/config.yaml
```

模板文件：

- `examples/business_skeleton/config.yaml.example`

这个模板里分成两块：

- `logicfp:`：库的运行配置
- `business:`：你自己的业务配置

## Registered Handlers

- `inventory_lookup`
- `order_quote`

## How To Use It

如果你准备开始自己的包结构，最推荐的方式是：

1. 复制这个目录结构
2. 把 `examples.business_skeleton` 改成你的真实包名
3. 把 `business:` 这一节扩成你自己的 settings
4. 把 repository/service/handler 逐步替换成真实业务实现

这套骨架更适合仓库内高级参考，不再作为默认公开接入路径。
