"""
Real OpenAI call protected by @protect().

Requirements:
    pip install openai
    export OPENAI_API_KEY=sk-...

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
def ask_openai(request):
    import openai

    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=request.payload.get("model", "gpt-4o-mini"),
        messages=[{"role": "user", "content": request.payload["prompt"]}],
        max_tokens=200,
    )
    return {
        "answer": response.choices[0].message.content.strip(),
        "model": response.model,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
        },
    }


@protect(simple=True)
def ask_openai_simple(request):
    import openai

    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=request.payload.get("model", "gpt-4o-mini"),
        messages=[{"role": "user", "content": request.payload["prompt"]}],
        max_tokens=200,
    )
    return {
        "answer": response.choices[0].message.content.strip(),
        "model": response.model,
    }


def main():
    prompt = "Explain what a circuit breaker pattern is in two sentences."

    print("=" * 60)
    print("1. simple=False (envelope mode)")
    print("=" * 60)

    result = ask_openai(payload={"prompt": prompt})
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
        result = ask_openai_simple(payload={"prompt": prompt})
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
