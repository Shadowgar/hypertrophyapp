"""Exercise the real helper's output boundaries without importing its DB setup."""
import ast
from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
from types import SimpleNamespace
import unittest


HELPER = Path(__file__).resolve().parents[3] / "docs/evidence/starting-load-2026-10-23/characterize.py"
SUCCESS = "Synthetic Authored characterization passed; all behavior assertions retained.\n"


class CharacterizationOutputTests(unittest.TestCase):
    def setUp(self):
        self.tree = ast.parse(HELPER.read_text())

    def test_success_output_does_not_serialize_response_evidence(self):
        sink = self.tree.body[-1]
        self.assertIsInstance(sink, ast.Expr)
        self.assertEqual(ast.unparse(sink.value.func), "print")
        namespace = {"results": {"private": {"weight": 876.543,
                     "receipt_id": "sensitive-receipt-marker", "nested": ["private-body-marker"]}}}
        # json is supplied for the original sink so the regression fails on disclosure.
        import json
        namespace["json"] = json
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            exec(compile(ast.Module(body=[sink], type_ignores=[]), str(HELPER), "exec"), namespace)
        self.assertEqual(output.getvalue(), SUCCESS)
        self.assertEqual(errors.getvalue(), "")

    def test_every_status_failure_still_fails_without_response_body(self):
        guards = [node for node in ast.walk(self.tree) if isinstance(node, ast.Assert)
                  and isinstance(node.test, ast.Compare)
                  and isinstance(node.test.left, ast.Attribute)
                  and node.test.left.attr == "status_code"]
        self.assertEqual(len(guards), 5)
        for guard in guards:
            variable = guard.test.left.value.id
            expected = guard.test.comparators[0].value
            for body in ("private-body-marker", '{"token":"nested-private-marker","weight":876.543}'):
                with self.subTest(line=guard.lineno, body_kind=body[0]):
                    code = compile(ast.Module(body=[guard], type_ignores=[]), str(HELPER), "exec")
                    with self.assertRaises(AssertionError) as raised:
                        exec(code, {variable: SimpleNamespace(status_code=500, text=body)})
                    message = str(raised.exception)
                    self.assertTrue(message)
                    self.assertNotIn(body, message)
                    self.assertNotIn("private-marker", message)
                    # Expected 200 and ownership-denial 404 remain successful controls.
                    exec(code, {variable: SimpleNamespace(status_code=expected, text=body)})


if __name__ == "__main__":
    unittest.main()
