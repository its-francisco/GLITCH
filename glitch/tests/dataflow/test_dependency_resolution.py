import os
import unittest
import tempfile
import glitch

from glitch.parsers.ansible import AnsibleParser
from glitch.repr.inter import UnitBlock, UnitBlockType
from glitch.dataflow.cfg import CFGBuilder
from glitch.dataflow.analysis import analyze_cfg_literals


class TestAnsibleDependencyResolution(unittest.TestCase):
    def test_vars_files_annotations_are_resolved(self) -> None:
        parser = AnsibleParser()
        path = os.path.join(
            os.path.dirname(glitch.__file__),
            "dataflow",
            "dependencyResolution",
            "vmware",
            "deploy.yml",
        )

        inter = parser.parse_file(path, UnitBlockType.script)
        self.assertIsInstance(inter, UnitBlock)

        cfg = CFGBuilder(inter, parser).build()  # type: ignore[arg-type]
        analyze_cfg_literals(cfg)

        data = inter.as_dict()  # type: ignore[union-attr]
        self.assertTrue(
            self._contains_var_annotation(data, "new_vm_passwd", "...customPasswd...")
        )

    def test_include_vars_mapping_annotations_are_resolved(self) -> None:
        parser = AnsibleParser()

        with tempfile.TemporaryDirectory() as tmp_dir:
            main_path = os.path.join(tmp_dir, "main.yml")
            vars_path = os.path.join(tmp_dir, "vars.yml")

            with open(vars_path, "w") as f:
                f.write('new_vm_passwd: "sekrit-from-vars"\n')

            with open(main_path, "w") as f:
                f.write(
                    """
- hosts: localhost
  gather_facts: no
  tasks:
    - include_vars:
        file: ./vars.yml
    - ansible.builtin.user:
        name: demo
        password: "{{ new_vm_passwd }}"
""".strip()
                )

            inter = parser.parse_file(main_path, UnitBlockType.script)
            self.assertIsInstance(inter, UnitBlock)

            cfg = CFGBuilder(inter, parser).build()  # type: ignore[arg-type]
            analyze_cfg_literals(cfg)

            data = inter.as_dict()  # type: ignore[union-attr]
            self.assertTrue(
                self._contains_var_annotation(data, "new_vm_passwd", "sekrit-from-vars")
            )

    def test_include_tasks_path_is_resolved(self) -> None:
        parser = AnsibleParser()

        with tempfile.TemporaryDirectory() as tmp_dir:
            main_path = os.path.join(tmp_dir, "main.yml")
            tasks_path = os.path.join(tmp_dir, "included_tasks.yml")

            with open(tasks_path, "w") as f:
                f.write(
                    """
- name: Example task
  debug:
    msg: hello
""".strip()
                )

            with open(main_path, "w") as f:
                f.write(
                    """
- hosts: localhost
  gather_facts: no
  tasks:
    - include_tasks: ./included_tasks.yml
""".strip()
                )

            inter = parser.parse_file(main_path, UnitBlockType.script)
            self.assertIsInstance(inter, UnitBlock)

            cfg_builder = CFGBuilder(inter, parser)  # type: ignore[arg-type]
            cfg = cfg_builder.build()
            analyze_cfg_literals(cfg)

            self.assertIn(os.path.abspath(tasks_path), cfg_builder.visited_files)

    def test_import_tasks_path_is_resolved(self) -> None:
        parser = AnsibleParser()

        with tempfile.TemporaryDirectory() as tmp_dir:
            main_path = os.path.join(tmp_dir, "main.yml")
            tasks_path = os.path.join(tmp_dir, "imported_tasks.yml")

            with open(tasks_path, "w") as f:
                f.write(
                    """
- name: Example imported task
  debug:
    msg: hello
""".strip()
                )

            with open(main_path, "w") as f:
                f.write(
                    """
- hosts: localhost
  gather_facts: no
  tasks:
    - import_tasks: ./imported_tasks.yml
""".strip()
                )

            inter = parser.parse_file(main_path, UnitBlockType.script)
            self.assertIsInstance(inter, UnitBlock)

            cfg_builder = CFGBuilder(inter, parser)  # type: ignore[arg-type]
            cfg = cfg_builder.build()
            analyze_cfg_literals(cfg)

            self.assertIn(os.path.abspath(tasks_path), cfg_builder.visited_files)

    def test_import_playbook_path_is_resolved(self) -> None:
        parser = AnsibleParser()

        with tempfile.TemporaryDirectory() as tmp_dir:
            main_path = os.path.join(tmp_dir, "main.yml")
            playbook_path = os.path.join(tmp_dir, "child_playbook.yml")

            with open(playbook_path, "w") as f:
                f.write(
                    """
- hosts: localhost
  gather_facts: no
  tasks:
    - debug:
        msg: imported
""".strip()
                )

            with open(main_path, "w") as f:
                f.write(
                    """
- import_playbook: ./child_playbook.yml
""".strip()
                )

            inter = parser.parse_file(main_path, UnitBlockType.script)
            self.assertIsInstance(inter, UnitBlock)

            cfg_builder = CFGBuilder(inter, parser)  # type: ignore[arg-type]
            cfg = cfg_builder.build()
            analyze_cfg_literals(cfg)

            self.assertIn(os.path.abspath(playbook_path), cfg_builder.visited_files)

    def _contains_var_annotation(
        self, node: object, var_name: str, literal_value: str
    ) -> bool:
        if isinstance(node, dict):
            if (
                node.get("ir_type") == "VariableReference"
                and node.get("value") == var_name
                and self._annotation_contains_literal(node.get("literal_annotation"), literal_value)
            ):
                return True
            return any(
                self._contains_var_annotation(child, var_name, literal_value)
                for child in node.values()
            )

        if isinstance(node, list):
            return any(
                self._contains_var_annotation(child, var_name, literal_value)
                for child in node
            )

        return False

    def _annotation_contains_literal(self, annotation: object, literal_value: str) -> bool:
        if not isinstance(annotation, dict):
            return False

        ann_type = annotation.get("type")
        if ann_type == "Literal":
            value = annotation.get("value")
            return isinstance(value, dict) and value.get("value") == literal_value

        if ann_type in {"Mixed", "Conflicting"}:
            values = annotation.get("values")
            if not isinstance(values, list):
                return False
            return any(
                isinstance(item, dict) and item.get("value") == literal_value
                for item in values
            )

        return False


if __name__ == "__main__":
    unittest.main()
