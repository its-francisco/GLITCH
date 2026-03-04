from typing import Dict, Optional, List, Set
from dataclasses import dataclass, field
from abc import ABC
import os

from glitch.repr.inter import (
    AtomicUnit, CodeElement, ConditionalStatement,
    Variable, VariableReference, UnitBlock, UnitBlockType,
    FunctionCall, MethodCall, Expr, UnaryOperation, BinaryOperation,
    Dependency, Null, Value, String, Integer, Float, Boolean, Hash, Complex, Array,
    Block, KeyValue, Comment, Attribute
)
from glitch.parsers.chef import AddArgs
from glitch.parsers.parser import Parser

from glitch.dataflow.scope_manager import ScopeManager

"""
The CFG is composed of:
  - VarNode: variable definitions
  - VarRefNode: variable uses
  - DummyNode: control flow placeholders (entry/exit, branches)
"""

@dataclass
class Node(ABC):
    id: int
    preds: List["Node"] = field(default_factory=list)
    succs: List["Node"] = field(default_factory=list)

class DefUseNode(Node, ABC):
    qualified_name: str = field(default_factory=str) # scope-qualified name

@dataclass
class VarNode(DefUseNode):
    var: Variable = field(default_factory=Variable)

    def __str__(self):
        return f"VarNode(Var: {self.var}, QualifiedName: {self.qualified_name})"

@dataclass
class VarRefNode(DefUseNode):
    var_ref: VariableReference = field(default_factory=VariableReference)

    def __str__(self):
        return f"VarRefNode(VarRef: {self.var_ref}, QualifiedName: {self.qualified_name})"

@dataclass
class DummyNode(Node):
    def __str__(self):
        return f"DummyNode(ID: {self.id})"

@dataclass
class CFG:
    nodes: Dict[int, Node] = field(default_factory=dict)
    entry: Optional[Node] = None
    exit: Optional[Node] = None
    next_node_id: int = 0

    def add_dummy_node(self) -> Node:
        node = DummyNode(id=self.next_node_id)
        self.next_node_id += 1
        self.nodes[node.id] = node
        return node

    def add_def_use_node(self, element: (Variable | VariableReference)) -> DefUseNode:
        assert isinstance(element, (Variable, VariableReference))

        if isinstance(element, Variable):
            node = VarNode(id=self.next_node_id, var=element)
        elif isinstance(element, VariableReference):
            node = VarRefNode(id=self.next_node_id, var_ref=element)

        self.next_node_id += 1
        self.nodes[node.id] = node
        return node

    def add_edge(self, src: Node, dst: Node):
        src.succs.append(dst)
        dst.preds.append(src)


    def __str__(self):
        return f"CFG(Entry: {self.entry}, Exit: {self.exit}, Nodes: {list(self.nodes.values())})"

