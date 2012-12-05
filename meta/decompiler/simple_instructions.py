'''
Created on Jul 14, 2011

@author: sean
'''
from __future__ import print_function

from opcode import *
import _ast
import sys

from meta.utils import py3, py3op, py2op
from meta.asttools.visitors.print_visitor import print_ast, dump_ast
from meta.asttools import cmp_ast
from meta.decompiler.expression_mutator import ExpressionMutator
from meta.decompiler.transformers import mkexpr
from meta.decompiler import extra_nodes as nodes

if py3:
    class _ast_Print: pass
else:
    _ast_Print = _ast.Print

def isNone(node):
    if node is None:
        return True
    elif isinstance(node, _ast.Name) and (node.id == 'None') and isinstance(node.ctx, _ast.Load):
        return True

    return False

def BINARY_(OP):

    def visit_BINARY_OP(self, instr):
        right = self.pop_ast_item()
        left = self.pop_ast_item()

        add = _ast.BinOp(left=left, right=right, op=OP(), lineno=instr.lineno, col_offset=0)

        self.push_ast_item(add)
    return visit_BINARY_OP

def INPLACE_(OP):

    def visit_INPLACE_OP(self, instr):
        right = self.pop_ast_item()
        left = self.pop_ast_item()

        left.ctx = _ast.Store()
        aug_assign = _ast.AugAssign(target=left, op=OP(), value=right, lineno=instr.lineno, col_offset=0)

        self.push_ast_item(aug_assign)

    return visit_INPLACE_OP


def UNARY_(OP):

    def visit_UNARY_OP(self, instr):
        expr = self.pop_ast_item()
        not_ = _ast.UnaryOp(op=OP(), operand=expr, lineno=instr.lineno, col_offset=0)

        self.push_ast_item(not_)

    return visit_UNARY_OP

CMP_OPMAP = {'>=' :_ast.GtE,
             '<=' :_ast.LtE,
             '>' :_ast.Gt,
             '<' :_ast.Lt,
             '==': _ast.Eq,
             '!=': _ast.NotEq,
             'in': _ast.In,
             'not in': _ast.NotIn,
             'is':_ast.Is,
             'is not':_ast.IsNot,
             }

def make_const(arg, lineno=0, col_offset=0):
    kw = {'lineno':lineno, 'col_offset':col_offset}
    
    if isinstance(arg, str):
        const = _ast.Str(s=arg, **kw)
    elif isinstance(arg, (int, float, complex)):
        const = _ast.Num(n=arg, **kw)
    elif arg is None:
        const = _ast.Name(id='None', ctx=_ast.Load(), **kw)
    elif isinstance(arg, tuple):
        elts = []
        for item in arg:
            elts.append(make_const(item, **kw))
        const = _ast.Tuple(elts=elts, ctx=_ast.Load(), **kw)
    else:
        const = arg
    
    return const

