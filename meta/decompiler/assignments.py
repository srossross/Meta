'''
Created on Nov 30, 2012

@author: sean
'''

from __future__ import print_function

import _ast

from meta.utils import py3, py3op
from meta.decompiler.transformers import mkexpr
from meta.decompiler import extra_nodes as nodes
from ast import copy_location

if py3:
    class _ast_Print: pass
else:
    _ast_Print = _ast.Print


def mkindex(index):
    c = lambda node: copy_location(node, index)
    if isinstance(index, _ast.Tuple):
        dims = []
        have_slice = False
        for dim in index.elts:
            if not isinstance(dim, _ast.Slice):
                dim = c(_ast.Index(value=dim))
            else:
                have_slice = True
            dims.append(dim)

        if have_slice:
            index = c(_ast.ExtSlice(dims=dims))
        else:
            index = c(_ast.Index(value=index))

    elif not isinstance(index, _ast.Slice):
        index = c(_ast.Index(value=index))
    return index

    
class AssignmentsMixin(object):

    def visit_UNPACK_SEQUENCE(self, instr):
        
        node = nodes.Unpack(nargs=instr.oparg, elts=[])
        self.push_ast_item(node)

#    def visit_STORE_ATTR(self, instr):
#
#        attrname = instr.arg
#        node = self.pop_ast_item()
#        expr = self.pop_ast_item()
#        expr = self.process_ifexpr(expr)
#
#        assattr = _ast.Attribute(value=node, attr=attrname, ctx=_ast.Store(), lineno=instr.lineno, col_offset=0)
#        set_attr = _ast.Assign(targets=[assattr], value=expr, lineno=instr.lineno, col_offset=0)
#
#        self.push_ast_item(set_attr)
    
    def _STORE_IMPORT(self, instr, value):
        if isinstance(value, _ast.ImportFrom):
            as_name = instr.arg
            name = value.names[-1].name
            if as_name != name:
                value.names[-1].asname = as_name
        else:
            as_name = instr.arg
            if value.names[0].asname is None:
                base_name = value.names[0].name.split('.')[0]
                if base_name != as_name:
                    value.names[0].asname = as_name

        self.push_ast_item(value)

    
    def visit_STORE_NAME(self, instr):

        value = self.pop_ast_item()
        
        if isinstance(value, (_ast.Import, _ast.ImportFrom)):
            return self._STORE_IMPORT(instr, value)
        elif isinstance(value, (_ast.ClassDef, _ast.FunctionDef)):
            return self._STORE_CLS(instr, value)
        
        value = mkexpr(value)
        ctx = _ast.Store()
        
        if instr.opname == 'STORE_ATTR':
            name = nodes.cpy_loc(_ast.Attribute(value, instr.arg, ctx), instr)
            value = self.pop_ast_item()
        elif instr.opname == 'STORE_SUBSCR':
            subj = self.pop_ast_item()
            index = mkindex(value)
            name = nodes.cpy_loc(_ast.Subscript(subj, index, ctx), instr)
            value = self.pop_ast_item()
        else:
            name = nodes.cpy_loc(_ast.Name(instr.arg, ctx), instr)
        
        value = mkexpr(value)
            
        if isinstance(value, nodes.Unpack) and value.nargs:
            value.elts.append(name)
            value.nargs -= 1
            if value.nargs:
                self.push_ast_item(value)
                return
        
        if isinstance(value, nodes.Unpack):
            assert value.nargs == 0, value.nargs
            tgt = _ast.Tuple(value.elts, ctx)
            targets = [nodes.cpy_loc(tgt, instr)]
            value = self.pop_ast_item()
        else:
            targets = [name]
            
        if isinstance(value, _ast.AugAssign):
            self.push_ast_item(value)
            return
        
        if isinstance(value, _ast.Assign):
            value.targets.extend(targets)
            targets = value.targets
            value = value.value
            other_item = self.pop_ast_item()
            
            if other_item is not value:
                are_tuples = len(targets) == 2 and isinstance(targets[0], _ast.Tuple) and isinstance(value, _ast.Tuple)
                if are_tuples and len(targets[0].elts) == len(value.elts):
                    # This is not nessesary, just makes the bytecode the same 
                    targets[0].elts.append(targets.pop())
                    value.elts.append(other_item)
                else:
                    targets = [nodes.cpy_loc(_ast.Tuple(targets, ctx), instr)]
                    value = nodes.cpy_loc(_ast.Tuple([value, other_item], _ast.Load()), instr)
        
        assign = _ast.Assign(targets=targets, value=value, lineno=instr.lineno, col_offset=0)
        
        self.push_ast_item(assign)
        return
    
    visit_STORE_ATTR = visit_STORE_NAME
    visit_STORE_SUBSCR = visit_STORE_NAME
    
    visit_STORE_FAST = visit_STORE_NAME
    visit_STORE_DEREF = visit_STORE_NAME


#    def visit_STORE_SUBSCR(self, instr):
#        index = self.pop_ast_item()
#        value = self.pop_ast_item()
#        expr = self.pop_ast_item()
#        
#        expr = mkexpr(expr)
#        
#        if isinstance(expr, _ast.AugAssign):
#            self.push_ast_item(expr)
#        else:
#            kw = dict(lineno=instr.lineno, col_offset=0)
#    
#            index = self.format_slice(index, kw)
#    
#            subscr = _ast.Subscript(value=value, slice=index, ctx=_ast.Store(), **kw)
#    
#            assign = _ast.Assign(targets=[subscr], value=expr, **kw)
#            self.push_ast_item(assign)

    @py3op
    def visit_STORE_LOCALS(self, instr):
        'remove Locals from class def'
        self.pop_ast_item()
        
    def visit_STORE_GLOBAL(self, instr):
        
        if not isinstance(self._ast_stack[0], _ast.Global):
            self._ast_stack.insert(0, _ast.Global(names=[]))
            
        if instr.arg not in self._ast_stack[0].names:
            self._ast_stack[0].names.append(instr.arg)
            
        self.STORE_NAME(instr)
