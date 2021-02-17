'''
Decompiler module.

This module can decompile arbitrary code objects into a python ast. 
'''

from meta.decompiler.instructions import make_module, make_function

import _ast
import struct
import time
import sys
import marshal



def decompile_func(func):
    '''
    Decompile a function into ast.FunctionDef node.
    
    :param func: python function (can not be a built-in)
    
    :return: ast.FunctionDef instance.
    '''
    if hasattr(func, 'func_code'):
        code = func.func_code
    else:
        code = func.__code__

    # For python 3
#    defaults = func.func_defaults if sys.version_info.major < 3 else func.__defaults__
#    if defaults:
#        default_names = code.co_varnames[:code.co_argcount][-len(defaults):]
#    else:
#        default_names = []
#    defaults = [_ast.Name(id='%s_default' % name, ctx=_ast.Load() , lineno=0, col_offset=0) for name in default_names]
    ast_node = make_function(code, defaults=[], lineno=code.co_firstlineno)

    return ast_node

def compile_func(ast_node, filename, globals, **defaults):
    '''
    Compile a function from an ast.FunctionDef instance.
    
    :param ast_node: ast.FunctionDef instance
    :param filename: path where function source can be found. 
    :param globals: will be used as func_globals
    
    :return: A python function object
    '''

    funcion_name = ast_node.name
    if sys.version_info >= (3, 8):
        module = _ast.Module(body=[ast_node], type_ignores=[])
    else:
        module = _ast.Module(body=[ast_node])

    ctx = {'%s_default' % key : arg for key, arg in defaults.items()}

    code = compile(module, filename, 'exec')

    eval(code, globals, ctx)

    function = ctx[funcion_name]

    return function

#from imp import get_magic
#
#def extract(binary):
#    
#    if len(binary) <= 8:
#        raise Exception("Binary pyc must be greater than 8 bytes (got %i)" % len(binary))
#    
#    magic = binary[:4]
#    MAGIC = get_magic()
#    
#    if magic != MAGIC:
#        raise Exception("Python version mismatch (%r != %r) Is this a pyc file?" % (magic, MAGIC))
#    
#    modtime = time.asctime(time.localtime(struct.unpack('i', binary[4:8])[0]))
#
#    code = marshal.loads(binary[8:])
#    
#    return modtime, code

def decompile_pyc(bin_pyc, output=sys.stdout):
    '''
    decompile apython pyc or pyo binary file.
    
    :param bin_pyc: input file objects
    :param output: output file objects
    '''
    
    from meta.asttools import python_source
    
    bin = bin_pyc.read()
    
    code = marshal.loads(bin[8:])
    
    mod_ast = make_module(code)
    
    python_source(mod_ast, file=output)
