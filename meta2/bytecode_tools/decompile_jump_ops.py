import dis

# from collections import namedtuple
from .visitor import ByteCodeVisitor

# from meta2.ast_tools.print_ast import print_ast


class DecompileJumpOps(ByteCodeVisitor):
    def pre_visit(self, op: dis.Instruction):
        if op.is_jump_target:
            asdf
