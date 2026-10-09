"""Command-line entry point for the interpreted Rule Engine DSL."""

import argparse
from pathlib import Path
import sys

from environment import Environment
from errors import DSLError
from evaluator import DEFAULT_LOOP_LIMIT, Evaluator
from lexer import Lexer
from parser import Parser


def positive_integer(value: str) -> int:
    try:
        result = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if result < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return result


def format_diagnostic(path: Path, error: DSLError, source: str,
                      show_source: bool = False) -> str:
    """Optionally append a source excerpt without changing the error message."""
    message = f"{path}: {error}"
    if not show_source or error.line is None or error.column is None:
        return message
    lines = source.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not 1 <= error.line <= len(lines) or error.column < 1:
        return message
    line = lines[error.line - 1]
    # Lexer columns count characters; expand tabs consistently for display.
    column = min(error.column - 1, len(line))
    padding = " " * len(line[:column].expandtabs(4))
    return f"{message}\n    {line.expandtabs(4)}\n    {padding}^"


def main(argv: list[str] | None = None) -> int:
    arguments = argparse.ArgumentParser(description="Run a Rule Engine DSL source file.")
    arguments.add_argument("file", nargs="?", type=Path,
                           default=Path(__file__).resolve().parent / "examples" / "sample.rule",
                           help="UTF-8 .rule source (default: bundled sample)")
    arguments.add_argument("--max-loop-iterations", type=positive_integer,
                           default=DEFAULT_LOOP_LIMIT,
                           help=f"limit per loop encounter (default: {DEFAULT_LOOP_LIMIT})")
    arguments.add_argument("--show-source", action="store_true",
                           help="show the source line and a caret for language errors")
    options = arguments.parse_args(argv)
    try:
        source = options.file.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as error:
        print(f"File error: cannot read '{options.file}': {error}", file=sys.stderr)
        return 1
    try:
        tokens = Lexer(source).tokenize()
        statements = Parser(tokens).parse()
        global_environment = Environment()
        Evaluator(global_environment,
                  max_loop_iterations=options.max_loop_iterations).execute(statements)
    except DSLError as error:
        print(format_diagnostic(options.file, error, source, options.show_source), file=sys.stderr)
        return 1
    except RecursionError:
        print(f"{options.file}: Runtime error: program nesting exceeds Python's recursion limit.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
