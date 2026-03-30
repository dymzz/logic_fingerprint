"""
Real Anthropic call protected by @protect().

Requirements:
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...

Shows:
    - success path with real LLM response
    - AI error fields (ai_error_code, retryable, provider, severity)
    - retry decision based on retryable flag
"""
from __future__ import annotations

import os
import json

from logicfp import protect
from logicfp.user_mode import ProtectRuntimeError


@protect(simple=False)
def ask_anthropic(request):
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=request.payload.get("model", "claude-sonnet-4-20250514"),
        max_tokens=200,
        messages=[{"role": "user", "content": request.payload["prompt"]}],
    )
    return {
        "answer": response.content[0].text.strip(),
        "model": response.model,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    }


@protect(simple=True)
def ask_anthropic_simple(request):
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=request.payload.get("model", "claude-sonnet-4-20250514"),
        max_tokens=200,
        messages=[{"role": "user", "content": request.payload["prompt"]}],
    )
    return {
        "answer": response.content[0].text.strip(),
        "model": response.model,
    }


def main():
    prompt = "Explain what a circuit breaker pattern is in two sentences."

    print("=" * 60)
    print("1. simple=False (envelope mode)")
    print("=" * 60)

    result = ask_anthropic(payload={"prompt": prompt})
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

    if not result["ok"]:
        error = result["error"]
        print(f"\n  ai_error_code : {error['ai_error_code']}")
        print(f"  retryable     : {error['retryable']}")
        print(f"  provider      : {error['provider']}")
        print(f"  severity      : {error['severity']}")

        if error["retryable"]:
            print("  -> worth retrying")
        else:
            print("  -> do NOT retry")

    print()
    print("=" * 60)
    print("2. simple=True (exception mode)")
    print("=" * 60)

    try:
        result = ask_anthropic_simple(payload={"prompt": prompt})
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except ProtectRuntimeError as exc:
        print(f"  code          : {exc.code}")
        print(f"  ai_error_code : {exc.ai_error_code}")
        print(f"  retryable     : {exc.retryable}")
        print(f"  provider      : {exc.provider}")
        print(f"  severity      : {exc.severity}")
        print(f"  message       : {exc}")


if __name__ == "__main__":
    main()
