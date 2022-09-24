import dis
from typing import Tuple, List


def visit_n(n):
    def visit_noop(self, op):
        for i in range(n):
            self.visit_last()

    return visit_noop


class FastForwarder:
    def __init__(self, instructions) -> None:
        self.instructions = instructions
        self.visited = []
        self.stack = []

    def visit(self, op: dis.Instruction):
        method_name = f"visit_{op.opname.lower()}"
        method = getattr(self, method_name, None)
        if method:
            return method(op)
        raise NotImplementedError(f"{self.__class__.__name__}.{method_name} {op}")

    def visit_first(self):
        op = self.instructions.pop(0)
        self.visited.append(op)
        self.visit(op)

    def ff(self, count):
        while count:
            self.visit_first()
            if len(self.stack) == 0:
                count -= 1

    def visit_for_iter(self, op):
        self.stack.append(None)

    def visit_store_fast(self, op):
        self.stack.pop()


class Dup:
    def __init__(self, v, count) -> None:
        self.v = v
        self.count = count


class Unwinder:
    """
    remove ops from bytecode until the stack is back at 0 items

    example, to unwind the follwing

        | LOAD_FAST
        | STORE_FAST
        | LOAD_FAST
        | STORE_FAST
    do::
        Unwinder(instructions).unwind(2)
    """

    def __init__(self, instructions) -> None:
        self.instructions = instructions
        self.visited = []
        self.stack = []

    def unwind(self, count):
        for _ in range(count):
            self.visit_last()

    def visit_last(self):
        if self.stack:
            self.stack.pop()
            return

        op = self.instructions.pop()
        self.visited.insert(0, op)
        self.visit(op)

    def visit(self, op: dis.Instruction):
        method_name = f"visit_{op.opname.lower()}"
        method = getattr(self, method_name, None)
        if method:
            return method(op)
        raise NotImplementedError(f"{self.__class__.__name__}.{method_name} {op}")

    def visit_call_function(self, op):
        for _ in range(op.argval):
            self.visit_last()
        self.visit_last()

    visit_unary_negative = visit_n(1)
    visit_binary_add = visit_n(2)

    visit_load_fast = visit_n(0)
    visit_load_global = visit_n(0)
    visit_load_deref = visit_n(0)

    visit_load_const = visit_n(0)

    visit_pop_jump_if_false = visit_n(1)
    visit_pop_jump_if_true = visit_n(1)
    visit_compare_op = visit_n(2)

    visit_rot_three = visit_n(3)

    def visit_dup_top(self, op):
        val = self.visit_last()
        self.stack.extend([val, val])


def split(
    instructions: List[dis.Instruction],
    unwind: int = None,
    ff: int = None,
    offset: int = None,
) -> Tuple[List[dis.Instruction], List[dis.Instruction]]:
    """
    split instruction list into two

    """
    if unwind is not None:
        consumer = Unwinder(instructions)
        consumer.unwind(unwind)
        return consumer.instructions, consumer.visited
    if ff is not None:
        consumer = FastForwarder(instructions)
        consumer.ff(ff)
        return consumer.visited, consumer.instructions
    if offset is not None:
        pre = []
        instructions = list(instructions)
        while instructions and instructions[0].offset < offset:
            pre.append(instructions.pop(0))
        return pre, instructions
