"""Exact source excerpts and caret alignment for optional CLI diagnostics."""

from pathlib import Path
import unittest

from errors import EvaluationError, LexerError, ParseError
from main import format_diagnostic


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.path = Path("program.rule")

    def test_excerpt_is_opt_in(self):
        error = LexerError("Unsupported character '@'.", 1, 3)
        self.assertEqual("program.rule: Lexer error at line 1, column 3: Unsupported character '@'.",
                         format_diagnostic(self.path, error, "  @"))

    def test_all_error_classes_keep_header_and_indentation(self):
        for error_type, label in ((LexerError, "Lexer error"), (ParseError, "Syntax error"),
                                  (EvaluationError, "Runtime error")):
            with self.subTest(error_type=error_type):
                error = error_type("Problem.", 2, 3)
                expected = f"program.rule: {label} at line 2, column 3: Problem.\n      bad\n      ^"
                self.assertEqual(expected, format_diagnostic(self.path, error, "\n  bad", True))

    def test_tabs_expand_consistently_before_caret(self):
        error = LexerError("Problem.", 1, 3)
        expected = "program.rule: Lexer error at line 1, column 3: Problem.\n         @\n         ^"
        self.assertEqual(expected, format_diagnostic(self.path, error, "\t @", True))

    def test_newline_formats_produce_identical_excerpt(self):
        error = ParseError("Problem.", 2, 2)
        expected = "program.rule: Syntax error at line 2, column 2: Problem.\n     bad\n     ^"
        for newline in ("\n", "\r\n", "\r"):
            with self.subTest(newline=newline):
                self.assertEqual(expected, format_diagnostic(self.path, error, "first" + newline + " bad", True))

    def test_empty_source_and_trailing_empty_line(self):
        for source, line in (("", 1), ("first\n", 2), ("first\r\n", 2)):
            with self.subTest(source=source):
                error = ParseError("Expected an expression.", line, 1)
                expected = (f"program.rule: Syntax error at line {line}, column 1: Expected an expression."
                            "\n    \n    ^")
                self.assertEqual(expected, format_diagnostic(self.path, error, source, True))

    def test_missing_or_invalid_locations_only_show_header(self):
        for line, column in ((None, None), (1, None), (None, 1), (0, 1), (-1, 1),
                             (2, 1), (1, 0), (1, -1)):
            with self.subTest(line=line, column=column):
                error = EvaluationError("Problem.", line, column)
                self.assertEqual(f"program.rule: {error}", format_diagnostic(self.path, error, "text", True))

    def test_column_past_line_points_to_end(self):
        error = ParseError("Problem.", 1, 100)
        expected = "program.rule: Syntax error at line 1, column 100: Problem.\n    end\n       ^"
        self.assertEqual(expected, format_diagnostic(self.path, error, "end", True))


if __name__ == "__main__":
    unittest.main()
