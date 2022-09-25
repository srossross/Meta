import dis
import ast
import opcode
from re import A
from ...ast_tools.print_ast import print_ast
from ...ast_tools.ast_to_source import ast_to_source
from .decompile_simple_ops import DecompileSimpleOps
from ..unwind import split

hascond = {opcode.opmap["POP_JUMP_IF_TRUE"], opcode.opmap["POP_JUMP_IF_FALSE"]}
anyjump = set(opcode.hasjabs) | set(opcode.hasjrel)


class NoOpDecompiler:
    def __len__(self):
        return 0

    def decompile(self):
        return []


class ForLoopDecompiler:
    def __init__(self, assign_part, body_part):
        self.assign_part = assign_part
        self.body_part = body_part

    def __len__(self):
        return len(self.assign_part) + len(self.body_part)

    def decompile(self):
        (iter,) = DecompileSimpleOps(self.assign_part).visit_reverse()

        for_op = self.body_part.pop(0)
        end_jump_op = self.body_part.pop()

        target_part, body_part = split(self.body_part, ff=1)

        body = DecompileSimpleOps(body_part).visit_reverse()
        # print("body_part", body_part[:-1])

        assigns = DecompileSimpleOps(target_part).visit_reverse()
        target = assigns[0].targets[0]
        return [
            ast.For(
                body=body,
                iter=iter,
                orelse=[],
                target=target,
                lineno=for_op.starts_line or 0,
                col_offset=for_op.offset or 0,
            )
        ]


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

    print("first_jump", first_jump)
    print("last_jump", last_jump)
    print("end", end)
    print("jump_map", jumps)
    pre, rest = split(instructions, offset=first_jump + 1)
    pre, jumps0 = split(pre, unwind=1)

    jumps1, rest = split(rest, offset=last_jump + 1)

    jumps = jumps0 + jumps1

    print("pre", [f"{op.opname}({op.offset}, {op.argrepr})" for op in pre])
    print("jumps", [f"{op.opname}({op.offset}, {op.argrepr})" for op in jumps])

    body, post = split(rest, offset=end)
    print("body", [f"{op.opname}({op.offset}, {op.argrepr})" for op in body])
    print("post", [f"{op.opname}({op.offset}, {op.argrepr})" for op in post])

    return pre, jumps, body, post


class WhileLoopDecompiler:
    @staticmethod
    def is_while_loop(body):
        if not body:
            return False
        last_op = body[-1]

        if last_op.opcode not in anyjump:
            return False

        if last_op.offset > last_op.argval:
            return True

    def __init__(self, conditions, body) -> None:
        self.conditions = conditions
        self.body = body

    def __len__(self):
        return len(self.conditions) + len(self.body)

    def decompile(self):
        test0 = DecompileSimpleOps(self.conditions).visit_last()

        body, test1 = split(self.body, unwind=1)

        test = DecompileSimpleOps(test0).visit_last()
        body = BlockDecompiler(body).consume_blocks()
        return [ast.While(body=body, orelse=[], test=test)]


class BlockDecompiler:
    def __init__(self, instructions):
        self.instructions = instructions
        self._results = []

    def detect_next_block(self):

        for i, op in enumerate(self.instructions):
            if op.opname == "FOR_ITER":
                assert self.instructions[i - 1].opname == "GET_ITER"

                pre, assign_part = split(self.instructions[: i - 1], unwind=1)
                body, post = split(self.instructions[i - 1 :], offset=op.argval)
                return pre, ForLoopDecompiler(assign_part, body), post
            if op.opcode in hascond:
                pre, conditions, body, post = gather_conditions(self.instructions)
                if WhileLoopDecompiler.is_while_loop(body):
                    return pre, WhileLoopDecompiler(conditions, body), post
                assert False, op

        return self.instructions, NoOpDecompiler(), []

    def handle_block(block_type, block):
        pass

    def consume_blocks(self):
        while self.instructions:
            pre, block_decompiler, post = self.detect_next_block()

            msg = f"{len(pre)} + {len(block_decompiler)} + {len(post)} != {len(self.instructions)}"
            expected = len(pre) + len(block_decompiler) + len(post)
            assert expected == len(self.instructions), msg

            self.instructions = post

            pre_ast = DecompileSimpleOps(pre).visit_reverse()
            self._results.extend(pre_ast)

            block_ast = block_decompiler.decompile()
            self._results.extend(block_ast)

        return self._results


def test():
    def while_loop():
        # while a and b and c:
        # a = (b if c else d) + 1
        # a
        # if a:
        #     return c
        # return d

        while a or b:
            start
            # if d:
            #     break
            end
        after1
        after2
        return f

        # f
        # g
        # for a in range(j):
        #     i
        #     # if n:
        #     #     break
        #     # i
        # else:
        #     do_else
        # end
        # end
        # end
        # end
        # end

    print_ast(
        ast.parse(
            """
while a:
    asfd
"""
        )
    )
    dis.dis(while_loop)
    instructions = list(dis.Bytecode(while_loop))
    bd = BlockDecompiler(instructions)
    bd.consume_blocks()

    print_ast(
        ast.parse(
            """
for a in range(j):
    k(i)
end
"""
        )
    )

    m = ast.Module(body=bd._results, type_ignores=[])
    print_ast(m)
    ast_to_source(m)


if __name__ == "__main__":
    test()
