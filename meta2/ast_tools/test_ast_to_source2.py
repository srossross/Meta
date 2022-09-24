import ast
import _ast
from .ast_to_source import SourceGen
from meta2.conftest import ast_deep_equal


def test_ast_to_static(corpus):

    module = ast.parse(corpus)
    # print(source)

    gen = SourceGen()
    gen.visit(module)

    generated_source = gen.dumps()
    new_module = ast.parse(generated_source)

    ast_deep_equal(module, new_module)
