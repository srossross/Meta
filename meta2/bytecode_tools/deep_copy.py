from .function_transformer import FunctionTransformer
from .functions_called import functions_called


class DeepCopy(FunctionTransformer):
    def transform(self):
        functions_called(self.func)
        return super().transform()

    def visit_transform(self):
        return list(self.bytecode)


def main():
    import dis

    import numpy as np

    def one():
        return 1.0

    def func(x):
        # return abs(-1)
        y = np.exp(-x)
        return (one() - y) / abs(one() + y)

    dis.dis(func)
    for item in dir(func.__code__):
        if item.startswith("co_"):
            # print('NEW: ', item, getattr(new_func.__code__, item))
            print("OLD: ", item, getattr(func.__code__, item))

    tf = DeepCopy(func)
    new_func = tf.transform()

    print("new_func", new_func)
    print(func(1))
    dis.dis(new_func)

    print(new_func.__globals__)
    for item in dir(new_func.__code__):
        if item.startswith("co_"):
            print("NEW: ", item, getattr(new_func.__code__, item))
            print("OLD: ", item, getattr(func.__code__, item))

    print(new_func(1))


if __name__ == "__main__":
    main()
