# Runtime and verification record

## Environment

- Required language runtime: Python 3.10 or later; standard library only.
- Actual runtime reported by the executed interpreter: **Python 3.14.7**.
- Operating system: **Windows 11**.
- Shell: Windows PowerShell.
- Project directory: the repository root.
- Interpreter: the project's local virtual environment (`.venv`).
- PyCharm's configured interpreter was queried before running Python commands. Its existing virtual environment was used; no packages were installed.

Personal paths and machine-specific build details are omitted from this public verification record. The runtime version and test results below reflect the actual verification run.

## Commands actually executed

The following verification commands are shown with repository-relative interpreter paths in place of the original local absolute paths. Run them from the repository root with a virtual environment at `.venv`.

```powershell
& .\.venv\Scripts\python.exe -m compileall -q main.py environment.py lexer.py parser.py ast_nodes.py evaluator.py errors.py

& .\.venv\Scripts\python.exe -m unittest discover -s tests -v

& .\.venv\Scripts\python.exe main.py examples/sample.rule
& .\.venv\Scripts\python.exe main.py examples/scope_demo.rule
& .\.venv\Scripts\python.exe main.py examples/nested_conditions.rule
& .\.venv\Scripts\python.exe main.py examples/loop_demo.rule
```

For a terminal whose `python` command selects Python 3.10 or later, the equivalent portable run/test commands are:

```console
python main.py examples/sample.rule
python main.py
python -m unittest discover -s tests -v
```

## Actual results

| Check | Observed result |
| --- | --- |
| Compile all seven interpreter modules | Exit 0; no syntax errors. |
| Full unittest discovery | Exit 0; 89 tests passed, no failures, errors, or skips. |
| Explicit sample invocation | Exit 0; exact expected output below. |
| Scope example | Exit 0; expected six output lines. |
| Nested conditions example | Exit 0; expected two output lines. |
| Nested loops example | Exit 0; expected five output lines. |
| Default sample, including launch from another directory | Passed actual subprocess integration tests. |
| Missing/unreadable files, invalid UTF-8, lexical/syntax/runtime errors | Passed subprocess tests: exit 1, useful stderr, no traceback. |
| Invalid loop-limit arguments | Passed subprocess tests: exit 2. |
| Infinite loop with configured limit | Passed subprocess test: stops at limit, exit 1. |
| Excessive expression nesting | Passed subprocess test: graceful recursion-limit diagnostic. |
| PyCharm inspections of `parser.py` and `evaluator.py` | Both returned empty problem lists. |
| Final source audit | All 19 requested files present; no TODO/FIXME markers, stub `pass` statements, `NotImplementedError`, skipped-test decorators, or Python `eval()`/`exec()` calls. |

The first complete test execution reported:

```text
----------------------------------------------------------------------
Ran 89 tests in 4.480s

OK
```

This is observed test-run timing, not an interpreter benchmark. Test duration varies by machine and run. The suite imports all project modules and exercises the real source-to-AST-to-output pipeline, including CLI subprocesses launched with `sys.executable`.

The final source audit used `rg --files` with local environment/IDE/cache exclusions and a pattern search of project Python files. The unfinished-code/prohibited-call search returned no matches (`rg` status 1 means no matches). PyCharm's file-problem inspection was also run on `parser.py` and `evaluator.py`; neither reported problems.

Actual sample output:

```text
Student passed!
Good job!
0
1
2
```

Actual scope output:

```text
outer block
10
inner block
outer block
global
15
```

Actual nested-conditions output:

```text
Passed with regular standing
Eligible for next term
```

Actual loop output:

```text
4
3
6
Total:
18
```

Tests verify exact text output with normal platform newline normalization. They also assert final global state, nearest-binding mutation, lookup/assignment across 100 parent links, fresh loop-body scopes, scope restoration after errors, and rule execution once per encounter.

## Environment and implementation limits

No environment limitation blocked implementation, test execution, or example execution. Only the configured Python 3.14.7 runtime on Windows was used for execution; Python 3.10 and other operating systems were not separately run. The implementation uses Python 3.10-compatible language features and standard-library APIs.

Python recursion depth bounds deeply nested ASTs and environment chains. The default safety limit is 10,000 iterations per loop encounter, configurable through `--max-loop-iterations`; nested loops have independent counters. This is not a global time/memory sandbox. Numeric sizes, floating-point precision, and integer text-conversion limits follow the host Python runtime, with common numeric failures translated into DSL errors.
