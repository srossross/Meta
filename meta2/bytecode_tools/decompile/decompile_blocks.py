import dis
import ast
import opcode
from meta2.ast_tools.print_ast import print_ast
from meta2.ast_tools.ast_to_source import ast_to_source
from meta2.bytecode_tools.decompile.decompile_expr_ops import DecompileExprOps
from .decompile_simple_ops import DecompileSimpleOps
from ..unwind import split

from .decompile_for_block import ForLoopDecompiler
from .decompile_while_block import WhileLoopDecompiler
from .decompile_with_block import WithDecompiler

hascond = {opcode.opmap["POP_JUMP_IF_TRUE"], opcode.opmap["POP_JUMP_IF_FALSE"]}
anyjump = set(opcode.hasjabs) | set(opcode.hasjrel)


class NoOpDecompiler:
    def __len__(self):
        return 0

    def decompile(self):
        return []


def spans_jumps(jumps, op):
    if not jumps:
        return True
    for start_offset, end_offset in jumps:
        if (start_offset < op.offset < end_offset) and op.argval > end_offset:
            return True


def gather_conditions(instructions):
    jumps = []
    for i, op in enumerate(instructions):
        if op.opcode in opcode.hasjabs or op.opcode in opcode.hasjrel:
            if spans_jumps(jumps, op):
                jumps.append((op.offset, op.argval))

    first_jump = min([s for s, _ in jumps])
    last_jump = max([s for s, _ in jumps])
    end = max([e for _, e in jumps])

    pre, rest = split(instructions, offset=first_jump + 1)
    pre, jumps0 = split(pre, unwind=1)

    jumps1, rest = split(rest, offset=last_jump + 1)

    jumps = jumps0 + jumps1

    body, post = split(rest, offset=end)
    # print("body", [f"{op.opname}({op.offset}, {op.argrepr})" for op in body])
    # print("post", [f"{op.opname}({op.offset}, {op.argrepr})" for op in post])

    return pre, jumps, body, post


class ExprDecompiler(DecompileSimpleOps, DecompileExprOps):
    pass


def decompile_instructions(instructions, has_blocks=True):
    if has_blocks:
        return BlockDecompiler(instructions).consume_blocks()

    return ExprDecompiler(instructions).visit_reverse()


class BlockDecompiler:
    def __init__(self, instructions):
        self.instructions = instructions
        self._results = []

    def detect_next_block(self):
        # import pdb

        # pdb.set_trace()

        print(
            "detect next block",
            [f"{op.opname}({op.offset}, {op.argrepr})" for op in self.instructions],
        )

        for i, op in enumerate(self.instructions):
            if op.opname == "FOR_ITER":
                assert self.instructions[i - 1].opname == "GET_ITER"

                pre, assign_part = split(self.instructions[: i - 1], unwind=1)
                body, post = split(self.instructions[i - 1 :], offset=op.argval)
                return (
                    pre,
                    ForLoopDecompiler(assign_part, body, decompile_instructions),
                    post,
                )
            if op.opname == "SETUP_WITH":
                return WithDecompiler.build(
                    self.instructions, i, decompile_instructions
                )
            if op.opcode in hascond:
                pre, conditions, body, post = gather_conditions(self.instructions)
                if WhileLoopDecompiler.is_while_loop(body):
                    return (
                        pre,
                        WhileLoopDecompiler(conditions, body, decompile_instructions),
                        post,
                    )
                assert False, op

        return self.instructions, NoOpDecompiler(), []

    def handle_block(block_type, block):
        pass

    def consume_blocks(self):
        while self.instructions:
            pre, block_decompiler, post = self.detect_next_block()
            print("block_decompiler", block_decompiler)
            print("----")

            msg = f"{len(pre)} + {len(block_decompiler)} + {len(post)} != {len(self.instructions)}"
            expected = len(pre) + len(block_decompiler) + len(post)
            assert expected == len(self.instructions), msg

            self.instructions = post

            pre_ast = ExprDecompiler(pre).visit_reverse()
            self._results.extend(pre_ast)

            block_ast = block_decompiler.decompile()
            self._results.extend(block_ast)

        return self._results
