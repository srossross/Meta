from meta.decompiler.disassemble import disassemble
import _ast
from meta.asttools.visitors.print_visitor import print_ast
from meta.asttools.visitors.pysourcegen import dump_python_source
from meta.decompiler import extra_nodes as nodes
from meta.decompiler.transformers import mkstmnt, mkexpr

from meta.decompiler.simple_instructions import SimpleInstructionMixin
from meta.decompiler.assignments import AssignmentsMixin


DEBG = False

def indexof(lst, test, start=0):
    items = [item for item in lst[start:] if test(item)]
    if not items:
        return -1
    fist_item = items[0]
    return lst.index(fist_item, start)

def POP_JUMP_IF(cond):
    def visitor(self, instr):
        test = self.pop_ast_item()
        node = nodes.PopJumpIf(test=test, to=instr.to, cond=cond)
        nodes.cpy_loc(node, instr)
        self.push_ast_item(node)
    return visitor
    

def JUMP_IF_X_OR_POP(cond):
    def visitor(self, instr):
        test = self.pop_ast_item()
        node = nodes.JumpOrPop(test=test, to=instr.to, cond=cond)
        nodes.cpy_loc(node, instr)
        self.push_ast_item(node)
    return visitor

class InstructionVisitor(SimpleInstructionMixin, AssignmentsMixin):
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
            # self.handle_label(instr.i)
            self.merge_control_flow(instr.i)
            
        method_name = 'visit_%s' % instr.opname.replace('+', '_')
        visitor_method = getattr(self, method_name)
        result = visitor_method(instr)
        
        if DEBG: self.print_stack_state(instr)
        
        return result
    
    def print_stack_state(self, msg, width=50):
        tmplt = '%%-%is --> %%s' % (width,)
        print tmplt % (msg, self._ast_stack)
        
    def pop_ast_item(self):
        node = self._ast_stack.pop()
        push_back = []
        while isinstance(node, nodes.CtlFlow): #Don't pop
            push_back.insert(0, node)
            node = self._ast_stack.pop()
        self._ast_stack.extend(push_back)
        return node
            
    
    def push_ast_item(self, item):
        self._ast_stack.append(item)

    def merge_control_flow(self, i):
        first_branch = lambda node: isinstance(node, nodes.CtlFlow) and node.to == i
        next_branch = lambda node: isinstance(node, nodes.CtlFlow)
        
        while True:
            idx = indexof(self._ast_stack, first_branch)
            if idx == -1:
                break
            node = self._ast_stack.pop(idx)
            
            next_idx = indexof(self._ast_stack, next_branch, idx)
            if next_idx == -1:
                span = self._ast_stack[idx:]
                del self._ast_stack[idx:]
                self.push_ast_item(node.finalize(span, self._ast_stack))
            else:
                next_node = self._ast_stack.pop(next_idx)
                span = self._ast_stack[idx:next_idx]
                del self._ast_stack[idx:next_idx]
                new_node = next_node.merge(node, span, self._ast_stack)
                if new_node is None:
                    new_node = next_node
                    
                self._ast_stack.insert(idx, new_node)
                     
                
            if DEBG: self.print_stack_state("Merge Flow   %02i" % (i))
         

    visit_POP_JUMP_IF_FALSE = POP_JUMP_IF(False)
    visit_POP_JUMP_IF_TRUE = POP_JUMP_IF(True)

    visit_JUMP_IF_TRUE_OR_POP = JUMP_IF_X_OR_POP(True)
    visit_JUMP_IF_FALSE_OR_POP = JUMP_IF_X_OR_POP(False)
    
    def visit_POP_TOP(self, instr):
        value = self.pop_ast_item()
        
        if value is None:
            self.push_ast_item(value)
            return
        elif isinstance(value, (_ast.ImportFrom)):
            self.push_ast_item(value)
            return
        
        value = mkexpr(value)
        
        node = _ast.Expr(value)
        nodes.cpy_loc(node, instr)
        self.push_ast_item(node)
        
    
    def visit_JUMP(self, instr):
        node = nodes.cpy_loc(nodes.Jump(test=None, body=[], orelse=[], cond=False, to=instr.to), instr)
        self.push_ast_item(node)
        
    
    visit_JUMP_ABSOLUTE = visit_JUMP
    visit_JUMP_FORWARD = visit_JUMP
    

    def visit_SETUP_LOOP(self, instr):
        node = nodes.Loop(body=None, orelse=None)
        nodes.cpy_loc(node, instr)
        self.push_ast_item(node)
        
    def visit_POP_BLOCK(self, instr):
        left, block, right = nodes.rsplit(self._ast_stack, key=lambda node: isinstance(node, nodes.Block) and not node.body)
        self._ast_stack = left
        assert not block.body
        block.body = right
        
        self.push_ast_item(block)
        
    def visit_GET_ITER(self, instr):
        value = self.pop_ast_item()
        node = nodes.Iter(value)
        nodes.cpy_loc(node, instr)
        self.push_ast_item(node)
    
    def visit_FOR_ITER(self, instr):
        value = self.pop_ast_item()
        node = _ast.For(None, value, [], [])
        nodes.cpy_loc(node, instr)
        self.push_ast_item(node)
    
if __name__ == '__main__':
    DEBG = True        
    def foo():
        if a: 
            b
        elif c:
            d
        elif e:
            f
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
