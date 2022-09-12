import sys
from meta.asttools.visitors.pysourcegen import python_source

# def F():
#     pass


# code = type(F.__code__)
# from


def print_function_recursive(
    func, ignore=None, ignore_modules=("numpy", "torch", "jax"), file=sys.stdout
):
    file.write(f"{func.__name__}():")
    func
    python_source()
