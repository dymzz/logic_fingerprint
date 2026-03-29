from logicfp import protect


@protect(simple=False)
def broken(request):
    return 1 / 0


if __name__ == "__main__":
    result = broken({})
    print(result)