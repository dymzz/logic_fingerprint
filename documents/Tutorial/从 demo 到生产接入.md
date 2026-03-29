# 从 Demo 到生产接入

这份文档给出一条最短可落地路径，把当前项目从：

- `demo handler`
- `examples registrar`
- `memory backend`

推进到：

- 真实业务 handler
- 配置驱动注册
- 可切换 `memory / redis / redis_ttl`
- 可部署的 HTTP 服务

这里建议同时记住两个对外模式：

- 用户模式：以 `@protect()` 为主入口
- 工程模式：以 `logic_fingerprint.engineering` / registrar / runtime 为主入口

单独教程看这里：

- `documents/Tutorial/protect 的用户模式与工程模式.md`
- `documents/Tutorial/config 参数说明.md`

## 1. 先分清三层运行方式

当前项目已经有三种清晰入口：

对外推荐导入路径：

- 用户模式：`from logic_fingerprint import protect, create_protector`
- 工程模式：`from logic_fingerprint.engineering import create_app, build_production_runtime`

1. Demo 运行时
   文件：
   `src/logic_fingerprint/runtime.py`
   `build_demo_runtime(...)`

   用途：
   本地演示、接口联调、行为观察。

2. Production 运行时
   文件：
   `src/logic_fingerprint/runtime.py`
   `build_production_runtime(...)`

   用途：
   不默认注册 demo handlers，只加载 builtin registrar 和配置里的业务 registrar。

3. HTTP 启动入口
   文件：
   `src/logic_fingerprint/app_factory.py`
   `create_app()`

   用途：
   生产默认入口。模块级 `app = create_app()` 现在默认就是 production 模式。

补充理解：

- 如果你是在函数边界包住 LangChain、SDK、工具调用，这属于用户模式。
- 如果你是在服务边界接 OpenClaw、Gateway、ACP、HTTP handler，这属于工程模式。

## 2. 生产接入的推荐目录

建议把你自己的业务 handler 放到独立模块，不要直接改 `runtime.py`。

推荐结构：

```text
src/your_real_package/
  handlers/
    order_handlers.py
    inventory_handlers.py
    register.py
  services/
    pricing_service.py
    inventory_service.py
  repositories/
    inventory_repository.py
  settings.py
```

其中最关键的是提供一个 registrar 模块，例如：

```python
from logic_fingerprint.handler_registry import HandlerRegistry
from your_real_package.handlers.order_handlers import build_order_quote_handler
from your_real_package.handlers.inventory_handlers import build_inventory_lookup_handler
from your_real_package.services.pricing_service import PricingService
from your_real_package.services.inventory_service import InventoryService
from your_real_package.repositories.inventory_repository import InventoryRepository
from your_real_package.settings import load_settings


def register_handlers(handler_registry: HandlerRegistry) -> None:
    settings = load_settings()

    inventory_repository = InventoryRepository(dsn=settings.inventory_dsn)
    inventory_service = InventoryService(repository=inventory_repository)
    pricing_service = PricingService(base_url=settings.pricing_base_url)

    handler_registry.register(
        "inventory_lookup",
        build_inventory_lookup_handler(inventory_service),
    )
    handler_registry.register(
        "order_quote",
        build_order_quote_handler(pricing_service),
    )
```

然后通过配置文件或环境变量接进系统：

```yaml
logic_fingerprint:
  handler_registrars:
    - your_real_package.handlers.register
```

推荐把这些参数放到你项目里的：

```text
config/config.yaml
```

## 3. 推荐的演进顺序

### 第一步：先从 examples 复制模板

建议起步不要从零写，直接复制其中一个：

- 纯 registrar 模板：
  `examples/production_handlers.py`
- 带依赖装配模板：
  `examples/production_services.py`
- LangChain 用户模式模板：
  `examples/langchain/user_mode.py`
- OpenClaw 工程模式模板：
  `examples/openclaw/register_handlers.py`

如果你的业务 handler 需要数据库、RPC、HTTP client、缓存，直接从
`production_services.py` 这条路径起步。

### 第二步：把 demo 逻辑替换成真实业务 handler

你的目标不是改 `create_app()`，而是实现自己的：

- `register_handlers(handler_registry)`
- 输入模型
- 输出模型
- 服务依赖装配

最小 handler 约定：

```python
def register_handlers(handler_registry: HandlerRegistry) -> None:
    handler_registry.register(
        "your_handler_name",
        your_handler,
        input_model=YourInputModel,
        output_model=YourOutputModel,
    )
```

### 第三步：先跑 memory backend

先用：

```yaml
logic_fingerprint:
  backend_type: memory
```

先把这几件事验证通：

- handler 能注册成功
- `/handlers` 能看到业务 handler
- `/execute_handler` 能跑通
- 输入输出校验符合预期
- 错误码和返回 envelope 符合预期

