import ast
from collections import namedtuple
from .visitor import ByteCodeVisitor
from meta2.ast_tools.print_ast import print_ast


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


PlaceHolder = namedtuple("PlaceHolder", "value count")


class Unpack(PlaceHolder):
    pass


class DupN(PlaceHolder):
    pass


class DecompileExprOps(ByteCodeVisitor):
    def _merge_targets(self, targets, target, d):
        assert len(targets) == 1
        if isinstance(targets[0], ast.Name):
            return [ast.Tuple(elts=[targets[0], target], ctx=ast.Store(), **d)]

        if isinstance(targets[0], ast.Tuple):
            t = targets[0]
            return [ast.Tuple(elts=[*t.elts, target], ctx=ast.Store(), **d)]
        assert False

    def _unpack_assign(self, targets, target, unpack, d):
        targets = self._merge_targets(targets, target, d)
        if unpack.count <= 2:
            return ast.Assign(
                targets=targets, type_comment=None, value=unpack.value, **d
            )
        else:
            return ast.Assign(
                targets=targets,
                type_comment=None,
                value=Unpack(unpack.value, unpack.count - 1),
                **d
            )

    def _multi_assign(self, targets, target, dup, d):
        return ast.Assign(
            targets=[*targets, target], type_comment=None, value=dup.value, **d
        )

    def visit_unpack_sequence(self, op):
        return Unpack(self.visit_last(), op.argval)

    def visit_dup_top(self, op):
        value = self.visit_last()
        if isinstance(value, ast.Assign):
            return ast.Assign(
                targets=value.targets,
                value=DupN(value.value, 2),
                type_comment=value.type_comment,
                lineno=value.lineno,
                col_offset=value.col_offset,
            )
        return DupN(value, 2)

    def visit_store_name(self, op):

        d = self.d(op)
        value = self.visit_last()
        target = ast.Name(id=op.argval, ctx=ast.Store(), **d)

        if isinstance(value, ast.Assign) and isinstance(value.value, Unpack):
            return self._unpack_assign(value.targets, target, value.value, d)

        if isinstance(value, ast.Assign) and isinstance(value.value, DupN):
            return self._multi_assign(value.targets, target, value.value, d)

        if not isinstance(value, ast.Assign):
            return ast.Assign(targets=[target], type_comment=None, value=value, **d)

        assert False, value

    def visit_store_attr(self, op):

        d = self.d(op)
        target = self.visit_last()
        target = ast.Attribute(
            # ast.Name(id=op.argval, ctx=ast.Store(), )
            attr=op.argval,
            ctx=ast.Store(),
            value=target,
            **d
        )

        value = self.visit_last()

        if isinstance(value, ast.Assign) and isinstance(value.value, Unpack):
            return self._unpack_assign(value.targets, target, value.value, d)

        if isinstance(value, ast.Assign) and isinstance(value.value, DupN):
            return self._multi_assign(value.targets, target, value.value, d)

        if not isinstance(value, ast.Assign):
            return ast.Assign(targets=[target], type_comment=None, value=value, **d)

        assert False, value
