from typing import Any
import unittest
from importlib.resources import files

from glitch.repr.inter import UnitBlock
from glitch.dataflow.cfg import CFGBuilder
from glitch.dataflow.analysis import analyze_cfg_literals
from glitch.tech import Tech
from glitch.tests.dataflow.ir_builder import IRBuilder
from glitch.analysis.security.visitor import SecurityVisitor




class TestIRJsonLintingDataflow(unittest.TestCase):
  def __help_test(self, inter, n_errors: int, codes, lines) -> None:
    analysis = SecurityVisitor(Tech.ansible)
    analysis.config(str(files("glitch") / "configs/default.ini"))
    errors = list(
      filter(lambda e: e.code.startswith("sec_"), set(analysis.check(inter)))
    )
    errors = sorted(errors, key=lambda e: (e.path, e.line, e.code))
    self.assertEqual(len(errors), n_errors)
    for i in range(n_errors):
      self.assertEqual(errors[i].code, codes[i])
      self.assertEqual(errors[i].line, lines[i])


    def __contains_annotation(self, jsonRepr: Any, var_name: str, var_value: str) -> bool:
      if isinstance(jsonRepr, dict):
        if (
          jsonRepr.get("ir_type", "") == "VariableReference"
          and jsonRepr.get("code", "") == var_name
          and "literal_annotation" in jsonRepr
          and jsonRepr.get("literal_annotation", "")['type'] in ['Mixed', 'Literal', 'Conflicting']
          and var_value in jsonRepr.get("literal_annotation").get("values")
        ):
          
          return True
        return any(self.__contains_annotation(child, var_name, var_value) for child in jsonRepr.values() if isinstance(child, dict) or isinstance(child, list))
      elif isinstance(jsonRepr, list):
        return any(self.__contains_annotation(item, var_name, var_value) for item in jsonRepr)
      return False
    
    def __finds_variable_reference(self, inter: UnitBlock, var_name: str, var_value: str) -> bool:
        node: Any = inter.as_dict()
        return self.__contains_annotation(node, var_name, var_value)

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

    def test_simple_has__admin(self):
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
      "line": 1,
      "column": 1,
      "end_line": 1,
      "end_column": 11,
      "code": "a",
      "name": "a",
      "value": {
        "ir_type": "String",
        "line": 1,
        "column": 5,
        "end_line": 1,
        "end_column": 11,
        "code": "root",
        "value": "root"
      }
    }
  ],
  "atomic_units": [
    {
      "ir_type": "AtomicUnit",
      "line": 7,
      "column": -33550336,
      "end_line": -33550336,
      "end_column": -33550336,
      "code": "chef_file file do\\n    sensitive new_resource.sensitive if new_resource.sensitive\\n    source src\\n    user a          \\n    group a         \\n    mode '0644'\\nend",
      "statements": [],
      "name": {
        "ir_type": "VariableReference",
        "line": 7,
        "column": 13,
        "end_line": 7,
        "end_column": 17,
        "code": "file",
        "value": "file"
      },
      "type": "chef_file",
      "attributes": [
        {
          "ir_type": "Attribute",
          "line": 8,
          "column": 5,
          "end_line": 8,
          "end_column": 37,
          "code": "sensitive new_resource.sensitive",
          "name": "sensitive",
          "value": {
            "ir_type": "MethodCall",
            "line": 8,
            "column": 15,
            "end_line": 8,
            "end_column": 37,
            "code": "new_resource.sensitive",
            "receiver": {
              "ir_type": "VariableReference",
              "line": 8,
              "column": 15,
              "end_line": 8,
              "end_column": 27,
              "code": "new_resource",
              "value": "new_resource"
            },
            "method": "sensitive",
            "args": []
          }
        },
        {
          "ir_type": "Attribute",
          "line": 9,
          "column": 5,
          "end_line": 9,
          "end_column": 15,
          "code": "source src",
          "name": "source",
          "value": {
            "ir_type": "VariableReference",
            "line": 9,
            "column": 12,
            "end_line": 9,
            "end_column": 15,
            "code": "src",
            "value": "src"
          }
        },
        {
          "ir_type": "Attribute",
          "line": 10,
          "column": 5,
          "end_line": 10,
          "end_column": 11,
          "code": "user a",
          "name": "user",
          "value": {
            "ir_type": "VariableReference",
            "line": 10,
            "column": 10,
            "end_line": 10,
            "end_column": 11,
            "code": "a",
            "value": "a"
          }
        },
        {
          "ir_type": "Attribute",
          "line": 11,
          "column": 5,
          "end_line": 11,
          "end_column": 12,
          "code": "group a",
          "name": "group",
          "value": {
            "ir_type": "VariableReference",
            "line": 11,
            "column": 11,
            "end_line": 11,
            "end_column": 12,
            "code": "a",
            "value": "a"
          }
        },
        {
          "ir_type": "Attribute",
          "line": 12,
          "column": 5,
          "end_line": 12,
          "end_column": 16,
          "code": "mode '0644'",
          "name": "mode",
          "value": {
            "ir_type": "String",
            "line": 12,
            "column": 10,
            "end_line": 12,
            "end_column": 16,
            "code": "0644",
            "value": "0644"
          }
        }
      ]
    }
  ],
  "unit_blocks": [],
  "attributes": [],
  "name": "admin.rb",
  "path": "tests/security/chef/files/admin.rb",
  "type": "script"
}

          """
          unit_block = self.IRBuilder.from_json(json_string)
          self.assertIsInstance(unit_block, UnitBlock)

          cfg_builder = CFGBuilder(unit_block)
          cfg = cfg_builder.build()
          analyze_cfg_literals(cfg)
          self.assertIsNotNone(unit_block)

          assert self.__finds_variable_reference(unit_block, 'a', 'root')
    
    
    def test_has_admin_many_paths(self):
          json_string = """
        {
  "ir_type": "UnitBlock",
  "line": -33550336,
  "column": -33550336,
  "end_line": -33550336,
  "end_column": -33550336,
  "code": "",
  "statements": [
    {
      "ir_type": "ConditionalStatement",
      "line": 1,
      "column": -33550336,
      "end_line": -33550336,
      "end_column": -33550336,
      "code": "new_resource.admin_mode\\n  a = 'root'\\nelse\\n  a = new_resource.chef_user",
      "statements": [
        {
          "ir_type": "Variable",
          "line": 2,
          "column": 3,
          "end_line": 2,
          "end_column": 13,
          "code": "a",
          "name": "a",
          "value": {
            "ir_type": "String",
            "line": 2,
            "column": 7,
            "end_line": 2,
            "end_column": 13,
            "code": "root",
            "value": "root"
          }
        }
      ],
      "condition": {
        "ir_type": "MethodCall",
        "line": 1,
        "column": 4,
        "end_line": 1,
        "end_column": 27,
        "code": "new_resource.admin_mode",
        "receiver": {
          "ir_type": "VariableReference",
          "line": 1,
          "column": 4,
          "end_line": 1,
          "end_column": 16,
          "code": "new_resource",
          "value": "new_resource"
        },
        "method": "admin_mode",
        "args": []
      },
      "type": "IF",
      "is_default": false,
      "else_statement": {
        "ir_type": "ConditionalStatement",
        "line": 4,
        "column": -33550336,
        "end_line": -33550336,
        "end_column": -33550336,
        "code": "a = new_resource.chef_user",
        "statements": [
          {
            "ir_type": "Variable",
            "line": 4,
            "column": 3,
            "end_line": 4,
            "end_column": 29,
            "code": "a",
            "name": "a",
            "value": {
              "ir_type": "MethodCall",
              "line": 4,
              "column": 7,
              "end_line": 4,
              "end_column": 29,
              "code": "new_resource.chef_user",
              "receiver": {
                "ir_type": "VariableReference",
                "line": 4,
                "column": 7,
                "end_line": 4,
                "end_column": 19,
                "code": "new_resource",
                "value": "new_resource"
              },
              "method": "chef_user",
              "args": []
            }
          }
        ],
        "condition": {
          "ir_type": "Null",
          "line": 4294967296,
          "column": 4294967296,
          "end_line": 4294967296,
          "end_column": 4294967296,
          "code": "",
          "value": null
        },
        "type": "IF",
        "is_default": true,
        "else_statement": null
      }
    }
  ],
  "dependencies": [],
  "comments": [],
  "variables": [],
  "atomic_units": [
    {
      "ir_type": "AtomicUnit",
      "line": 9,
      "column": -33550336,
      "end_line": -33550336,
      "end_column": -33550336,
      "code": "chef_file file do\\n    user a\\nend",
      "statements": [],
      "name": {
        "ir_type": "VariableReference",
        "line": 9,
        "column": 13,
        "end_line": 9,
        "end_column": 17,
        "code": "file",
        "value": "file"
      },
      "type": "chef_file",
      "attributes": [
        {
          "ir_type": "Attribute",
          "line": 10,
          "column": 5,
          "end_line": 10,
          "end_column": 11,
          "code": "user a",
          "name": "user",
          "value": {
            "ir_type": "VariableReference",
            "line": 10,
            "column": 10,
            "end_line": 10,
            "end_column": 11,
            "code": "a",
            "value": "a"
          }
        }
      ]
    }
  ],
  "unit_blocks": [],
  "attributes": [],
  "name": "admin.rb",
  "path": "tests/security/chef/files/admin.rb",
  "type": "script"
}

          """
          unit_block = self.IRBuilder.from_json(json_string)
          self.assertIsInstance(unit_block, UnitBlock)

          cfg_builder = CFGBuilder(unit_block)
          cfg = cfg_builder.build()
          analyze_cfg_literals(cfg)
          self.assertIsNotNone(unit_block)

          self.__finds_variable_reference(unit_block, 'a', 'root')

    