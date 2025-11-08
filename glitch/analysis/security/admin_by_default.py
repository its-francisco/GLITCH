import re
from glitch.analysis.rules import Error
from glitch.analysis.security.smell_checker import SecuritySmellChecker
from glitch.analysis.security.visitor import SecurityVisitor
from glitch.repr.inter import CodeElement, KeyValue
from glitch.analysis.expr_checkers.string_checker import StringChecker
from glitch.analysis.expr_checkers.var_checker import VariableChecker
from glitch.dataflow.literal_value import Literal, Conflicting, Mixed
from glitch.repr.inter import VariableReference, String
from typing import List


class AdminByDefault(SecuritySmellChecker):
    def check(self, element: CodeElement, file: str) -> List[Error]:
        if isinstance(element, KeyValue):
            var_checker = VariableChecker()

            for item in SecurityVisitor.ROLES + SecurityVisitor.USERS:
                if re.match(
                    r"[_A-Za-z0-9$\/\.\[\]-]*{text}\b".format(text=item), element.name
                ):
                    # treat variable references annotated as literal/conflicting/mixed
                    # as if they were literal values for this check
                    is_annotated_literal = (
                        isinstance(element.value, VariableReference)
                        and isinstance(
                            getattr(element.value, "literal_annotation", None),
                            (Literal, Conflicting, Mixed),
                        )
                    )

                    if not var_checker.check(element.value) or is_annotated_literal:
                        for admin in SecurityVisitor.ADMIN:
                            str_checker = StringChecker(lambda s: admin in s)
                            if str_checker.check(element.value):
                                return [
                                    Error("sec_def_admin", element, file, repr(element))
                                ]
                            # if annotated, inspect the annotated literal values
                            if isinstance(element.value, VariableReference):
                                ann = getattr(element.value, "literal_annotation", None)
                                if isinstance(ann, Literal):
                                    if isinstance(ann.value, String) and admin in ann.value.value:
                                        return [
                                            Error("sec_def_admin", element, file, repr(element))
                                        ]
                                elif isinstance(ann, (Conflicting, Mixed)):
                                    for v in ann.values:
                                        if isinstance(v, String) and admin in v.value:
                                            return [
                                                Error("sec_def_admin", element, file, repr(element))
                                            ]

        return []
