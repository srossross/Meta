import ast
import _ast
import inspect
from .visitor import Visitor
from string import Formatter
import sys
from contextlib import contextmanager

from io import StringIO


@contextmanager
def noctx():
    yield


class ASTFormatter(Formatter):
    def format_field(self, value, format_spec):
        if format_spec == "node":
            gen = ExprSourceGen()
            gen.visit(value)
            return gen.dumps()
        elif value == "":
            return value
        else:
            return super(ASTFormatter, self).format_field(value, format_spec)

    def get_value(self, key, args, kwargs):
        if key == "":
            return args[0]
        elif key in kwargs:
            return kwargs[key]
        elif isinstance(key, int):
            return args[key]

        key = int(key)
        return args[key]

        raise Exception


def str_node(node):
    gen = ExprSourceGen()
    gen.visit(node)
    return gen.dumps()


def simple_string(value):
    def visitNode(self, node):
        self.print(value, **node.__dict__)

    return visitNode


class ExprSourceGen(Visitor):
    def __init__(self, level=0, indent="    "):
        self.out = StringIO()
        self.formatter = ASTFormatter()
        self.indent = indent
        self.level = level

    @property
    def indenter(self):
        return Indenter(self)

    @property
    def no_indent(self):
        return NoIndent(self)

    def dump(self, file=sys.stdout):
        self.out.seek(0)
        print(self.out.read(), file=file)

    def dumps(self):
        self.out.seek(0)
        value = self.out.read()
        return value

    def print(self, line, *args, **kwargs):
        skip_format = kwargs.get("skip_format", False)
        if not skip_format:
            line = self.formatter.format(line, *args, **kwargs)

        level = kwargs.get("level")
        prx = self.indent * (level if level else self.level)
        print(prx, line, sep="", end="", file=self.out)

    def print_lines(
        self,
        lines,
    ):
        prx = self.indent * self.level
        for line in lines:
            print(prx, line, sep="", file=self.out)

    def visitName(self, node):
        self.print(node.id)

    def visitConstant(self, node):
        if node.value is Ellipsis:
            self.print("...")
            return
        self.print(repr(node.value), skip_format=True)

    def _format_pos_or_kw(self, arg, default):
        if default is not None:
            # print("arg, default", arg, default)
            return self.formatter.format("{:node}={:node}", arg, default)
        return self.formatter.format("{:node}", arg)

    def visitarguments(self, node):

        # Position only arguments foo(a,b, /, ...)
        farg_list = []
        pos = [self.formatter.format("{:node}", arg) for arg in node.posonlyargs]

        if pos:
            farg_list.extend(pos)
            farg_list.append("/")

        # Position or kw arguments foo(a,b=1)
        args = node.args
        defaults = [None] * (len(args) - len(node.defaults)) + node.defaults
        pos_or_kw = [
            self._format_pos_or_kw(arg, default) for arg, default in zip(args, defaults)
        ]

        farg_list.extend(pos_or_kw)

        # Var arg foo(*a) or foo(*, ...)
        if node.vararg:
            farg_list.append(self.formatter.format("*{:node}", node.vararg))
        elif node.kwonlyargs:
            farg_list.append("*")

        # Kw only args foo(*, b, c=1)
        args = node.kwonlyargs
        defaults = [None] * (len(args) - len(node.kw_defaults)) + node.kw_defaults
        kw = [
            self._format_pos_or_kw(arg, default) for arg, default in zip(args, defaults)
        ]

        farg_list.extend(kw)

        # Kw arg foo(..., **kw)
        if node.kwarg:
            farg_list.append(self.formatter.format("**{:node}", node.kwarg))

        self.print(", ".join(farg_list), skip_format=True)

    def visitNum(self, node):
        self.print(repr(node.n))

    def visitlong(self, node):
        self.print(repr(node))

    def visitBinOp(self, node):
        self.print(
            "({left:node} {op:node} {right:node})",
            left=node.left,
            op=node.op,
            right=node.right,
        )

    def visitAdd(self, node):
        self.print("+")

    def visitMatMult(self, node):
        self.print("@")

    def visitalias(self, node):
        if node.asname is None:
            self.print("{0}", node.name)
        else:
            self.print("{0} as {1}", node.name, node.asname)

    def visitStarred(self, node):
        self.print("*{:node}", node.value)

    def visitCall(self, node):

        self.print("{func:node}(", func=node.func)
        i = 0

        print_comma = lambda i: self.print(", ") if i > 0 else None
        with self.no_indent:

            for arg in node.args:
                print_comma(i)
                self.print("{:node}", arg)
                i += 1

            for kw in node.keywords:
                print_comma(i)
                if kw.arg is None:
                    self.print("**{:node}", kw.value)
                else:
                    self.print("{:node}", kw)
                i += 1

            self.print(")")

    def visitkeyword(self, node):
        self.print("{0}={1:node}", node.arg, node.value)

    def visitStr(self, node):
        self.print(repr(node.s), skip_format=True)

    def visitTuple(self, node, brace="()"):
        self.print(brace[0])

        print_comma = lambda i: self.print(", ") if i > 0 else None

        i = 0
        with self.no_indent:
            for elt in node.elts:
                print_comma(i)
                self.print("{:node}", elt)
                i += 1

            if len(node.elts) == 1:
                self.print(",")

            self.print(brace[1])

    def visitCompare(self, node):
        self.print("({0:node}", node.left)
        with self.no_indent:
            for (op, right) in zip(node.ops, node.comparators):
                self.print(" {0:node} {1:node}", op, right)
            self.print(")")

    def visitRaise(self, node):
        self.print("raise ")
        with self.no_indent:
            if node.exc:
                self.print("{:node}", node.exc)
            if node.cause:
                self.print(" from {:node}", node.cause)

    def visitAttribute(self, node):
        self.print("{:node}.{attr}", node.value, attr=node.attr)

    def visitDict(self, node):
        self.print("{{")

        items = zip(node.keys, node.values)

        with self.no_indent:
            i = 0
            pc = lambda: self.print(", ") if i > 0 else None

            for key, value in items:
                pc()
                if key is None:
                    self.print("**{0:node}", value)
                else:
                    self.print("{0:node}:{1:node}", key, value)
                i += 1

            self.print("}}")

    def visitSet(self, node):
        self.print("{{")

        items = node.elts

        with self.no_indent:
            i = 0
            pc = lambda: self.print(", ") if i > 0 else None

            for value in items:
                pc()
                self.print("{0:node}", value)
                i += 1

            self.print("}}")

    def visitList(self, node):
        self.print("[")

        with self.no_indent:
            i = 0
            pc = lambda: self.print(", ") if i > 0 else None

            for item in node.elts:
                pc()
                self.print("{:node}", item)
                i += 1
            self.print("]")

    def visitSubscript(self, node):

        # self.print('{0:node}[{1:node}]', node.value, node.slice)
        self.print("{0:node}[", node.value)
        if isinstance(node.slice, ast.Tuple):
            items = list(node.slice.elts)
            item = items.pop(0)
            self.print("{0:node}", item)
            while items:
                item = items.pop(0)
                self.print(", {0:node}", item)
        else:
            self.print("{0:node}", node.slice)

        self.print("]")

    def visitIndex(self, node):
        if isinstance(node.value, _ast.Tuple):
            with self.no_indent:
                self.visit(node.value, brace=["", ""])
        else:
            self.print("{:node}", node.value)

    def visitSlice(self, node):
        with self.no_indent:
            if node.lower is not None:
                self.print("{:node}", node.lower)
            self.print(":")
            if node.upper is not None:
                self.print("{:node}", node.upper)

            if node.step is not None:
                self.print(":")
                self.print("{:node}", node.step)

    def visitExtSlice(self, node):

        dims = list(node.dims)
        with self.no_indent:
            dim = dims.pop(0)
            self.print("{0:node}", dim)

            while dims:
                dim = dims.pop(0)
                self.print(", {0:node}", dim)

    def visitUnaryOp(self, node):
        self.print("({0:node}{1:node})", node.op, node.operand)

    def visitAssert(self, node):
        self.print("assert {0:node}", node.test)

        if node.msg:
            with self.no_indent:
                self.print(", {0:node}", node.msg)

    visitUSub = simple_string("-")
    visitUAdd = simple_string("+")
    visitNot = simple_string("not ")
    visitInvert = simple_string("~")

    visitAnd = simple_string("and")
    visitOr = simple_string("or")

    visitSub = simple_string("-")
    visitFloorDiv = simple_string("//")
    visitDiv = simple_string("/")
    visitMod = simple_string("%")
    visitMult = simple_string("*")
    visitPow = simple_string("**")

    visitEq = simple_string("==")
    visitNotEq = simple_string("!=")

    visitLt = simple_string("<")
    visitGt = simple_string(">")

    visitLtE = simple_string("<=")
    visitGtE = simple_string(">=")

    visitLShift = simple_string("<<")
    visitRShift = simple_string(">>")

    visitIn = simple_string("in")
    visitNotIn = simple_string("not in")

    visitIs = simple_string("is")
    visitIsNot = simple_string("is not")

    visitBitAnd = simple_string("&")
    visitBitOr = simple_string("|")
    visitBitXor = simple_string("^")

    visitEllipsis = simple_string("...")

    visitYield = simple_string("yield {value:node}")

    def visitBoolOp(self, node):

        with self.no_indent:
            values = list(node.values)
            left = values.pop(0)

            self.print("({:node}", left)
            while values:
                left = values.pop(0)
                self.print(" {0:node} {1:node}", node.op, left)
            self.print(")")

    def visitIfExp(self, node):
        self.print("{body:node} if {test:node} else {orelse:node}", **node.__dict__)

    def visitLambda(self, node):
        self.print("lambda {0:node}: {1:node}", node.args, node.body)

    def visitListComp(self, node):
        self.print("[{0:node}", node.elt)

        generators = list(node.generators)
        with self.no_indent:
            while generators:
                generator = generators.pop(0)
                self.print("{0:node}", generator)

            self.print("]")

    def visitSetComp(self, node):
        self.print("{{{0:node}", node.elt)

        generators = list(node.generators)
        with self.no_indent:
            while generators:
                generator = generators.pop(0)
                self.print("{0:node}", generator)

            self.print("}}")

    def visitDictComp(self, node):
        self.print("{{{0:node}:{1:node}", node.key, node.value)

        generators = list(node.generators)
        with self.no_indent:
            while generators:
                generator = generators.pop(0)
                self.print("{0:node}", generator)

            self.print("}}")

    def visitcomprehension(self, node):
        self.print(" for {0:node} in {1:node}", node.target, node.iter)

        ifs = list(node.ifs)
        while ifs:
            if_ = ifs.pop(0)
            self.print(" if {0:node}", if_)

    def visitarg(self, node):
        self.print(node.arg)

        if node.annotation:
            with self.no_indent:
                self.print(":{0:node}", node.annotation)

    def visitwithitem(self, node):
        self.print("{:node}", node.context_expr)
        if node.optional_vars:
            self.print(" as {:node}", node.optional_vars)


