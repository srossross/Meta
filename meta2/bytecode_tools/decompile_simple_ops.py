import ast
from .visitor import ByteCodeVisitor


def binary_op(ast_op: ast.AST):
    def visit_binary_op(self, op):
        rhs = self.visit_last()
        lhs = self.visit_last()
        return ast.BinOp(lhs, ast_op(), rhs, **self.d(op))

    return visit_binary_op


def unary_op(ast_op: ast.AST):
    def visit_unary_op(self, op):
        operand = self.visit_last()
        return ast.UnaryOp(operand=operand, op=ast_op(), **self.d(op))

    return visit_unary_op


class BytecodeToAST(ByteCodeVisitor):
    def visit_return_value(self, op):
        return ast.Return(value=self.visit_last(), **self.d(op))

    visit_binary_true_divide = binary_op(ast.Div)
    visit_binary_add = binary_op(ast.Add)
    visit_binary_subtract = binary_op(ast.Sub)

    visit_unary_negative = unary_op(ast.Sub)

    def visit_load_fast(self, op):
        return ast.Name(ctx=ast.Load(), id=op.argval, **self.d(op))

    def visit_load_const(self, op):
        return ast.Constant(value=op.argval, kind=None, **self.d(op))

    def visit_store_fast(self, op):
        value = self.visit_last()
        return ast.Assign(
            targets=[ast.Name(ctx=ast.Store(), id=op.argval)], value=value, **self.d(op)
        )

    def visit_call_method(self, op):
        args = [self.visit_last() for _ in range(op.argval)][::-1]
        method = self.visit_last()
        return ast.Call(args=args, func=method, keywords=[], **self.d(op))

    def visit_call_function(self, op):
        args = [self.visit_last() for _ in range(op.argval)][::-1]
        method = self.visit_last()
        return ast.Call(args=args, func=method, keywords=[], **self.d(op))

    def visit_call_function_kw(self, op):
        const_keys = self.visit_last()
        assert isinstance(const_keys, ast.Constant)
        keys = const_keys.value
        args = [self.visit_last() for _ in range(op.argval)][::-1]
        kwargs = args[-len(keys) :]
        args = args[: -len(keys)]
        method = self.visit_last()
        keywords = [ast.keyword(arg=k, value=v) for k, v in zip(keys, kwargs)]
        return ast.Call(args=args, func=method, keywords=keywords, **self.d(op))

    def visit_load_attr(self, op):
        value = self.visit_last()
        return ast.Attribute(attr=op.argval, ctx=ast.Load(), value=value, **self.d(op))

    def visit_load_method(self, op):
        value = self.visit_last()
        return ast.Attribute(attr=op.argval, ctx=ast.Load(), value=value, **self.d(op))

    def visit_load_global(self, op):
        return ast.Name(ctx=ast.Load(), id=op.argval, **self.d(op))

    def visit_pop_top(self, op):
        value = self.visit_last()
        return ast.Expr(value=value, **self.d(op))
        # return ast.Name(ctx=ast.Load(), id=op.argval, **self.d(op))
