from typing import Dict, Optional, List
from dataclasses import dataclass, field
from abc import ABC

from glitch.repr.inter import (
    AtomicUnit, CodeElement, ConditionalStatement,
    Variable, VariableReference, UnitBlock,
    FunctionCall, MethodCall, Expr, UnaryOperation, BinaryOperation,
    Dependency, Null, Value, String, Integer, Float, Boolean, Hash, Complex, Array,
    Block, KeyValue, Comment, Attribute
)
from glitch.parsers.chef import AddArgs

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
    def __init__(self, root: UnitBlock) -> None:
        self.root: UnitBlock = root
        self.scope_manager: ScopeManager = ScopeManager()

    def build(self) -> CFG:
        cfg = CFG()
        entry = cfg.add_dummy_node()
        exit = cfg.add_dummy_node()
        prev = entry
        prev = self._visit(cfg, prev, self.root)
        cfg.add_edge(prev, exit)
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
            #TODO what to do here? see tests/design/puppet/files/duplicate_block.pp
            print("Dependency encountered in CFG construction, skipping.")
            return prev
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
        return self._visit_expression(cfg, prev, attr.value)

    def _visit_atomicunit(self, cfg: CFG, prev: Node, atomic_unit: AtomicUnit) -> Node:
        current = prev

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

    def _visit_unitblock(self, cfg: CFG, prev: Node, block: UnitBlock) -> Node:
        current = prev

        # self.scope_manager.enter_scope(block)

        all_elements = sorted(
                block.statements + block.atomic_units +
                block.dependencies + block.unit_blocks + block.variables
                + block.comments + block.attributes,
                key=lambda x: x.line
            )

        for elem in all_elements:
            current = self._visit(cfg, current, elem)

        # self.scope_manager.exit_scope()

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
            node.qualified_name = f"{resolved_var.name}@{resolved_var.scope_id}"
        else:
            node.qualified_name = f"{var_ref.value}@<undeclared>"

        cfg.add_edge(prev, node)
        return node

    def _visit_expression(self, cfg: CFG, prev: Node, expr: Expr) -> Node:
        current = prev
        if isinstance(expr, Value):
            current = _visit_value(self, cfg, current, expr)

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
