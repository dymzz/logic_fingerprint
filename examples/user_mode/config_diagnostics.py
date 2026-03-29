from __future__ import annotations

import json

from logicfp.config import DECORATOR_PROFILE, describe_effective_config


def main() -> None:
    description = describe_effective_config(profile=DECORATOR_PROFILE)
    print(json.dumps(description, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
