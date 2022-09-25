import ast
import dis
from meta2.ast_tools.print_ast import print_ast
from .decompile import decompile


def test_decompile(corpus):

    module = ast.parse(corpus)
    print_ast(module)
    code_obj = compile(module, filename="<none>", mode="exec")
    orig_bytecode = dis.Bytecode(code_obj)
    print("orig_bytecode")
    print(orig_bytecode.dis())

    new_module = decompile(code_obj, "exec")

    print("new_module")
    print_ast(new_module)

    new_code_obj = compile(new_module, filename="<new_code_obj>", mode="exec")

    new_bytecode = dis.Bytecode(new_code_obj)

    print("new_code_obj")
    print(new_bytecode.dis())

    orig_ops = list(orig_bytecode)
    new_ops = list(new_bytecode)
    assert len(orig_ops) == len(new_ops)
    for orig_op, new_op in zip(orig_ops, new_ops):
        assert orig_op.opname == new_op.opname
        assert orig_op.argval == new_op.argval
