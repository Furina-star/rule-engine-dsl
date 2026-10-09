import unittest

from environment import Environment
from errors import EvaluationError
from evaluator import Evaluator
from lexer import Lexer
from parser import Parser


def program(source):
    return Parser(Lexer(source).tokenize()).parse()


class EvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.output = []
        self.evaluator = Evaluator(output=self.output.append)

    def run_source(self, source):
        self.evaluator.execute(program(source))
        return self.output

    def test_arithmetic_grouping_unary_and_associativity(self):
        self.assertEqual(self.run_source(
            "print(2 + 3 * 4); print((2 + 3) * 4); print(10 - 3 - 2);"
            "print(8 / 4 / 2); print(-2 * -3); print(1.5 + 2); print(7 / 2);"
        ), ["14", "20", "5", "1.0", "6", "3.5", "3.5"])

    def test_variables_assignments_and_persistent_globals(self):
        self.run_source("let x = 3; x = x + 4;")
        self.run_source("print(x); let y = x * 2; print(y);")
        self.assertEqual(self.output, ["7", "14"])
        self.assertEqual(self.evaluator.globals.values, {"x": 7, "y": 14})

    def test_supplied_global_environment(self):
        environment = Environment()
        environment.define("seed", 10)
        evaluator = Evaluator(environment, output=self.output.append)
        evaluator.execute(program("seed = seed + 1; print(seed);"))
        self.assertIs(evaluator.globals, environment)
        self.assertEqual(environment.get("seed"), 11)
        self.assertEqual(self.output, ["11"])

    def test_comparisons(self):
        self.assertEqual(self.run_source(
            "print(3 > 2); print(3 >= 3); print(2 < 3); print(2 <= 2);"
            "print(2 > 3); print(2 >= 3); print(3 < 2); print(3 <= 2);"
        ), ["true"] * 4 + ["false"] * 4)

    def test_equality_and_type_separation(self):
        self.assertEqual(self.run_source(
            'print(1 == 1.0); print(1 != 2); print("a" == "a"); print("a" != "b");'
            'print(true == true); print(true == 1); print(false == 0); print("1" == 1);'
            'print(true != 1); print(false != false);'
        ), ["true"] * 5 + ["false"] * 3 + ["true", "false"])

    def test_boolean_operations(self):
        self.assertEqual(self.run_source(
            "print(!true); print(!!true); print(true && true); print(true && false);"
            "print(false || true); print(false || false); print(true || false && false);"
        ), ["false", "true", "true", "false", "true", "false", "true"])

    def test_short_circuit_skips_undefined_and_division(self):
        self.assertEqual(self.run_source(
            "print(false && missing); print(true || missing);"
            "print(false && (1 / 0 > 0)); print(true || (1 / 0 > 0));"
        ), ["false", "true", "false", "true"])

    def test_logical_right_operand_evaluated_when_needed(self):
        for source in ("print(true && missing);", "print(false || missing);"):
            with self.subTest(source=source):
                with self.assertRaisesRegex(EvaluationError, "Undefined variable"):
                    self.run_source(source)

    def test_strict_boolean_operands_and_conditions(self):
        for source in (
            "if (1) {}", 'if ("") {}', "while (0) {}", "rule r when (1) {}",
            "print(!1);", "print(1 && true);", "print(0 || false);",
            "print(true && 1);", 'print(false || "yes");',
        ):
            with self.subTest(source=source):
                with self.assertRaisesRegex(EvaluationError, "requires a boolean"):
                    self.run_source(source)

    def test_skipped_boolean_operand_is_not_type_checked(self):
        self.assertEqual(self.run_source("print(false && 1); print(true || 0);"),
                         ["false", "true"])

    def test_true_false_branches_and_skipped_errors(self):
        self.assertEqual(self.run_source(
            'if (true) { print("then"); } else { print(missing); }'
            'if (false) { print(missing); } else { print("else"); }'
            'if (false) { print(missing); }'
        ), ["then", "else"])

    def test_nested_conditions(self):
        self.assertEqual(self.run_source(
            'let x = 5; if (x > 0) { if (x > 10) { print("large"); }'
            'else { if (x == 5 && !(x < 0)) { print("five"); } } }'
        ), ["five"])

    def test_while_termination_and_outer_mutation(self):
        self.assertEqual(self.run_source(
            "let x = 0; while (x < 3) { print(x); x = x + 1; } print(x);"
        ), ["0", "1", "2", "3"])

    def test_false_while_never_enters_body(self):
        self.assertEqual(self.run_source("while (false) { print(missing); }"), [])

    def test_nested_loops(self):
        self.assertEqual(self.run_source(
            "let i = 0; let count = 0; while (i < 3) { let j = 0;"
            "while (j < 2) { count = count + 1; j = j + 1; } i = i + 1; } print(count);"
        ), ["6"])
        self.assertEqual(self.evaluator.globals.values, {"i": 3, "count": 6})

    def test_loop_body_has_fresh_environment_each_iteration(self):
        # 'once' must disappear after the first iteration; otherwise this would print 99.
        with self.assertRaisesRegex(EvaluationError, "Undefined variable 'once'"):
            self.run_source(
                "let i = 0; while (i < 2) { if (i == 1) { print(once); }"
                "let once = 99; i = i + 1; }"
            )
        self.assertEqual(self.output, [])
        self.assertIs(self.evaluator.environment, self.evaluator.globals)

    def test_condition_runs_in_enclosing_scope(self):
        # A body-local variable cannot replace the enclosing flag in the next check.
        evaluator = Evaluator(max_loop_iterations=2)
        with self.assertRaisesRegex(EvaluationError, "Loop iteration limit"):
            evaluator.execute(program("let flag = true; while (flag) { let flag = false; }"))
        self.assertIs(evaluator.globals.get("flag"), True)

    def test_condition_is_type_checked_each_iteration(self):
        with self.assertRaisesRegex(EvaluationError, "while condition requires a boolean"):
            self.run_source("let flag = true; while (flag) { flag = 0; }")

    def test_scope_isolation_for_every_block_kind(self):
        for source in (
            "{ let local = 1; } print(local);",
            "if (true) { let local = 1; } print(local);",
            "if (false) {} else { let local = 1; } print(local);",
            "rule r when (true) { let local = 1; } print(local);",
            "let i = 0; while (i < 1) { let local = 1; i = i + 1; } print(local);",
        ):
            with self.subTest(source=source):
                with self.assertRaisesRegex(EvaluationError, "Undefined variable 'local'"):
                    self.run_source(source)

    def test_shadowing_and_nearest_parent_mutation(self):
        self.assertEqual(self.run_source(
            "let x = 1; { let x = 2; { x = 3; print(x); } print(x); } print(x);"
        ), ["3", "3", "1"])

    def test_recursive_parent_lookup_and_mutation(self):
        self.assertEqual(self.run_source(
            "let x = 1; { { { print(x); x = 9; } } } print(x);"
        ), ["1", "9"])

    def test_initializer_reads_outer_before_shadowing(self):
        self.assertEqual(self.run_source("let x = 2; { let x = x + 1; print(x); } print(x);"),
                         ["3", "2"])

    def test_true_and_false_rules(self):
        self.assertEqual(self.run_source(
            'let count = 0; rule yes when (true) { count = count + 1; print("fire"); }'
            'rule no when (false) { print(missing); } print(count);'
        ), ["fire", "1"])
        self.assertNotIn("yes", self.evaluator.globals.values)

    def test_rules_are_immediate_and_not_reactive(self):
        self.assertEqual(self.run_source(
            'let ready = false; rule later when (ready) { print("unexpected"); }'
            'ready = true; print("done");'
        ), ["done"])

    def test_rule_fires_once_per_encounter_in_loop(self):
        self.assertEqual(self.run_source(
            "let i = 0; let fires = 0; while (i < 3) {"
            "rule r when (i >= 1) { fires = fires + 1; } i = i + 1; } print(fires);"
        ), ["2"])

    def test_runtime_undefined_variable_and_assignment_errors(self):
        for source in ("print(missing);", "missing = 1;", "let x = x;"):
            with self.subTest(source=source):
                with self.assertRaisesRegex(EvaluationError, "[Uu]ndefined variable"):
                    self.run_source(source)

    def test_division_by_zero(self):
        for source in ("print(1 / 0);", "print(1 / -0.0);"):
            with self.subTest(source=source):
                with self.assertRaisesRegex(EvaluationError, "Division by zero"):
                    self.run_source(source)

    def test_numeric_type_errors(self):
        for expression in ('true + 1', '1 - false', '"a" * 2', '1 / true',
                           '"a" + "b"', '"a" < "b"', '1 >= false', '-true'):
            with self.subTest(expression=expression):
                with self.assertRaisesRegex(EvaluationError, "requires numeric operands"):
                    self.run_source(f"print({expression});")

    def test_nonfinite_result_and_overflow(self):
        with self.assertRaisesRegex(EvaluationError, "not finite"):
            self.run_source("print(" + "9" * 308 + ".0 * 2);")
        with self.assertRaisesRegex(EvaluationError, "overflowed"):
            self.run_source("print(" + "9" * 400 + " / 1);")

    def test_runtime_source_locations(self):
        for source, location in (("\n  print(missing);", (2, 9)),
                                 ("\n  print(1 / 0);", (2, 11)),
                                 ("\n  missing = 1;", (2, 3))):
            with self.subTest(source=source):
                with self.assertRaises(EvaluationError) as caught:
                    self.run_source(source)
                self.assertEqual((caught.exception.line, caught.exception.column), location)

    def test_environment_restored_after_nested_error(self):
        with self.assertRaises(EvaluationError):
            self.run_source("let x = 1; { let x = 2; { print(missing); } }")
        self.assertIs(self.evaluator.environment, self.evaluator.globals)
        self.run_source("print(x);")
        self.assertEqual(self.output, ["1"])

    def test_loop_safety_limit(self):
        evaluator = Evaluator(max_loop_iterations=3)
        with self.assertRaisesRegex(EvaluationError, r"Loop iteration limit \(3\) exceeded"):
            evaluator.execute(program("let count = 0; while (true) { count = count + 1; }"))
        self.assertEqual(evaluator.globals.get("count"), 3)
        self.assertIs(evaluator.environment, evaluator.globals)

    def test_exact_iteration_limit_allowed(self):
        evaluator = Evaluator(max_loop_iterations=3)
        evaluator.execute(program("let x = 0; while (x < 3) { x = x + 1; }"))
        self.assertEqual(evaluator.globals.get("x"), 3)

    def test_limit_resets_for_each_loop_encounter(self):
        evaluator = Evaluator(max_loop_iterations=2)
        evaluator.execute(program(
            "let i = 0; let count = 0; while (i < 2) { let j = 0;"
            "while (j < 2) { count = count + 1; j = j + 1; } i = i + 1; }"
        ))
        self.assertEqual(evaluator.globals.get("count"), 4)

    def test_invalid_loop_limit(self):
        for limit in (0, -1, True, 1.5, "2"):
            with self.subTest(limit=limit):
                with self.assertRaisesRegex(ValueError, "positive integer"):
                    Evaluator(max_loop_iterations=limit)


if __name__ == "__main__":
    unittest.main()

