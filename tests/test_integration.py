"""End-to-end tests use real files and actual command-line subprocesses."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from evaluator import Evaluator
from lexer import Lexer
from parser import Parser

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "sample.rule": "Student passed!\nGood job!\n0\n1\n2\n",
    "scope_demo.rule": "outer block\n10\ninner block\nouter block\nglobal\n15\n",
    "nested_conditions.rule": "Passed with regular standing\nEligible for next term\n",
    "loop_demo.rule": "4\n3\n6\nTotal:\n18\n",
}


class IntegrationTests(unittest.TestCase):
    @staticmethod
    def cli(*arguments: str | Path, cwd: str | Path = ROOT) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(ROOT / "main.py"), *map(str, arguments)],
                              cwd=cwd, capture_output=True, text=True, timeout=10)

    def assert_success(self, result: subprocess.CompletedProcess[str], expected: str) -> None:
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stderr)
        self.assertEqual(expected, result.stdout)

    def assert_failure(self, result: subprocess.CompletedProcess[str], message: str,
                       status: int = 1) -> None:
        self.assertEqual(status, result.returncode, result.stderr)
        self.assertIn(message, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def temporary_program(self, source: str, *arguments: str | Path) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.rule"
            path.write_text(source, encoding="utf-8")
            return self.cli(path, *arguments)

    def test_sample_pipeline_and_final_global_state(self):
        output = []
        evaluator = Evaluator(output=output.append)
        source = (ROOT / "examples" / "sample.rule").read_text(encoding="utf-8")
        evaluator.execute(Parser(Lexer(source).tokenize()).parse())
        self.assertEqual(EXPECTED["sample.rule"], "\n".join(output) + "\n")
        self.assertEqual({"score": 85, "counter": 3}, evaluator.globals.values)

    def test_all_example_files_via_cli(self):
        for filename, expected in EXPECTED.items():
            with self.subTest(filename=filename):
                self.assert_success(self.cli("examples/" + filename), expected)

    def test_default_sample(self):
        self.assert_success(self.cli(), EXPECTED["sample.rule"])

    def test_default_sample_from_other_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assert_success(self.cli(cwd=directory), EXPECTED["sample.rule"])

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.cli(Path(directory) / "does-not-exist.rule")
        self.assert_failure(result, "File error")
        self.assertEqual("", result.stdout)

    def test_directory_is_not_source_file(self):
        self.assert_failure(self.cli(ROOT / "examples"), "File error")

    def test_invalid_utf8(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.rule"
            path.write_bytes(b"\xff\xfe\x00")
            self.assert_failure(self.cli(path), "File error")

    def test_utf8_bom(self):
        self.assert_success(self.temporary_program('\ufeffprint("hello");'), "hello\n")

    def test_empty_source(self):
        self.assert_success(self.temporary_program("// empty program"), "")

    def test_lexer_error(self):
        result = self.temporary_program("\n  @")
        self.assert_failure(result, "Lexer error at line 2, column 3")
        self.assertEqual("", result.stdout)

    def test_parse_error_before_any_execution(self):
        result = self.temporary_program('print("should not run"); let x = ;')
        self.assert_failure(result, "Syntax error")
        self.assertEqual("", result.stdout)

    def test_runtime_error_keeps_prior_output(self):
        result = self.temporary_program('print("before");\nprint(1 / 0);')
        self.assert_failure(result, "Runtime error at line 2, column 9: Division by zero")
        self.assertEqual("before\n", result.stdout)

    def test_undefined_and_invalid_condition_errors(self):
        for source, message in (("x = 1;", "undefined variable"),
                                ("if (1) {}", "requires a boolean")):
            with self.subTest(source=source):
                self.assert_failure(self.temporary_program(source), message)

    def test_loop_limit_option(self):
        result = self.temporary_program("while (true) {}", "--max-loop-iterations", "2")
        self.assert_failure(result, "Loop iteration limit (2) exceeded")
        self.assert_success(self.temporary_program(
            "let i = 0; while (i < 2) { i = i + 1; } print(i);",
            "--max-loop-iterations", "2"), "2\n")

    def test_invalid_loop_limit_arguments(self):
        for value in ("0", "-1", "no", "1.5"):
            with self.subTest(value=value):
                self.assert_failure(self.cli("--max-loop-iterations", value),
                                    "must be a positive integer", status=2)

    def test_excessive_nesting_is_graceful(self):
        source = "print(" + "(" * 2000 + "1" + ")" * 2000 + ");"
        self.assert_failure(self.temporary_program(source), "program nesting exceeds")

    def test_help(self):
        result = self.cli("--help")
        self.assertEqual(0, result.returncode)
        self.assertIn("--max-loop-iterations", result.stdout)
        self.assertEqual("", result.stderr)

    def test_source_caret_for_lexer_parser_and_runtime_errors(self):
        for source, message, column, expected_output in (
            ("\n  @", "Lexer error at line 2, column 3", 3, ""),
            ("\n  print();", "Syntax error at line 2, column 9", 9, ""),
            ('print("before");\n  print(1 / 0);', "Runtime error at line 2, column 11", 11, "before\n"),
        ):
            with self.subTest(source=source):
                result = self.temporary_program(source, "--show-source")
                self.assert_failure(result, message)
                self.assertIn("test.rule:", result.stderr)
                self.assertEqual(expected_output, result.stdout)
                self.assertEqual(["    " + source.split("\n")[1], "    " + " " * (column - 1) + "^"],
                                 result.stderr.splitlines()[1:])

    def test_source_caret_handles_blank_eof_line(self):
        result = self.temporary_program("{\n", "--show-source")
        self.assert_failure(result, "Syntax error at line 2, column 1")
        self.assertEqual(["    ", "    ^"], result.stderr.splitlines()[1:])

    def test_error_excerpt_is_disabled_by_default(self):
        result = self.temporary_program("\n  @")
        self.assert_failure(result, "Lexer error at line 2, column 3")
        self.assertEqual(1, len(result.stderr.splitlines()))

    def test_else_if_program_via_cli(self):
        self.assert_success(self.temporary_program(
            'let score = 85; if (score >= 90) { print("excellent"); }'
            'else if (score >= 75) { print("passed"); } else { print("retry"); }'
        ), "passed\n")


if __name__ == "__main__":
    unittest.main()