class CFGBuilder:

    def __init__(
        self,
        root: UnitBlock,
        parser: Optional[Parser] = None,
        dependency_attribute_names: Optional[Set[str]] = None,
    ) -> None:
        self.root: UnitBlock = root
        self.scope_manager: ScopeManager = ScopeManager()
        self.parser: Optional[Parser] = parser
        self.visited_files: Set[str] = set()
        parser_names: Set[str] = parser.get_file_reference_keywords() if parser is not None else set()
        configured_names: Set[str] = parser_names | set()
        if dependency_attribute_names is not None:
            configured_names |= dependency_attribute_names
        self.dependency_attribute_names: Set[str] = {
            name.lower() for name in configured_names
        }
        if root.path:
            self.visited_files.add(os.path.abspath(root.path))

    def build(self) -> CFG:
        cfg = CFG()
        entry = cfg.add_dummy_node()
        exit_node = cfg.add_dummy_node()
        prev = entry
        prev = self._visit(cfg, prev, self.root)
        cfg.add_edge(prev, exit_node)
        return cfg

    def _visit(self, cfg: CFG, prev: Node, block: CodeElement) -> Node:
        if isinstance(block, Expr):
            return self._visit_expression(cfg, prev, block)
        elif isinstance(block, Block):
            return self._visit_block(cfg, prev, block)
        elif isinstance(block, KeyValue):
            return self._visit_keyvalue(cfg, prev, block)
        elif isinstance(block, Comment):
            return prev
        elif isinstance(block, Dependency):
            return self._resolve_dependency(cfg, prev, block)
        # elif isinstance(block, Variable):
        #     return self._visit_variable(cfg, prev, block)
        # elif isinstance(block, VariableReference):
        #     return self._visit_varref(cfg, prev, block)
        # elif isinstance(block, Null):
        #     return prev
        else:
            raise NotImplementedError(f"Unhandled CodeElement type: {type(block)}")

    def _visit_block(self, cfg: CFG, prev: Node, block: Block) -> Node:
        if isinstance(block, ConditionalStatement):
            return self._visit_conditional(cfg, prev, block)
        elif isinstance(block, UnitBlock):
            return self._visit_unitblock(cfg, prev, block)
        elif isinstance(block, AtomicUnit):
            return self._visit_atomicunit(cfg, prev, block)
        else:
            # TODO Can a block exist by itself?
            raise NotImplementedError(f"Unhandled block type: {type(block)}")

    def _visit_keyvalue(self, cfg: CFG, prev: Node, kv: KeyValue) -> Node:
        if isinstance(kv, Variable):
            return self._visit_variable(cfg, prev, kv)
        elif isinstance(kv, Attribute):
            return self._visit_attribute(cfg, prev, kv)
        else:
            # TODO Can a kv exist by itself?
            raise NotImplementedError(f"Unhandled KeyValue type: {type(kv)}")

    def _visit_attribute(self, cfg: CFG, prev: Node, attr: Attribute) -> Node:
        current = prev

        if attr.name.lower() in self.dependency_attribute_names:
            current = self._resolve_dependency_attribute(cfg, current, attr)

        return self._visit_expression(cfg, current, attr.value)

    def _visit_atomicunit(self, cfg: CFG, prev: Node, atomic_unit: AtomicUnit) -> Node:
        current = prev

        if atomic_unit.type.lower() in self.dependency_attribute_names:
            for attr in atomic_unit.attributes:
                current = self._resolve_dependency_attribute(cfg, current, attr)

        all_elements = sorted(
            atomic_unit.statements + atomic_unit.attributes + [atomic_unit.name],
            key=lambda x: x.line
        )

        for elem in all_elements:
            current = self._visit(cfg, current, elem)

        return current

    def _visit_statement_list(self, cfg: CFG, prev: Node, statements: List[CodeElement]) -> Node:
        current = prev

        for stmt in statements:
            current = self._visit(cfg, current, stmt)

        return current

    def _resolve_dependency(self, cfg: CFG, prev: Node, dep: Dependency) -> Node:
        current = prev
        if self.parser is None:
            return prev

        for dep_name in dep.names:
            current = self._resolve_and_visit_path(cfg, current, dep_name)
        
        return current

    def _resolve_dependency_attribute(self, cfg: CFG, prev: Node, attr: Attribute) -> Node:
        current = prev

        for dep_name in self._extract_dependency_paths(attr.value, attr.name):
            current = self._resolve_and_visit_path(cfg, current, dep_name)

        return current

    def _extract_dependency_paths(self, expr: Expr, attr_name: str = "") -> List[str]:
        if isinstance(expr, String):
            return [expr.value]

        if isinstance(expr, Array):
            values: List[str] = []
            for item in expr.value:
                if isinstance(item, String):
                    values.append(item.value)
            return values

        # TODO this section needs an abstraction
        if isinstance(expr, Hash):
            values: List[str] = []
            file_keys = {"file", "name", "dir"}
            if attr_name.lower() in {"include_tasks", "import_tasks", "import_playbook"}:
                file_keys = {"file"}
            for key, val in expr.value.items():
                key_value = key.value.lower() if isinstance(key, String) else ""
                if key_value in file_keys and isinstance(val, String):
                    values.append(val.value)
            return values

        return []

    def _resolve_and_visit_path(self, cfg: CFG, prev: Node, dep_name: str) -> Node:
        if self.parser is None or not self.root.path:
            return prev

        dep_name = dep_name.strip()
        if not dep_name:
            return prev

        base_dir = os.path.dirname(os.path.abspath(self.root.path))
        dep_path = dep_name if os.path.isabs(dep_name) else os.path.join(base_dir, dep_name)
        abs_dep_path = os.path.abspath(dep_path)

        if abs_dep_path in self.visited_files or not os.path.exists(abs_dep_path):
            return prev

        self.visited_files.add(abs_dep_path)

        try:
            dep_unit = self.parser.parse_file(abs_dep_path, UnitBlockType.unknown)
            if dep_unit is None:
                return prev
            if dep_unit.type == UnitBlockType.vars:
                return self._visit_unitblock_inline(cfg, prev, dep_unit)
            return self._visit(cfg, prev, dep_unit)
        except Exception:
            return prev

    def _visit_unitblock_inline(self, cfg: CFG, prev: Node, block: UnitBlock) -> Node:
        current = prev

        all_elements = sorted(
            block.statements
            + block.atomic_units
            + block.dependencies
            + block.unit_blocks
            + block.variables
            + block.comments
            + block.attributes,
            key=lambda x: x.line,
        )

        for elem in all_elements:
            current = self._visit(cfg, current, elem)

        return current

    def _visit_unitblock(self, cfg: CFG, prev: Node, block: UnitBlock) -> Node:
        current = prev

        self.scope_manager.enter_scope(block)

        all_elements = sorted(
                block.statements + block.atomic_units +
                block.dependencies + block.unit_blocks + block.variables
                + block.comments + block.attributes,
                key=lambda x: x.line
            )

        for elem in all_elements:
            current = self._visit(cfg, current, elem)

        self.scope_manager.exit_scope()

        return current

    def _visit_conditional(self, cfg: CFG, prev: Node, cond: ConditionalStatement) -> Node:
        current = prev
        #if cond.type == ConditionalStatement.ConditionType.IF:
        current = self._visit_expression(cfg, current, cond.condition)
        condition_node = cfg.add_dummy_node()

        cfg.add_edge(current, condition_node)

        if_merge_node = cfg.add_dummy_node()

        then_node: Node = cfg.add_dummy_node()
        cfg.add_edge(condition_node, then_node)
        then_exit_node = self._visit_statement_list(cfg, then_node, cond.statements)
        cfg.add_edge(then_exit_node, if_merge_node)

        if cond.else_statement:
            elseNode: Node = cfg.add_dummy_node()
            cfg.add_edge(condition_node, elseNode)
            else_exit_node = self._visit(cfg, elseNode, cond.else_statement)
            cfg.add_edge(else_exit_node, if_merge_node)
        else:
            cfg.add_edge(condition_node, if_merge_node)

        return if_merge_node
        # elif cond.type == ConditionalStatement.ConditionType.SWITCH:
        #     pass
        #     #raise NotImplementedError

        # return current

    def _visit_variable(self, cfg: CFG, prev: Node, var: Variable) -> Node:
        current = self._visit_expression(cfg, prev, var.value)
        self.scope_manager.declare_variable(var)

        node = cfg.add_def_use_node(var)
        node.qualified_name = f"{var.name}@{self.scope_manager.current_scope_id}"

        cfg.add_edge(current, node)
        return node

    def _visit_varref(self, cfg: CFG, prev: Node, var_ref: VariableReference) -> Node:
        node = cfg.add_def_use_node(var_ref)
        resolved_var = self.scope_manager.resolve_variable(var_ref)

        if resolved_var:
            node.qualified_name = f"{resolved_var.name}@{resolved_var.scope_id}" # type: ignore
        else:
            node.qualified_name = f"{var_ref.value}@<undeclared>"

        cfg.add_edge(prev, node)
        return node
    
    def _visit_value(self, cfg: CFG, prev: Node, value: Value) -> Node:
        current = prev
        if isinstance(value, (String, Integer, Complex, Float, Boolean, Null)):
            pass  # literals do not create CFG nodes

        elif isinstance(value, VariableReference):
            return self._visit_varref(cfg, current, value)

        elif isinstance(value, Hash):
            for key, val in value.value.items():
                current = self._visit_expression(cfg, current, key)
                current = self._visit_expression(cfg, current, val)

        elif isinstance(value, Array):
            for item in value.value:
                current = self._visit_expression(cfg, current, item)

        elif isinstance(value, AddArgs):
            for arg in value.value:
                current = self._visit_expression(cfg, current, arg)

        else:
            raise NotImplementedError(f"Unhandled expression type: {type(value)}")

        return current

    def _visit_expression(self, cfg: CFG, prev: Node, expr: Expr) -> Node:
        current = prev
        if isinstance(expr, Value):
            current = self._visit_value(cfg, current, expr)

        elif isinstance(expr, BinaryOperation):
            current = self._visit_expression(cfg, current, expr.left)
            current = self._visit_expression(cfg, current, expr.right)

        elif isinstance(expr, UnaryOperation):
            current = self._visit_expression(cfg, current, expr.expr)

        elif isinstance(expr, (FunctionCall, MethodCall)):
            for arg in expr.args:
                current = self._visit_expression(cfg, current, arg)
            if isinstance(expr, MethodCall):
                current = self._visit_expression(cfg, current, expr.receiver)
        elif isinstance(expr, ConditionalStatement):
            current = self._visit_conditional(cfg, current, expr)
        else:
            raise NotImplementedError(f"Unhandled expression type: {type(expr)}")

        return current

    
