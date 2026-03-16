## Dataflow extension overview

This development extends GLITCH with control-flow-aware literal propagation so security checks can reason about indirect values, not only direct literals.

Main implementation lives in [glitch/dataflow](glitch/dataflow):
- [glitch/dataflow/cfg.py](glitch/dataflow/cfg.py): builds a control-flow graph (CFG) from IR.
- [glitch/dataflow/analysis.py](glitch/dataflow/analysis.py): runs forward dataflow over that CFG.
- [glitch/dataflow/literal_value.py](glitch/dataflow/literal_value.py): defines the abstract domain (lattice values + merge/meet semantics).

## CFG model ([glitch/dataflow/cfg.py](glitch/dataflow/cfg.py))

The CFG is built over definition/use events.

Node types:
- `VarNode`: variable definition (`Variable` in IR).
- `VarRefNode`: variable use (`VariableReference` in IR).
- `DummyNode`: structural control-flow nodes (entry/exit and branch merge points).

Builder logic (`CFGBuilder`):
- Recursively visits `UnitBlock`, `AtomicUnit`, attributes, statements, expressions, conditionals.
- Uses `ScopeManager` to resolve references and generate scope-qualified names (`name@scope_id`).
- Creates edges in execution order.
- For conditionals, creates explicit branch split/merge dummy nodes.

Variable definitions and uses are topologically connected according to control flow, including nested scopes.

### ScopeManager current behavior ([glitch/dataflow/scope_manager.py](glitch/dataflow/scope_manager.py))

`ScopeManager` is currently a lightweight lexical scope tracker used only for def-use binding in CFG construction.

- Maintains a scope stack (`scope_stack`) where each scope stores:
	- `id`: unique numeric scope id,
	- `unit`: IR element that opened the scope,
	- `symbols`: `name -> Variable` map,
	- `parent`: pointer to parent scope object.
- On `enter_scope(...)`, allocates a fresh scope id and pushes a new scope frame.
- On `declare_variable(...)`, binds the variable in the current frame and writes `var.scope_id`.
- On `resolve_variable(...)`, walks the stack from innermost to outermost and returns the first matching declaration.
- If no declaration is found, resolution returns `None`, and CFG nodes are marked as undeclared (`name@<undeclared>`).

## Literal analysis ([glitch/dataflow/analysis.py](glitch/dataflow/analysis.py))

Forward worklist dataflow that computes `IN/OUT` state per CFG node.

Per-variable abstract state comes from `glitch/dataflow/literal_value.py`:
```
Lattice (per variable):

    T (Unknown)       → initial state (no information yet)
    Literal(v)        → variable is exactly literal v
    Conflicting(S)    → variable is literal, but with multiple distinct
                        literal values depending on path
    Mixed(S)          → variable is literal on some paths (values S), but
                        non-literal on others
    NonLiteral        → variable is never a literal

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
```

The introduction of `Conflicting` and `Mixed` cases is not strictly necessary for the current use case. It was done for semantics completeness.

The analysis's output is communicated by modifying the IR in-place: each `VariableReference` node gets a `literal_annotation` attribute set to the appropriate `AbstractValue` for that use site. 

Transfer behavior:
- At `VarNode`: evaluate assigned expression and update variable state.
- At `VarRefNode`: read current abstract value and annotate IR reference as `literal_annotation`.


Expression evaluation currently treats primitive IR values (`String`, `Integer`, `Float`, `Boolean`, `Null`) as literals, propagates through variable references using current state, and marks unsupported/composite computations as `NonLiteral`.

## Security rule integration

After this change, security checkers inspect `literal_annotation` on references and treat `Literal` / `Conflicting` / `Mixed` as evidence that the reference may carry hardcoded values.

## Analysis pipeline integration

Dataflow annotation is executed in CLI flow ([glitch/__main__.py](glitch/__main__.py)) via `annotate_ir(...)` defined in [glitch/dataflow/analysis.py](glitch/dataflow/analysis.py), before running rule visitors. It is opt-in: the `--dataflow` flag (default `False`) must be set to enable it.

## Tests added

[glitch/tests/dataflow/test_dataflow.py](glitch/tests/dataflow/test_dataflow.py) validates:
- indirect secret detection through variable aliases,
- scope behavior (inner/outer scope interactions),
- path-dependent outcomes (`Conflicting` / `Mixed`) reflected in findings

To simplify testing, a helper ([glitch/tests/dataflow/ir_builder.py](glitch/tests/dataflow/ir_builder.py)) was added to build IR objects from JSON serialization, keeping these tests isolated from parser behavior.

## Evaluation
made use of the anotated datasets in glitch-llm repository. Only puppet in the - dataset showed difference with the following false positives:

An evaluation was made, leveraging the annotated datasets from the glitch-llm repository. Only the Puppet subset of the dataset exhibited differences, where a small number of additional false positives were observed. 

## Validation Process

Validation was aided by Ruben Opdebeeck's replication package for the paper ["Control and Data Flow in Security Smell Detection for Infrastructure as Code: Is It Worth the Effort?"](https://doi.org/10.6084/m9.figshare.21929856). This made it possible to:

- Analyze some cases where GASEL detected a security smell but GLITCH did not, to identify potential improvements or missed detections.
- Investigate some cases where both tools detected a smell, with particular attention to findings involving variable indirection (indirection > 0), to validate the correctness of the dataflow extension.
- Review some instances where GLITCH detected a smell but GASEL did not to confirm if these were false positives.

## Next steps

Dependency-aware traversal in `CFGBuilder` is still work in progress. The current implementation resolves and visits several Ansible dependency patterns and prevents cycles with `visited_files`, but coverage is still limited.
This ongoing work is currently maintained in branch `inter-file-analysis`.

Current validation exists in [glitch/tests/dataflow/test_dependency_resolution.py](glitch/tests/dataflow/test_dependency_resolution.py), including:
- parsing and visiting of included files (`include_vars`, `include_tasks`, `import_tasks`, `import_playbook`),
- traversal bookkeeping and cycle prevention (`visited_files`).

Planned follow-up:
- expand dependency path extraction and normalization across additional provider-specific patterns,
- add configuration for lexical scoping rules so scope resolution is flexible,
- formalize cross-file scope and value propagation semantics,