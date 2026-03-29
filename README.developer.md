# logicfp Developer README

这份文档面向仓库开发者，不是最终用户说明。

## 项目定位

- 用户模式入口：`from logicfp import protect, create_protector`
- 工程模式入口：`from logicfp.engineering import create_http_app, build_production_runtime`
- CLI 入口：`logicfp start --config config/config.yaml`

## 仓库结构

```text
src/logicfp/                核心源码包
documents/Tutorial/         用户教程
examples/                   示例项目和示例配置
scripts/                    开发和发布脚本
tests/                      测试
config/                     仓库内配置模板
design/                     设计文档
```

## 本地开发

先安装项目本体：

```bash
pip install -e .
```

如果要做发布相关操作，再安装发布依赖：

```bash
pip install -e .[release]
```

## 常用命令

运行测试：

```bash
uv run pytest tests -q
```

启动本地 HTTP 服务：

```bash
logicfp start --config config/config.yaml
```

构建发布包：

```bash
python scripts/release_package.py build
python scripts/release_package.py check
python scripts/release_package.py release
```

发布到 PyPI：

```bash
python scripts/release_package.py publish --repository pypi
```

先发到 TestPyPI：

```bash
python scripts/release_package.py release --publish --testpypi
```

## 配置约定

- 用户项目标准配置路径：`your_project/config/config.yaml`
- 主 section：`logicfp:`
- 兼容旧 section：`logic_fingerprint:`
- 环境变量前缀：`LOGICFP_`
- 兼容旧环境变量前缀：`LOGIC_FINGERPRINT_`

详细配置说明见 [config 参数说明.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/config%20参数说明.md)。

## 文档分工

- [README.md](D:/workspace/python/logic_fingerprint_ai/README.md)：用户入口说明
- [protect 的用户模式与工程模式.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/protect%20的用户模式与工程模式.md)：入口模型说明
- [从 demo 到生产接入.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/从%20demo%20到生产接入.md)：接入路径
- [用户模式示例.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/用户模式示例.md)：用户模式示例
- [工程模式示例.md](D:/workspace/python/logic_fingerprint_ai/documents/Tutorial/工程模式示例.md)：工程模式示例

## 发布前检查

- 确认版本号已更新：[`src/logicfp/_version.py`](D:/workspace/python/logic_fingerprint_ai/src/logicfp/_version.py)
- 确认 `README.md` 面向用户，`README.developer.md` 面向开发者
- 运行测试
- 构建 `sdist` 和 `wheel`
- 先发 `TestPyPI`，再发正式 `PyPI`
- 发布后补 Git tag
