import ast
from meta2.ast_tools.print_ast import print_ast
from meta2.ast_tools.ast_to_source import ast_to_source
from ..unwind import split


class ForLoopDecompiler:
    def __init__(self, assign_part, body_part, decompile_inner):
        self.assign_part = assign_part
        self.body_part = body_part
        self._decompile_inner = decompile_inner

    def __len__(self):
        return len(self.assign_part) + len(self.body_part)

    def decompile(self):
        (iter,) = self._decompile_inner(self.assign_part)

        for_op = self.body_part.pop(0)
        end_jump_op = self.body_part.pop()

        target_part, body_part = split(self.body_part, ff=1)

        body = self._decompile_inner(body_part)
        # print("body_part", body_part[:-1])

        assigns = self._decompile_inner(target_part, has_blocks=False)
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
