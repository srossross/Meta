import dis
import numpy as np
from .build_graph import build_graph


def should_ignore(f, ignore_modules):
    # TODO: better handling
    if hasattr(f, "__module__"):
        return f.__module__ in ignore_modules
    return f.__class__.__module__ in ignore_modules


def functions_called(any, ignore_modules=("numpy", "torch", "jax", "jaxlib")):
    instructions = build_graph(any)
    function_calls = [
        i for i in instructions if i.opname in ["CALL_METHOD", "CALL_FUNCTION"]
    ]
    functions = {f.func() for f in function_calls}
    return [f for f in functions if not should_ignore(f, ignore_modules)]


def main():
    def one():
        return 1.0

    def func(x):
        y = np.exp(-x)
        return (one() - y) / (one() + y)

    dis.dis(func)

    print(functions_called(func))


if __name__ == "__main__":
    main()
