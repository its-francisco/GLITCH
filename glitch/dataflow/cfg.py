from typing import Dict, Optional, List
from dataclasses import dataclass, field
from abc import ABC

from glitch.repr.inter import (
    AtomicUnit, CodeElement, ConditionalStatement,
    Variable, VariableReference, UnitBlock,
    FunctionCall, MethodCall, Expr, UnaryOperation, BinaryOperation,
    Dependency, Null
)

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


@dataclass
class VarNode(Node):
    var: Variable = field(default_factory=Variable)

    def __str__(self):
        return f"VarNode(Var: {self.var})"


@dataclass
class VarRefNode(Node):
    varRef: VariableReference = field(default_factory=VariableReference)

    def __str__(self):
        return f"VarRefNode(VarRef: {self.varRef})"


@dataclass
class DummyNode(Node):
    pass

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

    def add_node(self, element: CodeElement) -> Node:
        if isinstance(element, Variable):
            node = VarNode(id=self.next_node_id, var=element)
        elif isinstance(element, VariableReference):
            node = VarRefNode(id=self.next_node_id, varRef=element)
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

    def build(self) -> CFG:
        cfg = CFG()
        entry = cfg.add_dummy_node()
        exit = cfg.add_dummy_node()
        prev = entry
        prev = self._visit(cfg, prev, self.root)
        cfg.add_edge(prev, exit)
        return cfg

    def _visit(self, cfg: CFG, prev: Node, block: CodeElement) -> Node:
        if isinstance(block, UnitBlock):
            return self._visit_unitblock(cfg, prev, block)
        elif isinstance(block, ConditionalStatement):
            return self._visit_conditional(cfg, prev, block)
        elif isinstance(block, Variable):
            return self._visit_variable(cfg, prev, block)
        elif isinstance(block, VariableReference):
            return self._visit_varref(cfg, prev, block)
        elif isinstance(block, AtomicUnit):
            return self._visit_atomicunit(cfg, prev, block)
        elif isinstance(block, Dependency):
            #TODO what to do here? see tests/design/puppet/files/duplicate_block.pp
            print("Dependency encountered in CFG construction, skipping.")
            return prev
        elif isinstance(block, Null):
            return prev
        else:
            raise NotImplementedError(f"Unhandled block type: {type(block)}")


    def _visit_atomicunit(self, cfg: CFG, prev: Node, atomic_unit: AtomicUnit) -> Node:
        current = prev

        for attr in atomic_unit.attributes:
            current = self._visit_expression(cfg, current, attr.value)

        return current

    def _visit_statement_list(self, cfg: CFG, prev: Node, statements: List[CodeElement]) -> Node:
        current = prev

        for stmt in statements:
            current = self._visit(cfg, current, stmt)

        return current

    def _visit_unitblock(self, cfg: CFG, prev: Node, block: UnitBlock) -> Node:
        current = prev

        all_elements = sorted(
                block.statements + block.atomic_units +
                block.dependencies + block.unit_blocks + block.variables,
                key=lambda x: x.line
            )

        for elem in all_elements:
            current = self._visit(cfg, current, elem)

        return current

    def _visit_conditional(self, cfg: CFG, prev: Node, cond: ConditionalStatement) -> Node:
        current = prev

        if cond.type == ConditionalStatement.ConditionType.IF:
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
                else_exit_node = self._visit_statement_list(cfg, elseNode, cond.else_statement.statements)
                cfg.add_edge(else_exit_node, if_merge_node)
            else:
                cfg.add_edge(condition_node, if_merge_node)

            return if_merge_node
        elif cond.type == ConditionalStatement.ConditionType.SWITCH:
            pass

        return current

    def _visit_variable(self, cfg: CFG, prev: Node, var: Variable) -> Node:
        node = cfg.add_node(var)
        cfg.add_edge(prev, node)
        return node

    def _visit_varref(self, cfg: CFG, prev: Node, varref: VariableReference) -> Node:
        node = cfg.add_node(varref)
        cfg.add_edge(prev, node)
        return node

    def _visit_expression(self, cfg: CFG, prev: Node, expr: Expr) -> Node:
        current = prev

        if isinstance(expr, VariableReference):
            return self._visit_varref(cfg, current, expr)

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

        return current
