'''
Created on Nov 30, 2012

@author: sean
'''
from _ast import Print as _ast_Print

class PrintMixin(object):
    
        


    def visit_PRINT_ITEM(self, instr):

        item = self.pop_ast_item()

        if self._ast_stack:
            print_ = self._ast_stack[-1]
        else:
            print_ = None

        if isinstance(print_, _ast_Print) and not print_.nl and print_.dest == None:
            print_.values.append(item)
        else:
            print_ = _ast_Print(dest=None, values=[item], nl=False, lineno=instr.lineno, col_offset=0)
            self.push_ast_item(print_)

    def visit_PRINT_NEWLINE(self, instr):
        item = self._ast_stack[-1]

        if isinstance(item, _ast_Print) and not item.nl and item.dest == None:
            item.nl = True
        else:
            print_ = _ast_Print(dest=None, values=[], nl=True, lineno=instr.lineno, col_offset=0)
            self.push_ast_item(print_)

    def visit_PRINT_ITEM_TO(self, instr):

        stream = self.pop_ast_item()

        print_ = None

        if isinstance(stream, _ast_Print) and not stream.nl:
            print_ = stream
            stream = self.pop_ast_item()
            dup_print = self.pop_ast_item()
            assert dup_print is print_
            self.push_ast_item(stream)
        else:
            print_ = _ast_Print(dest=stream, values=[], nl=False, lineno=instr.lineno, col_offset=0)

        item = self.pop_ast_item()

        print_.values.append(item)
        self.push_ast_item(print_)

    def visit_PRINT_NEWLINE_TO(self, instr):

        item = self.pop_ast_item()
        stream = self.pop_ast_item()

        self.push_ast_item(item)

        if isinstance(item, _ast_Print) and not item.nl and item.dest is stream:
            item.nl = True
        else:
            print_ = _ast_Print(dest=stream, values=[], nl=True, lineno=instr.lineno, col_offset=0)
            self.push_ast_item(print_)

