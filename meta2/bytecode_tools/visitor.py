import dis
from typing import List
import types


class ByteCodeVisitor:
    @classmethod
    def from_code(cls, code: types.CodeType):
        instructions = dis.Bytecode(code)
        return cls(list(instructions))

    def __init__(self, instructions: List[dis.Instruction]) -> None:
        self._ops = instructions
        self._results = []

    def post_visit(self, op, val):
        return val

    def pre_visit(self, op):
        return op

    def visit_last(self):
        op = self._ops.pop()
        val = self.visit(op)
        return val

    def visit_first(self):
        op = self._ops.pop(0)
        val = self.visit(op)
        return val

    def d(self, op):
        return {"lineno": op.starts_line or 0, "col_offset": op.offset or 0}

    def visit_forward(self):
        while self._ops:
            val = self.visit_first()
            if val is not None:
                self._results.append(val)
        return self._results

    def visit_reverse(self):
        while self._ops:
            val = self.visit_last()
            if val is not None:
                self._results.insert(0, val)
        return self._results

    def visit(self, op: dis.Instruction):

        self.pre_visit(op)

        if op is None:
            return

        method_name = f"visit_{op.opname.lower()}"
        method = getattr(self, method_name, None)
        default_method = getattr(self, "visit_default", None)
        if method:
            val = method(op)
        elif default_method:
            val = default_method(op)
        else:
            raise NotImplementedError(f"{self.__class__.__name__}.{method_name} {op}")

        val = self.post_visit(op, val)
        return val
