'''
Created on Nov 30, 2012

@author: sean
'''


import _ast
from meta.decompiler.transformers import mkexpr
from ast import copy_location
from meta.asttools.visitors.print_visitor import print_ast

def cpy_loc(node, instr):
    node.lineno = instr.lineno
    node.col_offset = 0
    if instr.is_jump:
        node.to = instr.to 
        node.label = None
        
    return node

_ast.stmt.__repr__ = lambda self: '%s()' % (type(self).__name__)
_ast.expr.__repr__ = lambda self: '%s()' % (type(self).__name__)
_ast.Name.__repr__ = lambda self: 'Name(%s)' % (self.id)
_ast.BoolOp.__repr__ = lambda self: '%s(%r)' % (type(self.op).__name__, self.values)
_ast.Assign.__repr__ = lambda self: 'Assign(%r, %r)' % (self.targets, self.value)
_ast.Import.__repr__ = lambda self: 'Import(%r)' % (self.names,)
_ast.ImportFrom.__repr__ = lambda self: 'ImportFrom(%r, %r)' % (self.module, self.names,)
_ast.alias.__repr__ = lambda self: 'alias(%r, %r)' % (self.name, self.asname) if self.asname else repr(self.name)
_ast.Compare.__repr__ = lambda self: 'Compare(%r, %r, %r)' % (self.left, self.ops, self.comparators)
_ast.cmpop.__repr__ = lambda self: type(self).__name__
_ast.Num.__repr__ = lambda self: 'Num(%r)' %(self.n,)

class Tmp(_ast.AST):
    def __repr__(self):
        return '<nan>' 

class Unpack(_ast.AST):
    def __repr__(self):
        return 'Unpack(%r)' % (self.elts,) 

class Iter(_ast.AST):
    _attributes = 'lineno', 'col_offset'
    _fields = 'value',

class CtlFlow(_ast.AST):
    _attributes = 'lineno', 'col_offset', 'to'
    cond = True

    
class Block(CtlFlow):
    _attributes = 'lineno', 'col_offset', 'to'
    
class Loop(Block):
    _fields = 'body', 'orelse'
    
class Cond(CtlFlow):
    _attributes = 'lineno', 'col_offset', 'to'
    def __repr__(self):
        return 'Jump%s(%r)' % (self.cond, self.test,)


class JumpX(CtlFlow):
    _attributes = 'lineno', 'col_offset', 'to'
    _fields = 'test', 'cond', 'body', 'orelse'
    
    def __repr__(self):
        return '%s(%r)' % (type(self).__name__, self.test)
    
    def merge(self, node, span, stack):
        assert isinstance(node, JumpX), node
        assert not span
        
        orelse = node.orelse
        while orelse:
            orelse = orelse[0].orelse
            
        orelse.append(self)
        return node
    
    def insert_orelse(self, node, span, stack):
        print_ast(self)
        print_ast(node)
        print span
        
        assert False
    
class Jump(CtlFlow):
    _attributes = 'lineno', 'col_offset', 'to'
    _fields = 'test', 'cond', 'body', 'orelse'
    special_case = False
    def __repr__(self):
        return '%s()' % (type(self).__name__)
    
    
    def detect_special_case(self, node, span):
        if self.special_case: 
            return True
        elif len(span) == 1 and isinstance(span[0], _ast.Compare) and isinstance(node, JumpOrPop) and isinstance(node.test, _ast.Compare): 
            return True
        
        return False
    
    def special_case_merge(self,node, span, stack):
        
        if self.special_case:
            bool_op = mkboolop(node.test, self.special_case, node.cond)
            self.special_case = copy_location(bool_op, node)
            return
        else: 
            assert not self.body, self.body
            assert not self.orelse, self.orelse
            
            self.special_case = node.test
            node.test.comparators.extend(span[0].comparators)
            node.test.ops.extend(span[0].ops)
            stack.extend([None,None])
            return
        
    def special_case_finalize(self, orelse, stack):
        assert not self.body, self.body
        assert not self.orelse, self.orelse

        assert len(orelse) == 2
        assert orelse[0] is None
        return self.special_case

    def merge(self, node, span, stack):
        
        #=======================================================================
        # Special Case for chained comparison 
        #=======================================================================
        if self.detect_special_case(node, span):
            self.special_case_merge(node, span, stack)
            return 
        #=======================================================================
        # End 
        #=======================================================================
        
        if isinstance(node, Jump):
