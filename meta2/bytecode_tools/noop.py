from .visitor import ByteCodeVisitor


def consume(n: int):
    def visit_X(self, op):
        for i in range(n):
            self.visit_last()
        return None

    return visit_X


class NoOp(ByteCodeVisitor):
    visit_return_value = consume(1)

    visit_binary_true_divide = consume(2)
    visit_binary_add = consume(2)
    visit_binary_subtract = consume(2)

    visit_unary_negative = consume(1)

    visit_load_fast = consume(0)
    visit_load_const = consume(0)

    visit_store_fast = consume(1)

    visit_load_attr = consume(1)
    visit_load_method = consume(1)
    visit_load_global = consume(0)
    visit_pop_top = consume(1)

    def visit_call_method(self, op):
        for _ in range(op.argval):
            self.visit_last()
        self.visit_last()  # method
        return None

    def visit_call_function(self, op):
        for _ in range(op.argval):
            self.visit_last()
        self.visit_last()  # method
        return None

    def visit_call_function_kw(self, op):
        self.visit_last()  # const_keys
        for _ in range(op.argval):
            self.visit_last()
        self.visit_last()  # method
        return None
