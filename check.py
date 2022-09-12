import meta2

def bar():
    pass

def foo():
    a = 1
    return bar()
    # return np.abs(-a)

mod = meta2.decompile_function_recursive(foo)

# meta2.print_ast(mod)
meta2.ast_to_source(mod)

