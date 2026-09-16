from typing import Protocol, cast

import qm.qua as q
from qm.qua._dsl import _ResultSource


class QuaVarWithStream(Protocol):
    st: _ResultSource

    def save(self) -> None: ...


def declare_qm_var(typ, stream_func=None) -> QuaVarWithStream:
    var = q.declare(typ)
    st = q.declare_stream()
    var.st = st
    # var.stream_func = stream_func
    var.save = lambda v=var, s=st: q.save(v, s)
    return cast(QuaVarWithStream, var)


def vars_save(*vars):
    for var in vars:
        var.save()
