from .visitor import ByteCodeVisitor
from .ir import IR


class ForwardPass:
    def __init__(self, ir) -> None:
        pass

    def push(self, v):
        self.stack.append(v)

    def pop(self):
        return self.stack.pop()

    def visit_load_global(self, op):
        v = self.func.__globals__[op.argval]
        self.push(v)

    def visit_load_method(self, op):
        s = self.pop()
        v = getattr(s, op.argval)
        self.push(v)


def main():
    import numpy as np
    import dis

    def func_forward(x):
        i0 = -x
        val = np.exp(i0)
        return val, (i0,)

    dis.dis(func_forward)
    ir = IR.from_function(func_forward)
    print(ir)


if __name__ == "__main__":
    main()
