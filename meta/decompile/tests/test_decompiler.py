'''
Created on Jul 14, 2011

@author: sean
'''
import unittest
import sys
import _ast
from meta.decompile import make_module
from meta.asttools import cmp_ast, print_ast
from meta.testing import py2, py2only
from meta.decompile.tests import Base


if py2:
    from StringIO import StringIO
else:
    from io import StringIO
    
filename = 'tests.py'


class Simple(Base):

    def test_assign(self):
        'a = b'
        self.statement('a = b')

    def test_assign2(self):
        'a = b = c'
        self.statement('a = b')

    def test_assign3(self):
        'a = b,d = c'
        self.statement('a = b')

    def test_assign4(self):
        'a.y = b,d = c'
        self.statement('a = b')

    def test_setattr(self):
        'a.b = b'
        self.statement('a.b = b')

    def test_getattr(self):
        'a = b.b'
        self.statement('a = b.b')

    def test_add(self):
        'a+b'
        self.statement('a+b')

    def test_sub(self):
        'a-b'
        self.statement('a-b')

    def test_mul(self):
        'a*b'
        self.statement('a*b')

    def test_div(self):
        'a/b'
        self.statement('a/b')

    def test_floordiv(self):
        'a//b'
        self.statement('a//b')

    def test_pow(self):
        'a**b'
        self.statement('a**b')

    def test_eq(self):
        'a==b'
        self.statement('a==b')

    def test_iadd(self):
        'a+=b'
        self.statement('a+=b')

    def test_isub(self):
        'a-=b'
        self.statement('a-=b')

    def test_binary_and(self):
        'a & b'
        self.statement('a & b')

    def test_binary_lshift(self):
        'a << b'
        self.statement('a << b')

    def test_binary_rshift(self):
        'a >> b'
        self.statement('a >> b')

    def test_binary_mod(self):
        'a % b'
        self.statement('a % b')

    def test_binary_or(self):
        'a | b'
        self.statement('a | b')

    def test_binary_xor(self):
        'a ^ b'
        self.statement('a ^ b')

    def test_build_list(self):
        '[x,y, 1, None]'
        self.statement('[x,y, 1, None]')

    def test_build_tuple(self):
        '(x,y, 1, None)'
        self.statement('(x,y, 1, None)')

    def test_build_set(self):
        '{x,y, 1, None}'
        self.statement('{x,y, 1, None}')

    def test_build_dict(self):
        '{a:x,b:y, c:1, d:None}'
        self.statement('{a:x,b:y, c:1, d:None}')

    def test_unpack_tuple(self):
        '(a,b) = c'
        self.statement('(a,b) = c')


    def test_delete_name(self):
        stmnt = 'del a'
        self.statement(stmnt)

    def test_delete_attr(self):
        stmnt = 'del a.a'
        self.statement(stmnt)

    @py2only
    def test_exec1(self):
        stmnt = 'exec a'
        self.statement(stmnt)
    
    @py2only
    def test_exec2(self):
        stmnt = 'exec a in b'
        self.statement(stmnt)
    
    @py2only
    def test_exec3(self):
        stmnt = 'exec a in b,c'
        self.statement(stmnt)

    def test_import_star(self):

        stmnt = 'from a import *'
        self.statement(stmnt)

        stmnt = 'from a.v import *'
        self.statement(stmnt)

    def test_import(self):
        stmnt = 'import a'
        self.statement(stmnt)

    def test_import_as(self):
        stmnt = 'import a as b'
        self.statement(stmnt)

    def test_import_from(self):
        stmnt = 'from c import a as b'
        self.statement(stmnt)

    def test_import_from2(self):
        stmnt = 'from c import a \nimport x'
        self.statement(stmnt)

    def test_not(self):
        stmnt = 'not a'
        self.statement(stmnt)


    def test_call(self):
        stmnt = 'a()'
        self.statement(stmnt)

    def test_call_args(self):
        stmnt = 'a(a, b)'
        self.statement(stmnt)

    def test_call_args1(self):
        stmnt = 'a(a, b, c=33)'
        self.statement(stmnt)

    def test_call_varargs(self):
        stmnt = 'a(*a)'
        self.statement(stmnt)

    def test_call_kwargs(self):
        stmnt = 'a(a, b=0, **a)'
        self.statement(stmnt)

    def test_call_var_kwargs(self):
        stmnt = 'a(a, b=0, *d, **a)'
        self.statement(stmnt)
    
    @py2only
    def test_print(self):
        stmnt = 'print foo,'
        self.statement(stmnt)
    
    @py2only
    def test_printnl(self):
        stmnt = 'print foo'
        self.statement(stmnt)
    
    @py2only
    def test_printitems(self):
        stmnt = 'print foo, bar, bas,'
        self.statement(stmnt)
    
    @py2only
    def test_printitemsnl(self):
        stmnt = 'print foo, bar, bas'
        self.statement(stmnt)
    
    @py2only
    def test_print_to(self):
        stmnt = 'print >> stream, foo,'
        self.statement(stmnt)
    
    @py2only
    def test_print_to_nl(self):
        stmnt = 'print >> stream, foo'
        self.statement(stmnt)
    
    @py2only
    def test_printitems_to(self):
        stmnt = 'print >> stream, foo, bar, bas,'
        self.statement(stmnt)
    
    @py2only
    def test_printitems_to_nl(self):
        stmnt = 'print >> stream, foo, bar, bas'
        self.statement(stmnt)

    def test_subscr(self):
        stmnt = 'x[y]'
        self.statement(stmnt)

    def test_subscr_assign(self):
        stmnt = 'x[y] =z'
        self.statement(stmnt)

    def test_subscr_del(self):
        stmnt = 'del x[y]'
        self.statement(stmnt)

    def test_subscr0(self):
        stmnt = 'x[:]'
        self.statement(stmnt)

    def test_subscr_assign0(self):
        stmnt = 'x[:] =z'
        self.statement(stmnt)

    def test_subscr_del0(self):
        stmnt = 'del x[:]'
        self.statement(stmnt)

    def test_subscr1(self):
        stmnt = 'x[a:]'
        self.statement(stmnt)

    def test_subscr_assign1(self):
        stmnt = 'x[a:] =z'
        self.statement(stmnt)

    def test_subscr_del1(self):
        stmnt = 'del x[a:]'
        self.statement(stmnt)

    def test_subscr2(self):
        stmnt = 'x[:a]'
        self.statement(stmnt)

    def test_subscr_assign2(self):
        stmnt = 'x[:a] =z'
        self.statement(stmnt)

    def test_subscr_del2(self):
        stmnt = 'del x[:a]'
        self.statement(stmnt)

    def test_subscr3(self):
        stmnt = 'x[b:a]'
        self.statement(stmnt)

    def test_subscr_assign3(self):
        stmnt = 'x[b:a] =z'
        self.statement(stmnt)

    def test_subscr_del3(self):
        stmnt = 'del x[b:a]'
        self.statement(stmnt)

    def test_subscrX(self):
        stmnt = 'x[b:a:c]'
        self.statement(stmnt)

    def test_subscr_assignX(self):
        stmnt = 'x[b:a:c] =z'
        self.statement(stmnt)

    def test_subscr_delX(self):
        stmnt = 'del x[b:a:c]'
        self.statement(stmnt)

    def test_subscrX2(self):
        stmnt = 'x[::]'
        self.statement(stmnt)

    def test_subscr_assignX2(self):
        stmnt = 'x[::] =z'
        self.statement(stmnt)

    def test_subscr_delX2(self):
        stmnt = 'del x[::]'
        self.statement(stmnt)

    def test_subscr_tuple(self):
        stmnt = 'x[x,a]'
        self.statement(stmnt)

    def test_subscr_tuple_set(self):
        stmnt = 'x[x,a] =z'
        self.statement(stmnt)

    def test_subscr_tuple_del(self):
        stmnt = 'del x[x,a]'
        self.statement(stmnt)

    def test_subscrX3(self):
        stmnt = 'x[x,:a]'
        self.statement(stmnt)

    def test_subscr_assignX3(self):
        stmnt = 'x[x,:a] =z'
        self.statement(stmnt)

    def test_subscr_delX3(self):
        stmnt = 'del x[x,:a]'
        self.statement(stmnt)

