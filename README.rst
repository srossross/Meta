Meta
====

A Pure Python module containing a framework to manipulate and analyze
python abstract syntax trees and bytecode.

Example
========

This shows how to take python source to a code object and back again from within python:

.. code-block:: python

    import meta, ast
    source = '''
    a = 1
    b = 2
    c = (a ** b)
    '''

    mod = ast.parse(source, '<nofile>', 'exec')
    code = compile(mod, '<nofile>', 'exec')

    mod2 = meta.decompile(code)
    source2 = meta.dump_python_source(mod2)

    assert source == source2

This shows the depyc script. The script compiles itself, and then the compiled script extracts itself:

.. code-block:: bash

    DEPYC_FILE=`python -c"import meta.scripts.depyc; print meta.scripts.depyc.__file__"`
    depyc $DEPYC_FILE --pyc > depycX.pyc
    python -m depycX depycX.pyc --python > depycX.py
    echo depycX.py


Notes
======

* Meta is python3 compliant (mostly)

Bugs
=====

* The decompliler does not yet support complex list/set/dict - comprehensions

Testing
=======

.. code-block:: bash

    python -m unittest discover meta

    test


Versioning
==========
From the version 1.0.0, Meta follows `Semantic Versioning <http://semver.org/spec/v1.0.0.html>`_.
The version X.Y.Z indicates:

* X is the major version (backward-incompatible),
* Y is the minor version (backward-compatible), and
* Z is the patch version (backward-compatible bug fix).

Prior to version 1.0.0, custom versioning scheme was used.

