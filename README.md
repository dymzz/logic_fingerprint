# Logic Fingerprint (logicfp)

`logicfp` is the unified package, CLI, and documentation name for this project.

## Install

```bash
pip install logicfp
```

## Import

```python
from logicfp import protect, create_protector
from logicfp.engineering import create_app
```

## CLI

```bash
logicfp start --config config/config.yaml
```

## Config

Put your project config at:

```text
your_project/config/config.yaml
```

Use `logicfp:` as the main YAML section name. Older `logic_fingerprint:` configs are still accepted for compatibility.