class LogicJumps(Base):
        
    def test_logic1(self):
        'a and b or c'
        self.statement('a and b or c')

    def test_logic2(self):
        'a or (b or c)'
        self.statement('a or (b or c)')


    def test_if_expr_discard(self):

        stmnt = 'a if b else c'
        self.statement(stmnt)

    def test_if_expr_assign(self):

        stmnt = 'd = a if b else c'
        self.statement(stmnt)

    def test_if_expr_assignattr(self):

        stmnt = 'd.a = a if b else c'
        self.statement(stmnt)

class Function(Base):

    def test_function(self):
        stmnt = '''
def foo():
    return None
'''
        self.statement(stmnt)

    def test_function_args(self):
        stmnt = '''
def foo(a, b, c='asdf'):
    return None
'''
        self.statement(stmnt)


    def test_function_var_args(self):
        stmnt = '''
def foo(a, b, *c):
    return None
'''
        self.statement(stmnt)


    def test_function_varkw_args(self):
        stmnt = '''
def foo(a, b, *c, **d):
    return None
'''
        self.statement(stmnt)

    def test_function_kw_args(self):
        stmnt = '''
def foo(a, b, **d):
    return None
'''
        self.statement(stmnt)

    def test_function_yield(self):
        stmnt = '''
def foo(a, b):
    yield a + b
    return
'''

        self.statement(stmnt)

    def test_function_decorator(self):
        stmnt = '''
@bar
def foo(a, b):
    return None
'''

        self.statement(stmnt)

    def test_function_decorator2(self):
        stmnt = '''
@bar
@bar2
def foo(a, b):
    return None
'''

        self.statement(stmnt)

    def test_build_lambda(self):
        stmnt = 'lambda a: a'
        self.statement(stmnt)

    def test_build_lambda1(self):
        stmnt = 'func = lambda a, b: a+1'
        self.statement(stmnt)

    def test_build_lambda_var_args(self):
        stmnt = 'func = lambda a, *b: a+1'
        self.statement(stmnt)

    def test_build_lambda_kw_args(self):
        stmnt = 'func = lambda **b: a+1'
        self.statement(stmnt)

    def test_build_lambda_varkw_args(self):
        stmnt = 'func = lambda *a, **b: a+1'
        self.statement(stmnt)


