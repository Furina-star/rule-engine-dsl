"""User-facing errors shared by the interpreter pipeline."""


class DSLError(Exception):
    """An expected language error, optionally attached to a source location."""

    label = "DSL error"

    def __init__(self, message: str, line: int | None = None,
                 column: int | None = None) -> None:
        self.message = message
        self.line = line
        self.column = column
        super().__init__(message)

    def __str__(self) -> str:
        location = "" if self.line is None else f" at line {self.line}, column {self.column}"
        return f"{self.label}{location}: {self.message}"


class LexerError(DSLError):
    label = "Lexer error"


class ParseError(DSLError):
    label = "Syntax error"


class EvaluationError(DSLError):
    label = "Runtime error"

