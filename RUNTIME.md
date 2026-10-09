# Runtime and verification record

## Requirements and runtime environment

- Python 3.10 or later; standard library only, with no package installation required.
- Latest verification: **2026-10-09**, using **Python 3.14.7** on **Windows 11**, build **10.0.26200**.
- Commands ran from the repository root. Python 3.10 and other operating systems were not separately tested.

## Verification commands

Use a `python` command that selects Python 3.10 or later. These portable commands are equivalent to the commands executed with the Python 3.14.7 interpreter during verification:

```console
python -m unittest discover -s tests -v
python -m compileall -q main.py environment.py lexer.py parser.py ast_nodes.py evaluator.py errors.py
python main.py examples/sample.rule
python main.py examples/scope_demo.rule
python main.py examples/nested_conditions.rule
python main.py examples/loop_demo.rule
python main.py --help
```

## Actual test results

The latest cleanup run discovered and passed **114 tests in 4.870 seconds**, with **zero failures, errors, or skips**. Compilation of all seven interpreter modules exited with status 0 and no syntax errors.

The suite verifies recursive parent lookup and assignment, lexical scoping and shadowing, AST dispatch, else-if parsing and execution, fresh loop-body scopes, immediate rules, short-circuiting, strict operand types, non-finite values, arithmetic overflow, division by zero, source locations, and loop-limit boundaries.

Additional checks confirmed that CLI help lists only the retained options and that lexer, parser, and runtime errors still include the file path, error type, message, line, and column on stderr. Expected DSL errors exit with status 1; invalid arguments exit with status 2; successful programs exit with status 0. Previously printed output survives a later runtime error. No Python traceback appears for these expected errors.

The cleanup removed exactly 10 obsolete feature tests. Every other test was retained. The recursive Environment, AST dispatch, parser, loops, and `_binary()` branch ordering were preserved. The outer `evaluate()` validation still rejects NaN and infinity, including externally supplied values. The checksum of `docs/rule-engine-dsl.docx` was unchanged.

### Historical evidence

Earlier Windows runs using Python 3.14.7 recorded:

| Verification stage | Observed result |
| --- | --- |
| Original implementation | 89 tests passed in 4.480 seconds. |
| Baseline before the previous interpreter refactoring | 93 tests passed in 4.316 seconds. |
| Previous refactoring | 124 tests passed in 5.477 seconds; a separate run passed all 31 newly added tests in 1.120 seconds. |
| Baseline immediately before this cleanup | 124 tests passed in 5.567 seconds. |
| Latest cleanup | 114 tests passed in 4.870 seconds. |

These counts describe different repository states. Test durations are observed timings, not interpreter performance benchmarks.

## Example execution results

All four programs exited with status 0 and matched the exact expected output documented in [README.md](README.md), after normalizing platform line endings:

| Program | Observed output |
| --- | --- |
| `sample.rule` | `Student passed!`, `Good job!`, `0`, `1`, `2` |
| `scope_demo.rule` | `outer block`, `10`, `inner block`, `outer block`, `global`, `15` |
| `nested_conditions.rule` | `Passed with regular standing`, `Eligible for next term` |
| `loop_demo.rule` | `4`, `3`, `6`, `Total:`, `18` |

Each listed value appears on its own output line. Integration tests also verify the default sample when launched from another working directory.

## Known limitations

Python's recursion limit bounds deeply nested syntax trees and parent-pointer chains. The default loop limit is 10,000 iterations per encounter; it is not a global time or memory budget. Floating-point precision, integer sizes, and number-to-text conversion limits follow the host runtime.

Exact-class dispatch rejects unregistered AST subclasses. The interpreter reports the first error and does not roll back earlier output or mutations. Rules are checked immediately when encountered and are not registered for future automatic execution. No cross-platform execution or performance benchmark was performed in this verification.
