
import _ast

def dont_visit(self, node):
    pass

def visit_children(self, node):
    for child in self.children(node):
        self.visit(child)


class Visitor(object):

    def children(self, node):
        for field in node._fields:
            value = getattr(node, field)
            if isinstance(value, (list, tuple)):
                for item in value:
                    if isinstance(item, _ast.AST):
                        yield item
                    else:
                        pass
            elif  isinstance(value, _ast.AST):
                yield value

        return



    def visit_list(self, nodes, *args, **kwargs):
        for node in nodes:
            self.visit(node, *args, **kwargs)

    def visit(self, node, *args, **kwargs):
        node_name = type(node).__name__

        attr = 'visit' + node_name

        if hasattr(self, attr):
            mehtod = getattr(self, 'visit' + node_name)
            return mehtod(node, *args, **kwargs)
        elif hasattr(self, 'visitDefault'):
            mehtod = getattr(self, 'visitDefault')
            return mehtod(node, *args, **kwargs)
        else:
            mehtod = getattr(self, 'visit' + node_name)
            return mehtod(node, *args, **kwargs)