#            assert not span, span
            print_ast(node)
            print_ast(self)
#            adsff

            print span
            
            if span:
                print_ast(span[0])
            self.orelse = [node]
            
        else:
            assert not self.test
            assert not self.body
            
            body = span
            orelse = []
            
            if node.cond:
                body,orelse = orelse, body
                
                
            jif = JumpX(test=node.test, body=body, orelse=orelse, to=self.to)
            return copy_location(jif, node)
        
            self.test = node.test
            self.body = span
            self.cond = node.cond
        
    def finalize(self, orelse, stack):
        
        if self.special_case:
            return self.special_case_finalize(orelse, stack)
        
        if self.orelse:
            # This happens for nest if exprs (e.g. 1 if a else 2 if b else 3)
            assert len(self.orelse) == 1
            orelse = [self.orelse[0].finalize(orelse, stack)]
        
        if self.cond:
            body = orelse
            orelse = self.body
        else:
            body = self.body
            
        _if = _ast.If(self.test, body, orelse)
        return copy_location(_if, self)
        
        
class JumpIf(CtlFlow):
    pass

def mkboolop(left, right, cond):
    op = _ast.Or() if cond else _ast.And()
    
    left, right = mkexpr(left), mkexpr(right)
    
    if isinstance(left, _ast.BoolOp) and isinstance(left.op, type(op)):
        left.values.append(right)
        bool_op = left
    else:
        bool_op = _ast.BoolOp(op, [left, right])
    return bool_op


class PopJumpIf(JumpIf):
    _attributes = 'lineno', 'col_offset', 'to', 'cond'
    _fields = 'test',
    
    def __repr__(self):
        return '%s(%r)' % (type(self).__name__, self.test)
    
    def merge(self, node, span, stack):
        assert not span, span
        if isinstance(node, PopJumpIf): #Boolean and/or 
            bool_op = mkboolop(node.test, self.test, node.cond)
            self.test = copy_location(bool_op, node)
        elif isinstance(node, JumpX): #This is the elif clause in an if statement
            node.insert_orelse(self, span, stack)
            return node
        else:
            assert False, node
    
class JumpOrPop(JumpIf):
    _attributes = 'lineno', 'col_offset', 'to', 'cond'
    _fields = 'test',
    def __repr__(self):
        return '%s(%r)' % (type(self).__name__, self.test)
    
    def merge(self, node, span, stack):
        assert not span, span
        assert isinstance(node, (JumpIf)), node
        
        if isinstance(node.test, _ast.Compare) and isinstance(self.test, _ast.Compare) and node.test.comparators[-1] is self.test.left:
            node.test.comparators.extend(self.test.comparators)
            node.test.ops.extend(self.test.ops)
            self.test = node.test
        else:
            bool_op = mkboolop(node.test, self.test, node.cond)
            self.test = copy_location(bool_op, node)

    def finalize(self, span, stack):
        
        assert len(span) == 1
        node = span[0]
        bool_op = mkboolop(self.test, node, self.cond)
        return copy_location(bool_op, node)

def rsplit(lst, key):
    matches = [x for x in lst if key(x)]
    if matches:
        idx = lst.index(matches[-1]) 
        return lst[:idx], lst[idx], lst[idx + 1:] 
    else:
        return lst[:], None, [] 


class BUILD_MAP(_ast.AST):
    _attributes = 'lineno', 'col_offset', 'nremain'
    _fields = 'keys', 'values'


