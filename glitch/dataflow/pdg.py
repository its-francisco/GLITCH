# from dataclasses import dataclass
# import networkx as nx
# from abc import ABC
# from typing import Dict, List, Optional, Set
# from collections import defaultdict
# from glitch.repr.inter import (
#     AtomicUnit, CodeElement, ConditionalStatement,
#     Variable, VariableReference, Dependency, UnitBlock,
#     FunctionCall, MethodCall, Expr, Assign,
# )


# class Node(ABC):
#     def __init__(self,
#                  id: int,
#                  element: Optional[CodeElement],
#                  defines:(Set[str] | None)=None,
#                  uses: (Set[str] | None)=None
#                  ):
#         self.id = id
#         self.element = element
#         self.defines = defines or set()
#         self.uses = uses or set()

# class DummyNode(Node):
#     def __init__(self, id: int):
#         super().__init__(id, None)

# class Edge(ABC):
#     def __init__(self, id: int):
#         self.id = id

# class ControlEdge(Edge):
#     def __init__(self, id: int):
#         super().__init__(id)


# class DataEdge(Edge):
#     ...

# class DefEdge(DataEdge):
#     ...

# class UseEdge(DataEdge):
#     ...

# @dataclass
# class PDG():
#     def __init__(self):
#         self.graph: nx.MultiDiGraph = nx.MultiDiGraph()
#         self.mapping: Dict[CodeElement, Node] = {}

#     def add_dummy_node(self) -> DummyNode:
#         dummyNode: DummyNode = DummyNode(self.graph.number_of_nodes())
#         self.graph.add_node(dummyNode) #type: ignore
#         return dummyNode

#     def add_node(self, node: CodeElement) -> Node:
#         if node in self.mapping:
#             return self.mapping[node]

#         self.mapping[node] = Node(self.graph.number_of_nodes(), node)
#         self.graph.add_node(self.mapping[node]) #type: ignore
#         return self.mapping[node]

#     def add_control_edge(self, source: Node, target: Node) -> ControlEdge:
#         edge: ControlEdge = ControlEdge(self.graph.number_of_edges()) #type: ignore
#         self.graph.add_edge(source, target, key="control", edge_obj=edge) #type: ignore
#         return edge

#     def add_data_use_edge(self, source: Node, target: Node) -> DataEdge:
#         edge: DataEdge = DataEdge(self.graph.number_of_edges()) #type: ignore
#         self.graph.add_edge(source, target, key="use", edge_obj=edge) #type: ignore
#         return edge

#     def add_data_def_edge(self, source: Node, target: Node) -> DataEdge:
#         edge: DataEdge = DataEdge(self.graph.number_of_edges()) #type: ignore
#         self.graph.add_edge(source, target, key="def", edge_obj=edge) #type: ignore
#         return edge


#     def get_node_label(self, node: Node) -> str:
#         """Get a display label for a node"""
#         if isinstance(node, DummyNode):
#             return f"dummy_{node.id}"
#         elif node.element is None:
#             return f"node_{node.id}"
#         else:
#             # Customize this based on your CodeElement types
#             element_type = type(node.element).__name__

#             # Use node.element.code property for the code string, escape for DOT
#             escaped_code = str(node.element.code).replace("\\", "\\\\").replace('"', '\\"')
#             return f"{element_type}\\n{escaped_code}"

#     def to_dot(self) -> str:
#             """Export to DOT format for Graphviz visualization"""
#             dot_lines = ["digraph PDG {"]
#             dot_lines.append("    rankdir=TB;")
#             dot_lines.append("    node [shape=box];")

#             # Add nodes
#             for node in list(self.graph.nodes):
#                 label = self.get_node_label(node)
#                 shape = "diamond" if isinstance(node, DummyNode) else "box"
#                 dot_lines.append(f'    {node.id} [label="{label}", shape={shape}];')

#             # Add edges
#             for source, target, edge_data in self.graph.edges(data=True):
#                 edge_type = edge_data.get('edge_type', 'control')
#                 style = "solid" if edge_type == "control" else "dashed"
#                 color = "black" if edge_type == "control" else "blue"
#                 dot_lines.append(f'    {source.id} -> {target.id} [style={style}, color={color}];')

#             dot_lines.append("}")
#             return "\n".join(dot_lines)


# class PDGBuilder():
#     def __init__(self, repr_root: CodeElement):
#         self.pdg: PDG = PDG()
#         self.entry_node: DummyNode = self.pdg.add_dummy_node()
#         self.repr_root = repr_root

#     @classmethod
#     def build(cls, repr_root: CodeElement) -> PDG:
#         builder: PDGBuilder = cls(repr_root)
#         builder.visit(builder.entry_node, repr_root)
#         # builder.build_data_edges()
#         return builder.pdg

#     def visit(self, entry_node: Node, element: CodeElement) -> Node:
#         """Returns last (exit) node"""
#         if isinstance(element, UnitBlock):
#             node = self.pdg.add_node(element)
#             self.pdg.add_control_edge(entry_node, node)
#             all_elements: List[CodeElement] = sorted(
#                 element.statements + element.atomic_units + element.dependencies + element.unit_blocks,
#                 key=lambda x: x.line
#             )

