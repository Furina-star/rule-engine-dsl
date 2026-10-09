# Runtime and verification record

The original verification below is retained as a historical record. The dated section at the end records the current refactoring separately.

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

## Verification on 2026-10-09: targeted interpreter refactoring

This verification used **Python 3.14.7**, reported as `3.14.7 (tags/v3.14.7:823f032, Aug 5 2026, 10:51:32) [MSC v.1944 64 bit (AMD64)]`, on **Windows 11**, build **10.0.26200**, in Windows PowerShell. The platform probe returned `Windows-11-10.0.26200-SP0`. Commands ran from the repository root using the existing PyCharm-configured virtual environment. No dependencies were installed. Python 3.10 and other operating systems were not separately executed.

The initial working tree contained an unrelated untracked `docs/` directory. It was preserved. No remote branches were changed, and no documents in that directory were edited.

### Baseline and final counts

- Baseline discovery: **93 tests passed in 4.316 seconds**, with zero failures, errors, or skips. The earlier 89-test result above is historical, not the current baseline.
- After implementation: **124 tests passed in 5.477 seconds**, with zero failures, errors, or skips.
- A separate targeted run selected the **31 newly added tests** by comparing their identifiers against test methods in `HEAD`: **31 passed in 1.120 seconds**.
- The same audit counted 93 baseline test methods and 124 current methods, confirmed 124 discovered tests, and found **zero removed baseline methods**. Existing tests were retained.

These are observed test timings, not interpreter performance measurements. Dispatch tables were introduced for maintainability; no speedup is claimed.

### Executed verification commands

As in the historical record, the absolute interpreter path used in the terminal is shown below as its repository-relative equivalent:

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
& .\.venv\Scripts\python.exe -m compileall -q main.py environment.py lexer.py parser.py ast_nodes.py evaluator.py errors.py
& .\.venv\Scripts\python.exe main.py examples/sample.rule
& .\.venv\Scripts\python.exe main.py examples/scope_demo.rule
& .\.venv\Scripts\python.exe main.py examples/nested_conditions.rule
& .\.venv\Scripts\python.exe main.py examples/loop_demo.rule
```

The targeted test audit and environment probe ran as an inline standard-library Python script, passed from a PowerShell here-string to `& .\.venv\Scripts\python.exe -`. It used `ast` to inspect test methods, `git show HEAD:tests/<filename>` to read the baseline, `unittest.TestLoader().discover('tests')` for current discovery, and `unittest.TextTestRunner(verbosity=2)` to execute identifiers absent from the baseline. It also printed `sys.version`, `platform.platform()`, and `platform.win32_ver()`; the results are recorded above.

| Check | Observed result |
| --- | --- |
| All seven interpreter modules compile | Exit 0; no output or syntax errors. |
| Full unittest suite | Exit 0; all 124 tests passed. |
| New targeted regressions | Exit 0; all 31 tests passed. |
| All four bundled examples through the CLI | Exit 0 each; exact outputs match the historical outputs above after platform newline normalization. |
| Exact-class statement/expression dispatch | Every supported AST class exercised; unregistered classes and subclasses produce the expected messages and locations. |
| Numeric evaluation | Left operand type checked before the right for numeric operators; equality and unsupported-operator diagnostics retained. All four arithmetic operators tested for non-finite results and overflow. |
| External non-finite values | Infinity, negative infinity, and NaN rejected from environments and manually constructed literals; skipped logical operands remain unevaluated. |
| Native else-if | Chained and nested branches, scope behavior, strict booleans, source locations, and malformed syntax tested. |
| Optional source diagnostics | `--show-source` tested through the CLI for lexer, parser, and evaluator errors; exact caret formatting tested for indentation, tabs, empty lines, EOF, line endings, and missing/invalid locations. |
| Laboratory behavior | Recursive calls to parent lookup/assignment confirmed; existing shadowing, fresh loop scopes, restoration after errors, loop limits, and immediate-rule tests still pass. |

### Decisions and remaining limits

`Environment.get()` and `Environment.assign()` remain recursive, with their original parent pointer and local binding dictionary. `__slots__` was not added: preserving ordinary instance extensibility and method wrapping requires no change to the already-correct class. The parser's `_location()` helper was retained because it centralizes keyword-only AST locations clearly. Arithmetic finiteness checks now sit next to the operations, but the general `evaluate()` guard remains necessary for external environments, literal nodes, and unary/grouped expressions.

Native else-if and optional diagnostics do not add functions, break/continue, static analysis, bytecode, dependencies, persistent rule registration, or reactive execution. Unregistered AST subclasses are intentionally unsupported by exact-class dispatch. The existing recursion-depth, float-precision, integer-resource, and per-loop-budget limits still apply. The optional caret display expands tabs but does not calculate terminal display widths for wide Unicode characters. No performance benchmark or cross-platform compatibility run was performed.
