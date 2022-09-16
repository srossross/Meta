import inspect
import dis

import numpy as np

from .visitor import ByteCodeVisitor


def visit_bin_op(func):
    def _visit_bin_op(self, op):
        lhs = self.pop()
        rhs = self.pop()
        f = lambda: func(lhs(), rhs())
        return self.push(f, lhs.static and rhs.static)

    return _visit_bin_op


def visit_unary_op(func):
    def _visit_unary_op(self, op):
        val = self.pop()
        f = lambda: func(val())
        return self.push(f, val.static)

    return _visit_unary_op


class BuildGraph(ByteCodeVisitor):
    """
    Mutate instructions to to add exec to each
    """

    def __init__(self, instructions, globals, nonlocals, stores) -> None:
        self.bytecode = list(instructions)
        self.globals = globals
        self.nonlocals = nonlocals

        self.stack = []
        self.stores = stores

    def post_visit(self, op, val):
        op.exec = val

    def push(self, val, static):
        val.static = static
        self.stack.append(val)
        return val

    def pop(self):
        return self.stack.pop()

    def visit_return_value(self, op):
        val = self.pop()
        return self.push(lambda: val(), val.static)

    def visit_load_global(self, op):
        def load():
            if op.argval in self.globals:
                return self.globals[op.argval]
            return __builtins__[op.argval]

        return self.push(load, True)

    def visit_load_method(self, op):
        klass = self.pop()
        return self.push(lambda: getattr(klass(), op.argval), klass.static)

    def visit_load_fast(self, op):
        val = self.stores[op.argval]
        return self.push(val, val.static)

    def visit_load_deref(self, op):
        if op.argval in self.stores:
            val = self.stores.get(op.argval)
            return self.push(val, val.static)
        val = self.nonlocals[op.argval]
        self.push(lambda: self.nonlocals[op.argval], True)

    def visit_load_const(self, op):
        return self.push(lambda: op.argval, True)

    def visit_store_fast(self, op):
        value = self.pop()
        self.stores[op.argval] = value

    def visit_call_function(self, op):
        args = [self.pop() for _ in range(op.argval)][::-1]
        func = self.pop()
        op.func = func
        static = func.static and all([arg.static for arg in args])
        return self.push(lambda: func()(*[arg() for arg in args]), static)

    visit_call_method = visit_call_function

    visit_binary_true_divide = visit_bin_op(lambda x, y: x / y)
    visit_binary_add = visit_bin_op(lambda x, y: x + y)
    visit_binary_subtract = visit_bin_op(lambda x, y: x - y)

    visit_unary_negative = visit_unary_op(lambda x: -x)


def build_graph(func):
    bytecode = list(dis.Bytecode(func))
    x_f = lambda: None
    x_f.static = False

    func_vars = inspect.getclosurevars(func)
    args = {k: x_f for k in inspect.getargs(func.__code__).args}
    bg = BuildGraph(bytecode, func_vars.globals, func_vars.nonlocals, args)
    bg.visit_forward()

    return bytecode


def main():
    def func(x):
        y = np.exp(-x)
        return (1.0 - y) / (1.0 + y)

    dis.dis(func)

    bytecode = build_graph(func)

    instr = bytecode[-1]
    print(instr.exec.static)
    print(instr.exec())
    print(bytecode)


if __name__ == "__main__":
    main()
