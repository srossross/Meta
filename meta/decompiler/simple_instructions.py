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

if py3:
    class _ast_Print: pass
    basestring = str
else:
    _ast_Print = _ast.Print

def isNone(node):
    if node is None:
        return True
    elif isinstance(node, _ast.Name) and (node.id == 'None') and isinstance(node.ctx, _ast.Load):
        return True

    return False

def BINARY_(OP):

    def BINARY_OP(self, instr):
        right = self.pop_ast_item()
        left = self.pop_ast_item()

        add = _ast.BinOp(left=left, right=right, op=OP(), lineno=instr.lineno, col_offset=0)

        self.push_ast_item(add)
    return BINARY_OP

def INPLACE_(OP):

    def INPLACE_OP(self, instr):
        right = self.pop_ast_item()
        left = self.pop_ast_item()

        left.ctx = _ast.Store()
        aug_assign = _ast.AugAssign(target=left, op=OP(), value=right, lineno=instr.lineno, col_offset=0)

        self.push_ast_item(aug_assign)

    return INPLACE_OP


def UNARY_(OP):

    def UNARY_OP(self, instr):
        expr = self.pop_ast_item()
        not_ = _ast.UnaryOp(op=OP(), operand=expr, lineno=instr.lineno, col_offset=0)

        self.push_ast_item(not_)

    return UNARY_OP

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

    if isinstance(arg, basestring):
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
    
