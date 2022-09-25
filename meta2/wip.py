import dis
import ast
import opcode
from meta2.ast_tools.print_ast import print_ast
from meta2.ast_tools.ast_to_source import ast_to_source

from meta2.bytecode_tools.decompile.decompile_blocks import BlockDecompiler
from meta2.bytecode_tools.unwind import split


def test():
    def while_loop():
        # while a and b and c:
        # a = (b if c else d) + 1
        # a
        # if a:
        #     return c
        # return d

        # while a or b:
        with a:
            asdf
            with b:
                if x:
                    return e
                y
            z
            # return

        n
        return f
        # while a < b < c:
        #     start
        #     # if d:
        #     #     break
        #     end
        # after1
        # after2
        # return f

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
with a:
    returnc
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
