from .visitor import ByteCodeVisitor


class ReverseExecutor(ByteCodeVisitor):
    def __init__(self, instructions, globals) -> None:
        self._ops = instructions
        self.globals = globals

    def visit_load_global(self, op):
        return self.globals[op.argval]

    def visit_load_method(self, op):
        kls = self.visit_last()
        return getattr(kls, op.argval)


def execute_last(instructions, globals):
    executor = ReverseExecutor(instructions, globals)
    return executor.visit_last()
