from logic_fingerprint import protect


@protect()
def hello(request):
    return {"msg": "hello world"}


if __name__ == "__main__":
    print(hello({}))