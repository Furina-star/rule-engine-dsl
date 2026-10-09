import unittest

from environment import Environment
from errors import EvaluationError


class EnvironmentTests(unittest.TestCase):
    def test_define_and_read_local(self):
        environment = Environment()
        environment.define("score", 85)
        self.assertEqual(environment.values, {"score": 85})
        self.assertEqual(environment.get("score"), 85)
        self.assertIsNone(environment.parent)

    def test_read_parent_and_preserve_pointer(self):
        parent = Environment()
        parent.define("x", 7)
        child = Environment(parent)
        self.assertIs(child.parent, parent)
        self.assertEqual(child.get("x"), 7)
        self.assertEqual(child.values, {})

    def test_many_nested_environments(self):
        root = Environment()
        root.define("x", 1)
        deepest = root
        for _ in range(100):
            deepest = Environment(deepest)
        self.assertEqual(deepest.get("x"), 1)
        deepest.assign("x", 2)
        self.assertEqual(root.get("x"), 2)

    def test_shadowing_and_nearest_assignment(self):
        root = Environment()
        root.define("x", 1)
        child = Environment(root)
        child.define("x", 2)
        grandchild = Environment(child)
        grandchild.assign("x", 3)
        self.assertEqual(root.get("x"), 1)
        self.assertEqual(child.get("x"), 3)
        self.assertEqual(grandchild.get("x"), 3)

    def test_assign_outer_and_local(self):
        root = Environment()
        root.define("x", 1)
        child = Environment(root)
        child.assign("x", 9)
        child.define("y", 3)
        child.assign("y", 4)
        self.assertEqual(root.get("x"), 9)
        self.assertEqual(child.values, {"y": 4})

    def test_redefinition_is_local(self):
        environment = Environment()
        environment.define("x", 1)
        environment.define("x", "replacement")
        self.assertEqual(environment.get("x"), "replacement")

    def test_falsy_values_are_existing_bindings(self):
        root = Environment()
        for name, value in (("zero", 0), ("false", False), ("empty", "")):
            root.define(name, value)
            self.assertEqual(Environment(root).get(name), value)

    def test_children_are_isolated(self):
        parent = Environment()
        child = Environment(parent)
        child.define("private", 1)
        for environment in (parent, Environment(parent)):
            with self.assertRaisesRegex(EvaluationError, "Undefined variable 'private'"):
                environment.get("private")

    def test_undefined_read(self):
        with self.assertRaisesRegex(EvaluationError, "Undefined variable 'missing'"):
            Environment(Environment()).get("missing")

    def test_undefined_assignment_does_not_create_binding(self):
        root = Environment()
        child = Environment(root)
        with self.assertRaisesRegex(EvaluationError, "Cannot assign undefined variable"):
            child.assign("missing", 3)
        self.assertEqual(root.values, {})
        self.assertEqual(child.values, {})


if __name__ == "__main__":
    unittest.main()

