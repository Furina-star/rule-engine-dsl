"""Test AST construction, operator precedence, control flow, and syntax errors."""

import unittest
from typing import TypeVar

import ast_nodes as ast
from errors import ParseError
from lexer import Lexer
from parser import Parser

NodeType = TypeVar("NodeType", bound=ast.Node)


def parse(source: str) -> list[ast.Stmt]:
    return Parser(Lexer(source).tokenize()).parse()


class ParserTests(unittest.TestCase):
    def assert_node(self, node: ast.Node | None, kind: type[NodeType]) -> NodeType:
        # Verify the node type before inspecting its fields.
        self.assertIsInstance(node, kind)
        return node

    def print_expression(self, source: str) -> ast.Expr:
        statement = self.assert_node(parse(source)[0], ast.PrintStatement)
        return statement.expression

    def test_variable_declaration_and_assignment(self):
        declaration, assignment = parse("let x = 5; x = 6;")
        declaration = self.assert_node(declaration, ast.LetStatement)
        self.assertEqual("x", declaration.name)
        initializer = self.assert_node(declaration.initializer, ast.NumberLiteral)
        self.assertEqual(5, initializer.value)
        assignment = self.assert_node(assignment, ast.Assignment)
        value = self.assert_node(assignment.value, ast.NumberLiteral)
        self.assertEqual(6, value.value)

    def test_literal_types_and_variable(self):
        statements = parse('print(1.5); print("hello"); print(true); print(false); print(x);')
        expected = (ast.NumberLiteral, ast.StringLiteral, ast.BooleanLiteral,
                    ast.BooleanLiteral, ast.Variable)
        for statement, kind in zip(statements, expected):
            statement = self.assert_node(statement, ast.PrintStatement)
            self.assertIsInstance(statement.expression, kind)

    def test_all_precedence_levels(self):
        expression = self.print_expression("print(true || false && 1 == 2 < 3 + 4 * -5);")
        for operator in ("||", "&&", "==", "<", "+", "*"):
            with self.subTest(operator=operator):
                binary = self.assert_node(expression, ast.Binary)
                self.assertEqual(operator, binary.operator)
                expression = binary.right
        unary = self.assert_node(expression, ast.Unary)
        self.assertEqual("-", unary.operator)

    def test_grouping_and_unary(self):
        expression = self.assert_node(self.print_expression("print(-(1 + 2) * 3);"), ast.Binary)
        self.assertEqual("*", expression.operator)
        left = self.assert_node(expression.left, ast.Unary)
        grouping = self.assert_node(left.operand, ast.Grouping)
        grouped = self.assert_node(grouping.expression, ast.Binary)
        self.assertEqual("+", grouped.operator)
        unary = self.assert_node(self.print_expression("print(!!false);"), ast.Unary)
        self.assertEqual("!", unary.operator)
        operand = self.assert_node(unary.operand, ast.Unary)
        self.assertEqual("!", operand.operator)

    def test_left_associativity(self):
        for source, operator in (("10 - 3 - 2", "-"), ("8 / 4 / 2", "/")):
            with self.subTest(source=source):
                expression = self.assert_node(self.print_expression(f"print({source});"), ast.Binary)
                self.assertEqual(operator, expression.operator)
                left = self.assert_node(expression.left, ast.Binary)
                self.assertEqual(operator, left.operator)
                self.assertIsInstance(expression.right, ast.NumberLiteral)

    def test_if_else(self):
        statement = parse("if (true) { print(1); } else { print(2); }")[0]
        statement = self.assert_node(statement, ast.IfStatement)
        self.assertIsInstance(statement.then_branch, ast.Block)
        else_branch = self.assert_node(statement.else_branch, ast.Block)
        printed = self.assert_node(else_branch.statements[0], ast.PrintStatement)
        value = self.assert_node(printed.expression, ast.NumberLiteral)
        self.assertEqual(2, value.value)

    def test_if_without_else(self):
        statement = self.assert_node(parse("if (false) {}")[0], ast.IfStatement)
        self.assertIsNone(statement.else_branch)
        self.assertEqual([], statement.then_branch.statements)

    def test_while(self):
        statement = parse("while (x < 3) { x = x + 1; }")[0]
        statement = self.assert_node(statement, ast.WhileStatement)
        condition = self.assert_node(statement.condition, ast.Binary)
        self.assertEqual("<", condition.operator)
        self.assertIsInstance(statement.body.statements[0], ast.Assignment)

    def test_rule(self):
        statement = parse('rule passing when (score >= 75) { print("pass"); }')[0]
        statement = self.assert_node(statement, ast.RuleStatement)
        self.assertEqual("passing", statement.name)
        condition = self.assert_node(statement.condition, ast.Binary)
        self.assertEqual(">=", condition.operator)
        self.assertIsInstance(statement.action, ast.Block)

    def test_nested_blocks_and_conditions(self):
        statement = parse("{ { if (true) { if (false) {} else {} } } }")[0]
        statement = self.assert_node(statement, ast.Block)
        block = self.assert_node(statement.statements[0], ast.Block)
        inner = self.assert_node(block.statements[0], ast.IfStatement)
        self.assertIsInstance(inner.then_branch.statements[0], ast.IfStatement)

    def test_source_locations(self):
        statement = self.assert_node(parse("\n  print(missing + 1);")[0], ast.PrintStatement)
        self.assertEqual((2, 3), (statement.line, statement.column))
        expression = self.assert_node(statement.expression, ast.Binary)
        self.assertEqual((2, 17), (expression.line, expression.column))
        self.assertEqual(9, expression.left.column)

    def test_empty_program(self):
        self.assertEqual([], parse("// nothing"))

    def test_malformed_statements(self):
        invalid = (
            "let x = 1", "x = 1", "print(1)", "let = 1;", "let x 1;",
            "print 1;", "print();", "print(1;", "if true {}", "if (true) print(1);",
            "if (true) {} else print(1);", "while (true) {", "rule when (true) {}",
            "rule r (true) {}", "rule r when true {}", "{ let x = 1;", "}",
            "else {}", "let x = ;", "let x = 1 + ;", "1 + 2;", "print((1);",
            "if (true) {};", "print(x = 2);", "let x = 1e3;",
        )
        for source in invalid:
            with self.subTest(source=source):
                with self.assertRaises(ParseError) as caught:
                    parse(source)
                self.assertIsNotNone(caught.exception.line)
                self.assertIsNotNone(caught.exception.column)

    def test_invalid_token_stream(self):
        for tokens in ([], Lexer("x").tokenize()[:-1], Lexer("").tokenize() * 2):
            with self.subTest(tokens=tokens):
                with self.assertRaises(ParseError):
                    Parser(tokens)

    def test_else_if_chain_reuses_if_nodes_and_locations(self):
        statement = self.assert_node(parse(
            "if (false) {}\n  else if (false) {} else if (true) {} else {}"
        )[0], ast.IfStatement)
        second = self.assert_node(statement.else_branch, ast.IfStatement)
        third = self.assert_node(second.else_branch, ast.IfStatement)
        self.assertIsInstance(third.else_branch, ast.Block)
        self.assertEqual((1, 1), (statement.line, statement.column))
        self.assertEqual((2, 8), (second.line, second.column))
        self.assertEqual((2, 27), (third.line, third.column))

    def test_else_if_inside_block_keeps_outer_else(self):
        statement = self.assert_node(parse(
            "if (true) { if (false) {} else if (true) {} } else {}"
        )[0], ast.IfStatement)
        inner = self.assert_node(statement.then_branch.statements[0], ast.IfStatement)
        self.assertIsInstance(inner.else_branch, ast.IfStatement)
        self.assertIsInstance(statement.else_branch, ast.Block)

    def test_malformed_else_if_requires_conditions_and_braces(self):
        sources = (
            "if (false) {} else if true {}",
            "if (false) {} else if () {}",
            "if (false) {} else if (true {}",
            "if (false) {} else if (true) print(1);",
            "if (false) {} else if (true) {",
            "if (false) {} else if (true &&) {}",
            "if (false) {} else if (false) {} else print(1);",
            "if (false) {} else print(1);",
            "if (false) {} else while (true) {}",
            "if (false) {} else { } else if (true) {}",
        )
        for source in sources:
            with self.subTest(source=source):
                parser = Parser(Lexer(source).tokenize())
                with self.assertRaises(ParseError) as caught:
                    parser.parse()
                self.assertIsNotNone(caught.exception.line)
                self.assertIsNotNone(caught.exception.column)


if __name__ == "__main__":
    unittest.main()
