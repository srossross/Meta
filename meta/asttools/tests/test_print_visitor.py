'''
Created on Mar 11, 2015

@author: sublee
'''
from __future__ import print_function

import unittest
from meta.asttools.visitors.print_visitor import ASTPrinter


class Test(unittest.TestCase):

    def test_string_literal_with_braces(self):
        printer = ASTPrinter()
        # without skip_format.
        self.assertRaises(KeyError, printer.print, 'Hello, {world}!')
        printer.print('Hello, {world}!', world='world')
        self.assertEqual(printer.out.getvalue(), 'Hello, world!')
        # clear the buffer.
        printer.out.truncate(0)
        printer.out.seek(0)
        # with skip_format.
        printer.print('Hello, {world}!', skip_format=True, world='dummy')
        self.assertEqual(printer.out.getvalue(), 'Hello, {world}!')


if __name__ == '__main__':

    unittest.main()
