
# from dataclasses import dataclass, field
# import networkx as nx
# from abc import ABC
# from typing import Dict, List, Optional, Set, Tuple
# from collections import defaultdict
# from glitch.repr.inter import (
#     AtomicUnit, CodeElement, ConditionalStatement,
#     Variable, VariableReference, Dependency, UnitBlock,
#     FunctionCall, MethodCall, Expr, Assign, UnaryOperation, BinaryOperation
# )

# @dataclass(frozen=True)
# class Node(ABC):
#     id: int
#     element: Optional[CodeElement] = None
#     defines: Set[str] = field(default_factory=set, compare=False, hash=False)
#     uses: Set[str] = field(default_factory=set, compare=False, hash=False)

# @dataclass(frozen=True) 
# class DummyNode(Node):
#     def __init__(self, id: int):
#         super().__init__(id=id)


# @dataclass(frozen=True)
# class Edge(ABC):
#     ...

# @dataclass(frozen=True)
# class ControlEdge(Edge):
#     ...

# @dataclass(frozen=True)
# class DataEdge(Edge):
#     variable: str

# CONTROL_EDGE = ControlEdge()

# @dataclass(frozen=True)
# class Definition:
#     variable: str
#     node_id: int

# class PDG():
#     def __init__(self):
#         self.graph: nx.MultiDiGraph = nx.MultiDiGraph()
#         self.mapping: Dict[CodeElement, Node] = {}
#         self._next_node_id: int = 0

#         self.in_sets: Dict[int, Set[Definition]] = {}
#         self.out_sets: Dict[int, Set[Definition]] = {}

#     def _get_next_node_id(self) -> int:
#         node_id = self._next_node_id
#         self._next_node_id += 1
#         return node_id

#     def add_dummy_node(self) -> DummyNode:
#         dummy_node = DummyNode(self._get_next_node_id())
#         self.graph.add_node(dummy_node)
#         return dummy_node

#     def add_node(self, element: CodeElement, defines: Set[str], uses: Set[str]) -> Node:
#         if element in self.mapping:
#             return self.mapping[element]

#         new_node = Node(self._get_next_node_id(), element, defines, uses)
#         self.mapping[element] = new_node
#         self.graph.add_node(new_node)
#         return new_node
    
#     def add_edge(self, source: Node, target: Node, kind: Edge) -> None:
#         self.graph.add_edge(source, target, kind=kind)

#     def get_node_label(self, node: Node) -> str:
#         if isinstance(node, DummyNode):
#             return f"dummy_{node.id}"
        
#         element_type = type(node.element).__name__
#         escaped_code = str(node.element.code).replace("\\", "\\\\").replace('"', '\\"')
#         defs = f"\\nDefines: {node.defines}" if node.defines else ""
#         uses = f"\\nUses: {node.uses}" if node.uses else ""
#         return f"{element_type}\\n{escaped_code}{defs}{uses}"

#     def to_dot(self) -> str:
#             dot_lines = ["digraph PDG {"]
#             dot_lines.append("    rankdir=TB;")
#             dot_lines.append("    node [shape=box];")

#             for node in list(self.graph.nodes):
#                 label = self.get_node_label(node)
#                 shape = "diamond" if isinstance(node, DummyNode) else "box"
#                 dot_lines.append(f'    {node.id} [label="{label}", shape={shape}];')

#             for source, target, data in self.graph.edges(data=True):
#                 kind = data.get("kind")
#                 if isinstance(kind, ControlEdge):
#                     dot_lines.append(f'    {source.id} -> {target.id} [style=solid, color=black];')
#                 elif isinstance(kind, DataEdge):
#                     dot_lines.append(f'    {source.id} -> {target.id} [style=dashed, color=blue, label="{kind.variable}"];')

#             dot_lines.append("}")
#             return "\n".join(dot_lines)

# class PDGBuilder():
#     def __init__(self, repr_root: CodeElement):
#         self.pdg: PDG = PDG()
#         self.entry_node: DummyNode = self.pdg.add_dummy_node()
#         self.repr_root = repr_root

#     @classmethod
#     def build(cls, repr_root: CodeElement) -> PDG:
#         builder = cls(repr_root)

#         builder.visit(builder.entry_node, repr_root)
        
#         builder.compute_reaching_definitions()

#         builder.build_data_edges()
        
#         return builder.pdg

#     def _extract_uses(self, expr: Expr) -> Set[str]:
#         uses: set[str] = set()
#         if isinstance(expr, VariableReference):
#             uses.add(expr.value)
#         elif isinstance(expr, (Assign, BinaryOperation)):
#             uses.update(self._extract_uses(expr.left))
#             uses.update(self._extract_uses(expr.right))
#         elif isinstance(expr, UnaryOperation):
#             uses.update(self._extract_uses(expr.expr))
#         elif isinstance(expr, (FunctionCall, MethodCall)):
#             for arg in expr.args:
#                 uses.update(self._extract_uses(arg))
#             if isinstance(expr, MethodCall):
#                 uses.update(self._extract_uses(expr.receiver))

#         return uses

#     def visit(self, entry_node: Node, element: CodeElement) -> Node:
#         defines, uses = set(), set()

#         if isinstance(element, UnitBlock):
#             node = self.pdg.add_node(element, defines, uses)
#             self.pdg.add_edge(entry_node, node, CONTROL_EDGE)
            
