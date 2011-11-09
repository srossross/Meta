import unittest
import sys
import _ast
from meta.decompile import make_module
from meta.asttools import cmp_ast, print_ast
from meta.testing import py2, py2only


if py2:
    from StringIO import StringIO
else:
    from io import StringIO
    
filename = 'tests.py'

class Base(unittest.TestCase):

    def assertAstEqual(self, left, right):

        if not isinstance(left, _ast.AST):
            raise self.failureException("%s is not an _ast.AST instance" % (left))
        if not isinstance(right, _ast.AST):
            raise self.failureException("%s is not an _ast.AST instance" % (right))
        result = cmp_ast(left, right)

        if not result:
            
            lstream = StringIO()
            print_ast(left, indent='', file=lstream, newline='')

            rstream = StringIO()
            print_ast(right, indent='', file=rstream, newline='')

            lstream.seek(0)
            rstream.seek(0)
            msg = 'Ast Not Equal:\nGenerated: %r\nExpected:  %r' % (lstream.read(), rstream.read())
            raise self.failureException(msg)



    def statement(self, stmnt, equiv=None):

        if equiv is None:
            expected_ast = compile(stmnt, filename, 'exec', _ast.PyCF_ONLY_AST)
            code = compile(expected_ast, filename, 'exec')
            mod_ast = make_module(code)
        else:
            expected_ast_ = compile(stmnt, filename, 'exec', _ast.PyCF_ONLY_AST)
            code = compile(expected_ast_, filename, 'exec')
            mod_ast = make_module(code)

            expected_ast = compile(equiv, filename, 'exec', _ast.PyCF_ONLY_AST)

        self.assertAstEqual(mod_ast, expected_ast)

        code = compile(mod_ast, filename, 'exec')
        expected_code = compile(expected_ast, filename, 'exec')

        self.assertEqual(code.co_code, expected_code.co_code)
