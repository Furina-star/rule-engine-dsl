"""A character-by-character lexer with one-based line/column positions."""

from dataclasses import dataclass
from enum import Enum, auto
from math import isfinite

from errors import LexerError


class TokenType(Enum):
    LET = auto()
    RULE = auto()
    WHEN = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    PRINT = auto()
    TRUE = auto()
    FALSE = auto()
    IDENTIFIER = auto()
    NUMBER = auto()
    STRING = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    EQUAL = auto()
    EQUAL_EQUAL = auto()
    BANG_EQUAL = auto()
    GREATER = auto()
    GREATER_EQUAL = auto()
    LESS = auto()
    LESS_EQUAL = auto()
    AND = auto()
    OR = auto()
    BANG = auto()
    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    LEFT_BRACE = auto()
    RIGHT_BRACE = auto()
    SEMICOLON = auto()
    EOF = auto()


@dataclass(frozen=True)
class Token:
    type: TokenType
    lexeme: str
    literal: int | float | str | None
    line: int
    column: int


KEYWORDS = {
    "let": TokenType.LET, "rule": TokenType.RULE, "when": TokenType.WHEN,
    "if": TokenType.IF, "else": TokenType.ELSE, "while": TokenType.WHILE,
    "print": TokenType.PRINT, "true": TokenType.TRUE, "false": TokenType.FALSE,
}
SINGLE_TOKENS = {
    "+": TokenType.PLUS, "-": TokenType.MINUS, "*": TokenType.STAR,
    "/": TokenType.SLASH, "=": TokenType.EQUAL, "!": TokenType.BANG,
    ">": TokenType.GREATER, "<": TokenType.LESS,
    "(": TokenType.LEFT_PAREN, ")": TokenType.RIGHT_PAREN,
    "{": TokenType.LEFT_BRACE, "}": TokenType.RIGHT_BRACE,
    ";": TokenType.SEMICOLON,
}
DOUBLE_TOKENS = {
    "==": TokenType.EQUAL_EQUAL, "!=": TokenType.BANG_EQUAL,
    ">=": TokenType.GREATER_EQUAL, "<=": TokenType.LESS_EQUAL,
    "&&": TokenType.AND, "||": TokenType.OR,
}


class Lexer:
    def __init__(self, source: str) -> None:
        # Treat Unix, Windows, and classic Mac newlines identically.
        self.source = source.replace("\r\n", "\n").replace("\r", "\n")
        self.current = 0
        self.line = 1
        self.column = 1

    def _peek(self) -> str:
        return self.source[self.current] if self.current < len(self.source) else ""

    def _advance(self) -> str:
        char = self.source[self.current]
        self.current += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    @staticmethod
    def _digit(char: str) -> bool:
        return bool(char) and "0" <= char <= "9"

    @staticmethod
    def _identifier_start(char: str) -> bool:
        return bool(char) and ("a" <= char <= "z" or "A" <= char <= "Z" or char == "_")

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while self.current < len(self.source):
            start, line, column = self.current, self.line, self.column
            char = self._advance()
            if char in " \t\n":
                continue
            if char == "/" and self._peek() == "/":
                self._skip_comment()
                continue
            tokens.append(self._scan_token(char, start, line, column))
        tokens.append(Token(TokenType.EOF, "", None, self.line, self.column))
        return tokens

    def _skip_comment(self) -> None:
        while self._peek() not in ("", "\n"):
            self._advance()

    def _scan_token(self, char: str, start: int, line: int, column: int) -> Token:
        literal = None
        if self._digit(char):
            literal = self._number(start, line, column)
            kind = TokenType.NUMBER
        elif self._identifier_start(char):
            kind = self._identifier(start)
        elif char == '"':
            literal = self._string(line, column)
            kind = TokenType.STRING
        else:
            kind = self._operator(char, line, column)
        return Token(kind, self.source[start:self.current], literal, line, column)

    def _number(self, start: int, line: int, column: int) -> int | float:
        self._consume_digits()
        if self._peek() == ".":
            self._advance()
            if not self._digit(self._peek()):
                raise LexerError("Expected a digit after decimal point.", line, column)
            self._consume_digits()
        number = self.source[start:self.current]
        try:
            literal = float(number) if "." in number else int(number)
        except ValueError as error:
            raise LexerError("Numeric literal is too large.", line, column) from error
        if isinstance(literal, float) and not isfinite(literal):
            raise LexerError("Numeric literal must be finite.", line, column)
        return literal

    def _consume_digits(self) -> None:
        while self._digit(self._peek()):
            self._advance()

    def _identifier(self, start: int) -> TokenType:
        char = self._peek()
        while self._identifier_start(char) or self._digit(char):
            self._advance()
            char = self._peek()
        return KEYWORDS.get(self.source[start:self.current], TokenType.IDENTIFIER)

    def _operator(self, char: str, line: int, column: int) -> TokenType:
        kind = DOUBLE_TOKENS.get(char + self._peek())
        if kind is not None:
            self._advance()
            return kind
        kind = SINGLE_TOKENS.get(char)
        if kind is None:
            raise LexerError(f"Unsupported character {char!r}.", line, column)
        return kind

    def _string(self, line: int, column: int) -> str:
        characters: list[str] = []
        escapes = {'"': '"', "\\": "\\", "n": "\n", "t": "\t", "r": "\r"}
        while self._peek() not in ("", "\n", '"'):
            char = self._advance()
            if char == "\\":
                if self._peek() in ("", "\n"):
                    break
                escape = self._advance()
                if escape not in escapes:
                    raise LexerError(f"Unsupported string escape '\\{escape}'.", line, column)
                char = escapes[escape]
            characters.append(char)
        if self._peek() != '"':
            raise LexerError("Unterminated string.", line, column)
        self._advance()
        return "".join(characters)
