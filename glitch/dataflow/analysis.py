from typing import Dict, List
from functools import reduce
from dataclasses import dataclass

from glitch.repr.inter import Expr, VariableReference, String, Integer, Float, Boolean, Null
from glitch.dataflow.cfg import CFG, Node, VarNode, VarRefNode
from glitch.dataflow.literal_value import AbstractValue, Unknown, Literal, NonLiteral, meet

"""
Forward data flow analysis to detect variables bound to hardcoded literal values in the IR.

Lattice (per variable):

    T (Unknown)       → initial state (no information yet)
    Literal(v)        → variable is exactly literal v
    Conflicting(S)    → variable is literal, but with multiple distinct
                        literal values depending on path
    Mixed(S)          → variable is literal on some paths (values S), but
                        non-literal on others
    NonLiteral        → variable is never a literal (derived from expressions
                        or external input only)

Ordering: T ≥ Literal(v), Conflicting(S), Mixed(S) ≥ NonLiteral

Meet:
  - Literal(v) ⊓ Literal(v) = Literal(v)
  - Literal(v1) ⊓ Literal(v2≠v1) = Conflicting({v1,v2})
  - Conflicting(S1) ⊓ Conflicting(S2) = Conflicting(S1 U S2)
  - Literal(v) ⊓ Conflicting(S) = Conflicting(S U {v})
  - Literal(v) ⊓ NonLiteral = Mixed({v})
  - Conflicting(S) ⊓ NonLiteral = Mixed(S)
  - Mixed(S1) ⊓ Mixed(S2) = Mixed(S1 U S2)
  - Mixed(S) ⊓ Literal(v) = Mixed(S U {v})
  - Mixed(S) ⊓ Conflicting(T) = Mixed(S U T)
  - Any ⊓ T = Any

"""
@dataclass
class LiteralAnalysisResult:
    cfg: CFG
    in_states: Dict[int, Dict[str, AbstractValue]]
    out_states: Dict[int, Dict[str, AbstractValue]]

    def __str__(self) -> str:
        lines: List[str] = []
        for node_id, node in self.cfg.nodes.items():
            lines.append(f"Node {node_id}: {node}")
            lines.append(f"  IN:  {self.in_states[node_id]}")
            lines.append(f"  OUT: {self.out_states[node_id]}")
        return "\n".join(lines)

class LiteralAnalysis:

    @classmethod
    def analyze(cls, cfg: CFG) -> LiteralAnalysisResult:
        # NodeID -> var_name -> AbstractValue
        in_states: Dict[int, Dict[str, AbstractValue]] = {}
        out_states: Dict[int, Dict[str, AbstractValue]] = {}

        # Initialize all states
        for node_id in cfg.nodes:
            in_states[node_id] = {}
            out_states[node_id] = {}

        # Worklist algorithm
        worklist = list(cfg.nodes.values())
        """
        possible efficiency improvement:
        in_worklist = set()    # track membership
        """
        while worklist:
            node = worklist.pop(0)

            # Compute IN[node] = merge of OUT[pred] for all predecessors
            old_in = in_states[node.id].copy()
            new_in = cls._merge_states([out_states[pred.id] for pred in node.preds])
            in_states[node.id] = new_in

            # Compute OUT[node] = transfer(IN[node])
            old_out = out_states[node.id].copy()
            new_out = cls._transfer(node, new_in)
            out_states[node.id] = new_out

            # If OUT changed, add successors to worklist
            if new_out != old_out or new_in != old_in:
                for succ in node.succs:
                    if succ not in worklist:
                        worklist.append(succ)

        return LiteralAnalysisResult(cfg, in_states, out_states)

    @classmethod
    def _merge_states(cls, states: list[Dict[str, AbstractValue]]) -> Dict[str, AbstractValue]:
        if not states:
            return {}

        result: Dict[str, AbstractValue] = {}
        all_vars = {var for state in states for var in state.keys()}

        for var in all_vars:
            vals = [state.get(var, Unknown()) for state in states]
            result[var] = reduce(meet, vals)

        return result

    @classmethod
    def _transfer(cls, node: Node, in_state: Dict[str, AbstractValue]) -> Dict[str, AbstractValue]:
        """Transfer function per node type."""
        out_state = in_state.copy()

        if isinstance(node, VarNode):
            #TODO: have to add support to Binary ops and more
            val = cls._evaluate_expression(node, node.var.value, in_state)
            var_name = node.qualified_name
            out_state[var_name] = val

        elif isinstance(node, VarRefNode):
            var_name = node.qualified_name
            val = in_state.get(var_name, Unknown())


            # Annotate the VarRefNode with its abstract value
            node.var_ref.literal_annotation = val

        return out_state

    @classmethod
    def _evaluate_expression(cls, parent: Node, expr: Expr, state: Dict[str, AbstractValue]) -> AbstractValue:
        """Return abstract value for an expression under a state."""
        if isinstance(expr, (String, Integer, Float, Boolean, Null)):
            return Literal(expr.value)

        # Variable reference
        if isinstance(expr, VariableReference):
            # for preds in parent, find the corresponding VarRefNode and get its annotation
            for pred in parent.preds:
                if isinstance(pred, VarRefNode) and pred.var_ref == expr:
                    return pred.var_ref.literal_annotation or Unknown()
            return state.get(expr.value, Unknown())

        # Anything else = not literal
        return NonLiteral()

def analyze_cfg_literals(cfg: CFG) -> None:
    LiteralAnalysis.analyze(cfg)
