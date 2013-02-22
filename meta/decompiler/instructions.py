'''
Created on Jul 14, 2011

@author: sean
'''
from __future__ import print_function

from meta.decompiler.simple_instructions import SimpleInstructions
from meta.decompiler.control_flow_instructions import CtrlFlowInstructions
import _ast
from meta.asttools import print_ast
from meta.utils import py3, py3op, py2op
from meta.decompiler.expression_mutator import ExpressionMutator
from ast import copy_location as cpy_loc

function_ops = ['CALL_FUNCTION', 'CALL_FUNCTION_KW', 'CALL_FUNCTION_VAR', 'CALL_FUNCTION_VAR_KW']

def merge_ifs(stmnts):
    last = stmnts.pop()
    
    while len(stmnts):
        stmnt = stmnts.pop()
        if isinstance(stmnt, _ast.If):
            if stmnt.orelse and not isinstance(stmnt.orelse[0], _ast.If):
                break
            stmnt.orelse.append(last)
            last = stmnt
    stmnts.append(last)
    return stmnts 
        
    
def pop_doc(stmnts):

    doc = pop_assignment(stmnts, '__doc__')

    assert isinstance(doc, _ast.Str) or doc is None

    return doc

def pop_assignment(stmnts, name):

    for i in range(len(stmnts)):
        stmnt = stmnts[i]
        if isinstance(stmnt, _ast.Assign) and len(stmnt.targets) == 1 \
            and isinstance(stmnt.targets[0], _ast.Name) \
            and isinstance(stmnt.targets[0].ctx, _ast.Store):
            if stmnt.targets[0].id == name:
                stmnts.pop(i)
                return stmnt.value

    return None

def pop_return(stmnts):

    ns = len(stmnts)
    for i in range(ns - 1, -1, -1):
        stmnt = stmnts[i]
        if isinstance(stmnt, _ast.Return):
            return stmnts.pop(i)
    return None


def make_module(code):
        from meta.decompiler.disassemble import disassemble
        instructions = Instructions(disassemble(code))
        stmnts = instructions.stmnt()

        doc = pop_doc(stmnts)
        pop_return(stmnts)

#        stmnt = ast.Stmt(stmnts, 0)

        if doc is not None:
            stmnts = [_ast.Expr(value=doc, lineno=doc.lineno, col_offset=0)] + stmnts

        ast_obj = _ast.Module(body=stmnts, lineno=0, col_offset=0)

        return ast_obj

@py2op
def make_function(code, defaults=None, lineno=0):
        from meta.decompiler.disassemble import disassemble

        instructions = Instructions(disassemble(code))

        stmnts = instructions.stmnt()

        if code.co_flags & 2:
            vararg = None
            kwarg = None

        varnames = list(code.co_varnames[:code.co_argcount])
        co_locals = list(code.co_varnames[code.co_argcount:])

        #have var args
        if code.co_flags & 4:
            vararg = co_locals.pop(0)

        #have kw args
        if code.co_flags & 8:
            kwarg = co_locals.pop()

        args = [_ast.Name(id=argname, ctx=_ast.Param(), lineno=lineno, col_offset=0) for argname in varnames]
            
        args = _ast.arguments(args=args,
                              defaults=defaults if defaults else [],
                              kwarg=kwarg,
                              vararg=vararg,
                              lineno=lineno, col_offset=0
                              )
        if code.co_name == '<lambda>':
            stmnts = merge_ifs(stmnts)

            body = _ast.Return(ExpressionMutator().visit(stmnts[0]))
            cpy_loc(body, stmnts[0])
            
            ast_obj = _ast.Lambda(args=args, body=body, lineno=lineno, col_offset=0)
        else:

            if instructions.seen_yield:
                return_ = stmnts[-1]

                assert isinstance(return_, _ast.Return)
                assert isinstance(return_.value, _ast.Name)
                assert return_.value.id == 'None'
                return_.value = None
            ast_obj = _ast.FunctionDef(name=code.co_name, args=args, body=stmnts, decorator_list=[], lineno=lineno, col_offset=0)

        return ast_obj