def visit_expr(node):
    gen = ExprSourceGen()
    gen.visit(node)
    return gen.dumps()


class NoIndent(object):
    def __init__(self, gen):
        self.gen = gen

    def __enter__(self):
        self.level = self.gen.level
        self.gen.level = 0

    def __exit__(self, *args):
        self.gen.level = self.level


class Indenter(object):
    def __init__(self, gen):
        self.gen = gen

    def __enter__(self):
        self.gen.print("\n", level=0)
        self.gen.level += 1

    def __exit__(self, *args):
        self.gen.level -= 1


class SourceGen(ExprSourceGen):
    def __init__(self, header=""):
        super(SourceGen, self).__init__()
        print(header, file=self.out)

    def visitModule(self, node):

        children = list(self.children(node))
        if children and isinstance(children[0], _ast.Expr):
            if isinstance(children[0].value, ast.Str):
                doc = children.pop(0).value
                self.print("'''")
                self.print_lines(doc.s.split("\n"))
                self.print_lines(["'''", "\n", "\n"])

        for node in children:
            self.visit(node)

    def visitFor(self, node):
        self.print("for {0:node} in {1:node}:", node.target, node.iter)
        with self.indenter:
            for stmnt in node.body:
                self.visit(stmnt)

        if node.orelse:
            self.print("else:")
            with self.indenter:
                for stmnt in node.orelse:
                    self.visit(stmnt)

    def visitFunctionDef(self, node):

        for decorator in node.decorator_list:
            self.print("@{decorator:node}\n", decorator=decorator)

        args = visit_expr(node.args)
        self.print("def {name}({args})", name=node.name, args=args)

        with self.no_indent:
            if node.returns:
                self.print(" -> {:node}:", node.returns)
            else:
                self.print(":", node.returns)

        with self.indenter:
            for child in node.body:
                self.visit(child)
        return

    def visitAssign(self, node):
        targets = [visit_expr(target) for target in node.targets]

        self.print(
            "{targets} = {value:node}\n", targets=" = ".join(targets), value=node.value
        )

    def visitAnnAssign(self, node):
        self.print(
            "{target:node}: {annotation:node} = {value:node}\n",
            target=node.target,
            annotation=node.annotation,
            value=node.value,
        )

    def visitAugAssign(self, node):
        self.print("{target:node} {op:node}= {value:node}\n", **node.__dict__)

    def visitIf(self, node, indent_first=True):
        with noctx() if indent_first else self.no_indent:
            self.print("if {:node}:", node.test)

        with self.indenter:
            if node.body:
                for expr in node.body:
                    self.visit(expr)
            else:
                self.print("pass")

        if (
            node.orelse
            and len(node.orelse) == 1
            and isinstance(node.orelse[0], _ast.If)
        ):
            self.print("el")
            self.visit(node.orelse[0], indent_first=False)
        elif node.orelse:
            self.print("else:")
            with self.indenter:
                for expr in node.orelse:
                    self.visit(expr)
        self.print("\n")

    def visitImportFrom(self, node):
        for name in node.names:
            self.print("from {0} import {1:node}\n", node.module, name)

    def visitImport(self, node):
        for name in node.names:
            self.print("import {:node}\n", name)

    def visitPrint(self, node):
        self.print("print ")

        with self.no_indent:
            if node.dest:
                self.print(">> {:node}", node.dest)
                if not node.values and node.nl:
                    self.print("\n")
                    return

                self.print(", ")

            i = 0
            pc = lambda: self.print(", ") if i > 0 else None
            for value in node.values:
                pc()
                self.print("{:node}", value)

            if not node.nl:
                self.print(",")

            self.print("\n")

    def visitExec(self, node):
        self.print(
            "exec {0:node} in {1}, {2}\n",
            node.body,
            "None" if node.globals is None else str_node(node.globals),
            "None" if node.locals is None else str_node(node.locals),
        )

    def visitWith(self, node):
        self.print("with ")
        with_items = list(node.items)
        item = with_items.pop(0)
        self.print("{0:node}", item)
        while with_items:
            item = with_items.pop(0)
            self.print(", {0:node}", item)
        self.print(":", level=0)

        with self.indenter:
            if node.body:
                for expr in node.body:
                    self.visit(expr)
            else:
                self.print("pass\n")

    def visitGlobal(self, node):
        self.print("global ")
        with self.no_indent:
            names = list(node.names)
            if names:
                name = names.pop(0)
                self.print(name)
            while names:
                name = names.pop(0)
                self.print(", {0}", name)
            self.print("\n")

    def visitDelete(self, node):
        self.print("del ")

        targets = list(node.targets)

        with self.no_indent:
            target = targets.pop(0)
            self.print("{0:node}", target)
            while targets:
                target = targets.pop(0)
                self.print(", {0:node}", target)
            self.print("\n")

    def visitWhile(self, node):
        self.print("while {0:node}:", node.test)

        with self.indenter:
            if node.body:
                for expr in node.body:
                    self.visit(expr)
            else:
                self.print("pass")

        if node.orelse:
            self.print("else:")
            with self.indenter:
                for expr in node.orelse:
                    self.visit(expr)
            self.print("\n")
        self.print("\n")

    def visitExpr(self, node):
        self.print("{:node}\n", node.value)

    visitBreak = simple_string("break\n")
    visitPass = simple_string("pass\n")
    visitContinue = simple_string("continue\n")

    def visitReturn(self, node):
        if node.value is not None:
            self.print("return {:node}\n", node.value)

    def visitTry(self, node):
        self.print("try:")

        with self.indenter:
            if node.body:
                for stmnt in node.body:
                    self.visit(stmnt)
            else:
                self.print("pass")

        for hndlr in node.handlers:
            self.visit(hndlr)

        if node.orelse:
            self.print("else:")
            with self.indenter:
                for stmnt in node.orelse:
                    self.visit(stmnt)

        if node.finalbody:
            self.print("finally:")
            with self.indenter:
                for item in node.finalbody:
                    self.visit(item)

    def visitExceptHandler(self, node):
        self.print("except")

        with self.no_indent:
            if node.type:
                self.print(" {0:node}", node.type)
            if node.name:
                self.print(" as {0}", node.name)

            self.print(":")

        with self.indenter:
            for stmnt in node.body:
                self.visit(stmnt)

    def visitClassDef(self, node):

        for decorator in node.decorator_list:
            self.print("@{0:node}\n", decorator)

        self.print("class {0}", node.name)

        with self.no_indent:
            self.print("(")
            bases = list(node.bases)
            i = 0
            if bases:
                i += 1
                base = bases.pop(0)
                self.print("{0:node}", base)
                while bases:
                    base = bases.pop(0)
                    self.print(", {0:node}", base)
            keywords = list(node.keywords)

            if keywords:
                if i:
                    self.print(", ")
                i += 1
                keyword = keywords.pop(0)
                self.print("{0:node}", keyword)
                while keywords:
                    base = keywords.pop(0)
                    self.print(", {0:node}", keyword)

            self.print(")")

            self.print(":")

        with self.indenter:
            if node.body:
                for stmnt in node.body:
                    self.visit(stmnt)
            else:
                self.print("pass\n\n")


def ast_to_source(ast, file=sys.stdout):
    """
    Generate executable python source code from an ast node.

    :param ast: ast node
    :param file: file to write output to.
    """
    gen = SourceGen()
    gen.visit(ast)
    gen.dump(file)


def dump_python_source(ast):
    """
    :return: a string containing executable python source code from an ast node.

    :param ast: ast node
    :param file: file to write output to.
    """
    gen = SourceGen()
    gen.visit(ast)
    return gen.dumps()
