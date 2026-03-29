# protect 的用户模式与工程模式

这份文档只讲一件事：什么时候直接用 `@protect()`，什么时候进入工程接入。

统一结论：

- 用户模式：默认入口是 `@protect()`
- 高级用户模式：需要多个保护实例时，用 `create_protector()`
- 工程模式：服务化接入时，用 `logic_fingerprint.engineering`

## 1. 两种模式分别解决什么问题

### 用户模式

用户模式适合“我只想保护一个函数边界”这类场景，比如：

- LangChain `invoke()` / `ainvoke()`
- SDK 调用
- 工具调用
- 本地脚本任务
- 单个业务函数

这一层的目标是：

- 不让用户手动组装 runtime
- 不让用户关心 handler registrar
- 除配置外，把 FSM、backend、metrics、logger 都包起来

最常见写法就是：

```python
from logic_fingerprint import protect
from pydantic import BaseModel


class ReviewInput(BaseModel):
    text: str


class ReviewOutput(BaseModel):
    summary: str


@protect(input_model=ReviewInput, output_model=ReviewOutput)
def review_text(request):
    return {"summary": request.payload["text"][:20]}
```

如果你需要两个不同配置的保护器，用：

```python
from logic_fingerprint import create_protector

fast_guard = create_protector(
    instance_id="fast-lane",
    probe_rate=0.1,
)

slow_guard = create_protector(
    instance_id="slow-lane",
    probe_rate=0.3,
)
```

### 工程模式

工程模式适合“我要把它接进一个服务或平台”这类场景，比如：

- FastAPI / HTTP 服务
- OpenClaw Gateway
- ACP / tool dispatch
- 平台统一注册 handlers
- 多实例共享 Redis 状态

这一层的目标是：

- 让 handler 注册可配置
- 让 backend 可切换 `memory / redis / redis_ttl`
- 让服务启动、运维、部署入口稳定

最常见写法是：

```python
from logic_fingerprint.engineering import create_app

app = create_app()
```

然后通过配置把你的 registrar 接进去：

```yaml
logic_fingerprint:
  handler_registrars:
    - your_real_package.handlers.register
```

## 2. 配置文件放哪里

无论是用户模式还是工程模式，默认都建议把配置文件放在你的项目里：

```text
your_project/
  config/
    config.yaml
```

Logic Fingerprint 现在会按这个顺序找文件：

1. 如果设置了 `LOGIC_FINGERPRINT_CONFIG_FILE`，优先使用它
2. 否则从当前工作目录开始，优先查找 `config/config.yaml`

所以最稳妥的做法就是：

- 把文件放到你的项目 `/config/config.yaml`
- 从项目根目录启动

模板可以直接参考：

- `config/config.yaml.example`

## 3. 两种模式怎么选

优先用用户模式的情况：

- 你只想保护函数调用
- 你不想引入 HTTP 服务
- 你不需要 handler registrar
- 你更像是在“用库”

进入工程模式的情况：

- 你要把它部署成服务
- 你要统一注册多个 handlers
- 你要给平台或网关接入
- 你要管理 Redis、多实例、运维入口

一个简单判断方法：

- 保护函数：用户模式
- 保护服务边界：工程模式

## 4. 用户模式怎么读取配置

`@protect()` 和 `create_protector()` 都会走同一条配置链：

1. `build_runtime_config()`
2. `build_runtime_settings(profile="decorator")`
3. 自动发现 `config/config.yaml`
4. 再叠加进程环境变量
5. 最后叠加显式参数

用户模式默认 profile 是：

- `instance_id=decorator-node`
- `default_source=decorator`

如果你在配置文件里写了同名参数，就会覆盖这些默认值。

## 5. 工程模式怎么读取配置

`logic_fingerprint.engineering.create_app()` 和
`logic_fingerprint.engineering.build_production_runtime()` 会走工程模式配置链：

1. `build_runtime_config()`
2. `build_runtime_settings(profile="api")`
3. 自动发现 `config/config.yaml`
4. 再叠加进程环境变量
5. 最后叠加显式参数

工程模式默认 profile 是：

- `instance_id=node-a`
- `default_source=api`

如果配置里提供了 `LOGIC_FINGERPRINT_HANDLER_REGISTRARS`，production runtime 会继续加载你的业务 registrar。

## 6. 对应示例看哪里

用户模式示例入口：

- `documents/Tutorial/用户模式示例.md`

工程模式示例入口：

- `documents/Tutorial/工程模式示例.md`

从 demo 走到生产接入：

- `documents/Tutorial/从 demo 到生产接入.md`

配置参数完整说明：

- `documents/Tutorial/config 参数说明.md`

## 7. 建议的对外心智

建议你对外就这么讲：

- 普通用户先学 `@protect()`
- 需要多实例时再看 `create_protector()`
- 要接服务、平台、网关时，再看工程模式

这样入口会非常清楚，不会让用户一上来就在 `runtime / registrar / app_factory` 里迷路。
