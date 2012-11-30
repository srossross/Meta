from meta.decompiler.disassemble import disassemble
import _ast
from meta.asttools.serialize import serialize
from meta.asttools.visitors.print_visitor import print_ast
from ast import copy_location, NodeTransformer
from meta.decompiler.simple_instructions import make_const, CMP_OPMAP
from dis import dis
from meta.asttools.visitors.pysourcegen import dump_python_source
from meta.decompiler.expression_mutator import ExpressionMutator

def cpy_loc(node, instr):
    node.lineno = instr.lineno
    node.col_offset = 0
    if instr.is_jump:
        node.to = instr.to 
        node.label = None

_ast.stmt.__repr__ = lambda self: '%s()' % (type(self).__name__)
_ast.expr.__repr__ = lambda self: '%s()' % (type(self).__name__)
_ast.Name.__repr__ = lambda self: 'Name(%s)' % (self.id)
_ast.BoolOp.__repr__ = lambda self: '%s(%r)' % (type(self.op).__name__, self.values)

class Iter(_ast.stmt):
    _attributes = 'lineno', 'col_offset'
    _fields = 'value',

class CtlFlow(_ast.stmt):
    _attributes = 'lineno', 'col_offset', 'to'
    cond = True
    
class Block(CtlFlow):
    _attributes = 'lineno', 'col_offset', 'to'
    
class Loop(Block):
    _fields = 'body', 'orelse'
    
class Cond(CtlFlow):
    _attributes = 'lineno', 'col_offset', 'to'
    def __repr__(self):
        return 'Jump%s(%r)' % (self.cond, self.test,)
    
class POP_JUMP_IF_FALSE(Cond):
    _fields = 'test', 'body', 'orelse'
    cond = False
    
class POP_JUMP_IF_TRUE(Cond):
    _fields = 'test', 'body', 'orelse'

class JUMP_IF_FALSE_OR_POP(Cond):
    _fields = 'test', 'body', 'orelse'
    cond = False
    
class JUMP_IF_TRUE_OR_POP(Cond):
    _fields = 'test', 'body', 'orelse'

def rsplit(lst, key):
    matches = [x for x in lst if key(x)]
    if matches:
        idx = lst.index(matches[-1]) 
        return lst[:idx], lst[idx], lst[idx + 1:] 
    else:
        return lst[:], None, [] 


class ExprTransformer(NodeTransformer):
    def visit_POP_JUMP_IF_FALSE(self, node):
        assert len(node.body) == 1
        assert len(node.orelse) == 1
        
        body = self.visit(node.body[0])
        orelse = self.visit(node.orelse[0])
        _if_exp = _ast.IfExp(node.test, body, orelse)
        copy_location(_if_exp, node)
        return _if_exp
    
    visit_If = visit_POP_JUMP_IF_FALSE
    
    def visit_POP_JUMP_IF_TRUE(self, node):

        assert len(node.body) == 1
        assert len(node.orelse) == 1
        
        not_test = _ast.UnaryOp(_ast.Not() , node.test)
        copy_location(not_test, node)

        _if_exp = _ast.IfExp(not_test, node.body[0], node.orelse[0])
        copy_location(_if_exp, node)
        return _if_exp
    
    def visit_BoolOp(self, node):
        if isinstance(node.op, _ast.And):
            i = 0 
            while i < len(node.values) - 1:
                left = node.values[i]
                right = node.values[i + 1]
                if isinstance(left, _ast.Compare) and isinstance(right, _ast.Compare):
                    if left.comparators[-1] is right.left:
                        node.values.pop(i + 1)
                        left.comparators.extend(right.comparators)
                        left.ops.extend(right.ops)
                i += 1
            if len(node.values) == 1:
                return node.values[0]
        return node
#    def visit_Compare(self, node):
#        pasdf

