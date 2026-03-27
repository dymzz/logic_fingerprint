from logic_fingerprint import protect


@protect(simple=False)
def hello(request):
    return {"msg": "hello world"}


if __name__ == "__main__":
    result = hello({})
    print(result)