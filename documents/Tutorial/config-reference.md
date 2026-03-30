# Config Reference

This page covers three things:

- Where to put config
- How config values are merged
- What each parameter does

## 1. Default Location

Place config in your project:

```text
your_project/
  config/
    config.yaml
```

Base template:

- `config/config.yaml.example`

Example templates:

- `examples/langchain/config.yaml.example`
- `examples/openclaw/config.yaml.example`
- `examples/user_mode/config.yaml.example`

## 2. How Parameters Are Resolved

The merge order is fixed:

```text
code defaults < config/config.yaml < environment variables < explicit function arguments
```

That is:

1. Start with code defaults
2. Override with `config/config.yaml` values
3. Override with environment variables
4. Override with explicit arguments passed to the function

Entry points:

- `build_runtime_config()`
- `build_runtime_settings()`

## 3. How the Config File Is Found

Default discovery order:

1. Explicit argument `config_file=...`
2. Environment variable `LOGICFP_CONFIG_FILE`
3. Walk up from the current working directory looking for `config/config.yaml`

## 4. Recommended YAML Structure

```yaml
logicfp:
  instance_id: decorator-node
  default_source: user_function
  backend_type: memory
  probe_rate: 0.2
  probe_interval_seconds: 5
  consecutive_success_threshold: 3
  total_nodes: 1
  global_fail_threshold: 1.0
```

The library reads the `logicfp:` section. The legacy `logic_fingerprint:` section is also accepted for compatibility.

## 5. RuntimeConfig Parameters

These parameters control the protection strategy.

| YAML key | Environment variable | Default | Description |
| --- | --- | --- | --- |
| `probe_rate` | `LOGICFP_PROBE_RATE` | `0.2` | Fraction of probe requests allowed through in HALF_OPEN state |
| `probe_interval_seconds` | `LOGICFP_PROBE_INTERVAL_SECONDS` | `5.0` | Minimum time interval between probes |
| `consecutive_success_threshold` | `LOGICFP_CONSECUTIVE_SUCCESS_THRESHOLD` | `3` | Consecutive successes needed to recover from HALF_OPEN to CLOSED |
| `total_nodes` | `LOGICFP_TOTAL_NODES` | `1` | Total node count for global failure ratio calculation |
| `global_fail_threshold` | `LOGICFP_GLOBAL_FAIL_THRESHOLD` | `1.0` | Global failure ratio threshold to trigger failure consensus |

Source:

- Defaults: `src/logicfp/config/runtime_config.py`
- Merge logic: `src/logicfp/config/loader.py`

## 6. RuntimeSettings Parameters

These parameters control the runtime environment and state backend.

| YAML key | Environment variable | Default | Description |
| --- | --- | --- | --- |
| `instance_id` | `LOGICFP_INSTANCE_ID` | `decorator-node` | Current instance identifier |
| `default_source` | `LOGICFP_DEFAULT_SOURCE` | `decorator` | Default source in the request context |
| `backend_type` | `LOGICFP_BACKEND_TYPE` | `memory` | State backend type: `memory` (recommended) |
| `redis_url` | `LOGICFP_REDIS_URL` | empty | Redis connection URL (advanced, shelved) |
| `redis_decode_responses` | `LOGICFP_REDIS_DECODE_RESPONSES` | `true` | Whether the Redis client auto-decodes responses |
| `redis_key` | `LOGICFP_REDIS_KEY` | `logicfp:failed_nodes` | Redis set mode key |
| `redis_key_prefix` | `LOGICFP_REDIS_KEY_PREFIX` | `logicfp:failed_node` | Redis TTL mode key prefix |
| `redis_ttl_seconds` | `LOGICFP_REDIS_TTL_SECONDS` | `30` | Redis TTL mode expiration time for failure records |

Source:

- Defaults: `src/logicfp/config/runtime_settings.py`
- Profile defaults: `_default_runtime_settings()` in `src/logicfp/config/loader.py`
- Merge logic: `build_runtime_settings()`

## 7. Config Diagnostics

Use `diagnose_config()` to detect common configuration issues:

```python
from logicfp.config import diagnose_config, RuntimeConfig, RuntimeSettings

warnings = diagnose_config(RuntimeConfig(), RuntimeSettings())
```

Or use `describe_effective_config()` which includes diagnostics automatically:

```python
from logicfp.config import describe_effective_config

result = describe_effective_config()
print(result["diagnostics"])
```

Detected issues include:

- `REDIS_URL_IGNORED` — redis_url set but backend_type is memory
- `REDIS_URL_MISSING` — backend_type is redis but no redis_url
- `PROBE_RATE_OUT_OF_RANGE` — probe_rate not between 0.0 and 1.0
- `GLOBAL_FAIL_THRESHOLD_OUT_OF_RANGE` — threshold not between 0.0 and 1.0
- `PROBE_INTERVAL_NON_POSITIVE` — probe_interval_seconds <= 0
- `CONSECUTIVE_SUCCESS_THRESHOLD_NON_POSITIVE` — threshold <= 0
- `LEGACY_ENV_PREFIX` — legacy `LOGIC_FINGERPRINT_*` environment variables detected

## 8. Example-Specific Config

The following are not core `logicfp` parameters but example-specific sections.

### LangChain User Mode

- Template: `examples/langchain/config.yaml.example`
- Main section: `logicfp:`
- External dependencies like `OPENAI_API_KEY` are read by the model SDK, not by logicfp

### OpenClaw User Mode

- Template: `examples/openclaw/config.yaml.example`
- Main section: `logicfp:`

## 9. Minimal User Mode Config

```yaml
logicfp:
  instance_id: langchain-node
  default_source: langchain
  backend_type: memory
  probe_rate: 0.2
  probe_interval_seconds: 5
  consecutive_success_threshold: 3
```
