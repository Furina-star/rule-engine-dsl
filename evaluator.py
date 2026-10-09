"""Execute AST statements and expressions in lexical scopes with runtime checks."""

from collections.abc import Callable, Iterable
from math import isfinite
import operator as numeric_ops
from typing import cast

import ast_nodes as nodes
from environment import Environment, Value
from errors import EvaluationError

DEFAULT_LOOP_LIMIT = 10_000
_NUMERIC_OPERATORS = {
    "+": numeric_ops.add,
    "-": numeric_ops.sub,
    "*": numeric_ops.mul,
    ">": numeric_ops.gt,
    ">=": numeric_ops.ge,
    "<": numeric_ops.lt,
    "<=": numeric_ops.le,
}


class Evaluator:
    def __init__(self, environment: Environment | None = None,
                 output: Callable[[str], None] = print,
                 max_loop_iterations: int = DEFAULT_LOOP_LIMIT) -> None:
        if type(max_loop_iterations) is not int or max_loop_iterations < 1:
            raise ValueError("max_loop_iterations must be a positive integer.")
        self.globals = environment if environment is not None else Environment()
        self.environment = self.globals
        self.output = output
        self.max_loop_iterations = max_loop_iterations
        self._statement_handlers: dict[type[nodes.Stmt], Callable[..., None]] = {
            nodes.LetStatement: self._execute_let,
            nodes.Assignment: self._execute_assignment,
            nodes.PrintStatement: self._execute_print,
            nodes.Block: self._execute_block,
            nodes.IfStatement: self._execute_if,
            nodes.WhileStatement: self._execute_while,
            nodes.RuleStatement: self._execute_rule,
        }
        self._expression_handlers: dict[type[nodes.Expr], Callable[..., Value]] = {
            nodes.NumberLiteral: self._evaluate_literal,
            nodes.StringLiteral: self._evaluate_literal,
            nodes.BooleanLiteral: self._evaluate_literal,
            nodes.Variable: self._evaluate_variable,
            nodes.Grouping: self._evaluate_grouping,
            nodes.Unary: self._evaluate_unary,
            nodes.Binary: self._binary,
        }

    def execute(self, statements: Iterable[nodes.Stmt]) -> None:
        # Globals persist across calls; statements run in source order.
        for statement in statements:
            self.execute_statement(statement)

    def execute_statement(self, statement: nodes.Stmt) -> None:
        # Attach the statement location only when an error has none.
        try:
            self._execute_statement(statement)
        except EvaluationError as error:
            if error.line is None:
                raise EvaluationError(error.message, statement.line, statement.column) from error
            raise

    def _execute_statement(self, statement: nodes.Stmt) -> None:
        handler = self._statement_handlers.get(type(statement))
        if handler is None:
            raise EvaluationError(f"Unsupported statement node: {type(statement).__name__}.")
        handler(statement)

    def _execute_let(self, statement: nodes.LetStatement) -> None:
        self.environment.define(statement.name, self.evaluate(statement.initializer))

    def _execute_assignment(self, statement: nodes.Assignment) -> None:
        self.environment.assign(statement.name, self.evaluate(statement.value))

    def _execute_rule(self, statement: nodes.RuleStatement) -> None:
        # Check rules immediately when encountered.
        if self._condition(statement.condition, f"rule '{statement.name}' condition"):
            self.execute_statement(statement.action)

    def _execute_print(self, statement: nodes.PrintStatement) -> None:
        value = self.evaluate(statement.expression)
        try:
            rendered = str(value).lower() if type(value) is bool else str(value)
        except ValueError as error:
            raise EvaluationError("Number is too large to print on this Python runtime.") from error
        self.output(rendered)

    def _execute_block(self, statement: nodes.Block) -> None:
        enclosing = self.environment
        self.environment = Environment(parent=enclosing)
        try:
            self.execute(statement.statements)
        finally:
            # Restore the parent even when a nested statement fails.
            self.environment = enclosing

    def _execute_if(self, statement: nodes.IfStatement) -> None:
        if self._condition(statement.condition, "if condition"):
            self.execute_statement(statement.then_branch)
        elif statement.else_branch is not None:
            self.execute_statement(statement.else_branch)

    def _execute_while(self, statement: nodes.WhileStatement) -> None:
        iterations = 0
        # The body restores the enclosing scope before this next check.
        while self._condition(statement.condition, "while condition"):
            if iterations >= self.max_loop_iterations:
                raise EvaluationError(
                    f"Loop iteration limit ({self.max_loop_iterations}) exceeded."
                )
            iterations += 1
            self.execute_statement(statement.body)

    def _condition(self, expression: nodes.Expr, context: str) -> bool:
        return self._boolean(self.evaluate(expression), context)

    @staticmethod
    def _boolean(value: Value, context: str) -> bool:
        if type(value) is not bool:
            raise EvaluationError(f"{context} requires a boolean; got {type(value).__name__}.")
        return value

    @staticmethod
    def _number(value: Value, operator: str) -> int | float:
        # Python's bool subclasses int; the DSL deliberately keeps them separate.
        if type(value) not in (int, float):
            raise EvaluationError(f"Operator '{operator}' requires numeric operands; "
                                  f"got {type(value).__name__}.")
        return cast(int | float, value)

    def evaluate(self, expression: nodes.Expr) -> Value:
        # Attach the expression location to runtime and overflow errors.
        try:
            # Also check literals and variables supplied by embedded callers.
            return self._finite(self._evaluate(expression))
        except EvaluationError as error:
            if error.line is None:
                raise EvaluationError(error.message, expression.line, expression.column) from error
            raise
        except OverflowError as error:
            raise EvaluationError("Numeric operation overflowed.",
                                  expression.line, expression.column) from error

    def _evaluate(self, expression: nodes.Expr) -> Value:
        handler = self._expression_handlers.get(type(expression))
        if handler is None:
            raise EvaluationError(f"Unsupported expression node: {type(expression).__name__}.")
        return handler(expression)

    @staticmethod
    def _evaluate_literal(expression: nodes.NumberLiteral | nodes.StringLiteral | nodes.BooleanLiteral) -> Value:
        return expression.value

    def _evaluate_variable(self, expression: nodes.Variable) -> Value:
        return self.environment.get(expression.name)

    def _evaluate_grouping(self, expression: nodes.Grouping) -> Value:
        return self.evaluate(expression.expression)

    def _evaluate_unary(self, expression: nodes.Unary) -> Value:
        value = self.evaluate(expression.operand)
        if expression.operator == "!":
            return not self._boolean(value, "Operator '!'")
        if expression.operator == "-":
            return -self._number(value, "-")
        raise EvaluationError(f"Unknown unary operator '{expression.operator}'.")

    @staticmethod
    def _finite(value: Value) -> Value:
        if isinstance(value, float) and not isfinite(value):
            raise EvaluationError("Numeric result is not finite.")
        return value

    def _binary(self, expression: nodes.Binary) -> Value:
        operator = expression.operator
        left = self.evaluate(expression.left)
        if operator in ("&&", "||"):
            return self._logical(expression, left)

        if operator in _NUMERIC_OPERATORS or operator == "/":
            first = self._number(left, operator)
            return self._numeric_binary(first, self.evaluate(expression.right), operator)

        right = self.evaluate(expression.right)
        if operator in ("==", "!="):
            return self._equality(left, right, operator)

        # Unknown operators retain their existing evaluation and validation order.
        return self._numeric_binary(self._number(left, operator), right, operator)

    def _logical(self, expression: nodes.Binary, left: Value) -> bool:
        operator = expression.operator
        boolean = self._boolean(left, f"Operator '{operator}'")
        if operator == "&&" and not boolean:
            return False
        if operator == "||" and boolean:
            return True
        return self._boolean(self.evaluate(expression.right), f"Operator '{operator}'")

    @staticmethod
    def _equality(left: Value, right: Value, operator: str) -> bool:
        both_numbers = type(left) in (int, float) and type(right) in (int, float)
        equal = (both_numbers or type(left) is type(right)) and left == right
        return equal if operator == "==" else not equal

    def _numeric_binary(self, first: int | float, right: Value, operator: str) -> Value:
        second = self._number(right, operator)
        if operator == "/":
            if second == 0:
                raise EvaluationError("Division by zero.")
            return first / second
        operation = _NUMERIC_OPERATORS.get(operator)
        if operation is None:
            raise EvaluationError(f"Unknown binary operator '{operator}'.")
        return operation(first, second)
