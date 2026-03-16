from glitch.dataflow.cfg import CFG, DummyNode, VarNode, VarRefNode

def generate_dot(cfg: CFG) -> str:
    """
    Generates a Graphviz DOT file for the CFG
    """
    lines = ["digraph CFG {", "  rankdir=TD;"]

    # Define nodes
    for node_id, node in cfg.nodes.items():
        label = str(node)
        if isinstance(node, VarNode):
            color = "lightblue"
        elif isinstance(node, VarRefNode):
            color = "lightgreen"
        elif isinstance(node, DummyNode):
            color = "gray"
        else:
            label = f"{type(node).__name__}\\n{node.id}"
            color = "white"

        lines.append(f'  {node_id} [label="{label}", style=filled, fillcolor={color}];')

    # Add edges
    for node in cfg.nodes.values():
        for succ in node.succs:
            lines.append(f"  {node.id} -> {succ.id};")

    if cfg.entry:
        lines.append('  entry [label="ENTRY", shape=oval, style=filled, fillcolor=yellow];')
        lines.append(f"  entry -> {cfg.entry.id};")
    if cfg.exit:
        lines.append('  exit [label="EXIT", shape=oval, style=filled, fillcolor=orange];')
        lines.append(f"{cfg.exit.id} -> exit;")

    lines.append("}")

    return "\n".join(lines)

def open_dot(dot: str) -> None:
    import tempfile
    import os
    import platform
    import subprocess
    import time

    # Create a temporary file for the DOT content
    with tempfile.NamedTemporaryFile(suffix='.dot', mode='w', delete=False) as dot_file:
        dot_file_path = dot_file.name
        dot_file.write(dot)

    # Output SVG file
    with tempfile.NamedTemporaryFile(suffix='.svg', mode='w', delete=False) as svg_file:
        svg_file_path = svg_file.name
        try:
            subprocess.run(["dot", "-Tsvg", dot_file_path, "-o", svg_file_path], check=True)

            # Open the generated SVG based on the OS
            if platform.system() == "Darwin":  # macOS
                proc = subprocess.Popen(["open", svg_file_path])
            elif platform.system() == "Windows":
                proc = subprocess.Popen(["start", svg_file_path], shell=True)
            else:  # Linux and others
                proc = subprocess.Popen(["xdg-open", svg_file_path])

            # Wait a bit to ensure viewer has loaded the file
            time.sleep(20)
        finally:
            # Clean up temporary files
            for f in [dot_file_path, svg_file_path]:
                if os.path.exists(f):
                    os.unlink(f)
