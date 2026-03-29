from logicfp import protect


@protect()
def ask_local_llm(request):
    import json
    import urllib.request

    payload = {
        "model": "gemma3:1b",
        "prompt": request.payload["prompt"],
        "stream": False,
    }

    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    return {"answer": body["response"].strip()}


if __name__ == "__main__":
    result = ask_local_llm({
        "prompt": "Explain circuit breaker in one sentence."
    })
    print(result)