from .not_used.function_transformer import FunctionTransformer
from .functions_called import functions_called
from .ir import IR


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
        y = np.exp(-x)
        return (1.0 - y) / abs(1.0 + y)
        # return one()

    dis.dis(func)
    # print("---")
    # dis.dis(func2)
    # for item in dir(func.__code__):
    #     if item.startswith("co_"):
    #         # print('NEW: ', item, getattr(new_func.__code__, item))
    #         print("OLD: ", item, getattr(func.__code__, item))

    ir = IR.from_function(func)

    new_func = ir.function()

    print("new_func", new_func)
    print(func(1))
    dis.dis(new_func)

    print(new_func.__globals__)
    # for item in dir(new_func.__code__):
    #     if item.startswith("co_"):
    #         print("NEW: ", item, getattr(new_func.__code__, item))
    #         print("OLD: ", item, getattr(func.__code__, item))

    print(new_func(1))


if __name__ == "__main__":
    main()
