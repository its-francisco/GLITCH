import unittest

from glitch.repr.inter import UnitBlock
from glitch.dataflow.cfg import CFGBuilder
from glitch.dataflow.analysis import analyze_cfg_literals
from glitch.analysis.rules import RuleVisitor, Error
from glitch.tech import Tech
from glitch.tests.dataflow.ir_builder import IRBuilder
from glitch.analysis.security.visitor import SecurityVisitor


import json

class TestIRJsonLintingDataflow(unittest.TestCase):
    def __help_test(self, inter, n_errors: int, codes, lines) -> None:
        analysis = SecurityVisitor(Tech.ansible)
        analysis.config("configs/default.ini")
        errors = list(
            filter(lambda e: e.code.startswith("sec_"), set(analysis.check(inter)))
        )
        errors = sorted(errors, key=lambda e: (e.path, e.line, e.code))
        self.assertEqual(len(errors), n_errors)
        for i in range(n_errors):
            self.assertEqual(errors[i].code, codes[i])
            self.assertEqual(errors[i].line, lines[i])

    
    def setUp(self):
        self.IRBuilder = IRBuilder

    def test_indirect_simple(self):
        json_string = """
        {
          "ir_type": "UnitBlock",
          "line": -33550336,
          "column": -33550336,
          "end_line": -33550336,
          "end_column": -33550336,
          "code": "",
          "statements": [],
          "dependencies": [],
          "comments": [],
          "variables": [
          ],
          "atomic_units": [],
          "unit_blocks": [
            {
              "ir_type": "UnitBlock",
              "line": -33550336,
              "column": -33550336,
              "end_line": -33550336,
              "end_column": -33550336,
              "code": "",
              "statements": [],
              "dependencies": [],
              "comments": [],
              "variables": [
                {
                  "ir_type": "Variable",
                  "line": 3,
                  "column": 5,
                  "end_line": 3,
                  "end_column": 18,
                  "code": "    a_var: sekrit\\n",
                  "name": "a_var",
                  "value": {
                    "ir_type": "String",
                    "line": 3,
                    "column": 12,
                    "end_line": 3,
                    "end_column": 18,
                    "code": "sekrit",
                    "value": "sekrit"
                  }
                }
              ],
              "atomic_units": [
                {
                  "ir_type": "AtomicUnit",
                  "line": 5,
                  "column": -33550336,
                  "end_line": -33550336,
                  "end_column": -33550336,
                  "code": "    - name: test\\n      user:\\n        name: me\\n        password: '{{ a_var }}'",
                  "statements": [],
                  "name": {
                    "ir_type": "String",
                    "line": 5,
                    "column": 13,
                    "end_line": 5,
                    "end_column": 17,
                    "code": "test",
                    "value": "test"
                  },
                  "type": "user",
                  "attributes": [
                    {
                      "ir_type": "Attribute",
                      "line": 7,
                      "column": 9,
                      "end_line": 7,
                      "end_column": 17,
                      "code": "name: me",
                      "name": "name",
                      "value": {
                        "ir_type": "String",
                        "line": 7,
                        "column": 15,
                        "end_line": 7,
                        "end_column": 17,
                        "code": "me",
                        "value": "me"
                      }
                    },
                    {
                      "ir_type": "Attribute",
                      "line": 8,
                      "column": 9,
                      "end_line": 8,
                      "end_column": 32,
                      "code": "password: '{{ a_var }}'",
                      "name": "password",
                      "value": {
                        "ir_type": "VariableReference",
                        "line": 8,
                        "column": 23,
                        "end_line": 8,
                        "end_column": 28,
                        "code": "a_var }}'",
                        "value": "a_var"
                      }
                    }
                  ]
                }
              ],
              "unit_blocks": [],
              "attributes": [
                {
                  "ir_type": "Attribute",
                  "line": 1,
                  "column": 3,
                  "end_line": 1,
                  "end_column": 19,
                  "code": "hosts: localhost",
                  "name": "hosts",
                  "value": {
                    "ir_type": "String",
                    "line": 1,
                    "column": 10,
                    "end_line": 1,
                    "end_column": 19,
                    "code": "localhost",
                    "value": "localhost"
                  }
                }
              ],
              "name": "",
              "path": "dataflow/test/indirect-simple.yaml",
              "type": "block"
            }
          ],
          "attributes": [],
          "name": "dataflow/test/indirect-simple.yaml",
          "path": "dataflow/test/indirect-simple.yaml",
          "type": "script"
        }
        """

        unit_block = self.IRBuilder.from_json(json_string)
        self.assertIsInstance(unit_block, UnitBlock)

        cfg_builder = CFGBuilder(unit_block)
        cfg = cfg_builder.build()
        analyze_cfg_literals(cfg)
        self.assertIsNotNone(unit_block)

        self.__help_test(unit_block, 2, ["sec_hard_pass", "sec_hard_secr"], [8, 8])


    def test_innerscope_alias(self):
        json_string = """
        {
          "ir_type": "UnitBlock",
          "line": -33550336,
          "column": -33550336,
          "end_line": -33550336,
          "end_column": -33550336,
          "code": "",
          "statements": [],
          "dependencies": [],
          "comments": [],
          "variables": [
                {
                  "ir_type": "Variable",
                  "line": 2,
                  "column": 5,
                  "end_line": 3,
                  "end_column": 18,
                  "code": "    a_var: sekrit\\n",
                  "name": "a_var",
                  "value": {
                    "ir_type": "String",
                    "line": 3,
                    "column": 12,
                    "end_line": 3,
                    "end_column": 18,
                    "code": "sekrit",
                    "value": "sekrit"
                  }
                }
              ],
          "atomic_units": [],
          "unit_blocks": [
            {
              "ir_type": "UnitBlock",
              "line": -33550336,
              "column": -33550336,
              "end_line": -33550336,
              "end_column": -33550336,
              "code": "",
              "statements": [],
              "dependencies": [],
              "comments": [],
              "variables": [
                {
                    "ir_type": "Variable",
                    "line": 3,
                    "column": 5,
                    "end_line": 3,
                    "end_column": 18,
                    "code": "    a_var: \\"{{ lookup('env', 'DATABASE_PASSWORD') }}\\"\\n",
                    "name": "a_var",
                    "value": {
                        "ir_type": "FunctionCall",
                        "line": 3,
                        "column": 18,
                        "end_line": 6,
                        "end_column": 19,
                        "code": "('env', 'DA"
                    }
                }
              ],
              "atomic_units": [
                {
                  "ir_type": "AtomicUnit",
                  "line": 5,
                  "column": -33550336,
                  "end_line": -33550336,
                  "end_column": -33550336,
                  "code": "    - name: test\\n      user:\\n        name: me\\n        password: '{{ a_var }}'",
                  "statements": [],
                  "name": {
                    "ir_type": "String",
                    "line": 5,
                    "column": 13,
                    "end_line": 5,
                    "end_column": 17,
                    "code": "test",
                    "value": "test"
                  },
                  "type": "user",
                  "attributes": [
                    {
                      "ir_type": "Attribute",
                      "line": 7,
                      "column": 9,
                      "end_line": 7,
                      "end_column": 17,
                      "code": "name: me",
                      "name": "name",
                      "value": {
                        "ir_type": "String",
                        "line": 7,
                        "column": 15,
                        "end_line": 7,
                        "end_column": 17,
                        "code": "me",
                        "value": "me"
                      }
                    },
                    {
                      "ir_type": "Attribute",
                      "line": 8,
                      "column": 9,
                      "end_line": 8,
                      "end_column": 32,
                      "code": "password: '{{ a_var }}'",
                      "name": "password",
                      "value": {
                        "ir_type": "VariableReference",
                        "line": 8,
                        "column": 23,
                        "end_line": 8,
                        "end_column": 28,
                        "code": "a_var }}'",
                        "value": "a_var"
                      }
                    }
                  ]
                }
              ],
              "unit_blocks": [],
              "attributes": [
                {
                  "ir_type": "Attribute",
                  "line": 1,
                  "column": 3,
                  "end_line": 1,
                  "end_column": 19,
                  "code": "hosts: localhost",
                  "name": "hosts",
                  "value": {
                    "ir_type": "String",
                    "line": 1,
                    "column": 10,
                    "end_line": 1,
                    "end_column": 19,
                    "code": "localhost",
                    "value": "localhost"
                  }
                }
              ],
              "name": "",
              "path": "dataflow/test/indirect-simple.yaml",
              "type": "block"
            }
          ],
          "attributes": [],
          "name": "dataflow/test/indirect-simple.yaml",
          "path": "dataflow/test/indirect-simple.yaml",
          "type": "script"
        }
        """
        unit_block = self.IRBuilder.from_json(json_string)
        self.assertIsInstance(unit_block, UnitBlock)

        cfg_builder = CFGBuilder(unit_block)
        cfg = cfg_builder.build()
        analyze_cfg_literals(cfg)
        self.assertIsNotNone(unit_block)

        self.__help_test(unit_block, 0, [], [])

    def test_outerscope_should_remain_unchanged_alias(self):
        json_string = """
        {
          "ir_type": "UnitBlock",
          "line": -33550336,
          "column": -33550336,
          "end_line": -33550336,
          "end_column": -33550336,
          "code": "",
          "statements": [],
          "dependencies": [],
          "comments": [],
          "variables": [
                {
                  "ir_type": "Variable",
                  "line": 2,
                  "column": 5,
                  "end_line": 3,
                  "end_column": 18,
                  "code": "    a_var: sekrit\\n",
                  "name": "a_var",
                  "value": {
                    "ir_type": "String",
                    "line": 3,
                    "column": 12,
                    "end_line": 3,
                    "end_column": 18,
                    "code": "sekrit",
                    "value": "sekrit"
                  }
                }
              ],
          "atomic_units": [
                {
                  "ir_type": "AtomicUnit",
                  "line": 6,
                  "column": -33550336,
                  "end_line": -33550336,
                  "end_column": -33550336,
                  "code": "    - name: test\\n      user:\\n        name: me\\n        password: '{{ a_var }}'",
                  "statements": [],
                  "name": {
                    "ir_type": "String",
                    "line": 5,
                    "column": 13,
                    "end_line": 5,
                    "end_column": 17,
                    "code": "test",
                    "value": "test"
                  },
                  "type": "user",
                  "attributes": [
                    {
                      "ir_type": "Attribute",
                      "line": 7,
                      "column": 9,
                      "end_line": 7,
                      "end_column": 17,
                      "code": "name: me",
                      "name": "name",
                      "value": {
                        "ir_type": "String",
                        "line": 7,
                        "column": 15,
                        "end_line": 7,
                        "end_column": 17,
                        "code": "me",
                        "value": "me"
                      }
                    },
                    {
                      "ir_type": "Attribute",
                      "line": 8,
                      "column": 9,
                      "end_line": 8,
                      "end_column": 32,
                      "code": "password: '{{ a_var }}'",
                      "name": "password",
                      "value": {
                        "ir_type": "VariableReference",
                        "line": 8,
                        "column": 23,
                        "end_line": 8,
                        "end_column": 28,
                        "code": "a_var }}'",
                        "value": "a_var"
                      }
                    }
                  ]
                }],
          "unit_blocks": [
            {
              "ir_type": "UnitBlock",
              "line": -33550336,
              "column": -33550336,
              "end_line": -33550336,
              "end_column": -33550336,
              "code": "",
              "statements": [],
              "dependencies": [],
              "comments": [],
              "variables": [
                {
                    "ir_type": "Variable",
                    "line": 3,
                    "column": 5,
                    "end_line": 3,
                    "end_column": 18,
                    "code": "    a_var: \\"{{ lookup('env', 'DATABASE_PASSWORD') }}\\"\\n",
                    "name": "a_var",
                    "value": {
                        "ir_type": "FunctionCall",
                        "line": 3,
                        "column": 18,
                        "end_line": 6,
                        "end_column": 19,
                        "code": "('env', 'DA"
                    }
                }
              ],
              "atomic_units": [
              ],
              "unit_blocks": [],
              "attributes": [
                {
                  "ir_type": "Attribute",
                  "line": 1,
                  "column": 3,
                  "end_line": 1,
                  "end_column": 19,
                  "code": "hosts: localhost",
                  "name": "hosts",
                  "value": {
                    "ir_type": "String",
                    "line": 1,
                    "column": 10,
                    "end_line": 1,
                    "end_column": 19,
                    "code": "localhost",
                    "value": "localhost"
                  }
                }
              ],
              "name": "",
              "path": "dataflow/test/indirect-simple.yaml",
              "type": "block"
            }
          ],
          "attributes": [],
          "name": "dataflow/test/indirect-simple.yaml",
          "path": "dataflow/test/indirect-simple.yaml",
          "type": "script"
        }
        """
        unit_block = self.IRBuilder.from_json(json_string)
        self.assertIsInstance(unit_block, UnitBlock)

        cfg_builder = CFGBuilder(unit_block)
        cfg = cfg_builder.build()
        analyze_cfg_literals(cfg)
        self.assertIsNotNone(unit_block)

        self.__help_test(unit_block, 2, ["sec_hard_pass", "sec_hard_secr"], [8,8])