class ClassDef(Base):
    def test_build_class(self):
        stmnt = '''
class Bar(object):
    'adsf'
    a = 1
'''
        self.statement(stmnt)

    def test_build_class_wfunc(self):
        stmnt = '''
class Bar(object):
    'adsf'
    a = 1
    def foo(self):
        return None
        
'''
        self.statement(stmnt)

    def test_build_class_wdec(self):
        stmnt = '''
@decorator
class Bar(object):
    'adsf'
    a = 1
    def foo(self):
        return None
        
'''
        self.statement(stmnt)



class ControlFlow(Base):
    def test_if(self):
        self.statement('if a: b')

    def test_if2(self):
        self.statement('if a: b or c')

    def test_if3(self):
        self.statement('if a and b: c')

    def test_if4(self):
        self.statement('if a or b: c')

    def test_if5(self):
        self.statement('if not a: c')

    def test_if6(self):
        self.statement('if not a or b: c')

    def test_elif(self):

        stmnt = '''if a: 
    b
elif c:
    d'''
        self.statement(stmnt)

    def test_if_else(self):

        stmnt = '''if a: 
    b
else:
    d'''
        self.statement(stmnt)

    def test_if_elif_else(self):

        stmnt = '''if a: 
    b
elif f:
    d
else:
    d'''
        self.statement(stmnt)

    def test_tryexcept1(self):
        stmnt = '''
try:
    foo
except:
    bar
'''
        self.statement(stmnt)

    def test_tryexcept_else(self):
        stmnt = '''
try:
    foo
except:
    bar
else:
    baz
'''
        self.statement(stmnt)

    def test_tryexcept2(self):
        stmnt = '''
try:
    foo
except Exception:
    bar
else:
    baz
'''
        self.statement(stmnt)


    def test_tryexcept3(self):
        stmnt = '''
try:
    foo
except Exception as error:
    bar
else:
    baz
'''
        self.statement(stmnt)

    def test_tryexcept4(self):
        stmnt = '''
try:
    foo
except Exception as error:
    bar
except Baz as error:
    bar
else:
    baz
'''
        self.statement(stmnt)

    def test_while(self):
        self.statement('while b: a')

    def test_while1(self):
        self.statement('while 1: a')


    def test_while_logic(self):
        self.statement('while a or b: x')

    def test_while_logic2(self):
        self.statement('while a and b: x')

    def test_while_logic3(self):
        self.statement('while a >= r and b == c: x')

    def test_while_else(self):
        stmnt = '''
while a:
    break
else:
    a
'''
        self.statement(stmnt)

    def test_for(self):
        stmnt = '''
for i in  a:
    break
'''
        self.statement(stmnt)

    def test_for2(self):
        stmnt = '''
for i in  a:
    b = 3
'''
        self.statement(stmnt)

    def test_for_else(self):
        stmnt = '''
for i in  a:
    b = 3
else:
    b= 2
'''
        self.statement(stmnt)

    def test_for_continue(self):
        stmnt = '''
for i in  a:
    b = 3
    continue
'''
        self.statement(stmnt)

    def test_for_unpack(self):
        stmnt = '''
for i,j in  a:
    b = 3
'''
        self.statement(stmnt)

class Complex(Base):

    def test_if_in_for(self):
        stmnt = '''
for i in j:
    if i:
        j =1
'''
        self.statement(stmnt)

    def test_if_in_for2(self):
        stmnt = '''
for i in j:
    if i:
        a
    else:
        b
        
'''
        self.statement(stmnt)

    def test_if_in_for3(self):
        stmnt = '''
for i in j:
    if i:
        break
    else:
        continue
        
'''
        equiv = '''
for i in j:
    if i:
        break
        continue
        
'''
        self.statement(stmnt, equiv)

    def test_if_in_while(self):
        stmnt = '''
while i in j:
    if i:
        a
    else:
        b
    
'''
        self.statement(stmnt)


    def test_nested_if(self):
        stmnt = '''
if a: 
    if b:
        c
    else:
        d
'''
        self.statement(stmnt)

    def test_nested_if2(self):
        stmnt = '''
if a: 
    if b:
        c
    else:
        d
else:
    b
'''
        self.statement(stmnt)

    def test_if_return(self):
        stmnt = '''
def a():
    if b:
        return None
    return None
'''
        self.statement(stmnt)

    def test_if_return2(self):
        stmnt = '''
def a():
    if b:
        a
    else:
        return b
        
    return c
'''
        self.statement(stmnt)

        
    def test_aug_assign_slice(self):
        stmnt = 'c[idx:a:3] += b[idx:a]'
        self.statement(stmnt)
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.test_assign']
    unittest.main()

