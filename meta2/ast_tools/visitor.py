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
            elif isinstance(value, _ast.AST):
                yield value

        return

    def visit_list(self, nodes, *args, **kwargs):

        result = []
        for node in nodes:
            result.append(self.visit(node, *args, **kwargs))
        return result

    def visit(self, node, *args, **kwargs):
        node_name = type(node).__name__

        attr = "visit" + node_name

        if hasattr(self, attr):
            method = getattr(self, "visit" + node_name)
            return method(node, *args, **kwargs)
        elif hasattr(self, "visitDefault"):
            method = getattr(self, "visitDefault")
            return method(node, *args, **kwargs)
        else:
            method = getattr(self, "visit" + node_name)
            return method(node, *args, **kwargs)