@make_function.py3op
def make_function(code, defaults=None, annotations=(), kw_defaults=(), lineno=0):
        from meta.decompiler.disassemble import disassemble

        instructions = Instructions(disassemble(code))

        stmnts = instructions.stmnt()

        if code.co_flags & 2:
            vararg = None
            kwarg = None

        varnames = list(code.co_varnames[:code.co_argcount])
        kwonly_varnames = list(code.co_varnames[code.co_argcount:code.co_argcount + code.co_kwonlyargcount])
        co_locals = list(code.co_varnames[code.co_argcount + code.co_kwonlyargcount:])

        assert (len(kw_defaults) % 2) == 0
        
        kw_defaults = list(kw_defaults)
        kw_default_dict = {}
        
        while kw_defaults:
            name = kw_defaults.pop(0)
            value = kw_defaults.pop(0)
            
            kw_default_dict[name.s] = value
        
        kw_defaults = []
        for argname in kwonly_varnames:
            kw_defaults.append(kw_default_dict.pop(argname))
        
        #have var args
        if code.co_flags & 4:
            vararg = co_locals.pop(0)

        #have kw args
        if code.co_flags & 8:
            kwarg = co_locals.pop()

        args = []
        annotation_names = [annotation.arg for annotation in annotations]
        
        for argname in varnames:
            if argname in annotation_names:
                arg = [annotation for annotation in annotations if annotation.arg == argname][0]
            else:
                arg = _ast.arg(annotation=None, arg=argname, lineno=lineno, col_offset=0) #@UndefinedVariable
                
            args.append(arg)

        kwonlyargs = []

        for argname in kwonly_varnames:
            if argname in annotation_names:
                arg = [annotation for annotation in annotations if annotation.arg == argname][0]
            else:
                arg = _ast.arg(annotation=None, arg=argname, lineno=lineno, col_offset=0) #@UndefinedVariable
                
            kwonlyargs.append(arg)
            
        if 'return' in annotation_names:
            arg = [annotation for annotation in annotations if annotation.arg == 'return'][0]
            returns = arg.annotation
        else:
            returns = None
        
        if vararg in annotation_names:
            arg = [annotation for annotation in annotations if annotation.arg == vararg][0]
            varargannotation = arg.annotation
        else:
            varargannotation = None
            
        if kwarg in annotation_names:
            arg = [annotation for annotation in annotations if annotation.arg == kwarg][0]
            kwargannotation = arg.annotation
        else:
            kwargannotation = None
        
        args = _ast.arguments(args=args,
                              defaults=defaults if defaults else [],
                              kwarg=kwarg,
                              vararg=vararg,
                              kw_defaults=kw_defaults,
                              kwonlyargs=kwonlyargs,
                              kwargannotation=kwargannotation,
                              varargannotation=varargannotation,
                              lineno=lineno, col_offset=0
                              )
        
        
        if code.co_name == '<lambda>':
            stmnts = merge_ifs(stmnts)

            body = _ast.Return(ExpressionMutator().visit(stmnts[0]))
            cpy_loc(body, stmnts[0])
            
            ast_obj = _ast.Lambda(args=args, body=body, lineno=lineno, col_offset=0)
        else:

            if instructions.seen_yield:
                return_ = stmnts[-1]

                assert isinstance(return_, _ast.Return)
                assert isinstance(return_.value, _ast.Name)
                assert return_.value.id == 'None'
                return_.value = None
            
            ast_obj = _ast.FunctionDef(name=code.co_name, args=args,
                                       body=stmnts, decorator_list=[],
                                       returns=returns,
                                       lineno=lineno, col_offset=0)

        return ast_obj

class StackLogger(list):
    def append(self, object):
        print('    + ', end='')
        print_ast(object, indent='', newline='')
        print()
        list.append(self, object)

    def pop(self, *index):
        value = list.pop(self, *index)
        print('    - ', end='')
        print_ast(value, indent='', newline='')
        print()
        return value

def bitrange(x, start, stop):
    return ((1 << (stop - start)) - 1) & (x >> start)

level = 0
class Instructions(CtrlFlowInstructions, SimpleInstructions):

    def __init__(self, ilst, stack_items=None, jump_map=False, outer_scope=None):
        self.ilst_processed = []
        self.ilst = ilst[:]
        self.orig_ilst = ilst
        self.seen_yield = False
        self.outer_scope = outer_scope

        if jump_map:
            self.jump_map = jump_map
        else:
            self.jump_map = {}

#        self.ast_stack = StackLogger()
        self._ast_stack = []

        if stack_items:
            self._ast_stack.extend(stack_items)
    
    def pop_ast_item(self):
        if self._ast_stack:
            item = self._ast_stack.pop()
        else:
            item = self.outer_scope.pop_ast_item()

#        print(' ' * level, '- ', end='')
#        print_ast(item, indent='', newline='')
#        print()

        return item
    
    def push_ast_item(self, item):
        
#        print(' ' * level, '+ ', end='')
#        print_ast(item, indent='', newline='')
#        print()

        self._ast_stack.append(item)
    
    def decompile_block(self, ilst, stack_items=None, jump_map=False):
        return Instructions(ilst, stack_items=stack_items, jump_map=jump_map, outer_scope=self)

    def stmnt(self):

        while len(self.ilst):
            instr = self.ilst.pop(0)
            self.visit(instr)

        return self._ast_stack

    def visit(self, instr):
        global level
        name = instr.opname.replace('+', '_')

        method = getattr(self, name, None)
        if method is None:
            raise AttributeError('can not handle instruction %r' % (str(instr)))
        
