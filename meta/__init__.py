
from meta.decompile.instructions import make_module
from meta.asttools.visitors.pysourcegen import dump_python_source

def decompile(code, mode='exec'):
    '''
    Decompile a code object into python ast.
    
    :param mode: must be 'exec' to compile a module or 'eval' to compile an expression.

    '''
    if mode == 'exec':
        return make_module(code)
    else:
        raise Exception("can not handle mode %r yet" % mode)
        
