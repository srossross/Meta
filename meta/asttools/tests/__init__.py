import unittest
import ast
import inspect
from meta.asttools import Visitor, cmp_ast, str_ast
from meta.asttools.visitors.graph_visitor import GraphGen


class NodeRecorder(Visitor):
    def __init__(self):
        self.ast_nodenames = set()

    def visitDefault(self, node):
        self.ast_nodenames.add(type(node).__name__)

        for child in self.children(node):
            self.visit(child)


def ast_types(node):
    rec = NodeRecorder()
    rec.visit(node)
    return rec.ast_nodenames


class AllTypesTested(object):
    def __init__(self):

        self.nodenames = set()

    def update(self, node):
        self.nodenames.update(ast_types(node))

    def tested(self):
        all_ast_nodes = set()
        B = ast.AST
        for item in dir(ast):
            C = getattr(ast, item)
            if inspect.isclass(C) and issubclass(C, B):
                all_ast_nodes.add(item)

        return all_ast_nodes - self.nodenames


def assert_ast_eq(testcase, orig_ast, expected_ast):

    if not cmp_ast(orig_ast, expected_ast):
        str1 = str_ast(orig_ast, indent=" ", newline="\n")
        str2 = str_ast(expected_ast, indent=" ", newline="\n")
        msg = (
            "AST Trees are not equal\n## left ########### \n%s\n## right ########### \n%s"
            % (str1, str2)
        )
        testcase.fail(msg)


try:
    import networkx

    have_networkx = True
except:
    have_networkx = False

skip_networkx = unittest.skipIf(not have_networkx, "Require networkx for these tests")


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