class SimpleInstructions(object):

    def LOAD_CONST(self, instr):
        const = make_const(instr.arg, lineno=instr.lineno, col_offset=0)

        self.push_ast_item(const)

    def LOAD_NAME(self, instr):
        name = _ast.Name(id=instr.arg, ctx=_ast.Load(), lineno=instr.lineno, col_offset=0)
        self.push_ast_item(name)

    def LOAD_DEREF(self, instr):
        name = _ast.Name(id=instr.arg, ctx=_ast.Load(), lineno=instr.lineno, col_offset=0)
        self.push_ast_item(name)

    def CALL_FUNCTION_VAR(self, instr):

        arg = self.pop_ast_item()

        self.CALL_FUNCTION(instr)
        callfunc = self.pop_ast_item()

        callfunc.starargs = arg

        self.push_ast_item(callfunc)

    def CALL_FUNCTION_KW(self, instr):

        kwarg = self.pop_ast_item()

        self.CALL_FUNCTION(instr)
        callfunc = self.pop_ast_item()

        callfunc.kwargs = kwarg

        self.push_ast_item(callfunc)

    def CALL_FUNCTION_VAR_KW(self, instr):
        kwarg = self.pop_ast_item()
        arg = self.pop_ast_item()

        self.CALL_FUNCTION(instr)
        callfunc = self.pop_ast_item()

        callfunc.starargs = arg
        callfunc.kwargs = kwarg

        self.push_ast_item(callfunc)

    def CALL_FUNCTION(self, instr):
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

    def LOAD_FAST(self, instr):
        name = _ast.Name(id=instr.arg, ctx=_ast.Load(), lineno=instr.lineno, col_offset=0)
        self.push_ast_item(name)

    def LOAD_GLOBAL(self, instr):
        name = _ast.Name(id=instr.arg, ctx=_ast.Load(), lineno=instr.lineno, col_offset=0)
        self.push_ast_item(name)

    def STORE_FAST(self, instr):
        self.STORE_NAME(instr)

    def STORE_DEREF(self, instr):
        self.STORE_NAME(instr)

    def STORE_NAME(self, instr):

        value = self.pop_ast_item()
        value = self.process_ifexpr(value)
        
        if isinstance(value, _ast.Import):

            if value.from_:
                assert isinstance(self._ast_stack[-1], _ast.ImportFrom)
                from_ = self.pop_ast_item()

                as_name = instr.arg
                name = from_.names[0].name
                if as_name != name:
                    from_.names[0].asname = as_name

                self.push_ast_item(from_)
            else:
                as_name = instr.arg
                if value.names[0].asname is None:
                    base_name = value.names[0].name.split('.')[0]
                    if base_name != as_name:
                        value.names[0].asname = as_name

            self.push_ast_item(value)
            
        elif isinstance(value, (_ast.Attribute)) and isinstance(value.value, (_ast.Import)):
            asname = instr.arg
            value = value.value
            value.names[0].asname = asname
            
            self.push_ast_item(value)
            
        elif isinstance(value, (_ast.ClassDef, _ast.FunctionDef)):
            as_name = instr.arg
            value.name = as_name
            self.push_ast_item(value)
        elif isinstance(value, _ast.AugAssign):
            self.push_ast_item(value)
        elif isinstance(value, _ast.Assign):
            _ = self.pop_ast_item()
            assname = _ast.Name(instr.arg, _ast.Store(), lineno=instr.lineno, col_offset=0)
            if _ is value.value or isinstance(_, _ast.Assign):
                value.targets.append(assname)
            else:
                if not isinstance(value.targets, _ast.Tuple):
                    value.targets = [_ast.Tuple(value.targets, _ast.Store())]
                    value.value = _ast.Tuple([value.value], _ast.Load())
                    value.targets[0].lineno = value.targets[0].elts[0].lineno
                    value.targets[0].col_offset = value.targets[0].elts[0].col_offset
                    value.value.lineno = value.value.elts[0].lineno
                    value.value.col_offset = value.value.elts[0].col_offset
                value.targets[0].elts.append(assname)
                value.value.elts.append(_)

            self.push_ast_item(value)
        else:

            assname = _ast.Name(instr.arg, _ast.Store(), lineno=instr.lineno, col_offset=0)

            assign = _ast.Assign(targets=[assname], value=value, lineno=instr.lineno, col_offset=0)
            self.push_ast_item(assign)
    
    @py3op
    def STORE_LOCALS(self, instr):
        'remove Locals from class def'
        self.pop_ast_item()
        
    def STORE_GLOBAL(self, instr):
        
        if not isinstance(self._ast_stack[0], _ast.Global):
            self._ast_stack.insert(0, _ast.Global(names=[]))
            
        if instr.arg not in self._ast_stack[0].names:
            self._ast_stack[0].names.append(instr.arg)
            
        self.STORE_NAME(instr)
    
    def RETURN_VALUE(self, instr):
        value = self.pop_ast_item()
        value = self.process_ifexpr(value)
        ret = _ast.Return(value=value, lineno=instr.lineno, col_offset=0)

        self.push_ast_item(ret)

    def LOAD_ATTR(self, instr):

        name = self.pop_ast_item()

        attr = instr.arg

        get_attr = _ast.Attribute(value=name, attr=attr, ctx=_ast.Load(), lineno=instr.lineno, col_offset=0)

        self.push_ast_item(get_attr)

    def STORE_ATTR(self, instr):

        attrname = instr.arg
        node = self.pop_ast_item()
        expr = self.pop_ast_item()
        expr = self.process_ifexpr(expr)

        assattr = _ast.Attribute(value=node, attr=attrname, ctx=_ast.Store(), lineno=instr.lineno, col_offset=0)
        set_attr = _ast.Assign(targets=[assattr], value=expr, lineno=instr.lineno, col_offset=0)

        self.push_ast_item(set_attr)

    def IMPORT_NAME(self, instr):

        from_ = self.pop_ast_item()

        hmm = self.pop_ast_item()

        names = [_ast.alias(name=instr.arg, asname=None)]
        import_ = _ast.Import(names=names, lineno=instr.lineno, col_offset=0)

        import_.from_ = not isNone(from_)

        self.push_ast_item(import_)

    def IMPORT_FROM(self, instr):
        import_ = self.pop_ast_item()

        names = [_ast.alias(instr.arg, None)]
        modname = import_.names[0].name
        from_ = _ast.ImportFrom(module=modname, names=names, level=0, lineno=instr.lineno, col_offset=0)

        self.push_ast_item(from_)
        self.push_ast_item(import_)

    def IMPORT_STAR(self, instr):
        import_ = self.pop_ast_item()

        names = import_.names
        alias = _ast.alias(name='*', asname=None)

        from_ = _ast.ImportFrom(module=names[0].name, names=[alias], level=0, lineno=instr.lineno, col_offset=0)

        self.push_ast_item(from_)

    def process_ifexpr(self, node):
        if node == 'LOAD_LOCALS': #Special directive
            return node
        
        return ExpressionMutator().visit(node)

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

    def ROT_TWO(self, instr):
        
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

    BINARY_ADD = BINARY_(_ast.Add)
    BINARY_SUBTRACT = BINARY_(_ast.Sub)
    BINARY_DIVIDE = BINARY_(_ast.Div)
    BINARY_TRUE_DIVIDE = BINARY_(_ast.Div)
    BINARY_MULTIPLY = BINARY_(_ast.Mult)
    BINARY_FLOOR_DIVIDE = BINARY_(_ast.FloorDiv)
    BINARY_POWER = BINARY_(_ast.Pow)

    BINARY_AND = BINARY_(_ast.BitAnd)
    BINARY_OR = BINARY_(_ast.BitOr)
    BINARY_XOR = BINARY_(_ast.BitXor)

    BINARY_LSHIFT = BINARY_(_ast.LShift)
    BINARY_RSHIFT = BINARY_(_ast.RShift)
    BINARY_MODULO = BINARY_(_ast.Mod)

    INPLACE_ADD = INPLACE_(_ast.Add)
    INPLACE_SUBTRACT = INPLACE_(_ast.Sub)
    INPLACE_DIVIDE = INPLACE_(_ast.Div)
    INPLACE_FLOOR_DIVIDE = INPLACE_(_ast.FloorDiv)
    INPLACE_MULTIPLY = INPLACE_(_ast.Mult)

    INPLACE_AND = INPLACE_(_ast.BitAnd)
    INPLACE_OR = INPLACE_(_ast.BitOr)
    INPLACE_LSHIFT = INPLACE_(_ast.LShift)
    INPLACE_RSHIFT = INPLACE_(_ast.RShift)
    INPLACE_POWER = INPLACE_(_ast.Pow)
    INPLACE_MODULO = INPLACE_(_ast.Mod)
    INPLACE_XOR = INPLACE_(_ast.BitXor)

    UNARY_NOT = UNARY_(_ast.Not)
    UNARY_NEGATIVE = UNARY_(_ast.USub)
    UNARY_INVERT = UNARY_(_ast.Invert)
    UNARY_POSITIVE = UNARY_(_ast.UAdd)

    def COMPARE_OP(self, instr):
        
        op = instr.arg

        right = self.pop_ast_item()
        
        expr = self.pop_ast_item()

        OP = CMP_OPMAP[op]
        compare = _ast.Compare(left=expr, ops=[OP()], comparators=[right], lineno=instr.lineno, col_offset=0)

        
        self.push_ast_item(compare)
        


    def YIELD_VALUE(self, instr):
        value = self.pop_ast_item()

        yield_ = _ast.Yield(value=value, lineno=instr.lineno, col_offset=0)

        self.push_ast_item(yield_)

        self.seen_yield = True

    def BUILD_LIST(self, instr):

        nitems = instr.oparg

        nodes = []
        list_ = _ast.List(elts=nodes, ctx=_ast.Load(), lineno=instr.lineno, col_offset=0)
        for i in range(nitems):
            nodes.insert(0, self.pop_ast_item())

        self.push_ast_item(list_)

    def BUILD_TUPLE(self, instr):

        nitems = instr.oparg

        nodes = []
        list_ = _ast.Tuple(elts=nodes, ctx=_ast.Load(), lineno=instr.lineno, col_offset=0)
        for i in range(nitems):
            nodes.insert(0, self.pop_ast_item())

        if any([item == 'CLOSURE' for item in nodes]):
            assert all([item == 'CLOSURE' for item in nodes])
            return

        self.push_ast_item(list_)

    def BUILD_SET(self, instr):

        nitems = instr.oparg

        nodes = []
        list_ = _ast.Set(elts=nodes, ctx=_ast.Load(), lineno=instr.lineno, col_offset=0)
        for i in range(nitems):
            nodes.insert(0, self.pop_ast_item())

        self.push_ast_item(list_)

    def BUILD_MAP(self, instr):

        nitems = instr.oparg
        keys = []
        values = []
        for i in range(nitems):
            map_instrs = []
            while 1:
                new_instr = self.ilst.pop(0)

                if new_instr.opname == 'STORE_MAP':
                    break

                map_instrs.append(new_instr)

            items = self.decompile_block(map_instrs).stmnt()
            assert len(items) == 2

            values.append(items[0])
            keys.append(items[1])


        list_ = _ast.Dict(keys=keys, values=values, lineno=instr.lineno, col_offset=0)
        self.push_ast_item(list_)

    def UNPACK_SEQUENCE(self, instr):
        nargs = instr.oparg

        nodes = []
        ast_tuple = _ast.Tuple(elts=nodes, ctx=_ast.Store(), lineno=instr.lineno, col_offset=0)
        for i in range(nargs):
            nex_instr = self.ilst.pop(0)
            self.push_ast_item(None)
            self.visit(nex_instr)

            node = self.pop_ast_item()
            nodes.append(node.targets[0])

        expr = self.pop_ast_item()
        if isinstance(expr, _ast.Assign):
            assgn = expr 
            assgn.targets.append(ast_tuple)
            
            value_dup = self.pop_ast_item()
            
            assert cmp_ast(assgn.value, value_dup)
            
        else:
            assgn = _ast.Assign(targets=[ast_tuple], value=expr, lineno=instr.lineno, col_offset=0)
        self.push_ast_item(assgn)

    def DELETE_NAME(self, instr):

        name = _ast.Name(id=instr.arg, ctx=_ast.Del(), lineno=instr.lineno, col_offset=0)

        delete = _ast.Delete(targets=[name], lineno=instr.lineno, col_offset=0)
        self.push_ast_item(delete)

    def DELETE_FAST(self, instr):

        name = _ast.Name(id=instr.arg, ctx=_ast.Del(), lineno=instr.lineno, col_offset=0)

        delete = _ast.Delete(targets=[name], lineno=instr.lineno, col_offset=0)
        self.push_ast_item(delete)

    def DELETE_ATTR(self, instr):

        expr = self.pop_ast_item()
        attr = _ast.Attribute(value=expr, attr=instr.arg, ctx=_ast.Del(), lineno=instr.lineno, col_offset=0)

        delete = _ast.Delete(targets=[attr], lineno=instr.lineno, col_offset=0)
        self.push_ast_item(delete)

    def EXEC_STMT(self, instr):
        locals_ = self.pop_ast_item()
        globals_ = self.pop_ast_item()
        expr = self.pop_ast_item()

        if locals_ is globals_:
            locals_ = None

        if isinstance(globals_, _ast.Name) and getattr(globals_, 'id',) == 'None':
            globals_ = None

        exec_ = _ast.Exec(body=expr, globals=globals_, locals=locals_, lineno=instr.lineno, col_offset=0)
        
        self.push_ast_item(exec_)

    def DUP_TOP(self, instr):

        expr = self.pop_ast_item()

        self.push_ast_item(expr)
        self.push_ast_item(expr)
    
    @py3op
    def DUP_TOP_TWO(self, instr):
        
        expr1 = self.pop_ast_item()
        expr2 = self.pop_ast_item()

        self.push_ast_item(expr2)
        self.push_ast_item(expr1)
        self.push_ast_item(expr2)
        self.push_ast_item(expr1)

    
    def DUP_TOPX(self, instr):

        exprs = []
        for i in range(instr.oparg):
            expr = self.pop_ast_item()
            exprs.insert(0, expr)
            
        self._ast_stack.extend(exprs)
        self._ast_stack.extend(exprs)
        
    def ROT_THREE(self, instr):
        expr1 = self.pop_ast_item()
        expr2 = self.pop_ast_item()
        expr3 = self.pop_ast_item()
        
        self.push_ast_item(expr1)
        self.push_ast_item(expr3)
        self.push_ast_item(expr2)
        
        
    def ROT_FOUR(self, instr):
        expr1 = self.pop_ast_item()
        expr2 = self.pop_ast_item()
        expr3 = self.pop_ast_item()
        expr4 = self.pop_ast_item()
        
        self.push_ast_item(expr1)
        self.push_ast_item(expr4)
        self.push_ast_item(expr3)
        self.push_ast_item(expr2)
        
        


    def PRINT_ITEM(self, instr):

        item = self.pop_ast_item()

        if self._ast_stack:
            print_ = self._ast_stack[-1]
        else:
            print_ = None

        if isinstance(print_, _ast_Print) and not print_.nl and print_.dest == None:
            print_.values.append(item)
        else:
            print_ = _ast_Print(dest=None, values=[item], nl=False, lineno=instr.lineno, col_offset=0)
            self.push_ast_item(print_)

    def PRINT_NEWLINE(self, instr):
        item = self._ast_stack[-1]

        if isinstance(item, _ast_Print) and not item.nl and item.dest == None:
            item.nl = True
        else:
            print_ = _ast_Print(dest=None, values=[], nl=True, lineno=instr.lineno, col_offset=0)
            self.push_ast_item(print_)

    def PRINT_ITEM_TO(self, instr):

        stream = self.pop_ast_item()

        print_ = None

        if isinstance(stream, _ast_Print) and not stream.nl:
            print_ = stream
            stream = self.pop_ast_item()
            dup_print = self.pop_ast_item()
            assert dup_print is print_
            self.push_ast_item(stream)
        else:
            print_ = _ast_Print(dest=stream, values=[], nl=False, lineno=instr.lineno, col_offset=0)

        item = self.pop_ast_item()

        print_.values.append(item)
        self.push_ast_item(print_)

    def PRINT_NEWLINE_TO(self, instr):

        item = self.pop_ast_item()
        stream = self.pop_ast_item()

        self.push_ast_item(item)

        if isinstance(item, _ast_Print) and not item.nl and item.dest is stream:
            item.nl = True
        else:
            print_ = _ast_Print(dest=stream, values=[], nl=True, lineno=instr.lineno, col_offset=0)
            self.push_ast_item(print_)


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

    def BINARY_SUBSCR(self, instr):

        index = self.pop_ast_item()
        value = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)

        index = self.format_slice(index, kw)

        subscr = _ast.Subscript(value=value, slice=index, ctx=_ast.Load(), **kw)

        self.push_ast_item(subscr)

    def SLICE_0(self, instr):
        'obj[:]'
        value = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)
        slice = _ast.Slice(lower=None, step=None, upper=None, **kw)
        subscr = _ast.Subscript(value=value, slice=slice, ctx=_ast.Load(), **kw)

        self.push_ast_item(subscr)

    def SLICE_1(self, instr):
        'obj[lower:]'
        lower = self.pop_ast_item()
        value = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)
        slice = _ast.Slice(lower=lower, step=None, upper=None, **kw)
        subscr = _ast.Subscript(value=value, slice=slice, ctx=_ast.Load(), **kw)

        self.push_ast_item(subscr)

    def SLICE_2(self, instr):
        'obj[:stop]'
        upper = self.pop_ast_item()
        value = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)
        slice = _ast.Slice(lower=None, step=None, upper=upper, **kw)
        subscr = _ast.Subscript(value=value, slice=slice, ctx=_ast.Load(), **kw)

        self.push_ast_item(subscr)


    def SLICE_3(self, instr):
        'obj[lower:upper]'
        upper = self.pop_ast_item()
        lower = self.pop_ast_item()
        value = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)
        slice = _ast.Slice(lower=lower, step=None, upper=upper, **kw)
        subscr = _ast.Subscript(value=value, slice=slice, ctx=_ast.Load(), **kw)

        self.push_ast_item(subscr)


    def BUILD_SLICE(self, instr):

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

    def STORE_SLICE_0(self, instr):
        'obj[:] = expr'
        value = self.pop_ast_item()
        expr = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)
        slice = _ast.Slice(lower=None, step=None, upper=None, **kw)
        subscr = _ast.Subscript(value=value, slice=slice, ctx=_ast.Store(), **kw)

        assign = _ast.Assign(targets=[subscr], value=expr, **kw)
        self.push_ast_item(assign)

    def STORE_SLICE_1(self, instr):
        'obj[lower:] = expr'
        lower = self.pop_ast_item()
        value = self.pop_ast_item()
        expr = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)
        slice = _ast.Slice(lower=lower, step=None, upper=None, **kw)
        subscr = _ast.Subscript(value=value, slice=slice, ctx=_ast.Store(), **kw)

        assign = _ast.Assign(targets=[subscr], value=expr, **kw)
        self.push_ast_item(assign)


    def STORE_SLICE_2(self, instr):
        'obj[:upper] = expr'
        upper = self.pop_ast_item()
        value = self.pop_ast_item()
        expr = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)
        slice = _ast.Slice(lower=None, step=None, upper=upper, **kw)
        subscr = _ast.Subscript(value=value, slice=slice, ctx=_ast.Store(), **kw)

        assign = _ast.Assign(targets=[subscr], value=expr, **kw)
        self.push_ast_item(assign)

    def STORE_SLICE_3(self, instr):
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

    def DELETE_SLICE_0(self, instr):
        'obj[:] = expr'
        value = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)
        slice = _ast.Slice(lower=None, step=None, upper=None, **kw)
        subscr = _ast.Subscript(value=value, slice=slice, ctx=_ast.Del(), **kw)

        delete = _ast.Delete(targets=[subscr], **kw)
        self.push_ast_item(delete)

    def DELETE_SLICE_1(self, instr):
        'obj[lower:] = expr'
        lower = self.pop_ast_item()
        value = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)
        slice = _ast.Slice(lower=lower, step=None, upper=None, **kw)
        subscr = _ast.Subscript(value=value, slice=slice, ctx=_ast.Del(), **kw)

        delete = _ast.Delete(targets=[subscr], **kw)
        self.push_ast_item(delete)


    def DELETE_SLICE_2(self, instr):
        'obj[:upper] = expr'
        upper = self.pop_ast_item()
        value = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)
        slice = _ast.Slice(lower=None, step=None, upper=upper, **kw)
        subscr = _ast.Subscript(value=value, slice=slice, ctx=_ast.Del(), **kw)

        delete = _ast.Delete(targets=[subscr], **kw)
        self.push_ast_item(delete)

    def DELETE_SLICE_3(self, instr):
        'obj[lower:upper] = expr'
        upper = self.pop_ast_item()
        lower = self.pop_ast_item()
        value = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)
        slice = _ast.Slice(lower=lower, step=None, upper=upper, **kw)
        subscr = _ast.Subscript(value=value, slice=slice, ctx=_ast.Del(), **kw)

        delete = _ast.Delete(targets=[subscr], **kw)
        self.push_ast_item(delete)

    def STORE_SUBSCR(self, instr):
        index = self.pop_ast_item()
        value = self.pop_ast_item()
        expr = self.pop_ast_item()
        
        expr = self.process_ifexpr(expr)
        
        if isinstance(expr, _ast.AugAssign):
            self.push_ast_item(expr)
        else:
            kw = dict(lineno=instr.lineno, col_offset=0)
    
            index = self.format_slice(index, kw)
    
            subscr = _ast.Subscript(value=value, slice=index, ctx=_ast.Store(), **kw)
    
            assign = _ast.Assign(targets=[subscr], value=expr, **kw)
            self.push_ast_item(assign)

    def DELETE_SUBSCR(self, instr):
        index = self.pop_ast_item()
        value = self.pop_ast_item()

        kw = dict(lineno=instr.lineno, col_offset=0)

        index = self.format_slice(index, kw)

        subscr = _ast.Subscript(value=value, slice=index, ctx=_ast.Del(), **kw)

        delete = _ast.Delete(targets=[subscr], **kw)
        self.push_ast_item(delete)
    
    @py2op
    def RAISE_VARARGS(self, instr):
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

    @RAISE_VARARGS.py3op
    def RAISE_VARARGS(self, instr):
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
    def EXTENDED_ARG(self, instr):
        code = self.pop_ast_item()
        argument_names = self.pop_ast_item()
        
        assert len(argument_names.elts) == (instr.oparg - 1)
        args = []
        kw = dict(lineno=instr.lineno, col_offset=0)
        for argument_name in argument_names.elts[::-1]:
            annotation = self.pop_ast_item()
            arg = _ast.arg(annotation=annotation, arg=argument_name.s, **kw) #@UndefinedVariable
            args.append(arg)

        for arg in args:
            self.push_ast_item(arg)
        self.push_ast_item(code)
        
    @EXTENDED_ARG.py2op
    def EXTENDED_ARG(self, instr):
        raise Exception("This is not available in python 2.x")
        
