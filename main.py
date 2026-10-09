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


def main(argv: list[str] | None = None) -> int:
    arguments = argparse.ArgumentParser(description="Run a Rule Engine DSL source file.")
    arguments.add_argument("file", nargs="?", type=Path,
                           default=Path(__file__).resolve().parent / "examples" / "sample.rule",
                           help="UTF-8 .rule source (default: bundled sample)")
    arguments.add_argument("--max-loop-iterations", type=positive_integer,
                           default=DEFAULT_LOOP_LIMIT,
                           help=f"limit per loop encounter (default: {DEFAULT_LOOP_LIMIT})")
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
        print(f"{options.file}: {error}", file=sys.stderr)
        return 1
    except RecursionError:
        print(f"{options.file}: Runtime error: program nesting exceeds Python's recursion limit.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

