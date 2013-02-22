'''
Created on Nov 27, 2012

@author: sean
'''

from ast import NodeTransformer
import _ast
 
class ExpressionMutator(NodeTransformer):
    def visit_If(self, node):

        assert len(node.body) == 1
        
        assert len(node.orelse) == 1
        
        test = self.visit(node.test)
        then = self.visit(node.body[0])
        else_ = self.visit(node.orelse[0])

        if_exp = _ast.IfExp(test, then, else_, lineno=node.lineno, col_offset=0)
        return if_exp
    
    def visit_Return(self, node):
        return NodeTransformer.generic_visit(self, node.value) 
    
    def visit_FunctionDef(self, node):
        return node
    
    def generic_visit(self, node):
        if node is None:
            return node
        if isinstance(node, (str)):
            import pdb;pdb.set_trace()
            return node
        
#        if not isinstance(node, (_ast.expr, _ast.expr_context, _ast.slice, _ast.operator, _ast.boolop)):
#            raise Exception("expected a Python '_ast.expr' node (got %r)" % (type(node),))
        return NodeTransformer.generic_visit(self, node)
    
