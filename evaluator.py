"""A tree-walk interpreter: recursively evaluate AST nodes in lexical scopes."""

from collections.abc import Callable, Iterable
from math import isfinite
import operator as numeric_ops
from typing import cast

import ast_nodes as ast
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

    def execute(self, statements: Iterable[ast.Stmt]) -> None:
        """Execute in order, retaining globals even across calls to execute()."""
        for statement in statements:
            self.execute_statement(statement)

    def execute_statement(self, statement: ast.Stmt) -> None:
        try:
            self._execute_statement(statement)
        except EvaluationError as error:
            if error.line is None:
                raise EvaluationError(error.message, statement.line, statement.column) from error
            raise

    def _execute_statement(self, statement: ast.Stmt) -> None:
        if isinstance(statement, ast.LetStatement):
            self.environment.define(statement.name, self.evaluate(statement.initializer))
        elif isinstance(statement, ast.Assignment):
            self.environment.assign(statement.name, self.evaluate(statement.value))
        elif isinstance(statement, ast.PrintStatement):
            self._execute_print(statement)
        elif isinstance(statement, ast.Block):
            self._execute_block(statement)
        elif isinstance(statement, ast.IfStatement):
            self._execute_if(statement)
        elif isinstance(statement, ast.WhileStatement):
            self._execute_while(statement)
        elif isinstance(statement, ast.RuleStatement):
            if self._condition(statement.condition, f"rule '{statement.name}' condition"):
                self.execute_statement(statement.action)
        else:
            raise EvaluationError(f"Unsupported statement node: {type(statement).__name__}.")

    def _execute_print(self, statement: ast.PrintStatement) -> None:
        value = self.evaluate(statement.expression)
        try:
            rendered = str(value).lower() if type(value) is bool else str(value)
        except ValueError as error:
            raise EvaluationError("Number is too large to print on this Python runtime.") from error
        self.output(rendered)

    def _execute_block(self, statement: ast.Block) -> None:
        enclosing = self.environment
        self.environment = Environment(parent=enclosing)
        try:
            self.execute(statement.statements)
        finally:
            # Restore the parent even when a nested statement fails.
            self.environment = enclosing

    def _execute_if(self, statement: ast.IfStatement) -> None:
        if self._condition(statement.condition, "if condition"):
            self.execute_statement(statement.then_branch)
        elif statement.else_branch is not None:
            self.execute_statement(statement.else_branch)

    def _execute_while(self, statement: ast.WhileStatement) -> None:
        iterations = 0
        # The body restores the enclosing scope before this next check.
        while self._condition(statement.condition, "while condition"):
            if iterations >= self.max_loop_iterations:
                raise EvaluationError(
                    f"Loop iteration limit ({self.max_loop_iterations}) exceeded."
                )
            iterations += 1
            self.execute_statement(statement.body)

    def _condition(self, expression: ast.Expr, context: str) -> bool:
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

    def evaluate(self, expression: ast.Expr) -> Value:
        try:
            result = self._evaluate(expression)
            if isinstance(result, float) and not isfinite(result):
                raise EvaluationError("Numeric result is not finite.")
            return result
        except EvaluationError as error:
            if error.line is None:
                raise EvaluationError(error.message, expression.line, expression.column) from error
            raise
        except OverflowError as error:
            raise EvaluationError("Numeric operation overflowed.",
                                  expression.line, expression.column) from error

    def _evaluate(self, expression: ast.Expr) -> Value:
        if isinstance(expression, (ast.NumberLiteral, ast.StringLiteral, ast.BooleanLiteral)):
            return expression.value
        if isinstance(expression, ast.Variable):
            return self.environment.get(expression.name)
        if isinstance(expression, ast.Grouping):
            return self.evaluate(expression.expression)
        if isinstance(expression, ast.Unary):
            value = self.evaluate(expression.operand)
            if expression.operator == "!":
                return not self._boolean(value, "Operator '!'")
            if expression.operator == "-":
                return -self._number(value, "-")
            raise EvaluationError(f"Unknown unary operator '{expression.operator}'.")
        if isinstance(expression, ast.Binary):
            return self._binary(expression)
        raise EvaluationError(f"Unsupported expression node: {type(expression).__name__}.")

    def _binary(self, expression: ast.Binary) -> Value:
        operator = expression.operator
        left = self.evaluate(expression.left)
        if operator in ("&&", "||"):
            return self._logical(expression, left)

        right = self.evaluate(expression.right)
        if operator in ("==", "!="):
            return self._equality(left, right, operator)

        return self._numeric_binary(left, right, operator)

    def _logical(self, expression: ast.Binary, left: Value) -> bool:
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

    def _numeric_binary(self, left: Value, right: Value, operator: str) -> Value:
        first = self._number(left, operator)
        second = self._number(right, operator)
        if operator == "/":
            if second == 0:
                raise EvaluationError("Division by zero.")
            return first / second
        operation = _NUMERIC_OPERATORS.get(operator)
        if operation is None:
            raise EvaluationError(f"Unknown binary operator '{operator}'.")
        return operation(first, second)
