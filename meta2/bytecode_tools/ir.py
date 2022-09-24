import inspect
import dis
import opcode
import types
from collections import defaultdict
from .consume_static import consume_static
from .unwind import Unwinder

COMPILER_FLAGS = {v: k for k, v in dis.COMPILER_FLAG_NAMES.items()}

hascall = [dis.opmap["CALL_FUNCTION"], dis.opmap["CALL_METHOD"]]
hasglobal = [dis.opmap["LOAD_GLOBAL"], dis.opmap["LOAD_DEREF"]]
hasbuild = [opcode.opmap["BUILD_TUPLE"]]

stack_size = defaultdict(lambda: 1)
for i in range(256):
    if opcode.opname[i].startswith("BINARY_"):
        stack_size[i] = 2
stack_size[opcode.opmap["ROT_TWO"]] = 2
stack_size[opcode.opmap["ROT_THREE"]] = 3
stack_size[opcode.opmap["ROT_FOUR"]] = 3
stack_size[opcode.opmap["DUP_TOP"]] = 2
stack_size[opcode.opmap["DUP_TOP_TWO"]] = 4


def _load_global(op, globals, nonlocals, new_globals):
    if op.opcode not in hasglobal:
        return op

    if op.opcode == dis.opmap["LOAD_DEREF"]:
        op = dis.Instruction(
            "LOAD_GLOBAL",
            dis.opmap["LOAD_GLOBAL"],
            op.arg,
            op.argval,
            op.argrepr,
            op.offset,
            op.starts_line,
            op.is_jump_target,
        )

    if op.argval in new_globals:
        return op

    if op.argval in nonlocals:
        new_globals[op.argval] = nonlocals[op.argval]
        return op

    if op.argval in globals:
        new_globals[op.argval] = globals[op.argval]
        return op

    new_globals[op.argval] = __builtins__[op.argval]
    return op


def _load_globals(instructions, globals, nonlocals):
    new_globals = {}
    new_instructions = [
        _load_global(op, globals, nonlocals, new_globals) for op in instructions
    ]
    return new_instructions, new_globals


def _inline_function(op, new_instructions, globals):
    uw = Unwinder(new_instructions)
    uw.unwind(op.argval)
    visited = uw.visited
    name, value = consume_static(new_instructions, globals)
    globals[name] = value
    load_op = dis.Instruction(
        "LOAD_GLOBAL",
        opcode.opmap["LOAD_GLOBAL"],
        None,
        name,
        None,
        0,
        None,
        False,
    )
    new_instructions.append(load_op)
    new_instructions.extend(visited)


def _inline_functions(instructions, globals):
    instructions = list(instructions)
    new_instructions = []
    while instructions:
        op = instructions.pop(0)
        if op.opcode in hascall:
            _inline_function(op, new_instructions, globals)
            op = op_replace(
                op, opcode=opcode.opmap["CALL_FUNCTION"], opname="CALL_FUNCTION"
            )
        new_instructions.append(op)
    return new_instructions


class IR:
    @classmethod
    def from_function(cls, func):
        globals = func.__globals__
        nonlocals = inspect.getclosurevars(func).nonlocals

        bytecode = dis.Bytecode(func)
        instructions = list(bytecode)

        co = func.__code__

        return cls(
            instructions=instructions,
            globals=globals,
            nonlocals=nonlocals,
            co_consts=co.co_consts,
            co_argcount=co.co_argcount,
            co_kwonlyargcount=co.co_kwonlyargcount,
            co_posonlyargcount=co.co_posonlyargcount,
            co_flags=co.co_flags,
            co_varnames=co.co_varnames,
            co_name=co.co_name,
            co_firstlineno=co.co_firstlineno,
            co_linetable=co.co_linetable,
        )

    def __init__(
        self,
        *,
        instructions,
        globals,
        nonlocals,
        co_consts,
        co_argcount,
        co_kwonlyargcount,
        co_posonlyargcount,
        co_flags,
        co_varnames,
        co_name,
        co_firstlineno,
        co_linetable
    ) -> None:
        self.co_consts = co_consts
        self.co_argcount = co_argcount
        self.co_kwonlyargcount = co_kwonlyargcount
        self.co_posonlyargcount = co_posonlyargcount
        self.co_flags = co_flags
        self.co_varnames = co_varnames
        self.co_name = co_name
        self.co_firstlineno = co_firstlineno
        self.co_linetable = co_linetable

        instructions, globals = _load_globals(instructions, globals, nonlocals)
        print("_inline_functions")
        instructions = _inline_functions(instructions, globals)
        self.instructions = instructions
        self.globals = globals

    def _op_arg(self, op_opcode, op_arg, op_argval, consts, names, varnames):

        if op_opcode in opcode.hasconst:
            if op_argval not in consts:
                consts.append(op_argval)
            op_arg = consts.index(op_argval)
            return op_opcode, op_arg

        if op_opcode in opcode.hasname:
            if op_argval not in names:
                names.append(op_argval)
            op_arg = names.index(op_argval)
            return op_opcode, op_arg

        if op_opcode in opcode.haslocal:
            if op_argval not in varnames:
                varnames.append(op_argval)
            op_arg = varnames.index(op_argval)
            return op_opcode, op_arg

        if op_opcode >= opcode.HAVE_ARGUMENT:
            assert op_arg is not None
            return op_opcode, op_arg

        return op_opcode, 0

    def _op_stacksize(self, op_opcode, op_argval):
        if op_opcode in hascall:
            return op_argval + 1
        if op_opcode in hasbuild:
            return op_argval
        return stack_size[op_opcode]

    def code(self):
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
        stack_size = 1
        for i, op in enumerate(self.instructions):
            op_opcode = op.opcode

            op_opcode, op_arg = self._op_arg(
                op_opcode, op.arg, op.argval, consts, names, varnames
            )
            code.append(op_opcode)
            code.append(op_arg)

            stack_size = max(stack_size, self._op_stacksize(op_opcode, op.argval))

        freevars = ()
        cellvars = ()
        code = types.CodeType(
            self.co_argcount,
            self.co_posonlyargcount,
            self.co_kwonlyargcount,
            len(varnames),  # TODO: verify this is correct
            stack_size,
            self.co_flags,
            bytes(code),
            tuple(consts),
            tuple(names),
            tuple(varnames),
            "no-file",
            self.co_name,
            self.co_firstlineno,
            self.co_linetable,
            freevars,
            cellvars,
        )
        return code

    def function(self):
        code = self.code()

        return types.FunctionType(
            code,
            self.globals,
            name=self.co_name,
            argdefs=None,
        )

    def __iter__(self):
        return iter(list(self.instructions))

    def replace_op(self, i, **kw):
        op = self.instructions[i]
        new_op = op_replace(op, **kw)
        self.instructions[i] = new_op


def op_replace(op, **kw):
    return dis.Instruction(*[kw.get(field, getattr(op, field)) for field in op._fields])
