from typing import Dict
from functools import reduce

from glitch.repr.inter import Variable, VariableReference, Value, String, Integer, Float, Boolean, Null
from glitch.dataflow.cfg import CFG, Node, VarNode, VarRefNode, DummyNode
from glitch.dataflow.literal_value import AbstractValue, Unknown, Literal, Conflicting, Mixed, NonLiteral, meet

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

class LiteralAnalysis:
    def __init__(self, cfg: CFG):
        self.cfg = cfg
        # NodeID -> var_name -> AbstractValue
        self.in_states: Dict[int, Dict[str, AbstractValue]] = {}
        self.out_states: Dict[int, Dict[str, AbstractValue]] = {}
    
    def analyze(self) -> None:
        # Initialize all states
        for node_id in self.cfg.nodes:
            self.in_states[node_id] = {}
            self.out_states[node_id] = {}
        
        # Worklist algorithm
        worklist = list(self.cfg.nodes.values())
        """
        possible efficiency improvement:
        in_worklist = set()    # track membership
        """
        while worklist:
            node = worklist.pop(0)
            
            # Compute IN[node] = merge of OUT[pred] for all predecessors
            old_in = self.in_states[node.id].copy()
            new_in = self._merge_states([self.out_states[pred.id] for pred in node.preds])
            self.in_states[node.id] = new_in
            
            # Compute OUT[node] = transfer(IN[node])
            old_out = self.out_states[node.id].copy()
            new_out = self._transfer(node, new_in)
            self.out_states[node.id] = new_out
            
            # If OUT changed, add successors to worklist
            if new_out != old_out or new_in != old_in:
                for succ in node.succs:
                    if succ not in worklist:
                        worklist.append(succ)


    def _merge_states(self, states: list[Dict[str, AbstractValue]]) -> Dict[str, AbstractValue]:
        if not states:
            return {}

        result: Dict[str, AbstractValue] = {}
        all_vars = {var for state in states for var in state.keys()}

        for var in all_vars:
            vals = [state.get(var, Unknown()) for state in states]
            result[var] = reduce(meet, vals)

        return result
    
    def _transfer(self, node: Node, in_state: Dict[str, AbstractValue]) -> Dict[str, AbstractValue]:
        """Transfer function per node type."""
        out_state = in_state.copy()

        if isinstance(node, VarNode):
            var_name = node.var.name
            val = self._evaluate_expression(node.var.value, in_state)
            out_state[var_name] = val

        elif isinstance(node, VarRefNode):
            var_name = node.varRef.value
            val = in_state.get(var_name, Unknown())

            # Annotate the VarRefNode with its abstract value
            node.varRef.literal_annotation = val

        return out_state
    
    def _evaluate_expression(self, expr, state: Dict[str, AbstractValue]) -> AbstractValue:
        """Return abstract value for an expression under a state."""
        # Direct literals
        if isinstance(expr, (String, Integer, Float, Boolean, Null)):
            return Literal(expr.value)

        # Variable reference
        if isinstance(expr, VariableReference):
            # Look up variable in state and propagate its literal value

            return state.get(expr.value, Unknown())

        # Anything else = not literal
        return NonLiteral()
    
    def print_analysis_results(self) -> None:
        print("=== Literal Analysis Results ===")
        for node_id, node in self.cfg.nodes.items():
            print(f"\nNode {node_id} ({type(node).__name__}):")
            print(f"  IN:  {self.in_states[node_id]}")
            print(f"  OUT: {self.out_states[node_id]}")


def analyze_cfg_literals(cfg: CFG) -> LiteralAnalysis:
    analysis = LiteralAnalysis(cfg)
    analysis.analyze()
    return analysis
