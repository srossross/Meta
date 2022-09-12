from .bytecode_tools.decompile import decompile_function, decompile_function_recursive
from .ast_tools.print_ast import print_ast
from .ast_tools.ast_to_source import ast_to_source


def print_source_tree(func):
    mod = decompile_function_recursive(func)
    ast_to_source(mod)
