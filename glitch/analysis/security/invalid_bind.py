import re
from glitch.analysis.rules import Error
from glitch.analysis.security.smell_checker import SecuritySmellChecker
from glitch.analysis.security.visitor import SecurityVisitor
from glitch.repr.inter import *
from glitch.analysis.expr_checkers.string_checker import StringChecker
from glitch.dataflow.literal_value import Literal, Conflicting, Mixed
from glitch.repr.inter import VariableReference, String, Boolean
from typing import Any
from typing import List


class InvalidBind(SecuritySmellChecker):
    def check(self, element: CodeElement, file: str) -> List[Error]:
        check_invalid = StringChecker(
            lambda s: re.match(r"(?:https?://|^)0.0.0.0", s) is not None
        )
        check_ipv6 = StringChecker(lambda s: s in {"*", "::"})
        def annotated_string_check(expr: Any, checker: StringChecker) -> bool:
            # direct string check
            if checker.check(expr):
                return True
            # check variable references annotated with literal/conflicting/mixed
            if isinstance(expr, VariableReference):
                ann = getattr(expr, "literal_annotation", None)
                if isinstance(ann, Literal):
                    v = ann.value
                    if isinstance(v, String):
                        return checker.str_check(v.value)
                elif isinstance(ann, (Conflicting, Mixed)):
                    for v in ann.values:
                        if isinstance(v, String) and checker.str_check(v.value):
                            return True
            return False

        def annotated_boolean_true(expr: Any) -> bool:
            if isinstance(expr, Boolean) and expr.value is True:
                return True
            if isinstance(expr, VariableReference):
                ann = getattr(expr, "literal_annotation", None)
                if isinstance(ann, Literal):
                    v = ann.value
                    if isinstance(v, Boolean) and v.value is True:
                        return True
                elif isinstance(ann, (Conflicting, Mixed)):
                    for v in ann.values:
                        if isinstance(v, Boolean) and v.value is True:
                            return True
            return False

        if isinstance(element, KeyValue) and (
            annotated_string_check(element.value, check_invalid)
            or (element.name == "ip" and annotated_string_check(element.value, check_ipv6))
            or (
                element.name in SecurityVisitor.IP_BIND_COMMANDS
                and (
                    annotated_boolean_true(element.value)
                    or annotated_string_check(element.value, check_ipv6)
                )
            )
        ):
            return [Error("sec_invalid_bind", element, file, repr(element))]

        return []
