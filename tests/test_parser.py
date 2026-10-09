import unittest

import ast_nodes as ast
from errors import ParseError
from lexer import Lexer
from parser import Parser


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


class ParserTests(unittest.TestCase):
    def test_variable_declaration_and_assignment(self):
        declaration, assignment = parse("let x = 5; x = 6;")
        self.assertIsInstance(declaration, ast.LetStatement)
        self.assertEqual(declaration.name, "x")
        self.assertEqual(declaration.initializer.value, 5)
        self.assertIsInstance(assignment, ast.Assignment)
        self.assertEqual(assignment.value.value, 6)

    def test_literal_types_and_variable(self):
        statements = parse('print(1.5); print("hello"); print(true); print(false); print(x);')
        expected = (ast.NumberLiteral, ast.StringLiteral, ast.BooleanLiteral,
                    ast.BooleanLiteral, ast.Variable)
        for statement, kind in zip(statements, expected):
            self.assertIsInstance(statement, ast.PrintStatement)
            self.assertIsInstance(statement.expression, kind)

    def test_all_precedence_levels(self):
        expression = parse("print(true || false && 1 == 2 < 3 + 4 * -5);")[0].expression
        self.assertEqual(expression.operator, "||")
        expression = expression.right
        self.assertEqual(expression.operator, "&&")
        expression = expression.right
        self.assertEqual(expression.operator, "==")
        expression = expression.right
        self.assertEqual(expression.operator, "<")
        expression = expression.right
        self.assertEqual(expression.operator, "+")
        expression = expression.right
        self.assertEqual(expression.operator, "*")
        self.assertIsInstance(expression.right, ast.Unary)
        self.assertEqual(expression.right.operator, "-")

    def test_grouping_and_unary(self):
        expression = parse("print(-(1 + 2) * 3);")[0].expression
        self.assertEqual(expression.operator, "*")
        self.assertIsInstance(expression.left.operand, ast.Grouping)
        self.assertEqual(expression.left.operand.expression.operator, "+")
        unary = parse("print(!!false);")[0].expression
        self.assertEqual(unary.operator, "!")
        self.assertEqual(unary.operand.operator, "!")

    def test_left_associativity(self):
        for source, operator in (("10 - 3 - 2", "-"), ("8 / 4 / 2", "/")):
            with self.subTest(source=source):
                expression = parse(f"print({source});")[0].expression
                self.assertEqual(expression.operator, operator)
                self.assertEqual(expression.left.operator, operator)
                self.assertIsInstance(expression.right, ast.NumberLiteral)

    def test_if_else(self):
        statement = parse("if (true) { print(1); } else { print(2); }")[0]
        self.assertIsInstance(statement, ast.IfStatement)
        self.assertIsInstance(statement.then_branch, ast.Block)
        self.assertIsInstance(statement.else_branch, ast.Block)
        self.assertEqual(statement.else_branch.statements[0].expression.value, 2)

    def test_if_without_else(self):
        statement = parse("if (false) {}")[0]
        self.assertIsNone(statement.else_branch)
        self.assertEqual(statement.then_branch.statements, [])

    def test_while(self):
        statement = parse("while (x < 3) { x = x + 1; }")[0]
        self.assertIsInstance(statement, ast.WhileStatement)
        self.assertEqual(statement.condition.operator, "<")
        self.assertIsInstance(statement.body.statements[0], ast.Assignment)

    def test_rule(self):
        statement = parse('rule passing when (score >= 75) { print("pass"); }')[0]
        self.assertIsInstance(statement, ast.RuleStatement)
        self.assertEqual(statement.name, "passing")
        self.assertEqual(statement.condition.operator, ">=")
        self.assertIsInstance(statement.action, ast.Block)

    def test_nested_blocks_and_conditions(self):
        statement = parse("{ { if (true) { if (false) {} else {} } } }")[0]
        inner = statement.statements[0].statements[0]
        self.assertIsInstance(inner, ast.IfStatement)
        self.assertIsInstance(inner.then_branch.statements[0], ast.IfStatement)

    def test_source_locations(self):
        statement = parse("\n  print(missing + 1);")[0]
        self.assertEqual((statement.line, statement.column), (2, 3))
        self.assertEqual((statement.expression.line, statement.expression.column), (2, 17))
        self.assertEqual(statement.expression.left.column, 9)

    def test_empty_program(self):
        self.assertEqual(parse("// nothing"), [])

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


if __name__ == "__main__":
    unittest.main()

