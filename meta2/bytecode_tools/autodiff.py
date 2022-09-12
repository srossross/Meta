from .visitor import ByteCodeVisitor


class ForwardPass(ByteCodeVisitor):
    def __init__(self, func) -> None:
        super().__init__(func)
        self.vars = {}
        self.graph = {}
        self.stack = []

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
