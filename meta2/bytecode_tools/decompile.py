import ast
import inspect
from inspect import _ParameterKind as PK
from .functions_called import functions_called
from .decompile_simple_ops import BytecodeToAST


def wrap_body(func):
    body = BytecodeToAST(any).visit_reverse()
    args = ast.arguments(
        args=[],
        defaults=[],
        kw_defaults=[],
        kwarg=None,
        kwonlyargs=[],
        posonlyargs=[],
        vararg=None,
    )
    return ast.FunctionDef(
        name=any.__name__,
        decorator_list=[],
        args=args,
        body=body,
        returns=None,
        type_comment=None,
    )


def decompile_function(any):
    body = BytecodeToAST(any).visit_reverse()
    sig = inspect.signature(any)

    pos = [p for p in sig.parameters.values() if p.kind is PK.VAR_POSITIONAL]
    pos = pos[0] if pos else None

    kw = [p for p in sig.parameters.values() if p.kind is PK.VAR_KEYWORD]
    kw = kw[0] if kw else None

    p_or_k = [p for p in sig.parameters.values() if p.kind is PK.POSITIONAL_OR_KEYWORD]
    k_only = [p for p in sig.parameters.values() if p.kind is PK.KEYWORD_ONLY]
    args = ast.arguments(
        args=[ast.arg(arg=p.name, annotation=None, type_comment=None) for p in p_or_k],
        defaults=[ast.Constant(value=p.default, kind=None) for p in p_or_k if p.default is not inspect._empty],
        kwarg=ast.arg(arg=kw.name, annotation=None, type_comment=None) if kw else None,
        kwonlyargs=[ast.arg(arg=p.name, annotation=None, type_comment=None) for p in k_only],
        kw_defaults=[ast.Constant(value=p.default, kind=None) for p in k_only if p.default is not inspect._empty],
        vararg=ast.arg(arg=pos.name, annotation=None, type_comment=None) if pos else None,
        posonlyargs=[],
    )
    return ast.FunctionDef(
        name=any.__name__,
        decorator_list=[],
        args=args,
        body=body,
        returns=None,
        type_comment=None,
    )


def decompile_function_recursive(any, ignore_modules=('numpy', 'torch', 'jax')):
    body = _decompile_function_recursive(any, ignore_modules)
    mod = ast.Module(body=body, type_ignores=[])
    return mod


def _decompile_function_recursive(any, ignore_modules):
    body = []
    for func in functions_called(any):
        new_body = _decompile_function_recursive(func, ignore_modules)
        body.extend(new_body)

    ast_func = decompile_function(any)
    body.append(ast_func)
    return body