class SimpleInstructionMixin(object):

    def visit_LOAD_CONST(self, instr):
        const = make_const(instr.arg, lineno=instr.lineno, col_offset=0)
        self.push_ast_item(const)

    def visit_LOAD_NAME(self, instr):
        name = _ast.Name(id=instr.arg, ctx=_ast.Load(), lineno=instr.lineno, col_offset=0)
        self.push_ast_item(name)

    def visit_LOAD_DEREF(self, instr):
        name = _ast.Name(id=instr.arg, ctx=_ast.Load(), lineno=instr.lineno, col_offset=0)
        self.push_ast_item(name)

    def visit_CALL_FUNCTION_VAR(self, instr):

        arg = self.pop_ast_item()

        self.visit_CALL_FUNCTION(instr)
        callfunc = self.pop_ast_item()

        callfunc.starargs = arg

        self.push_ast_item(callfunc)

    def visit_CALL_FUNCTION_KW(self, instr):

        kwarg = self.pop_ast_item()

        self.visit_CALL_FUNCTION(instr)
        callfunc = self.pop_ast_item()

        callfunc.kwargs = kwarg

        self.push_ast_item(callfunc)

    def visit_CALL_FUNCTION_VAR_KW(self, instr):
        kwarg = self.pop_ast_item()
        arg = self.pop_ast_item()

        self.visit_CALL_FUNCTION(instr)
        callfunc = self.pop_ast_item()

        callfunc.starargs = arg
        callfunc.kwargs = kwarg

        self.push_ast_item(callfunc)

    def visit_CALL_FUNCTION(self, instr):
        nkwargs = instr.oparg >> 8
        nargs = (~(nkwargs << 8)) & instr.oparg


        args = []
        keywords = []

        for _ in range(nkwargs):
            expr = self.pop_ast_item()
            name = self.pop_ast_item()

            keyword = _ast.keyword(arg=name.s, value=expr, lineno=instr.lineno)
            keywords.insert(0, keyword)

        for _ in range(nargs):
            arg = self.pop_ast_item()
            args.insert(0, arg)


        if len(args) == 1 and isinstance(args[0], (_ast.FunctionDef, _ast.ClassDef)):
            function = args[0]

            if function.decorator_list is None:
                function.decorator_list = []

            node = self.pop_ast_item()
            function.decorator_list.insert(0, node)

            self.push_ast_item(function)
            return


        node = self.pop_ast_item()
        callfunc = _ast.Call(func=node, args=args, keywords=keywords, starargs=None, kwargs=None,
                             lineno=instr.lineno, col_offset=0)

        self.push_ast_item(callfunc)

    def visit_LOAD_FAST(self, instr):
        name = _ast.Name(id=instr.arg, ctx=_ast.Load(), lineno=instr.lineno, col_offset=0)
        self.push_ast_item(name)

    def visit_LOAD_GLOBAL(self, instr):
        name = _ast.Name(id=instr.arg, ctx=_ast.Load(), lineno=instr.lineno, col_offset=0)
        self.push_ast_item(name)

    
    def visit_RETURN_VALUE(self, instr):
        value = self.pop_ast_item()
        value = mkexpr(value)
        ret = _ast.Return(value=value, lineno=instr.lineno, col_offset=0)

        self.push_ast_item(ret)

    def visit_LOAD_ATTR(self, instr):

        name = self.pop_ast_item()

        attr = instr.arg

        get_attr = _ast.Attribute(value=name, attr=attr, ctx=_ast.Load(), lineno=instr.lineno, col_offset=0)

        self.push_ast_item(get_attr)

    def visit_IMPORT_NAME(self, instr):

        from_ = self.pop_ast_item()

        hmm = self.pop_ast_item()

        names = [_ast.alias(name=instr.arg, asname=None)]
        import_ = _ast.Import(names=names, lineno=instr.lineno, col_offset=0)

        import_.from_ = not isNone(from_)

        self.push_ast_item(import_)

    def visit_IMPORT_FROM(self, instr):
        import_ = self.pop_ast_item()
        
        alias = _ast.alias(instr.arg, None)
        assert len(import_.names) == 1, import_.names
        
        if isinstance(import_, _ast.ImportFrom):
            from_ = import_
            from_.names.append(alias)
        else:
            modname = import_.names[0].name
            from_ = _ast.ImportFrom(module=modname, names=[alias], level=0, lineno=instr.lineno, col_offset=0)

        self.push_ast_item(from_)
#        self.push_ast_item(import_)

    def visit_IMPORT_STAR(self, instr):
        import_ = self.pop_ast_item()

        names = import_.names
        alias = _ast.alias(name='*', asname=None)

        from_ = _ast.ImportFrom(module=names[0].name, names=[alias], level=0, lineno=instr.lineno, col_offset=0)

        self.push_ast_item(from_)

#    def visit_process_ifexpr(self, node):
#        if node == 'LOAD_LOCALS': #Special directive
#            return node
#        
#        return ExpressionMutator().visit(node)

    def POP_TOP(self, instr):

        node = self.pop_ast_item()
        node = self.process_ifexpr(node)

        if isinstance(node, _ast.Import):
            return

        if isinstance(node, _ast_Print):
            _ = self.pop_ast_item()
            self.push_ast_item(node)
            return

        discard = _ast.Expr(value=node, lineno=instr.lineno, col_offset=0)
        self.push_ast_item(discard)

    def _visit_ROT_TWO(self, instr):
        
        one = self.pop_ast_item()
        two = self.pop_ast_item()
        
        if self.ilst[0].opname == 'STORE_NAME':
            
            kw = dict(lineno=instr.lineno, col_offset=0)
            stores = []
            while self.ilst[0].opname == 'STORE_NAME':
                stores.append(self.ilst.pop(0))
                
            assert len(stores) <= 3, stores
            elts_load = [one, two]
            if len(stores) == 3:
                elts_load.insert(0, self.pop_ast_item())
                
            tup_load = _ast.Tuple(elts=elts_load[::-1], ctx=_ast.Load(), **kw)
            
            elts_store = [_ast.Name(id=store.arg, ctx=_ast.Store(), **kw) for store in stores]
            tup_store = _ast.Tuple(elts=elts_store, ctx=_ast.Store(), **kw)
            
            assgn = _ast.Assign(value=tup_load, targets=[tup_store], **kw)
            self.push_ast_item(assgn)
