import ast
from ..visitor import ByteCodeVisitor


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


class DecompileSimpleOps(ByteCodeVisitor):
    def visit_return_value(self, op):
        return ast.Return(value=self.visit_last(), **self.d(op))

    visit_binary_true_divide = binary_op(ast.Div)
    visit_binary_add = binary_op(ast.Add)
    visit_binary_subtract = binary_op(ast.Sub)
    visit_binary_and = binary_op(ast.BitAnd)
    visit_binary_or = binary_op(ast.BitOr)
    visit_binary_xor = binary_op(ast.BitXor)
    visit_binary_modulo = binary_op(ast.Mod)
    visit_binary_multiply = binary_op(ast.Mult)
    visit_binary_matrix_multiply = binary_op(ast.MatMult)
    visit_binary_power = binary_op(ast.Pow)
    visit_binary_floor_divide = binary_op(ast.FloorDiv)
    visit_binary_lshift = binary_op(ast.LShift)
    visit_binary_rshift = binary_op(ast.RShift)

    visit_unary_negative = unary_op(ast.USub)
    visit_unary_positive = unary_op(ast.UAdd)
    visit_unary_invert = unary_op(ast.Invert)

    def visit_load_fast(self, op):
        return ast.Name(ctx=ast.Load(), id=op.argval, **self.d(op))

    def visit_load_name(self, op):
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

    def _mk_keyword(self, arg, value, d):
        if isinstance(arg, ast.Constant):
            arg = arg.value

        return ast.keyword(arg=arg, value=value, **d)

    def visit_call_function_ex(self, op):
        d = self.d(op)
        kwargs = []
        if op.argval:
            kwargs = self.visit_last()
        args = self.visit_last()
        method = self.visit_last()

        if isinstance(args, ast.Tuple):
            args = args.elts

        if isinstance(args, ast.Constant):
            args = list(args.value)

        if isinstance(kwargs, ast.Dict):
            kwargs = [
                self._mk_keyword(k, v, d) for k, v in zip(kwargs.keys, kwargs.values)
            ]

        return ast.Call(args=args, func=method, keywords=kwargs, **d)

    def visit_call_function_kw(self, op):
        const_keys = self.visit_last()
        assert isinstance(const_keys, ast.Constant)
        keys = const_keys.value
        args = [self.visit_last() for _ in range(op.argval)][::-1]
        kwargs = args[-len(keys) :]
        args = args[: -len(keys)]
        method = self.visit_last()
        keywords = [
            ast.keyword(arg=k, value=v, **self.d(op)) for k, v in zip(keys, kwargs)
        ]
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

    def visit_binary_subscr(self, op):
        slice = self.visit_last()
        value = self.visit_last()
        return ast.Subscript(slice=slice, value=value, ctx=ast.Load(), **self.d(op))

    def visit_build_slice(self, op):
        if op.argval == 2:
            step = None
            upper = self.visit_last()
            lower = self.visit_last()
        elif op.argval == 3:
            step = self.visit_last()
            upper = self.visit_last()
            lower = self.visit_last()
        else:
            assert False, op

        return ast.Slice(lower=lower, step=step, upper=upper, **self.d(op))

    def visit_build_list(self, op):
        elts = [self.visit_last() for _ in range(op.argval)][::-1]
        return ast.List(elts=elts, ctx=ast.Load(), **self.d(op))

    def visit_list_extend(self, op):
        to_extend = self.visit_last()
        lst = self.visit_last()

        return ast.List(
            elts=[
                *lst.elts,
                ast.Starred(value=to_extend, ctx=ast.Load(), **self.d(op)),
            ],
            ctx=ast.Load(),
            **self.d(op)
        )

    def visit_list_append(self, op):
        to_append = self.visit_last()
        lst = self.visit_last()

        return ast.List(elts=[*lst.elts, to_append], ctx=ast.Load(), **self.d(op))

    def visit_build_map(self, op):
        elts = [self.visit_last() for _ in range(op.argval * 2)][::-1]
        keys = elts[::2]
        values = elts[1::2]
        return ast.Dict(keys=keys, values=values, ctx=ast.Load(), **self.d(op))

    def _kv(self, node):
        if isinstance(node, ast.Dict):
            return node.keys, node.values
        return [None], [node]

    def visit_dict_merge(self, op):
        d1 = self.visit_last()
        d2 = self.visit_last()
        d1_keys, d1_values = self._kv(d1)
        d2_keys, d2_values = self._kv(d2)

        return ast.Dict(
            keys=[*d2_keys, *d1_keys],
            values=[*d2_values, *d1_values],
            ctx=ast.Load(),
            **self.d(op)
        )

    def visit_dict_update(self, op):
        d1 = self.visit_last()
        d2 = self.visit_last()

        d1_keys, d1_values = self._kv(d1)
        d2_keys, d2_values = self._kv(d2)

        return ast.Dict(
            keys=[*d2_keys, *d1_keys],
            values=[*d2_values, *d1_values],
            ctx=ast.Load(),
            **self.d(op)
        )

    def visit_build_tuple(self, op):
        elts = [self.visit_last() for _ in range(op.argval)][::-1]
        return ast.Tuple(elts=elts, ctx=ast.Load(), **self.d(op))

    def visit_list_to_tuple(self, op):
        lst = self.visit_last()
        return ast.Tuple(elts=lst.elts, ctx=lst.ctx, **self.d(op))

    def visit_build_set(self, op):
        elts = [self.visit_last() for _ in range(op.argval)][::-1]
        return ast.Set(elts=elts, ctx=ast.Load(), **self.d(op))

    def visit_for_iter(self, op):
        return None


def main():
    import dis

    def foo(a):
        # while a:
        #     b
        if a:
            a -= 1
        # b

    # return 1

    dis.dis(foo)


if __name__ == "__main__":
    main()
