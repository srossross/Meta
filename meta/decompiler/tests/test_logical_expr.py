'''
Created on Nov 24, 2012

@author: sean
'''
from meta.testing import py2only
from meta.decompiler.tests import Base
import unittest


class Test(Base):

    def test_simple(self):
        self.statement('a == b')

    def test_chain1(self):
        self.statement('a == b > f')

    def test_chain2(self):
        self.statement('a == b > f < e')

    def test_simple_with_and(self):
        self.statement('x and a == b')

    def test_simple_with_or(self):
        self.statement('x or a == b')

    def test_simple_with_and2(self):
        self.statement('a == b and y')

    def test_simple_with_or2(self):
        self.statement('a == b or y')

    def test_chain1_and(self):
        self.statement('x and a == b > f')
        
    def test_chain1_or(self):
        self.statement('x or a == b > f')

    def test_chain1_and2(self):
        self.statement('x and a == b > f and z', 'x and (((a == b) and (b > f)) and z)')
        
    def test_chain1_or2(self):
        self.statement('x or a == b > f or z', 'x or (((a == b) and (b > f)) or z)')
    
    def test_chain2_or(self):
        self.statement('x or a == b > f < e')
        
    def test_chain2_and(self):
        self.statement('x and a == b > f < e')



if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
