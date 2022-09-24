from .ir import IR


class ReplaceGlobal:
    """TODO: update for use new IR"""

    def __init__(self, ir, oldname, newname, newvalue, new_func_name=None) -> None:
        """
        mapping must be a dict with structure {name: (newname, newvalue)}
        """
        self.oldname = oldname
        self.newname = newname
        self.newvalue = newvalue
        self.ir = ir

        if new_func_name:
            self.ir.co_name = new_func_name
        else:
            self.ir.co_name = f"{newname}_{self.ir.co_name}"

    def transform(self):

        self.ir.globals[self.newname] = self.newvalue

        for i, op in enumerate(self.ir):
            if op.opname == "LOAD_GLOBAL":
                if op.argval == self.oldname:
                    self.ir.replace_op(i, argval=self.newname, arg=None)

        del self.ir.globals[self.oldname]


def replace_global(ir, mapping):
    ReplaceGlobal(ir, mapping).transform()


def main():
    import numpy as np
    import torch
    import dis

    def foo():
        return np.abs(-1)

    ir = IR.from_function(foo)
    ReplaceGlobal(ir, "np", "torch", torch).transform()

    dis.dis(ir.function())


if __name__ == "__main__":
    main()
