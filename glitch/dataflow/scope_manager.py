from glitch.repr.inter import Variable, VariableReference, CodeElement
from typing import Dict, List, Optional

class ScopeManager:
    def __init__(self):
        self.scope_stack: List[Dict] = []
        self.current_scope_id = 0
        self.unique_scope_ids = set([0])

    def enter_scope(self, unit: CodeElement):
        while self.current_scope_id in self.unique_scope_ids:
            self.current_scope_id += 1
        self.unique_scope_ids.add(self.current_scope_id)
        new_scope = {
            'id': self.current_scope_id,
            'unit': unit,
            'symbols': {},  # name -> Variable
            'parent': self.scope_stack[-1] if self.scope_stack else None
        }
        self.scope_stack.append(new_scope)
        return new_scope

    def exit_scope(self):
        popped = self.scope_stack.pop()
        self.current_scope_id = self.scope_stack[-1]['id'] if self.scope_stack else 0
        return popped

    def declare_variable(self, var: Variable):
        """Declare a variable in current scope"""
        current = self.scope_stack[-1]
        current['symbols'][var.name] = var
        var.scope_id = current['id']

    def resolve_variable(self, var_ref: VariableReference) -> Optional[Variable]:
        """Resolve a variable reference to its declaration"""
        # Walk up scope chain to find declaration
        for scope in reversed(self.scope_stack):
            if var_ref.value in scope['symbols']:
                return scope['symbols'][var_ref.value]
        return None  # Undeclared variable
