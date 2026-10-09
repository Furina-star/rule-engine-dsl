"""Recursive-descent statements and one expression method per precedence level."""

from collections.abc import Callable

import ast_nodes as ast
from errors import ParseError
from lexer import Token, TokenType as T


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        if not tokens or tokens[-1].type != T.EOF:
            raise ParseError("Token stream must end with EOF.")
        if any(token.type == T.EOF for token in tokens[:-1]):
            raise ParseError("Unexpected EOF inside token stream.")
        self.tokens = tokens
        self.current = 0

    def _peek(self) -> Token:
        return self.tokens[self.current]

    def _check(self, kind: T) -> bool:
        return self._peek().type == kind

    def _match(self, *kinds: T) -> bool:
        if self._peek().type in kinds:
            self.current += 1
            return True
        return False

    def _consume(self, kind: T, message: str) -> Token:
        token = self._peek()
        if not self._match(kind):
            found = repr(token.lexeme) if token.type != T.EOF else "end of file"
            raise ParseError(f"{message} Found {found}.", token.line, token.column)
        return token

    @staticmethod
    def _location(token: Token) -> dict[str, int]:
        return {"line": token.line, "column": token.column}

    def parse(self) -> list[ast.Stmt]:
        statements: list[ast.Stmt] = []
        while not self._check(T.EOF):
            statements.append(self._statement())
        return statements

    def _statement(self) -> ast.Stmt:
        token = self._peek()
        location = self._location(token)
        if self._match(T.LET):
            name = self._consume(T.IDENTIFIER, "Expected variable name after 'let'.")
            self._consume(T.EQUAL, "Expected '=' after variable name.")
            value = self._expression()
            self._consume(T.SEMICOLON, "Expected ';' after declaration.")
            return ast.LetStatement(name.lexeme, value, **location)
        if self._match(T.PRINT):
            value = self._parenthesized("print")
            self._consume(T.SEMICOLON, "Expected ';' after print statement.")
            return ast.PrintStatement(value, **location)
        if self._match(T.IF):
            condition = self._parenthesized("if")
            then_branch = self._block()
            else_branch = self._block() if self._match(T.ELSE) else None
            return ast.IfStatement(condition, then_branch, else_branch, **location)
        if self._match(T.WHILE):
            condition = self._parenthesized("while")
            return ast.WhileStatement(condition, self._block(), **location)
        if self._match(T.RULE):
            name = self._consume(T.IDENTIFIER, "Expected rule name.")
            self._consume(T.WHEN, "Expected 'when' after rule name.")
            condition = self._parenthesized("when")
            return ast.RuleStatement(name.lexeme, condition, self._block(), **location)
        if self._check(T.LEFT_BRACE):
            return self._block()
        if self._match(T.IDENTIFIER):
            self._consume(T.EQUAL, "Expected '=' after assignment target.")
            value = self._expression()
            self._consume(T.SEMICOLON, "Expected ';' after assignment.")
            return ast.Assignment(token.lexeme, value, **location)
        raise ParseError("Expected a statement.", token.line, token.column)

    def _block(self) -> ast.Block:
        start = self._consume(T.LEFT_BRACE, "Expected '{' to begin block.")
        statements: list[ast.Stmt] = []
        while not self._check(T.RIGHT_BRACE) and not self._check(T.EOF):
            statements.append(self._statement())
        self._consume(T.RIGHT_BRACE, "Expected '}' after block.")
        return ast.Block(statements, **self._location(start))

    def _parenthesized(self, keyword: str) -> ast.Expr:
        self._consume(T.LEFT_PAREN, f"Expected '(' after '{keyword}'.")
        expression = self._expression()
        self._consume(T.RIGHT_PAREN, "Expected ')' after expression.")
        return expression

    def _expression(self) -> ast.Expr:
        return self._or()

    def _binary(self, operand: Callable[[], ast.Expr], *operators: T) -> ast.Expr:
        """Build a left-associative chain at one precedence level."""
        expression = operand()
        while self._match(*operators):
            operator = self.tokens[self.current - 1]
            expression = ast.Binary(expression, operator.lexeme, operand(),
                                    **self._location(operator))
        return expression

    def _or(self) -> ast.Expr:
        return self._binary(self._and, T.OR)

    def _and(self) -> ast.Expr:
        return self._binary(self._equality, T.AND)

    def _equality(self) -> ast.Expr:
        return self._binary(self._comparison, T.EQUAL_EQUAL, T.BANG_EQUAL)

    def _comparison(self) -> ast.Expr:
        return self._binary(self._term, T.GREATER, T.GREATER_EQUAL, T.LESS, T.LESS_EQUAL)

    def _term(self) -> ast.Expr:
        return self._binary(self._factor, T.PLUS, T.MINUS)

    def _factor(self) -> ast.Expr:
        return self._binary(self._unary, T.STAR, T.SLASH)

    def _unary(self) -> ast.Expr:
        if self._match(T.BANG, T.MINUS):
            operator = self.tokens[self.current - 1]
            return ast.Unary(operator.lexeme, self._unary(), **self._location(operator))
        return self._primary()

    def _primary(self) -> ast.Expr:
        token = self._peek()
        location = self._location(token)
        if self._match(T.NUMBER):
            return ast.NumberLiteral(token.literal, **location)
        if self._match(T.STRING):
            return ast.StringLiteral(token.literal, **location)
        if self._match(T.TRUE, T.FALSE):
            return ast.BooleanLiteral(token.type == T.TRUE, **location)
        if self._match(T.IDENTIFIER):
            return ast.Variable(token.lexeme, **location)
        if self._match(T.LEFT_PAREN):
            expression = self._expression()
            self._consume(T.RIGHT_PAREN, "Expected ')' after grouped expression.")
            return ast.Grouping(expression, **location)
        raise ParseError("Expected an expression.", token.line, token.column)

