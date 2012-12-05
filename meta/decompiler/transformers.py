'''
Created on Nov 30, 2012

@author: sean
'''
import _ast
from ast import copy_location, NodeTransformer


class ExprTransformer(NodeTransformer):
    
    def visit_If(self, node):
        assert len(node.body) == 1
        assert len(node.orelse) == 1
        
        body = self.visit(node.body[0])
        orelse = self.visit(node.orelse[0])
        _if_exp = _ast.IfExp(node.test, body, orelse)
        copy_location(_if_exp, node)
        return _if_exp
    
#    visit_If = visit_POP_JUMP_IF_FALSE
#    
#    def visit_POP_JUMP_IF_TRUE(self, node):
#
#        assert len(node.body) == 1
#        assert len(node.orelse) == 1
#        
#        not_test = _ast.UnaryOp(_ast.Not() , node.test)
#        copy_location(not_test, node)
#
#        _if_exp = _ast.IfExp(not_test, node.body[0], node.orelse[0])
#        copy_location(_if_exp, node)
#        return _if_exp
    
#    def visit_BoolOp(self, node):
#        
#        if isinstance(node.op, _ast.And):
#            i = 0 
#            while i < len(node.values) - 1:
#                left = mkexpr(node.values[i])
#                right = mkexpr(node.values[i + 1])
#                if isinstance(left, _ast.Compare) and isinstance(right, _ast.Compare):
#                    if left.comparators[-1] is right.left:
#                        node.values.pop(i + 1)
#                        left.comparators.extend(right.comparators)
#                        left.ops.extend(right.ops)
#                i += 1
#            if len(node.values) == 1:
#                return node.values[0]
##        print 'ret', node
#        
#        return node
    
    def visit_BUILD_MAP(self, node):
        return copy_location(_ast.Dict([],[]), node)

class StatementTransformer(NodeTransformer):
    pass
#    def generic_visit(self, node):
#        
#        if isinstance(node, _ast.stmt):
#            return NodeTransformer.generic_visit(self, node)
#        else:
#            return node
#    
#    def visit_Expr(self, node):
#        new_node = mkexpr(node.value)
#        copy_location(new_node, node)
#        return new_node
    
#    def visit_POP_JUMP_IF_FALSE(self, node):
#        _if = _ast.If(node.test, node.body, node.orelse)
#        copy_location(_if, node)
#        return _if
#    
#    def visit_POP_JUMP_IF_TRUE(self, node):
#        not_test = _ast.UnaryOp(_ast.Not() , node.test)
#        copy_location(not_test, node)
#        _if = _ast.If(not_test, node.body, node.orelse)
#        copy_location(_if, node)
#        return _if

mkexpr = lambda node: ExprTransformer().visit(node)
mkstmnt = lambda node: StatementTransformer().visit(node)

def pop_top(stmnt):
    if isinstance(stmnt, _ast.expr):
        node = _ast.Expr(stmnt)
        return copy_location(node, stmnt)
     
    return stmnt
