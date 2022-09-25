import ast
import opcode
from meta2.ast_tools.print_ast import print_ast
from meta2.ast_tools.ast_to_source import ast_to_source
from ..unwind import split

WITH_INSTRUCTION_OVERHEAD = 8


def make_optional_vars(op):
    if op.opname == "POP_TOP":
        return None
    if op.opname in "STORE_FAST":
        return ast.Name(id=op.argval, ctx=ast.Store())

    assert False, op


class WithDecompiler:
    @staticmethod
    def build(instructions, i, decompile_instructions):
        with_op = instructions[i]
        pre, with_setup = split(instructions[:i], unwind=1)
        store_with = instructions[i + 1]
        block, post = split(instructions[i + 2 :], offset=with_op.argval)

        print("WITH block")

        for op in block:
            print(f"    + {op.opname}({op.offset}, {op.argrepr})")
        print("xxxx")

        post = post[WITH_INSTRUCTION_OVERHEAD:]
        print("POST WITH block")
        for op in post:
            print(f"    + {op.opname}({op.offset}, {op.argrepr})")
        print("xxxx")
        # import pdb

        # pdb.set_trace()

        return (
            pre,
            WithDecompiler(with_setup, store_with, block, decompile_instructions),
            post,
        )

    def __init__(self, with_setup, store_with, block, decompile_instructions):
        self.with_setup = with_setup
        self.store_with = store_with
        self.block = block

        self._decompile_inner = decompile_instructions

    def __len__(self):
        store = 1
        setup_with = 1
        return (
            len(self.with_setup)
            + store
            + setup_with
            + WITH_INSTRUCTION_OVERHEAD
            + len(self.block)
            # - 1
        )

    def decompile(self):
        (context_expr,) = self._decompile_inner(self.with_setup, has_blocks=False)
        optional_vars = make_optional_vars(self.store_with)

        i = len(self.block) - 1
        while self.block[i].opname != "POP_BLOCK":
            i -= 1

        body = self._decompile_inner(self.block[:i])

        return [
            ast.With(
                body=body,
                items=[
                    ast.withitem(context_expr=context_expr, optional_vars=optional_vars)
                ],
            )
        ]