#             all_elements = sorted(
#                 element.statements + element.atomic_units + element.dependencies + element.unit_blocks,
#                 key=lambda x: x.line
#             )
#             current_node = node
#             for v in element.variables:
#                 defines.add(v.name)
#                 uses.update(self._extract_uses(v.value))
#             for e in all_elements:
#                 current_node = self.visit(current_node, e)
#             return current_node

#         elif isinstance(element, ConditionalStatement):
#             if element.type == ConditionalStatement.ConditionType.IF:

#                 uses.update(self._extract_uses(element.condition))
#                 condition_node = self.pdg.add_node(element, defines, uses)
#                 self.pdg.add_edge(entry_node, condition_node, CONTROL_EDGE)

#                 if_merge_node = self.pdg.add_dummy_node()

#                 then_node: Node = self.pdg.add_dummy_node()
#                 self.pdg.add_edge(condition_node, then_node, CONTROL_EDGE)
#                 then_exit_node = self.visit_statement_list(then_node, element.statements)
#                 self.pdg.add_edge(then_exit_node, if_merge_node, CONTROL_EDGE)

#                 if element.else_statement:
#                     elseNode: Node = self.pdg.add_dummy_node()
#                     self.pdg.add_edge(condition_node, elseNode, CONTROL_EDGE)
#                     else_exit_node = self.visit_statement_list(elseNode, element.else_statement.statements)
#                     self.pdg.add_edge(else_exit_node, if_merge_node, CONTROL_EDGE)
#                 else:
#                     self.pdg.add_edge(condition_node, if_merge_node, CONTROL_EDGE)
                
#                 return if_merge_node
#             elif element.type == ConditionalStatement.ConditionType.SWITCH:
#                 pass

#         elif isinstance(element, Variable):
#             defines.add(element.name)
#             uses.update(self._extract_uses(element.value))
#             node = self.pdg.add_node(element, defines, uses)
#             self.pdg.add_edge(entry_node, node, CONTROL_EDGE)
#             return node

#         elif isinstance(element, AtomicUnit):
#             for attr in element.attributes:
#                 uses.update(self._extract_uses(attr.value))
#             uses.update(self._extract_uses(element.name))
#             node = self.pdg.add_node(element, defines, uses)
#             self.pdg.add_edge(entry_node, node, CONTROL_EDGE)
#             return node
        
#         else:
#             print(element)
#             raise NotImplementedError

#     def visit_statement_list(self, start_node: Node, stmt_list: list[CodeElement]) -> Node:
#         current_node = start_node
#         for stmt in stmt_list:
#             current_node = self.visit(current_node, stmt)
#         return current_node

#     def build_data_edges(self):
#         node_map = {node.id: node for node in self.pdg.graph.nodes()}

#         for node_id, reaching_defs in self.pdg.in_sets.items():
#             consumer_node = node_map.get(node_id)
#             if not consumer_node: continue

#             for used_var in consumer_node.uses:
#                 for definition in reaching_defs:
#                     if definition.variable == used_var:
#                         producer_node = node_map.get(definition.node_id)
#                         if producer_node:
#                             self.pdg.add_edge(producer_node, consumer_node, DataEdge(variable=used_var))


#     def compute_reaching_definitions(self) -> None:
#         nodes = list(self.pdg.graph.nodes)
#         in_sets: Dict[int, Set[Definition]] = {node.id: set() for node in nodes}
#         out_sets: Dict[int, Set[Definition]] = {node.id: set() for node in nodes}
        
#         # Compute GEN and KILL sets for each node
#         gen_sets: Dict[int, Set[Definition]] = defaultdict(set)
#         kill_sets: Dict[int, Set[Definition]] = defaultdict(set)

#         for node in nodes:
#             for var in node.defines:
#                 gen_sets[node.id].add(Definition(var, node.id))

#         for node in nodes:
#             for var in node.defines:
#                 kill_sets[node.id].add(Definition(var, node.id))

#         # Iterative fixed-point 
#         changed = True
#         while changed:
#             changed = False
#             for node in nodes:
#                 # IN[n] = U (OUT[p]) for all predecessors p of n
#                 preds = self.pdg.graph.predecessors(node)
#                 pred_out_union = set().union(*(out_sets.get(p.id, set()) for p in preds))
                
#                 if pred_out_union != in_sets[node.id]:
#                     in_sets[node.id] = pred_out_union
#                     changed = True

#                 # OUT[n] = GEN[n] U (IN[n] - KILL[n])
#                 old_out = out_sets[node.id]
#                 new_out = gen_sets[node.id].union(in_sets[node.id] - kill_sets[node.id])
                
#                 if new_out != old_out:
#                     out_sets[node.id] = new_out
#                     changed = True

#         self.pdg.in_sets = in_sets
#         self.pdg.out_sets = out_sets


# # def hasDUpath(pdg: PDG, n: CodeElement, u: CodeElement):
# #     n_node = pdg.mapping.get(n)
# #     u_node = pdg.mapping.get(u)

# #     if not n_node or not u_node:
# #         return False

# #     common_vars = n_node.defines.intersection(u_node.uses)

# #     if not common_vars:
# #         return False

# #     reaching_defs_at_u = pdg.in_sets.get(u_node.id, set())
# #     for var in common_vars:
# #         definition_from_n = Definition(variable=var, node_id=n_node.id)
# #         if definition_from_n in reaching_defs_at_u:
# #             return True

# #     return False

# # def hasDUpath(pdg: PDG, n: CodeElement, l: Value):
# #     pass

# def hasDUpath(pdg: PDG, n: CodeElement, e: Edge, t: CodeElement):
#     pass