class StatementTransformer(NodeTransformer):
    
    def generic_visit(self, node):
        
        if isinstance(node, _ast.stmt):
            return NodeTransformer.generic_visit(self, node)
        else:
            return node
    
    def visit_Expr(self, node):
        new_node = mkexpr(node.value)
        copy_location(new_node, node)
        return new_node
    
    def visit_POP_JUMP_IF_FALSE(self, node):
        _if = _ast.If(node.test, node.body, node.orelse)
        copy_location(_if, node)
        return _if
    
    def visit_POP_JUMP_IF_TRUE(self, node):
        not_test = _ast.UnaryOp(_ast.Not() , node.test)
        copy_location(not_test, node)
        _if = _ast.If(not_test, node.body, node.orelse)
        copy_location(_if, node)
        return _if

mkexpr = lambda node: ExprTransformer().visit(node)
mkstmnt = lambda node: StatementTransformer().visit(node)
# mkstmnt = lambda node:node

class InstructionVisitor(object):
    def __init__(self, code):
        self.instructions = disassemble(code)
        self.code = code
        self._ast_stack = []
        self.labels = {}
        self.jump_or_pop_ctx = False
        
    def make_ast(self):
        for idx, instr in enumerate(self.instructions):
            self.idx = idx
            self.visit(instr)
        return [mkstmnt(node) for node in self._ast_stack]
    
    def visit(self, instr):
        if instr.is_jump:
            self.labels.setdefault(instr.to, [])
        
        if instr.i in self.labels:
            self.handle_label(instr.i)
            
        method_name = 'visit_%s' % instr.opname.replace('+', '_')
        visitor_method = getattr(self, method_name)
        result = visitor_method(instr)
        
        print '%-50s ' % (instr,), '-->', self._ast_stack
        
        return result
    
    def pop_ast_item(self):
        return self._ast_stack.pop()
    
    def push_ast_item(self, item):
        self._ast_stack.append(item)

    def handle_label(self, i):
        if self.jump_or_pop_ctx and self.labels[i]:
            stack = self.labels[i][0].stack
            self._ast_stack = stack
            self.jump_or_pop_ctx = False
            
        node = self.pop_ast_item()
            
        while self.labels[i]:
            prev = self.labels[i].pop()
