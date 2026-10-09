"""Recursive-descent statements and one expression method per precedence level."""

from collections.abc import Callable
from typing import cast

import ast_nodes as nodes
from errors import ParseError
from lexer import Token, TokenType


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        if not tokens or tokens[-1].type != TokenType.EOF:
            raise ParseError("Token stream must end with EOF.")
        if any(token.type == TokenType.EOF for token in tokens[:-1]):
            raise ParseError("Unexpected EOF inside token stream.")
        self.tokens = tokens
        self.current = 0

    def _peek(self) -> Token:
        return self.tokens[self.current]

    def _check(self, kind: TokenType) -> bool:
        return self._peek().type == kind

    def _match(self, *kinds: TokenType) -> bool:
        if self._peek().type in kinds:
            self.current += 1
            return True
        return False

    def _consume(self, kind: TokenType, message: str) -> Token:
        token = self._peek()
        if token.type != kind:
            found = repr(token.lexeme) if token.type != TokenType.EOF else "end of file"
            raise ParseError(f"{message} Found {found}.", token.line, token.column)
        self.current += 1
        return token

    @staticmethod
    def _location(token: Token) -> dict[str, int]:
        return {"line": token.line, "column": token.column}

    def parse(self) -> list[nodes.Stmt]:
        statements: list[nodes.Stmt] = []
        while not self._check(TokenType.EOF):
            statements.append(self._statement())
        return statements

    def _statement(self) -> nodes.Stmt:
        token = self._peek()
        location = self._location(token)
        if self._match(TokenType.LET):
            name = self._consume(TokenType.IDENTIFIER, "Expected variable name after 'let'.")
            self._consume(TokenType.EQUAL, "Expected '=' after variable name.")
            value = self._expression()
            self._consume(TokenType.SEMICOLON, "Expected ';' after declaration.")
            return nodes.LetStatement(name.lexeme, value, **location)
        if self._match(TokenType.PRINT):
            value = self._parenthesized("print")
            self._consume(TokenType.SEMICOLON, "Expected ';' after print statement.")
            return nodes.PrintStatement(value, **location)
        if self._match(TokenType.IF):
            return self._if_statement(token)
        if self._match(TokenType.WHILE):
            condition = self._parenthesized("while")
            return nodes.WhileStatement(condition, self._block(), **location)
        if self._match(TokenType.RULE):
            name = self._consume(TokenType.IDENTIFIER, "Expected rule name.")
            self._consume(TokenType.WHEN, "Expected 'when' after rule name.")
            condition = self._parenthesized("when")
            return nodes.RuleStatement(name.lexeme, condition, self._block(), **location)
        if self._check(TokenType.LEFT_BRACE):
            return self._block()
        if self._match(TokenType.IDENTIFIER):
            self._consume(TokenType.EQUAL, "Expected '=' after assignment target.")
            value = self._expression()
            self._consume(TokenType.SEMICOLON, "Expected ';' after assignment.")
            return nodes.Assignment(token.lexeme, value, **location)
        raise ParseError("Expected a statement.", token.line, token.column)

    def _if_statement(self, start: Token) -> nodes.IfStatement:
        condition = self._parenthesized("if")
        then_branch = self._block()
        else_branch = None
        if self._match(TokenType.ELSE):
            if self._match(TokenType.IF):
                else_branch = self._if_statement(self.tokens[self.current - 1])
            else:
                else_branch = self._block()
        return nodes.IfStatement(condition, then_branch, else_branch, **self._location(start))

    def _block(self) -> nodes.Block:
        start = self._consume(TokenType.LEFT_BRACE, "Expected '{' to begin block.")
        statements: list[nodes.Stmt] = []
        while not self._check(TokenType.RIGHT_BRACE) and not self._check(TokenType.EOF):
            statements.append(self._statement())
        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after block.")
        return nodes.Block(statements, **self._location(start))

    def _parenthesized(self, keyword: str) -> nodes.Expr:
        self._consume(TokenType.LEFT_PAREN, f"Expected '(' after '{keyword}'.")
        expression = self._expression()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' after expression.")
        return expression

    def _expression(self) -> nodes.Expr:
        return self._or()

    def _binary(self, operand: Callable[[], nodes.Expr], *operators: TokenType) -> nodes.Expr:
        """Build a left-associative chain at one precedence level."""
        expression = operand()
        while self._match(*operators):
            operator = self.tokens[self.current - 1]
            expression = nodes.Binary(expression, operator.lexeme, operand(),
                                    **self._location(operator))
        return expression

    def _or(self) -> nodes.Expr:
        return self._binary(self._and, TokenType.OR)

    def _and(self) -> nodes.Expr:
        return self._binary(self._equality, TokenType.AND)

    def _equality(self) -> nodes.Expr:
        return self._binary(self._comparison, TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL)

    def _comparison(self) -> nodes.Expr:
        return self._binary(self._term, TokenType.GREATER, TokenType.GREATER_EQUAL,
                            TokenType.LESS, TokenType.LESS_EQUAL)

    def _term(self) -> nodes.Expr:
        return self._binary(self._factor, TokenType.PLUS, TokenType.MINUS)

    def _factor(self) -> nodes.Expr:
        return self._binary(self._unary, TokenType.STAR, TokenType.SLASH)

    def _unary(self) -> nodes.Expr:
        if self._match(TokenType.BANG, TokenType.MINUS):
            operator = self.tokens[self.current - 1]
            return nodes.Unary(operator.lexeme, self._unary(), **self._location(operator))
        return self._primary()

    def _primary(self) -> nodes.Expr:
        token = self._peek()
        location = self._location(token)
        # The lexer guarantees that each literal matches its token type.
        if self._match(TokenType.NUMBER):
            return nodes.NumberLiteral(cast(int | float, token.literal), **location)
        if self._match(TokenType.STRING):
            return nodes.StringLiteral(cast(str, token.literal), **location)
        if self._match(TokenType.TRUE, TokenType.FALSE):
            return nodes.BooleanLiteral(token.type == TokenType.TRUE, **location)
        if self._match(TokenType.IDENTIFIER):
            return nodes.Variable(token.lexeme, **location)
        if self._match(TokenType.LEFT_PAREN):
            expression = self._expression()
            self._consume(TokenType.RIGHT_PAREN, "Expected ')' after grouped expression.")
            return nodes.Grouping(expression, **location)
        raise ParseError("Expected an expression.", token.line, token.column)
