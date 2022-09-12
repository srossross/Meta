from .visitor import ByteCodeVisitor
import numpy as np
import dis

def visit_bin_op(func):
    def _visit_bin_op(self, op):
        lhs = self.pop()
        rhs = self.pop()
        f = lambda: func(lhs(), rhs())
        return self.push(f)
    return _visit_bin_op


def visit_unary_op(func):
    def _visit_unary_op(self, op):
        val = self.pop()
        f = lambda: func(val())
        return self.push(f)
    return _visit_unary_op


class BuildGraph(ByteCodeVisitor):
    """
    Mutate instructions to to add exec to each
    """
    def __init__(self, instructions, globals, stores) -> None:
        self.bytecode = list(instructions)
        self.globals = globals
        self.stack = []
        self.stores = stores

    def post_visit(self, op, val):
        op.exec = val

    def push(self, val):
        self.stack.append(val)
        return val

    def pop(self):
        return self.stack.pop()

    def visit_return_value(self, op):
        val = self.pop()
        return self.push(lambda: val())

    def visit_load_global(self, op):
        return self.push(lambda: self.globals[op.argval])

    def visit_load_method(self, op):
        klass = self.pop()
        return self.push(lambda: getattr(klass(), op.argval))

    def visit_load_fast(self, op):
        val = self.stores[op.argval]
        return self.push(val)

    def visit_load_const(self, op):
        return self.push(lambda: op.argval)

    def visit_store_fast(self, op):
        value = self.pop()
        self.stores[op.argval] = value

    def visit_call_method(self, op):
        args = [self.pop() for _ in range(op.argval)][::-1]
        func = self.pop()
        op.func = func
        return self.push(lambda: func()(*[arg() for arg in args]))

    visit_binary_true_divide = visit_bin_op(lambda x, y: x / y)
    visit_binary_add = visit_bin_op(lambda x, y: x + y)
    visit_binary_subtract = visit_bin_op(lambda x, y: x - y)

    visit_unary_negative = visit_unary_op(lambda x: -x)


def build_graph(func):
    bytecode = list(dis.Bytecode(func))
    bg = BuildGraph(bytecode, func.__globals__, {'x': lambda: 1})
    bg.visit_forward()

    return bytecode


def main():

    def func(x):
        y = np.exp(-x)
        return (1.0 - y) / (1.0 + y)

    dis.dis(func)

    bytecode = list(dis.Bytecode(func))
    bg = BuildGraph(bytecode, func.__globals__, {'x': lambda: 1})
    bg.visit_forward()

    instr = bytecode[-1]
    print(instr.exec())
    print(bytecode)


if __name__ == "__main__":
    main()
