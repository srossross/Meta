import dis

from .visitor import ByteCodeVisitor


class StaticConsumer(ByteCodeVisitor):
    """
    Consumes instructions from the end of instructions and returns the static value
    that would result from the instruction set
    """

    def __init__(self, instructions, globals) -> None:
        self._ops = instructions
        self.globals = globals
        self.value_name = ""

    def push_name(self, s):
        if not self.value_name:
            self.value_name = s
            return
        self.value_name = f"{self.value_name}_{s}"

    def visit(self, op: dis.Instruction):
        method_name = f"visit_{op.opname.lower()}"
        method = getattr(self, method_name, None)
        if method:
            return method(op)
        raise NotImplementedError(f"{self.__class__.__name__}.{method_name} {op}")

    def visit_load_global(self, op):
        self.push_name(op.argval)
        return self.globals[op.argval]

    def visit_load_method(self, op):
        klass = self.visit_last()
        self.push_name(op.argval)
        return getattr(klass, op.argval)


def consume_static(instructions, globals):
    consumer = StaticConsumer(instructions, globals)
    value = consumer.visit_last()
    return consumer.value_name, value
