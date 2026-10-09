"""The syntax tree: data only, with source locations for runtime diagnostics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(kw_only=True)
class Node:
    line: int = 1
    column: int = 1


class Expr(Node):
    """Base type for expressions, which produce values."""


@dataclass
class NumberLiteral(Expr):
    value: int | float


@dataclass
class StringLiteral(Expr):
    value: str


@dataclass
class BooleanLiteral(Expr):
    value: bool


@dataclass
class Variable(Expr):
    name: str


@dataclass
class Unary(Expr):
    operator: str
    operand: Expr


@dataclass
class Binary(Expr):
    left: Expr
    operator: str
    right: Expr


@dataclass
class Grouping(Expr):
    expression: Expr


class Stmt(Node):
    """Base type for statements, which change state or control execution."""


@dataclass
class LetStatement(Stmt):
    name: str
    initializer: Expr


@dataclass
class Assignment(Stmt):
    name: str
    value: Expr


@dataclass
class PrintStatement(Stmt):
    expression: Expr


@dataclass
class Block(Stmt):
    statements: list[Stmt]


@dataclass
class IfStatement(Stmt):
    condition: Expr
    then_branch: Block
    else_branch: Block | None = None


@dataclass
class WhileStatement(Stmt):
    condition: Expr
    body: Block


@dataclass
class RuleStatement(Stmt):
    name: str
    condition: Expr
    action: Block

