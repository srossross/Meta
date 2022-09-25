import ast
import opcode
from meta2.ast_tools.print_ast import print_ast
from meta2.ast_tools.ast_to_source import ast_to_source
from ..unwind import split

hascond = {opcode.opmap["POP_JUMP_IF_TRUE"], opcode.opmap["POP_JUMP_IF_FALSE"]}
anyjump = set(opcode.hasjabs) | set(opcode.hasjrel)


class WhileLoopDecompiler:
    @staticmethod
    def is_while_loop(body):
        if not body:
            return False
        last_op = body[-1]
        # if last_op == opcode

        if last_op.opcode not in anyjump:
            return False

        if last_op.offset > last_op.argval:
            return True

    def __init__(self, conditions, body, decompile_inner) -> None:
        self.conditions = conditions
        self.body = body
        self._decompile_inner = decompile_inner

    def __len__(self):
        return len(self.conditions) + len(self.body)

    def decompile(self):
        test0 = self._decompile_inner(self.conditions, has_blocks=False)

        body, test1 = split(self.body, unwind=1)

        test = self._decompile_inner(test0)
        body = self._decompile_inner(body)
        return [ast.While(body=body, orelse=[], test=test)]