#            assert prev.to == i
            op = _ast.Or() if prev.cond else _ast.And()
            node = _ast.BoolOp(op, [prev.test, node])
            copy_location(node, prev)
            
        self.push_ast_item(node)
        
        
        for idx in range(len(self._ast_stack) - 2, -1, -1):
            if len(self._ast_stack) <= idx + 1:
                break
            
            node = self._ast_stack[idx]
            node_next = self._ast_stack[idx + 1]
            
            if isinstance(node, Cond) and node.to == i:
                assert not node.orelse
                if not node.body and isinstance(node_next, Cond):
                    self._ast_stack.pop(idx)
                    # assert not node.body, 
                    op = _ast.Or() if node.cond else _ast.And()
                    bool_op = _ast.BoolOp(op, [node.test, node_next.test])
                    copy_location(bool_op, node)
                    node_next.test = bool_op
                else:
                    node.orelse = [mkstmnt(elnode) for elnode in self._ast_stack[idx + 1:]]
                    self._ast_stack = self._ast_stack[:idx + 1]

        print "%-50s " % ("Handle Label %02i" % (i)), '-->', self._ast_stack
        
    def visit_LOAD_GLOBAL(self, instr):
        name = _ast.Name(id=instr.arg, ctx=_ast.Load(), lineno=instr.lineno, col_offset=0)
        self.push_ast_item(name)
    
    def POP_JUMP_IF(logical):
        def visitor(self, instr):
            cond = self.pop_ast_item()
            cls = POP_JUMP_IF_TRUE if logical else POP_JUMP_IF_FALSE
            node = cls(test=cond, body=None, orelse=None)
            
            cpy_loc(node, instr)
            self.push_ast_item(node)
        return visitor
        
    visit_POP_JUMP_IF_FALSE = POP_JUMP_IF(False)
    visit_POP_JUMP_IF_TRUE = POP_JUMP_IF(True)
    
    def JUMP_IF_X_OR_POP(logical):
        def visitor(self, instr):
            cond = self.pop_ast_item()
            cls = JUMP_IF_TRUE_OR_POP if logical else JUMP_IF_FALSE_OR_POP
            stack = self._ast_stack[:]
            stack.append(cond)
            node = cls(test=cond, stack=stack)
            
            cpy_loc(node, instr)
            self.labels[instr.to].append(node)
        return visitor

    visit_JUMP_IF_TRUE_OR_POP = JUMP_IF_X_OR_POP(True)
    visit_JUMP_IF_FALSE_OR_POP = JUMP_IF_X_OR_POP(False)
    
    def visit_POP_TOP(self, instr):
        value = self.pop_ast_item()
        node = _ast.Expr(value)
        cpy_loc(node, instr)
        self.push_ast_item(node)
        
    
    def visit_JUMP(self, instr):
        
        left, cond, right = rsplit(self._ast_stack, key=lambda node: isinstance(node, Cond) and not node.body)
        if cond:
            assert not cond.body
            self._ast_stack = left
            cond.body = [mkstmnt(node) for node in right]
            cond.to = instr.to
            self.push_ast_item(cond)
            
        nexti = self.instructions[self.idx + 1].i
        if self.labels.get(nexti):
            assert nexti < instr.to
            stack = self._ast_stack
            self._ast_stack = self.labels.get(nexti)[0].stack[:]
            self.labels.get(nexti)[0].stack = stack
            self.labels[instr.to] = self.labels.pop(nexti)
            self.jump_or_pop_ctx = True
            
            
    
    visit_JUMP_ABSOLUTE = visit_JUMP
    visit_JUMP_FORWARD = visit_JUMP
    
    def visit_LOAD_CONST(self, instr):
        node = make_const(instr.arg)
        cpy_loc(node, instr)
        self.push_ast_item(node)
    
    def visit_RETURN_VALUE(self, instr):
        value = self.pop_ast_item()
        node = _ast.Return(value=value)
        cpy_loc(node, instr)
        self.push_ast_item(node)

    def visit_SETUP_LOOP(self, instr):
        node = Loop(body=None, orelse=None)
        cpy_loc(node, instr)
        self.push_ast_item(node)
        
    def visit_POP_BLOCK(self, instr):
        left, block, right = rsplit(self._ast_stack, key=lambda node: isinstance(node, Block) and not node.body)
        self._ast_stack = left
        assert not block.body
        block.body = right
        
        self.push_ast_item(block)
        
    def visit_GET_ITER(self, instr):
        value = self.pop_ast_item()
        node = Iter(value)
        cpy_loc(node, instr)
        self.push_ast_item(node)
    
    def visit_FOR_ITER(self, instr):
        value = self.pop_ast_item()
        node = _ast.For(None, value, [], [])
        cpy_loc(node, instr)
        self.push_ast_item(node)
    
    def visit_STORE_FAST(self, instr):
        value = self.pop_ast_item()
        assname = _ast.Name(instr.arg, _ast.Store())
        cpy_loc(assname, instr)
        node = _ast.Assign(targets=[assname], value=value)
        cpy_loc(node, instr)
        self.push_ast_item(node)
    
    def visit_DUP_TOP(self, instr):
        node = self.pop_ast_item()
        self.push_ast_item(node)
        self.push_ast_item(node)
    
    def visit_ROT_TWO(self, instr):
        n0 = self.pop_ast_item()
        n1 = self.pop_ast_item()
        self.push_ast_item(n0)
        self.push_ast_item(n1)
        
    def visit_ROT_THREE(self, instr):
        n0 = self.pop_ast_item()
        n1 = self.pop_ast_item()
        n2 = self.pop_ast_item()
        self.push_ast_item(n0)
        self.push_ast_item(n2)
        self.push_ast_item(n1)
        
    def visit_COMPARE_OP(self, instr):
        op = instr.arg

        right = self.pop_ast_item()
        
        expr = self.pop_ast_item()

        OP = CMP_OPMAP[op]
        compare = _ast.Compare(left=expr, ops=[OP()], comparators=[right])

        cpy_loc(compare, instr)
        self.push_ast_item(compare)

    
def foo():
    if a:
        if b:
            c
        
statements = InstructionVisitor(foo.func_code).make_ast()

print '----'
for stmnt in statements:
    print_ast(stmnt)
print '----'
print '----'
for stmnt in statements:
    print dump_python_source(stmnt)
print '----'
    
# print "statements", [serialize(stmnt) for stmnt in statements]