#             current_node = node
#             for e in all_elements:
#                 current_node = self.visit(current_node, e)

#             return current_node

#         elif isinstance(element, ConditionalStatement):
#             if element.type == ConditionalStatement.ConditionType.IF:
#                 condition_node: Node = self.pdg.add_node(element.condition)
#                 self.pdg.add_control_edge(entry_node, condition_node)

#                 if_merge_node = self.pdg.add_dummy_node()

#                 # visit statements inside then branch
#                 then_node: Node = self.pdg.add_dummy_node()
#                 self.pdg.add_control_edge(condition_node, then_node)
#                 then_end_node = self.visitStatementList(then_node, element.statements)
#                 self.pdg.add_control_edge(then_end_node, if_merge_node)

#                 # visit statements inside else branch
#                 if element.else_statement is not None:
#                     elseNode: Node = self.pdg.add_dummy_node()
#                     self.pdg.add_control_edge(condition_node, elseNode)
#                     elseEnd: Node = self.visitStatementList(elseNode, element.else_statement.statements)
#                     self.pdg.add_control_edge(elseEnd, if_merge_node)

#                 else:
#                     # no else branch, connect condition directly to merge node
#                     self.pdg.add_control_edge(condition_node, if_merge_node)

#                 return if_merge_node

#             elif element.type == ConditionalStatement.ConditionType.SWITCH:
#                 e: Optional[ConditionalStatement] = element

#                 switch_merge_node: Node = self.pdg.add_dummy_node()

#                 while e is not None:
#                     #FIXME: default case is node with null code element, store the code
#                     condition_node: Node = self.pdg.add_node(e.condition)
#                     self.pdg.add_control_edge(entry_node, condition_node)

#                     current_case_end_node: Node = self.visitStatementList(condition_node, e.statements)
#                     self.pdg.add_control_edge(current_case_end_node, switch_merge_node)

#                     e = e.else_statement

#                 return switch_merge_node

#         elif isinstance(element, Variable):
#             node = self.pdg.add_node(element)
#             self.pdg.add_data_def_edge(entry_node, node)
#             return node
#         elif isinstance(element, VariableReference):
#             node = self.pdg.add_node(element)
#             self.pdg.add_data_use_edge(entry_node, node)
#             return node

#         elif isinstance(element, Dependency):
#             pass

#         elif isinstance(element, Expr):
#             pass

#         elif isinstance(element, AtomicUnit):
#             node = self.pdg.add_node(element)
#             self.pdg.add_control_edge(entry_node, node)
#             return self.visitStatementList(node, element.statements)


#         elif isinstance(element, (FunctionCall, MethodCall)):
#             current_node = entry_node
#             if isinstance(element, MethodCall):
#                 current_node = self.visit(current_node, element.receiver)
#             for arg in element.args:
#                 current_node = self.visit(current_node, arg)
#             return current_node

#         else:
#             raise NotImplementedError(f"In pdg.py: Unhandled CodeElement type: {type(element).__name__}")

#         return entry_node

#     def visitStatementList(self, startNode: Node, stmtList: list[CodeElement]) -> Node:
#         """Returns last created Node"""
#         currentNode: Node = startNode
#         for stmt in stmtList:
#             currentNode = self.visit(currentNode, stmt)
#         return currentNode


# def reaching_definitions(cfg: PDG):
#     in_sets: Dict[int,Set[str]] = defaultdict(set)
#     out_sets: Dict[int,Set[str]] = defaultdict(set)
#     gen_sets: Dict[int,Set[str]] = defaultdict(set)
#     kill_sets: Dict[int,Set[str]] = defaultdict(set)

#     # Step 1: Compute gen and kill sets
#     def_map = defaultdict(list)  # var -> list of nodes defining it

#     for node in cfg.graph.nodes.values():
#         node: Node

#         gen: Set[Node] = set()
#         for var in node.defines:
#             gen.add(Definition(var, node.id))
#             def_map[var].append(node.id)
#         gen_sets[node.id] = gen

#     for node in cfg.nodes.values():
#         kill = set()
#         for var in node.defines:
#             for other_node_id in def_map[var]:
#                 if other_node_id != node.id:
#                     kill.add(Definition(var, other_node_id))
#         kill_sets[node.id] = kill

#     # Step 2: Initialize out[n] = gen[n]
#     for node in cfg.nodes.values():
#         out_sets[node.id] = gen_sets[node.id]

#     # Step 3: Fixed-point iteration
#     changed = True
#     while changed:
#         changed = False
#         for node in cfg.nodes.values():
#             pred_out_union = set()
#             for pred in node.predecessors:
#                 pred_out_union |= out_sets[pred.id]

#             new_in = pred_out_union
#             new_out = gen_sets[node.id] | (new_in - kill_sets[node.id])

#             if new_in != in_sets[node.id] or new_out != out_sets[node.id]:
#                 changed = True
#                 in_sets[node.id] = new_in
#                 out_sets[node.id] = new_out

#     return in_sets, out_sets
