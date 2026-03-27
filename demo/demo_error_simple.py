from logic_fingerprint import protect


@protect()
def broken(request):
    return 1 / 0


if __name__ == "__main__":
    try:
        result = broken({})
        print(result)
    except Exception as e:
        print(type(e).__name__, str(e))