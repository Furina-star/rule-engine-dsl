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
            literal = None
            if char in " \t\n":
                continue
            if char == "/" and self._peek() == "/":
                while self._peek() not in ("", "\n"):
                    self._advance()
                continue
            if self._digit(char):
                while self._digit(self._peek()):
                    self._advance()
                if self._peek() == ".":
                    self._advance()
                    if not self._digit(self._peek()):
                        raise LexerError("Expected a digit after decimal point.", line, column)
                    while self._digit(self._peek()):
                        self._advance()
                number = self.source[start:self.current]
                try:
                    literal = float(number) if "." in number else int(number)
                except ValueError as error:
                    raise LexerError("Numeric literal is too large.", line, column) from error
                if isinstance(literal, float) and not isfinite(literal):
                    raise LexerError("Numeric literal must be finite.", line, column)
                kind = TokenType.NUMBER
            elif self._identifier_start(char):
                while self._identifier_start(self._peek()) or self._digit(self._peek()):
                    self._advance()
                kind = KEYWORDS.get(self.source[start:self.current], TokenType.IDENTIFIER)
            elif char == '"':
                literal = self._string(line, column)
                kind = TokenType.STRING
            elif char + self._peek() in DOUBLE_TOKENS:
                kind = DOUBLE_TOKENS[char + self._advance()]
            elif char in SINGLE_TOKENS:
                kind = SINGLE_TOKENS[char]
            else:
                raise LexerError(f"Unsupported character {char!r}.", line, column)
            tokens.append(Token(kind, self.source[start:self.current], literal, line, column))
        tokens.append(Token(TokenType.EOF, "", None, self.line, self.column))
        return tokens

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

