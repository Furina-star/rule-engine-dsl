"""Lexical scopes implemented with recursive parent-pointer traversal."""

from __future__ import annotations

from typing import TypeAlias

from errors import EvaluationError

Value: TypeAlias = int | float | str | bool


class Environment:
    """A local binding dictionary and an optional enclosing environment."""

    def __init__(self, parent: Environment | None = None) -> None:
        self.parent = parent
        self.values: dict[str, Value] = {}

    def define(self, name: str, value: Value) -> None:
        """Create or replace a binding in this scope only."""
        self.values[name] = value

    def get(self, name: str) -> Value:
        """Recursively read the nearest binding, starting in this scope."""
        if name in self.values:
            return self.values[name]
        if self.parent is not None:
            return self.parent.get(name)
        raise EvaluationError(f"Undefined variable '{name}'.")

    def assign(self, name: str, value: Value) -> None:
        """Recursively update the nearest existing binding; never create one."""
        if name in self.values:
            self.values[name] = value
            return
        if self.parent is not None:
            self.parent.assign(name, value)
            return
        raise EvaluationError(f"Cannot assign undefined variable '{name}'.")

