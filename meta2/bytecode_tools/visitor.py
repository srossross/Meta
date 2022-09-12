import dis


class ByteCodeVisitor:
    def __init__(self, func) -> None:
        self.func = func
        self.bytecode = dis.Bytecode(func)

    def post_visit(self, op, val):
        pass

    def visit_last(self):
        op = self._ops.pop()
        val = self.visit(op)
        return val

    def d(self, op):
        return {"lineno": op.starts_line, "col_offset": op.offset}

    def visit_forward(self):
        self._ops = list(self.bytecode)
        self._results = []
        while self._ops:
            op = self._ops.pop(0)
            val = self.visit(op)
            if val is not None:
                self._results.append(val)
        return self._results

    def visit_reverse(self):
        self._ops = list(self.bytecode)
        self._results = []
        while self._ops:
            op = self._ops.pop()
            val = self.visit(op)
            if val is not None:
                self._results.insert(0, val)
        return self._results

    def visit(self, op: dis.Instruction):
        method_name = f"visit_{op.opname.lower()}"
        method = getattr(self, method_name, None)
        default_method = getattr(self, "visit_default", None)
        if method:
            val = method(op)
        elif default_method:
            val = default_method(op)
        else:
            raise NotImplementedError(f"{self.__class__.__name__}.{method_name} {op}")

        self.post_visit(op, val)
        return val