### 第四步：再切 redis / redis_ttl

当单机逻辑跑稳后，再切共享状态：

```yaml
logic_fingerprint:
  backend_type: redis_ttl
  redis_url: redis://127.0.0.1:6379/0
  redis_key_prefix: logic_fingerprint:failed_node
  redis_ttl_seconds: 30
```

如果需要集合型失败节点记录，可以切：

```yaml
logic_fingerprint:
  backend_type: redis
  redis_url: redis://127.0.0.1:6379/0
  redis_key: logic_fingerprint:failed_nodes
```

## 4. 生产环境最小配置

最小可运行配置：

```yaml
server:
  port: 8000

app:
  demo: false

logic_fingerprint:
  instance_id: prod-node-a
  default_source: api
  backend_type: memory
  handler_registrars:
    - your_real_package.handlers.register
```

推荐补齐的运行参数：

```yaml
logic_fingerprint:
  probe_rate: 0.2
  probe_interval_seconds: 5
  consecutive_success_threshold: 3
  total_nodes: 3
  global_fail_threshold: 0.5
```

如果要切 Redis：

```yaml
logic_fingerprint:
  redis_url: redis://127.0.0.1:6379/0
  redis_decode_responses: true
```

## 5. 启动方式

推荐直接用 CLI：

```powershell
logicfingerprint start --port 8000 --config config/config.yaml
```

如果不传 `--config`，CLI 会先找项目里的：

```text
config/config.yaml
```

再去常见系统目录里找，比如：

- `/etc/logic_fingerprint/*.yaml`
- `%ProgramData%\\logic_fingerprint\\*.yaml`

从仓库根目录启动：

```powershell
$env:PYTHONPATH=".;src"
uv run logicfingerprint start --config config/config.yaml --port 8000
```

这条启动链会经过：

1. `create_app()`
2. `build_production_runtime()`
3. `build_runtime_settings()`
4. `load_handler_registrars(...)`
5. `register_handlers(handler_registry)`

## 6. 接入真实业务时的建议写法

建议把 handler 写成“薄入口”，把业务逻辑放进 service。

不建议：

```python
def register_handlers(handler_registry):
    def big_handler(request):
        # 数据库、HTTP、计算、格式化全部写这里
        ...
```

建议：

```python
def build_order_quote_handler(service):
    async def handler(request):
        result = await service.quote(
            order_id=request.payload["order_id"],
            items=request.payload["items"],
        )
        return {"ok": True, "data": result}

    return handler
```

这样后面做测试、替换依赖、拆模块都更轻松。

## 7. 上线前必须补的几项

这几项建议至少作为 P0：

1. 鉴权
   当前 `/force_fail`、`/move_half_open`、`/metrics` 仍应加权限控制。

2. 真实日志输出
   当前默认还是 print 风格 logger，建议替换成结构化日志。

3. Redis 依赖安装与连通性检查
   如果启用 `redis` 或 `redis_ttl`，部署环境必须安装 `redis` Python 包，并在启动前验证连通性。

4. 健康检查增强
   `/healthz` 建议加 backend 可用性检查，不只返回状态字符串。

5. 压测和故障演练
   至少验证：
   - OPEN -> HALF_OPEN -> CLOSED
   - 多实例共享失败状态
   - 业务 handler 超时 / 异常 / 空返回

## 8. 建议的落地节奏

推荐按这个顺序推进：

1. 从 `examples/production_services.py` 复制出你的 registrar 模块
2. 接 1 个真实 handler，先用 `memory`
3. 跑通 `/handlers` 和 `/execute_handler`
4. 增加输入输出模型和集成测试
5. 切到 `redis_ttl`
6. 补鉴权、日志、健康检查
7. 再接更多业务 handler

## 9. 对应样板文件

可以直接参考这些文件：

- `examples/production_handlers.py`
- `examples/production_services.py`
- `examples/langchain/user_mode.py`
- `examples/openclaw/register_handlers.py`
- `examples/langchain/README.md`
- `examples/openclaw/README.md`
- `examples/business_skeleton/handlers/register.py`
- `examples/business_skeleton/settings.py`
- `examples/business_skeleton/repositories/inventory_repository.py`
- `examples/business_skeleton/services/pricing_service.py`
- `examples/run_demo.ps1`
- `examples/run_services_demo.ps1`
- `examples/invoke_demo.ps1`
- `examples/invoke_services_demo.ps1`

如果你已经准备开始自己的业务目录，不想再从单文件示例改起，优先从：

- `examples/business_skeleton/`

开始复制。

## 10. 一句话迁移策略

先复制 `examples/production_services.py` 做你的业务 registrar，先用 `memory` 跑通，再切 `redis_ttl`，最后补鉴权、日志和健康检查。
