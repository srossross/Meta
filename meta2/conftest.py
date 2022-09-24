import pytest
import _ast

CORPUS = []
_marks = []


def add_expr(expr, id=None, marks=()):
    if id is None:
        id = expr
    if not isinstance(marks, (list, tuple)):
        marks = [marks]
    p = pytest.param(expr, id=id, marks=[*marks, *_marks])
    CORPUS.append(p)


# Unary
_marks = [pytest.mark.unary]
add_expr("+b")
add_expr("-b")
add_expr("~b")

# Binary
_marks = [pytest.mark.binary]
add_expr("a + b")
add_expr("a - b")
add_expr("a & b")
add_expr("a | b")
add_expr("a ^ b")
add_expr("a / b")
add_expr("a // b")
add_expr("a << b")
add_expr("a >> b")
add_expr(r"a % b")
add_expr(r"a @ b")
add_expr(r"a * b")
add_expr(r"a ** b")
# add_expr(r"x = a < b > c in d")
# add_expr(r"c = a and b")

# Exprs
_marks = [pytest.mark.expr]
add_expr("a")
add_expr("a.b")
add_expr("a.b.c")


# Calling
_marks = [pytest.mark.func]
add_expr("foo()")
add_expr("a = foo()")
add_expr("foo(x)")
add_expr("foo(x, y)")
add_expr("foo(x=y)")
add_expr("foo(z, x=y)")
add_expr("foo(y, *z)")
add_expr("foo(y=a, **z)")
# add_expr("foo(r, a, *d, b=c, **z)")

# Lists
_marks = [pytest.mark.list]
add_expr("[]")
add_expr("[a, b]")
add_expr("[*a, b]")
add_expr("[a, *b]")
add_expr("[c, *a, b]")

# Dicts
_marks = [pytest.mark.dict]
add_expr(r"{}")
add_expr(r"{a: b, c: d}")
add_expr(r"{**kw, x: y}")

# Sets
_marks = [pytest.mark.set]
add_expr(r"{a, b}")

# Indexing
_marks = [pytest.mark.index]
add_expr("a[0]")
add_expr("a[b]")
add_expr("a[b, c]")
add_expr("a[:]")
add_expr("a[1:]")
add_expr("a[1:2]")
add_expr("a[1:2:3]")
add_expr("a[1::3]")
add_expr("a[::3]")
add_expr("a[:3]")
add_expr("a[...]")

# Assignments
_marks = [pytest.mark.assign]
add_expr("a = b")
add_expr("a.b = c")
add_expr("a, b = c")
add_expr("a, b, c = d", "unpack3")
add_expr("a = b = c", "multi_assign2")
add_expr("a = b = c = d", "multi_assign3")

_marks = [pytest.mark.blocks]
add_expr(
    """
with a: 
    b = 1
c = 2
"""
)

_marks = [pytest.mark.cond]
add_expr("a < b < c; b =1 ")
add_expr("if a: b")

_marks = [pytest.mark.loop]
add_expr("for i in j: b")
add_expr(
    """
for i in j: 
    b
    if a: break
else:
    c
d
"""
)
add_expr(
    """
while i > k > l: 
    j
"""
)

_marks = []


@pytest.fixture(params=CORPUS)
def corpus(request):
    yield request.param


def ast_deep_equal(node1, node2, field_name=""):
    assert type(node1) == type(node2)

    if isinstance(node1, (list, tuple)):
        assert len(node1) == len(node2), f"{field_name} is not the same size"
        for i, (a, b) in enumerate(zip(node1, node2)):
            ast_deep_equal(a, b, field_name=f"{field_name}[{i}]")
        return

    if not isinstance(node1, _ast.AST):
        assert node1 == node2, f"{field_name} is not equal ({node1} != {node2})"
        return

    if isinstance(node1, _ast.AST):
        for field in node1._fields:
            node1_field = getattr(node1, field)
            node2_field = getattr(node2, field)
            ast_deep_equal(node1_field, node2_field, field_name=f"{field_name}.{field}")
        return