#            self.push_ast_item(tup_store)
        else:
            self.push_ast_item(one)
            self.push_ast_item(two)

    visit_BINARY_ADD = BINARY_(_ast.Add)
    visit_BINARY_SUBTRACT = BINARY_(_ast.Sub)
    visit_BINARY_DIVIDE = BINARY_(_ast.Div)
    visit_BINARY_TRUE_DIVIDE = BINARY_(_ast.Div)
    visit_BINARY_MULTIPLY = BINARY_(_ast.Mult)
    visit_BINARY_FLOOR_DIVIDE = BINARY_(_ast.FloorDiv)
    visit_BINARY_POWER = BINARY_(_ast.Pow)

    visit_BINARY_AND = BINARY_(_ast.BitAnd)
    visit_BINARY_OR = BINARY_(_ast.BitOr)
    visit_BINARY_XOR = BINARY_(_ast.BitXor)

    visit_BINARY_LSHIFT = BINARY_(_ast.LShift)
    visit_BINARY_RSHIFT = BINARY_(_ast.RShift)
    visit_BINARY_MODULO = BINARY_(_ast.Mod)

    visit_INPLACE_ADD = INPLACE_(_ast.Add)
    visit_INPLACE_SUBTRACT = INPLACE_(_ast.Sub)
    visit_INPLACE_DIVIDE = INPLACE_(_ast.Div)
    visit_INPLACE_FLOOR_DIVIDE = INPLACE_(_ast.FloorDiv)
    visit_INPLACE_MULTIPLY = INPLACE_(_ast.Mult)

    visit_INPLACE_AND = INPLACE_(_ast.BitAnd)
    visit_INPLACE_OR = INPLACE_(_ast.BitOr)
    visit_INPLACE_LSHIFT = INPLACE_(_ast.LShift)
    visit_INPLACE_RSHIFT = INPLACE_(_ast.RShift)
    visit_INPLACE_POWER = INPLACE_(_ast.Pow)
    visit_INPLACE_MODULO = INPLACE_(_ast.Mod)
    visit_INPLACE_XOR = INPLACE_(_ast.BitXor)

    visit_UNARY_NOT = UNARY_(_ast.Not)
    visit_UNARY_NEGATIVE = UNARY_(_ast.USub)
    visit_UNARY_INVERT = UNARY_(_ast.Invert)
    visit_UNARY_POSITIVE = UNARY_(_ast.UAdd)

    def visit_COMPARE_OP(self, instr):
        
        op = instr.arg

        right = self.pop_ast_item()
        
        expr = self.pop_ast_item()

        OP = CMP_OPMAP[op]
        compare = _ast.Compare(left=expr, ops=[OP()], comparators=[right], lineno=instr.lineno, col_offset=0)

        self.push_ast_item(compare)
        
    def visit_YIELD_VALUE(self, instr):
        value = self.pop_ast_item()

        yield_ = _ast.Yield(value=value, lineno=instr.lineno, col_offset=0)

        self.push_ast_item(yield_)

        self.seen_yield = True

    def visit_BUILD_LIST(self, instr):

        nitems = instr.oparg

        nodes = []
        list_ = _ast.List(elts=nodes, ctx=_ast.Load(), lineno=instr.lineno, col_offset=0)
        for i in range(nitems):
            nodes.insert(0, self.pop_ast_item())

        self.push_ast_item(list_)

    def visit_BUILD_TUPLE(self, instr):

        nitems = instr.oparg

        nodes = []
        list_ = _ast.Tuple(elts=nodes, ctx=_ast.Load(), lineno=instr.lineno, col_offset=0)
        for i in range(nitems):
            nodes.insert(0, self.pop_ast_item())

        if any([item == 'CLOSURE' for item in nodes]):
            assert all([item == 'CLOSURE' for item in nodes])
            return

        self.push_ast_item(list_)

    def visit_BUILD_SET(self, instr):

        nitems = instr.oparg

        nodes = []
        list_ = _ast.Set(elts=nodes, ctx=_ast.Load(), lineno=instr.lineno, col_offset=0)
        for i in range(nitems):
            nodes.insert(0, self.pop_ast_item())

        self.push_ast_item(list_)

    def visit_BUILD_MAP(self, instr):
        build_map = nodes.BUILD_MAP(keys=[], values=[], nremain=instr.oparg)
        self.push_ast_item(nodes.cpy_loc(build_map, instr))
        
    def visit_STORE_MAP(self, instr):
        
        key = self.pop_ast_item()
        value = self.pop_ast_item()
        
        build_map = self.pop_ast_item()
        build_map.nremain -= 1
        
        build_map.keys.append(key)
        build_map.values.append(value)
        
        if build_map.nremain > 0:
            node = build_map 
        if build_map.nremain == 0:
            node = _ast.Dict(keys=build_map.keys, values=build_map.values, lineno=instr.lineno, col_offset=0)
            
        self.push_ast_item(node)

    def visit_DELETE_NAME(self, instr):

        name = _ast.Name(id=instr.arg, ctx=_ast.Del(), lineno=instr.lineno, col_offset=0)

        delete = _ast.Delete(targets=[name], lineno=instr.lineno, col_offset=0)
        self.push_ast_item(delete)

    def visit_DELETE_FAST(self, instr):

        name = _ast.Name(id=instr.arg, ctx=_ast.Del(), lineno=instr.lineno, col_offset=0)

        delete = _ast.Delete(targets=[name], lineno=instr.lineno, col_offset=0)
        self.push_ast_item(delete)

    def visit_DELETE_ATTR(self, instr):

        expr = self.pop_ast_item()
        attr = _ast.Attribute(value=expr, attr=instr.arg, ctx=_ast.Del(), lineno=instr.lineno, col_offset=0)

        delete = _ast.Delete(targets=[attr], lineno=instr.lineno, col_offset=0)
        self.push_ast_item(delete)

    def visit_EXEC_STMT(self, instr):
        locals_ = mkexpr(self.pop_ast_item())
        globals_ = mkexpr(self.pop_ast_item())
        expr = mkexpr(self.pop_ast_item())

        if locals_ is globals_:
            locals_ = None

        if isinstance(globals_, _ast.Name) and getattr(globals_, 'id',) == 'None':
            globals_ = None

        exec_ = _ast.Exec(body=expr, globals=globals_, locals=locals_, lineno=instr.lineno, col_offset=0)
        
        self.push_ast_item(exec_)

    def visit_DUP_TOP(self, instr):

        expr = self.pop_ast_item()

        self.push_ast_item(expr)
        self.push_ast_item(expr)
    
    @py3op
    def visit_DUP_TOP_TWO(self, instr):
        
        expr1 = self.pop_ast_item()
        expr2 = self.pop_ast_item()

        self.push_ast_item(expr2)
        self.push_ast_item(expr1)
        self.push_ast_item(expr2)
        self.push_ast_item(expr1)

    
    def visit_DUP_TOPX(self, instr):

        exprs = []
        for i in range(instr.oparg):
            expr = self.pop_ast_item()
            exprs.insert(0, expr)
            
        self._ast_stack.extend(exprs)
        self._ast_stack.extend(exprs)
        
    def visit_ROT_TWO(self, instr):
        n0 = self.pop_ast_item()
        n1 = self.pop_ast_item()
        self.push_ast_item(n0)
        self.push_ast_item(n1)

    def visit_ROT_THREE(self, instr):
        expr1 = self.pop_ast_item()
        expr2 = self.pop_ast_item()
        expr3 = self.pop_ast_item()
        
        self.push_ast_item(expr1)
        self.push_ast_item(expr3)
        self.push_ast_item(expr2)
        
        
    def visit_ROT_FOUR(self, instr):
        expr1 = self.pop_ast_item()
        expr2 = self.pop_ast_item()
        expr3 = self.pop_ast_item()
        expr4 = self.pop_ast_item()
        
        self.push_ast_item(expr1)
        self.push_ast_item(expr4)
        self.push_ast_item(expr3)
        self.push_ast_item(expr2)
        
    def format_slice(self, index, kw):

        if isinstance(index, _ast.Tuple):
            dims = []
            have_slice = False
            for dim in index.elts:
                if not isinstance(dim, _ast.Slice):
                    dim = _ast.Index(value=dim, **kw)
                else:
                    have_slice = True
                dims.append(dim)

            if have_slice:
                index = _ast.ExtSlice(dims=dims, **kw)
            else:
                index = _ast.Index(value=index, **kw)

        elif not isinstance(index, _ast.Slice):
            index = _ast.Index(value=index, **kw)
        return index

    def visit_BINARY_SUBSCR(self, instr):

        index = self.pop_ast_item()
        value = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)

        index = self.format_slice(index, kw)

        subscr = _ast.Subscript(value=value, slice=index, ctx=_ast.Load(), **kw)

        self.push_ast_item(subscr)

    def visit_SLICE_0(self, instr):
        'obj[:]'
        value = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)
        slice = _ast.Slice(lower=None, step=None, upper=None, **kw)
        subscr = _ast.Subscript(value=value, slice=slice, ctx=_ast.Load(), **kw)

        self.push_ast_item(subscr)

    def visit_SLICE_1(self, instr):
        'obj[lower:]'
        lower = self.pop_ast_item()
        value = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)
        slice = _ast.Slice(lower=lower, step=None, upper=None, **kw)
        subscr = _ast.Subscript(value=value, slice=slice, ctx=_ast.Load(), **kw)

        self.push_ast_item(subscr)

    def visit_SLICE_2(self, instr):
        'obj[:stop]'
        upper = self.pop_ast_item()
        value = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)
        slice = _ast.Slice(lower=None, step=None, upper=upper, **kw)
        subscr = _ast.Subscript(value=value, slice=slice, ctx=_ast.Load(), **kw)

        self.push_ast_item(subscr)


    def visit_SLICE_3(self, instr):
        'obj[lower:upper]'
        upper = self.pop_ast_item()
        lower = self.pop_ast_item()
        value = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)
        slice = _ast.Slice(lower=lower, step=None, upper=upper, **kw)
        subscr = _ast.Subscript(value=value, slice=slice, ctx=_ast.Load(), **kw)

        self.push_ast_item(subscr)


    def visit_BUILD_SLICE(self, instr):

        step = None
        upper = None
        lower = None

        if instr.oparg > 2:
            step = self.pop_ast_item()
        if instr.oparg > 1:
            upper = self.pop_ast_item()
        if instr.oparg > 0:
            lower = self.pop_ast_item()

        upper = None if isNone(upper) else upper
        lower = None if isNone(lower) else lower

        kw = dict(lineno=instr.lineno, col_offset=0)
        slice = _ast.Slice(lower=lower, step=step, upper=upper, **kw)

        self.push_ast_item(slice)

    def visit_STORE_SLICE_0(self, instr):
        'obj[:] = expr'
        value = self.pop_ast_item()
        expr = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)
        slice = _ast.Slice(lower=None, step=None, upper=None, **kw)
        subscr = _ast.Subscript(value=value, slice=slice, ctx=_ast.Store(), **kw)

        assign = _ast.Assign(targets=[subscr], value=expr, **kw)
        self.push_ast_item(assign)

    def visit_STORE_SLICE_1(self, instr):
        'obj[lower:] = expr'
        lower = self.pop_ast_item()
        value = self.pop_ast_item()
        expr = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)
        slice = _ast.Slice(lower=lower, step=None, upper=None, **kw)
        subscr = _ast.Subscript(value=value, slice=slice, ctx=_ast.Store(), **kw)

        assign = _ast.Assign(targets=[subscr], value=expr, **kw)
        self.push_ast_item(assign)


    def visit_STORE_SLICE_2(self, instr):
        'obj[:upper] = expr'
        upper = self.pop_ast_item()
        value = self.pop_ast_item()
        expr = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)
        slice = _ast.Slice(lower=None, step=None, upper=upper, **kw)
        subscr = _ast.Subscript(value=value, slice=slice, ctx=_ast.Store(), **kw)

        assign = _ast.Assign(targets=[subscr], value=expr, **kw)
        self.push_ast_item(assign)

    def visit_STORE_SLICE_3(self, instr):
        'obj[lower:upper] = expr'

        upper = self.pop_ast_item()
        lower = self.pop_ast_item()
        value = self.pop_ast_item()
        expr = self.pop_ast_item()
        
        kw = dict(lineno=instr.lineno, col_offset=0)
        slice = _ast.Slice(lower=lower, step=None, upper=upper, **kw)
        subscr = _ast.Subscript(value=value, slice=slice, ctx=_ast.Store(), **kw)
        
        if isinstance(expr, _ast.AugAssign):
            assign = expr
            result = cmp_ast(expr.target, subscr)
            
            assert result
        else:
            assign = _ast.Assign(targets=[subscr], value=expr, **kw)
            
        self.push_ast_item(assign)

    def visit_DELETE_SLICE_0(self, instr):
        'obj[:] = expr'
        value = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)
        slice = _ast.Slice(lower=None, step=None, upper=None, **kw)
        subscr = _ast.Subscript(value=value, slice=slice, ctx=_ast.Del(), **kw)

        delete = _ast.Delete(targets=[subscr], **kw)
        self.push_ast_item(delete)

    def visit_DELETE_SLICE_1(self, instr):
        'obj[lower:] = expr'
        lower = self.pop_ast_item()
        value = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)
        slice = _ast.Slice(lower=lower, step=None, upper=None, **kw)
        subscr = _ast.Subscript(value=value, slice=slice, ctx=_ast.Del(), **kw)

        delete = _ast.Delete(targets=[subscr], **kw)
        self.push_ast_item(delete)


    def visit_DELETE_SLICE_2(self, instr):
        'obj[:upper] = expr'
        upper = self.pop_ast_item()
        value = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)
        slice = _ast.Slice(lower=None, step=None, upper=upper, **kw)
        subscr = _ast.Subscript(value=value, slice=slice, ctx=_ast.Del(), **kw)

        delete = _ast.Delete(targets=[subscr], **kw)
        self.push_ast_item(delete)

    def visit_DELETE_SLICE_3(self, instr):
        'obj[lower:upper] = expr'
        upper = self.pop_ast_item()
        lower = self.pop_ast_item()
        value = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)
        slice = _ast.Slice(lower=lower, step=None, upper=upper, **kw)
        subscr = _ast.Subscript(value=value, slice=slice, ctx=_ast.Del(), **kw)

        delete = _ast.Delete(targets=[subscr], **kw)
        self.push_ast_item(delete)

    def visit_DELETE_SUBSCR(self, instr):
        index = self.pop_ast_item()
        value = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)

        index = self.format_slice(index, kw)

        subscr = _ast.Subscript(value=value, slice=index, ctx=_ast.Del(), **kw)

        delete = _ast.Delete(targets=[subscr], **kw)
        self.push_ast_item(delete)
    
    @py2op
    def visit_RAISE_VARARGS(self, instr):
        nargs = instr.oparg

        tback = None
        inst = None
        type = None
        if nargs > 2:
            tback = self.pop_ast_item()
        if nargs > 1:
            inst = self.pop_ast_item()
        if nargs > 0:
            type = self.pop_ast_item()

        raise_ = _ast.Raise(tback=tback, inst=inst, type=type,
                            lineno=instr.lineno, col_offset=0)
        self.push_ast_item(raise_)

    @visit_RAISE_VARARGS.py3op
    def visit_RAISE_VARARGS(self, instr):
        nargs = instr.oparg
        
        cause = None
        exc = None
        
        if nargs > 1:
            cause = self.pop_ast_item()
        if nargs > 0:
            exc = self.pop_ast_item()

        raise_ = _ast.Raise(exc=exc, cause=cause,
                            lineno=instr.lineno, col_offset=0)
        self.push_ast_item(raise_)
    
    @py3op
    def visit_EXTENDED_ARG(self, instr):
        code = self.pop_ast_item()
        argument_names = self.pop_ast_item()
        
        assert len(argument_names.elts) == (instr.oparg - 1)
        args = []
        kw = dict(lineno=instr.lineno, col_offset=0)
        for argument_name in argument_names.elts[::-1]:
            annotation = self.pop_ast_item()
            arg = _ast.arg(annotation=annotation, arg=argument_name.s, **kw)  # @UndefinedVariable
            args.append(arg)

        for arg in args:
            self.push_ast_item(arg)
        self.push_ast_item(code)
        
    @visit_EXTENDED_ARG.py2op
    def visit_EXTENDED_ARG(self, instr):
        raise Exception("This is not available in python 2.x")
        
