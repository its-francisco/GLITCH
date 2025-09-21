from __future__ import annotations
from dataclasses import dataclass
from typing import Set, TYPE_CHECKING
from abc import ABC

if TYPE_CHECKING:
    from glitch.repr.inter import Value

class AbstractValue(ABC):
    pass

@dataclass(frozen=True)
class Unknown(AbstractValue):
    pass

@dataclass(frozen=True)
class Literal(AbstractValue):
    value: "Value"

@dataclass(frozen=True)
class Conflicting(AbstractValue):
    values: Set["Value"]

@dataclass(frozen=True)
class Mixed(AbstractValue):
    values: Set["Value"]

@dataclass(frozen=True)
class NonLiteral(AbstractValue):
    pass



def meet(v1: AbstractValue, v2: AbstractValue) -> AbstractValue:
    """
    Compute least upper bound (meet) of two abstract values.
    """
    if isinstance(v1, Unknown):
        return v2

    if isinstance(v1, Literal):
        if isinstance(v2, Literal):
            return v1 if v1.value == v2.value else Conflicting({v1.value, v2.value})
        elif isinstance(v2, Conflicting):
            return Conflicting({v1.value} | v2.values)
        elif isinstance(v2, Mixed):
            return Mixed({v1.value} | v2.values)
        elif isinstance(v2, NonLiteral):
            return Mixed({v1.value})

    elif isinstance(v1, Conflicting):
        if isinstance(v2, Literal):
            return Conflicting(v1.values | {v2.value})
        elif isinstance(v2, Conflicting):
            return Conflicting(v1.values | v2.values)
        elif isinstance(v2, Mixed):
            return Mixed(v1.values | v2.values)
        elif isinstance(v2, NonLiteral):
            return Mixed(v1.values)

    elif isinstance(v1, Mixed):
        if isinstance(v2, Literal):
            return Mixed(v1.values | {v2.value})
        elif isinstance(v2, Conflicting):
            return Mixed(v1.values | v2.values)
        elif isinstance(v2, Mixed):
            return Mixed(v1.values | v2.values)
        elif isinstance(v2, NonLiteral):
            return Mixed(v1.values)

    elif isinstance(v1, NonLiteral):
        return NonLiteral()

    # should not reach
    raise NotImplementedError(f"Unhandled meet case: {v1}, {v2}")