#        print(' ' * level, "*%s* visit:" % instr.opname, repr(instr))
#        level += 1
        method(instr)
#        level -= 1
#        print(' ' * level, "* stack:", self._ast_stack)


    def make_block(self, to, inclusive=True, raise_=True):
#        print("make_block", to,)
        block = []
        while len(self.ilst):
            instr = self.ilst.pop(0)
            block.append(instr)
            
#            instr_i = self.jump_map.get(instr.i, instr.i)
            instr_i = instr.i
            
            if to == instr_i:
                if not inclusive:
                    instr = block.pop()
                    self.ilst.insert(0, instr)
                break
        else:
            if raise_:
#                print(block)
                raise IndexError("no instrcution i=%s " % (to,))

        return block
    
    @py3op
    def MAKE_FUNCTION(self, instr):

        code = self.pop_ast_item()
        
        ndefaults = bitrange(instr.oparg, 0, 8)
        nkwonly_defaults = bitrange(instr.oparg, 8, 16)
        nannotations = bitrange(instr.oparg, 16, 32) - 1
        
        annotations = []
        for i in range(nannotations):
            annotations.insert(0, self.pop_ast_item())
        
        kw_defaults = []
        for i in range(nkwonly_defaults * 2):
            kw_defaults.insert(0, self.pop_ast_item())
            
        defaults = []
        for i in range(ndefaults):
            defaults.insert(0, self.pop_ast_item())

        function = make_function(code, defaults, lineno=instr.lineno, annotations=annotations, kw_defaults=kw_defaults)
        
        doc = code.co_consts[0] if code.co_consts else None
        
        if isinstance(doc, str):
            function.body.insert(0, _ast.Expr(value=_ast.Str(s=doc, lineno=instr.lineno, col_offset=0),
                                              lineno=instr.lineno, col_offset=0))
            
        self.push_ast_item(function)
        
    @MAKE_FUNCTION.py2op
    def MAKE_FUNCTION(self, instr):

        code = self.pop_ast_item()

        ndefaults = instr.oparg

        defaults = []
        for i in range(ndefaults):
            defaults.insert(0, self.pop_ast_item())

        function = make_function(code, defaults, lineno=instr.lineno)
        
        doc = code.co_consts[0] if code.co_consts else None
        
        if isinstance(doc, str):
            function.body.insert(0, _ast.Expr(value=_ast.Str(s=doc, lineno=instr.lineno, col_offset=0),
                                              lineno=instr.lineno, col_offset=0))

        
        self.push_ast_item(function)

    def LOAD_LOCALS(self, instr):
        self.push_ast_item('LOAD_LOCALS')
    
    @py3op
    def LOAD_BUILD_CLASS(self, instr):
        
        class_body = []
        
        body_instr = instr

        while body_instr.opname not in function_ops:
            body_instr = self.ilst.pop(0)
            class_body.append(body_instr)
            
        call_func = self.decompile_block(class_body, stack_items=[None]).stmnt()
        
        assert len(call_func) == 1
        call_func = call_func[0]
        
        func_def = call_func.args[0]
        code = func_def.body
        name = call_func.args[1].s
        bases = call_func.args[2:]
        
        keywords = call_func.keywords
        kwargs = call_func.kwargs
        starargs = call_func.starargs
                
        if isinstance(code[0], _ast.Expr):
            _name = code.pop(1)
            _doc = code.pop(1)
        elif isinstance(code[0], _ast.Assign):
            _name = code.pop(0)
        else:
            assert False
            
        ret = code.pop(-1)
        
        assert isinstance(ret, _ast.Return)
            
        class_ = _ast.ClassDef(name=name, bases=bases, body=code, decorator_list=[],
                               kwargs=kwargs, keywords=keywords, starargs=starargs,
                               lineno=instr.lineno, col_offset=0,
                               )

        self.push_ast_item(class_)
    
    @py2op
    def BUILD_CLASS(self, instr):

        call_func = self.pop_ast_item()

        assert isinstance(call_func, _ast.Call)

        func = call_func.func

        assert isinstance(func, _ast.FunctionDef)

        code = func.body
        pop_assignment(code, '__module__')
        doc = pop_doc(code)

        ret = code.pop()

        assert isinstance(ret, _ast.Return) and ret.value == 'LOAD_LOCALS'

        bases = self.pop_ast_item()

        assert isinstance(bases, _ast.Tuple)
        bases = bases.elts
        name = self.pop_ast_item()

        class_ = _ast.ClassDef(name=name, bases=bases, body=code, decorator_list=[],
                               lineno=instr.lineno, col_offset=0)

        self.push_ast_item(class_)

    def LOAD_CLOSURE(self, instr):
        self.push_ast_item('CLOSURE')

    def MAKE_CLOSURE(self, instr):
        return self.MAKE_FUNCTION(instr)
    
