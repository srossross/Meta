'''
Created on Nov 28, 2012

@author: sean
'''


from ast import NodeVisitor
import _ast
import sys

node_name = '0__node_name__'

not_py3 = sys.version_info.major < 3


class DictAst(NodeVisitor):
    def generic_visit(self, node):
        dct = {node_name: type(node).__name__}
        for attr in node._attributes:
            dct[attr] = getattr(node,attr)
        for field in node._fields:
            value = getattr(node,field)
            if isinstance(value, list):
                dct[field] = [self.generic_visit(child) for child in value]
            elif  isinstance(value, _ast.AST):
                dct[field] = self.generic_visit(value)
            else: 
                dct[field] = value
        return dct

def serialize(node):
    '''
    :param node: an _ast.AST object
    
    searialize an ast into a dictionary object
    '''
    return DictAst().visit(node)

def deserialize(obj):
    '''
    :param obj: a dctionary created by `serialize`
    
    :returns: An ast object
    '''

    if isinstance(obj, dict) and node_name in obj:
        node_type = getattr(_ast, obj.pop(node_name))
        node = node_type(**{key:deserialize(value) for key,value in obj.items()})
        return node
    elif isinstance(obj,list):
        return [deserialize(value) for value in obj]
    elif not_py3 and isinstance(obj, unicode):
        return obj.encode()
    else:
        return obj
