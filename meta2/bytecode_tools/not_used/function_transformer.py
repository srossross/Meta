import opcode
import inspect
import types
from dis import COMPILER_FLAG_NAMES
from abc import ABCMeta, abstractmethod


from .visitor import ByteCodeVisitor

COMPILER_FLAGS = {v: k for k, v in COMPILER_FLAG_NAMES.items()}


class FunctionTransformer(ByteCodeVisitor, metaclass=ABCMeta):
    """
    NOT USED
    """

    def __init__(self, func) -> None:
        super().__init__(func)
        self.globals = func.__globals__
        self.nonlocals = inspect.getclosurevars(self.func).nonlocals
        self.co_argcount = func.__code__.co_argcount
        self.co_posonlyargcount = func.__code__.co_posonlyargcount
        self.co_kwonlyargcount = func.__code__.co_kwonlyargcount
        self.co_nlocals = func.__code__.co_nlocals
        self.co_stacksize = func.__code__.co_stacksize
        self.co_flags = func.__code__.co_flags
        self.co_codestring = func.__code__.co_code
        self.co_consts = func.__code__.co_consts
        self.co_names = func.__code__.co_names
        self.co_varnames = func.__code__.co_varnames
        self.co_filename = func.__code__.co_filename
        self.co_name = func.__code__.co_name
        self.co_firstlineno = func.__code__.co_firstlineno
        self.co_linetable = func.__code__.co_linetable
        self.co_freevars = func.__code__.co_freevars
        self.co_cellvars = func.__code__.co_cellvars

    def transform_name(self):
        return f"{self.__class__.__name__}_{self.func.__name__}"

    @abstractmethod
    def visit_transform(self):
        pass

    def argdefs(self):
        return None

    def scan(self, instructions):
        globals = {}
        consts = [self.co_consts[0]]

        nargs = self.co_argcount
        nargs += self.co_kwonlyargcount
        if self.co_flags & COMPILER_FLAGS["VARARGS"]:
            nargs += 1
        if self.co_flags & COMPILER_FLAGS["VARKEYWORDS"]:
            nargs += 1

        varnames = list(self.co_varnames[:nargs])

        names = []
        code = []
        for i, op in enumerate(instructions):
            op_opcode = op.opcode

            if op_opcode == opcode.opmap["LOAD_DEREF"]:
                op_opcode = opcode.opmap["LOAD_GLOBAL"]

            if op_opcode in opcode.hasconst:
                if op.argval not in consts:
                    consts.append(op.argval)
                arg = consts.index(op.argval)

            elif op_opcode in opcode.hasname:
                if op.argval not in names:
                    names.append(op.argval)
                arg = names.index(op.argval)

            elif op_opcode in opcode.haslocal:
                if op.argval not in varnames:
                    varnames.append(op.argval)
                arg = varnames.index(op.argval)

            elif op.opcode >= opcode.HAVE_ARGUMENT:
                arg = op.arg
                assert op.arg is not None, op
            else:
                arg = 0

            if op_opcode == opcode.opmap["LOAD_GLOBAL"]:
                print("self.nonlocals", self.nonlocals)
                if op.argval in self.nonlocals:
                    globals[op.argval] = self.nonlocals[op.argval]
                elif op.argval in self.globals:
                    globals[op.argval] = self.globals[op.argval]
                else:
                    globals[op.argval] = __builtins__[op.argval]

            code.append(op_opcode)
            code.append(arg)

        return globals, bytes(code), tuple(consts), tuple(names), tuple(varnames), ()

    def to_function(self, instructions):

        assert not self.co_cellvars, f"cant handle this yet{self.co_cellvars}"

        globals, codestring, consts, names, varnames, freevars = self.scan(instructions)

        print("varnames", varnames)
        print("self.co_varnames", self.co_varnames)
        code = types.CodeType(
            self.co_argcount,
            self.co_posonlyargcount,
            self.co_kwonlyargcount,
            self.co_nlocals,
            self.co_stacksize,
            self.co_flags,
            codestring,
            consts,
            names,
            varnames,
            self.co_filename,
            self.transform_name(),
            self.co_firstlineno,
            self.co_linetable,
            freevars,
            self.co_cellvars,
        )
        return types.FunctionType(
            code, globals, name=self.transform_name(), argdefs=self.argdefs()
        )

    def transform(self):
        new_instructions = self.visit_transform()
        return self.to_function(new_instructions)


def main():
    def foo():
        print("Hello world")

    f = Transformer(foo)


if __name__ == "__main__":
    main()
