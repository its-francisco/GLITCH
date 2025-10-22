import json
from typing import Any, Dict, List
from glitch.repr.inter import (
    UnitBlock, UnitBlockType, Variable, AtomicUnit, Attribute,
    String, VariableReference, ElementInfo, Integer, Float, Boolean,
    Null, Complex, Array, Hash, FunctionCall, MethodCall,
    BinaryOperation, UnaryOperation, Not, Minus,
    Or, And, Sum, Equal, NotEqual, LessThan, LessThanOrEqual,
    GreaterThan, GreaterThanOrEqual, In, Subtract, Multiply,
    Divide, Modulo, Power, RightShift, LeftShift, Access,
    BitwiseAnd, BitwiseOr, BitwiseXor, Assign,
    ConditionalStatement, Comment, Dependency, Expr, Value
)


class IRBuilder:
    """Builds IR objects from JSON representation."""
    
    @staticmethod
    def create_element_info(data: Dict[str, Any]) -> ElementInfo:
        """Create ElementInfo from JSON data."""
        return ElementInfo(
            line=data.get("line", -33550336),
            column=data.get("column", -33550336),
            end_line=data.get("end_line", -33550336),
            end_column=data.get("end_column", -33550336),
            code=data.get("code", "")
        )

    @staticmethod
    def json_to_expr(data: Dict[str, Any]) -> Expr:
        """Convert JSON dictionary to appropriate Expr object."""
        ir_type = data.get("ir_type")
        info = IRBuilder.create_element_info(data)
        
        # Value types
        if ir_type == "String":
            return String(value=data["value"], info=info)
        elif ir_type == "Integer":
            return Integer(value=data["value"], info=info)
        elif ir_type == "Float":
            return Float(value=data["value"], info=info)
        elif ir_type == "Boolean":
            return Boolean(value=data["value"], info=info)
        elif ir_type == "Complex":
            return Complex(value=complex(data["value"]), info=info)
        elif ir_type == "Null":
            return Null(info=info)
        elif ir_type == "VariableReference":
            # Preserve literal_annotation if provided in JSON
            var_ref = VariableReference(value=data["value"], info=info)
            if "literal_annotation" in data:
                setattr(var_ref, "literal_annotation", data.get("literal_annotation"))
            else:
                # Ensure attribute exists (None if not provided)
                setattr(var_ref, "literal_annotation", None)
            return var_ref
        
        # Collection types
        elif ir_type == "Array":
            values = [IRBuilder.json_to_expr(v) for v in data["value"]]
            return Array(value=values, info=info)
        elif ir_type == "Hash":
            hash_dict = {}
            for item in data["value"]:
                key = IRBuilder.json_to_expr(item["key"])
                value = IRBuilder.json_to_expr(item["value"])
                hash_dict[key] = value
            return Hash(value=hash_dict, info=info)
        
        # Function and method calls
        elif ir_type == "FunctionCall":
            args = [IRBuilder.json_to_expr(arg) for arg in data.get("args", [])]
            return FunctionCall(name=data.get("name", ""), args=args, info=info)
        elif ir_type == "MethodCall":
            receiver = IRBuilder.json_to_expr(data["receiver"])
            args = [IRBuilder.json_to_expr(arg) for arg in data.get("args", [])]
            return MethodCall(receiver=receiver, method=data["method"], args=args, info=info)
        
        # Unary operations
        elif ir_type == "Not":
            expr = IRBuilder.json_to_expr(data["expr"])
            return Not(info=info, expr=expr)
        elif ir_type == "Minus":
            expr = IRBuilder.json_to_expr(data["expr"])
            return Minus(info=info, expr=expr)
        
        # Binary operations
        elif ir_type in ["Or", "And", "Sum", "Equal", "NotEqual", "LessThan", 
                         "LessThanOrEqual", "GreaterThan", "GreaterThanOrEqual",
                         "In", "Subtract", "Multiply", "Divide", "Modulo", "Power",
                         "RightShift", "LeftShift", "Access", "BitwiseAnd", 
                         "BitwiseOr", "BitwiseXor", "Assign"]:
            left = IRBuilder.json_to_expr(data["left"])
            right = IRBuilder.json_to_expr(data["right"])
            
            binary_ops = {
                "Or": Or, "And": And, "Sum": Sum, "Equal": Equal, "NotEqual": NotEqual,
                "LessThan": LessThan, "LessThanOrEqual": LessThanOrEqual,
                "GreaterThan": GreaterThan, "GreaterThanOrEqual": GreaterThanOrEqual,
                "In": In, "Subtract": Subtract, "Multiply": Multiply, "Divide": Divide,
                "Modulo": Modulo, "Power": Power, "RightShift": RightShift,
                "LeftShift": LeftShift, "Access": Access, "BitwiseAnd": BitwiseAnd,
                "BitwiseOr": BitwiseOr, "BitwiseXor": BitwiseXor, "Assign": Assign
            }
            
            op_class = binary_ops.get(ir_type)
            if op_class:
                return op_class(info=info, left=left, right=right)
        
        raise ValueError(f"Unknown ir_type: {ir_type}")

    @staticmethod
    def json_to_attribute(data: Dict[str, Any]) -> Attribute:
        """Convert JSON to Attribute object."""
        info = IRBuilder.create_element_info(data)
        value = IRBuilder.json_to_expr(data["value"])
        return Attribute(name=data["name"], value=value, info=info)

    @staticmethod
    def json_to_variable(data: Dict[str, Any]) -> Variable:
        """Convert JSON to Variable object."""
        info = IRBuilder.create_element_info(data)
        value = IRBuilder.json_to_expr(data["value"])
        return Variable(name=data["name"], value=value, info=info)

    @staticmethod
    def json_to_atomic_unit(data: Dict[str, Any]) -> AtomicUnit:
        """Convert JSON to AtomicUnit object."""
        name = IRBuilder.json_to_expr(data["name"])
        atomic_unit = AtomicUnit(name=name, type=data["type"])
        atomic_unit.set_element_info(IRBuilder.create_element_info(data))
        
        # Add attributes
        for attr_data in data.get("attributes", []):
            atomic_unit.add_attribute(IRBuilder.json_to_attribute(attr_data))
        
        # Add statements if any
        for stmt_data in data.get("statements", []):
            if isinstance(stmt_data, dict):
                stmt = IRBuilder.json_to_code_element(stmt_data)
                atomic_unit.add_statement(stmt)
        
        return atomic_unit

    @staticmethod
    def json_to_comment(data: Dict[str, Any]) -> Comment:
        """Convert JSON to Comment object."""
        comment = Comment(content=data["content"])
        comment.line = data.get("line", -33550336)
        comment.column = data.get("column", -33550336)
        comment.end_line = data.get("end_line", -33550336)
        comment.end_column = data.get("end_column", -33550336)
        comment.code = data.get("code", "")
        return comment

    @staticmethod
    def json_to_dependency(data: Dict[str, Any]) -> Dependency:
        """Convert JSON to Dependency object."""
        dependency = Dependency(names=data["names"])
        dependency.line = data.get("line", -33550336)
        dependency.column = data.get("column", -33550336)
        dependency.end_line = data.get("end_line", -33550336)
        dependency.end_column = data.get("end_column", -33550336)
        dependency.code = data.get("code", "")
        return dependency

    @staticmethod
    def json_to_conditional_statement(data: Dict[str, Any]) -> ConditionalStatement:
        """Convert JSON to ConditionalStatement object."""
        # Parse condition type
        cond_type_str = data.get("type", "IF")
        if cond_type_str == "IF":
            cond_type = ConditionalStatement.ConditionType.IF
        elif cond_type_str == "SWITCH":
            cond_type = ConditionalStatement.ConditionType.SWITCH
        else:
            cond_type = ConditionalStatement.ConditionType.IF
        
        # Create condition expression
        condition = IRBuilder.json_to_expr(data["condition"])
        
        # Create conditional statement
        is_default = data.get("is_default", False)
        conditional = ConditionalStatement(
            condition=condition,
            type=cond_type,
            is_default=is_default
        )
        
        # Set element info
        conditional.set_element_info(IRBuilder.create_element_info(data))
        
        # Add statements
        for stmt_data in data.get("statements", []):
            if isinstance(stmt_data, dict):
                stmt = IRBuilder.json_to_code_element(stmt_data)
                conditional.add_statement(stmt)
        
        # Handle else statement
        if data.get("else_statement") is not None:
            conditional.else_statement = IRBuilder.json_to_conditional_statement(data["else_statement"])
        
        return conditional

    @staticmethod
    def json_to_unit_block(data: Dict[str, Any]) -> UnitBlock:
        """Convert JSON to UnitBlock object."""
        # Get type
        block_type = UnitBlockType(data["type"])
        
        # Create unit block
        unit_block = UnitBlock(name=data.get("name"), type=block_type)
        unit_block.path = data.get("path", "")
        unit_block.set_element_info(IRBuilder.create_element_info(data))
        
        # Add dependencies
        for dep_data in data.get("dependencies", []):
            unit_block.add_dependency(IRBuilder.json_to_dependency(dep_data))
        
        # Add comments
        for comment_data in data.get("comments", []):
            unit_block.add_comment(IRBuilder.json_to_comment(comment_data))
        
        # Add variables
        for var_data in data.get("variables", []):
            unit_block.add_variable(IRBuilder.json_to_variable(var_data))
        
        # Add atomic units
        for atomic_data in data.get("atomic_units", []):
            unit_block.add_atomic_unit(IRBuilder.json_to_atomic_unit(atomic_data))
        
        # Add nested unit blocks
        for nested_data in data.get("unit_blocks", []):
            unit_block.add_unit_block(IRBuilder.json_to_unit_block(nested_data))
        
        # Add attributes
        for attr_data in data.get("attributes", []):
            unit_block.add_attribute(IRBuilder.json_to_attribute(attr_data))
        
        # Add statements
        for stmt_data in data.get("statements", []):
            if isinstance(stmt_data, dict):
                stmt = IRBuilder.json_to_code_element(stmt_data)
                unit_block.add_statement(stmt)
        
        return unit_block

    @staticmethod
    def json_to_code_element(data: Dict[str, Any]):
        """Generic converter for any CodeElement."""
        ir_type = data.get("ir_type")
        
        if ir_type == "UnitBlock":
            return IRBuilder.json_to_unit_block(data)
        elif ir_type == "AtomicUnit":
            return IRBuilder.json_to_atomic_unit(data)
        elif ir_type == "Variable":
            return IRBuilder.json_to_variable(data)
        elif ir_type == "Attribute":
            return IRBuilder.json_to_attribute(data)
        elif ir_type == "Comment":
            return IRBuilder.json_to_comment(data)
        elif ir_type == "Dependency":
            return IRBuilder.json_to_dependency(data)
        elif ir_type == "ConditionalStatement":
            return IRBuilder.json_to_conditional_statement(data)
        else:
            # Try as expression
            return IRBuilder.json_to_expr(data)

    @classmethod
    def from_json(cls, json_str: str) -> UnitBlock:
        """
        Build IR object from JSON string.
        
        Args:
            json_str: JSON string representation of the IR
            
        Returns:
            UnitBlock object
        """
        data = json.loads(json_str)
        return cls.json_to_unit_block(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> UnitBlock:
        """
        Build IR object from dictionary.
        
        Args:
            data: Dictionary representation of the IR
            
        Returns:
            UnitBlock object
        """
        return cls.json_to_unit_block(data)


# Example usage
if __name__ == "__main__":
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
      "variables": [],
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
    
    # Build the IR object from JSON
    ir_object = IRBuilder.from_json(json_string)
    
    # Verify by converting back to dict and printing
    print(json.dumps(ir_object.as_dict(), indent=2))