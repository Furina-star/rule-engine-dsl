# Rule Engine DSL

A complete **interpreted domain-specific language** for a Programming Languages laboratory, implemented in Python using only the standard library. Source files are tokenized, parsed into an abstract syntax tree (AST), and executed by a tree-walk evaluator. There is no Python `eval()`/`exec()`, generated parser, or hardcoded program tree.

## Laboratory requirements and objectives

The official activity requires:

1. **A recursive Environment class with a parent pointer.** `environment.py` stores local variables in `values` and an enclosing scope in `parent`. Both `get()` and `assign()` actually recurse through that pointer.
2. **A tree-walk evaluator supporting conditional branches and loops.** `evaluator.py` visits AST nodes, selects `if`/`else` branches, and repeatedly evaluates `while` conditions and bodies.

The project demonstrates how lexical analysis, recursive-descent parsing, precedence, AST traversal, lexical scope, mutation, conditional execution, and loop control fit together. Students can trace a complete program from its source characters to printed output and explain the two distinct uses of recursion.

## What is a Rule Engine DSL?

A domain-specific language provides notation tailored to a particular problem. This DSL expresses named condition/action rules, supported by variables, arithmetic, branches, and loops. For example:

```text
let score = 85;
rule passing_score when (score >= 75) {
    print("Student passed!");
}
```

The rule checks its condition **immediately when execution reaches it**. A true condition runs its action block exactly once for that encounter. A false condition skips the block. Names label rules; they do not create variables or register callable rules. Later changes to `score` do not automatically recheck earlier rules. A rule inside a loop is checked again each time execution reaches it.

This is a small procedural interpreter with condition/action rules. It does not implement forward chaining, backward chaining, an inference network, or a persistent rule agenda.

## Run the project

Install Python **3.10 or later** and open a terminal in this directory. No package installation is required.

```console
python main.py examples/sample.rule
python main.py
python main.py examples/scope_demo.rule
python main.py examples/nested_conditions.rule
python main.py examples/loop_demo.rule
```

With no file argument, the interpreter finds the bundled sample relative to `main.py`, even when launched from another directory. An explicit relative path is resolved from the terminal's current directory. Input is UTF-8; a UTF-8 byte-order mark is accepted.

Successful execution prints only the program's output and exits with status 0. File, lexical, syntax, and runtime errors go to standard error and exit with status 1. Invalid command-line arguments exit with status 2. `python main.py --help` describes the options.

To include the source line and a caret in language-error diagnostics, add `--show-source`:

```console
python main.py examples/sample.rule --show-source
```

The option applies to lexical, syntax, and runtime errors on stderr. Error messages, file paths, one-based locations, and exit codes remain the same. Tabs expand to four-column stops for caret alignment, and blank lines at end of file are supported.

## Architecture

```text
Source Code -> Lexer -> Tokens -> Parser -> AST -> Tree-Walk Evaluator -> Output
                                                           |
                                                     Environment
                                                   locals -> parent
```

| Component | Responsibility |
| --- | --- |
| `main.py` | Read a file, run the pipeline, configure the loop limit, report errors and exit status. |
| `lexer.py` | Convert characters to tokens with one-based line/column locations. |
| `parser.py` | Parse statements and expressions using recursive descent and precedence levels. |
| `ast_nodes.py` | Dataclasses representing expressions and statements, with source locations. |
| `environment.py` | Store local bindings and recursively resolve or update enclosing bindings. |
| `evaluator.py` | Walk the AST, compute values, manage scopes, and execute control flow. |
| `errors.py` | Define shared language errors with readable diagnostics. |

### Lexer

`Lexer(source).tokenize()` scans left to right. It recognizes keywords, identifiers, numbers, strings, operators, delimiters, and an explicit EOF token. Two-character operators are recognized before their single-character counterparts. `//` comments run to the end of the line; comment markers inside a string are ordinary string content.

Every token contains its type, source lexeme, optional literal value, and starting line and column. Unix, Windows, and classic Mac line endings are normalized. Spaces, tabs, and newlines separate tokens. Unsupported characters, incomplete decimals, invalid string escapes, non-finite decimal literals, and unterminated strings raise `LexerError`.

### Parser and AST

`Parser(tokens).parse()` returns a list of top-level statements. The parser consumes actual source tokens, checks required punctuation, and creates explicit AST objects. It rejects the first syntax error with a source location. The entire file is parsed before any statement executes.

Expression nodes are `NumberLiteral`, `StringLiteral`, `BooleanLiteral`, `Variable`, `Unary`, `Binary`, and `Grouping`. Statement nodes are `LetStatement`, `Assignment`, `PrintStatement`, `Block`, `IfStatement`, `WhileStatement`, and `RuleStatement`.

Each precedence level has its own parsing method. For example, `2 + 3 * 4` becomes a `Binary(+)` node whose right child is a `Binary(*)` node. Repeated binary operators at the same level associate to the left: `10 - 3 - 2` means `(10 - 3) - 2`. Unary operators recurse to the right: `!!true` means `!(!true)`.

### Recursive environments and parent pointers

Each `Environment` has a separate dictionary and an optional parent:

```text
inner block: {name: "inner block"}
    parent -> outer block: {name: "outer block"}
                  parent -> global: {name: "global", total: 10}
                                parent -> None
```

- `define(name, value)` creates or replaces a local binding. An outer binding with the same name remains unchanged.
- `get(name)` checks the local dictionary, then calls `parent.get(name)` recursively. An exhausted parent chain raises an undefined-variable error.
- `assign(name, value)` updates a local binding if present; otherwise it calls `parent.assign(name, value)` recursively. It updates the nearest existing binding and never implicitly creates one.

Every `{ ... }` block creates a child environment. This includes standalone blocks, conditional branches, loop bodies, and rule actions. Top-level statements share one global environment. A child-only declaration disappears from visibility when its block exits; parents and sibling blocks cannot read it. A declaration's initializer is evaluated before its binding is defined, so `let x = x + 1;` in a child scope can read an existing outer `x` before shadowing it.

The implementation has no fixed number of supported nesting levels. Like other recursive Python programs, practical depth is bounded by Python's recursion limit. Tests exercise lookup and assignment across 100 nested environments.

### Tree-walk evaluation

`Evaluator.execute(statements)` executes the top-level list in order. `evaluate(expression)` recursively evaluates expression children and returns a value. Statement dispatch performs declarations, assignments, printing, and control flow. Variables always resolve through `Environment.get()`; assignment always uses `Environment.assign()`.

The evaluator builds two reusable dispatch dictionaries during initialization. They map exact AST classes (`type(node)`) to statement and expression handlers. Handlers recursively visit child nodes; dispatch tables organize the same tree-walk interpreter without a visitor framework or bytecode. Unregistered AST classes, including subclasses of supported nodes, produce unsupported-node errors. This design improves maintainability; no speed improvement is claimed.

A block saves the enclosing environment, installs a child, executes its statements, and restores the enclosing environment in `finally`, including on runtime errors. An evaluator retains its global environment across multiple `execute()` calls. An output callback can be supplied for tests or embedding; by default it is Python's `print`.

**The two kinds of recursion are different:** AST recursion follows syntax-tree children to evaluate nested expressions and statements. Environment recursion follows enclosing-scope parent pointers to locate a name. For `print(x + 1)` in a nested block, AST traversal reaches `Variable("x")`; that lookup separately walks the environment chain. A while loop uses repeated execution, not one Python recursive call per iteration.

### Conditional branches

An `if` evaluates its condition once and requires a boolean. If true, it executes the `then` block; otherwise it checks the next `else if` or executes the final `else` block. The first matching branch runs. Unselected conditions and branches are not evaluated, although they must still contain valid syntax. Nested conditionals use the same evaluator and block-scoping rules.

```text
let score = 85;
if (score >= 90) {
    print("Excellent!");
} else if (score >= 75) {
    print("Passed!");
} else {
    print("Try again.");
}
```

An `else if` is another `IfStatement` stored as the preceding node's `else_branch`. Chaining introduces no extra scope around its condition; every executed branch block still creates its own child environment.

### Loops and safety limit

A `while` reevaluates its condition in the **enclosing environment** before each iteration. False means zero further iterations; true executes the body in a **fresh child environment**. Assignments can update enclosing variables to make the condition eventually false. Variables declared in a previous body execution do not persist into the next.

The default limit is **10,000 body executions per loop encounter**. If the condition remains true after that many executions, the evaluator raises a runtime error before executing another body. A loop that becomes false after exactly the limit is allowed.

```console
python main.py examples/loop_demo.rule --max-loop-iterations 100
```

For embedding, use `Evaluator(max_loop_iterations=100)`. The limit must be a positive integer. Each nested or subsequently encountered loop has its own counter. This is protection against accidental endless demonstrations, not a total program instruction/time budget; nested loops can multiply the work.

### Rule actions

A rule checks its condition in the current environment and requires a boolean. A true result executes its action block with normal child-scope semantics. The action can shadow variables locally or assign enclosing variables. The rule itself performs no repeated checks or registration.

## Language reference

### Values and names

- **Numbers:** decimal integers (`0`, `85`) and decimal floating-point literals (`3.14`, `0.5`). Use unary `-` for negative numbers. Decimal points require digits on both sides. Exponent notation and numeric separators are not supported.
- **Strings:** double quoted, with escapes `\"`, `\\`, `\n`, `\t`, and `\r`. Raw multiline strings are rejected. Strings support printing, storage, and equality; there is no concatenation or ordering.
- **Booleans:** `true` and `false`, printed in lowercase.
- **Identifiers:** case-sensitive ASCII names matching `[A-Za-z_][A-Za-z0-9_]*`. Keywords cannot be used as identifiers.

Variables are dynamically typed: assignment can change a binding's value type. A repeated `let` in the same scope replaces that binding. There is no null value or implicit variable declaration.

### Statements

```text
let name = expression;
name = expression;
print(expression);
{ statements }
if (condition) { statements }
if (condition) { statements } else { statements }
if (condition) { statements } else if (condition) { statements } else { statements }
while (condition) { statements }
rule name when (condition) { statements }
```

Declarations, assignments, and print statements require semicolons. Blocks and control statements do not take a trailing semicolon. Ordinary branches and control bodies require braces, even for one statement. Native `else if` chains may have any number of branches and an optional final `else` block. An arbitrary statement immediately after `else` is rejected. Explicitly nesting an `if` inside an `else` block also remains supported. Standalone expression statements and assignment expressions are not supported. `print` takes exactly one expression.

### Operators (highest to lowest precedence)

| Level | Operators | Semantics |
| --- | --- | --- |
| 1 | literals, identifiers, `(expression)` | Values, lookup, explicit grouping |
| 2 | `!`, unary `-` | Boolean negation, numeric negation |
| 3 | `*`, `/` | Numeric multiplication and division |
| 4 | `+`, `-` | Numeric addition and subtraction |
| 5 | `>`, `>=`, `<`, `<=` | Numeric comparisons |
| 6 | `==`, `!=` | Value equality and inequality |
| 7 | `&&` | Short-circuit boolean AND |
| 8 | `\|\|` | Short-circuit boolean OR |

Arithmetic and ordering require numeric operands. Booleans do **not** count as numbers, even though Python's `bool` inherits from `int`. Division produces a floating-point result (`4 / 2` prints `2.0`); division by zero raises an error. Decimal arithmetic uses Python floats and their ordinary rounding behavior. Non-finite results and floating-point overflow raise language errors.

Numeric operators validate the left operand before evaluating the right. For example, `true + missing` reports a numeric type error before resolving `missing`. Equality remains unrestricted by numeric type checks. Arithmetic results are checked for finiteness where they are produced, and expression evaluation also rejects non-finite values supplied through an external environment or manually constructed literal.

Equality accepts any pair of supported values. Integers and floats compare numerically (`1 == 1.0` is true); different nonnumeric types compare unequal (`true == 1` and `"1" == 1` are false). `!=` negates equality. Comparisons do not have Python-style chaining: use `x > 0 && x < 10`.

### Strict booleans and short-circuiting

Conditions of `if`, `while`, and `rule` must be booleans. `!`, `&&`, and `||` also require boolean operands when evaluated. Numbers and strings have no implicit truthiness; `if (1)` is an error.

`false && expression` returns false without evaluating the right side. `true || expression` returns true without evaluating the right side. Skipped operands are neither resolved nor type-checked at runtime; for example, `false && missing` safely returns false. When the right operand is needed, it must be boolean. Logical operators always return booleans.

### Grammar

Here `*` means repetition and `?` means optional syntax; quoted symbols are literal source tokens.

```text
program     -> statement* EOF
statement   -> "let" IDENTIFIER "=" expression ";"
             | IDENTIFIER "=" expression ";"
             | "print" "(" expression ")" ";"
             | conditional
             | "while" "(" expression ")" block
             | "rule" IDENTIFIER "when" "(" expression ")" block
             | block
block       -> "{" statement* "}"
conditional -> "if" "(" expression ")" block ("else" (conditional | block))?
expression  -> logical_or
logical_or  -> logical_and ("||" logical_and)*
logical_and -> equality ("&&" equality)*
equality    -> comparison (("==" | "!=") comparison)*
comparison  -> term ((">" | ">=" | "<" | "<=") term)*
term        -> factor (("+" | "-") factor)*
factor      -> unary (("*" | "/") unary)*
unary       -> ("!" | "-") unary | primary
primary     -> NUMBER | STRING | "true" | "false" | IDENTIFIER
             | "(" expression ")"
```

## Example programs and expected output

### `examples/sample.rule`

The official sample combines a passing-score rule, an if/else branch, and a three-iteration counter loop.

```text
Student passed!
Good job!
0
1
2
```

### `examples/scope_demo.rule`

Two nested blocks follow parent pointers to read outer variables, shadow `name`, and update the global `total` from 10 to 15. The global name survives unchanged.

```text
outer block
10
inner block
outer block
global
15
```

### `examples/nested_conditions.rule`

Score and attendance comparisons use `&&`, `||`, and `!` to choose nested branches and trigger an eligibility rule.

```text
Passed with regular standing
Eligible for next term
```

### `examples/loop_demo.rule`

Nested loops multiply rows 1 through 3 by columns 1 through 2. An inner condition prints products of at least 3, while assignments accumulate all six products in a global total.

```text
4
3
6
Total:
18
```

## Automated tests and verification

```console
python -m unittest discover -s tests -v
```

The standard-library suite covers recursive lookup and assignment, shadowing, tokenization, AST structure and precedence, malformed syntax, all control statements, strict operand types, short-circuiting, fresh loop scopes, immediate rules, source locations, and safety-limit boundaries. Integration tests run actual CLI subprocesses, compare every example's exact output, verify the default sample from another working directory, and check expected failures without tracebacks.

The current suite passes **124 tests**, with no skipped tests. The latest refactoring baseline was 93 passing tests; the original historical record reports 89. See [RUNTIME.md](RUNTIME.md) for the actual Python version, operating system, commands, and observed results. Python 3.10 is the minimum target; execution was verified on the version recorded there.

## Project directory structure

```text
rule-engine-dsl/
|-- main.py
|-- environment.py
|-- lexer.py
|-- parser.py
|-- ast_nodes.py
|-- evaluator.py
|-- errors.py
|-- examples/
|   |-- sample.rule
|   |-- scope_demo.rule
|   |-- nested_conditions.rule
|   `-- loop_demo.rule
|-- tests/
|   |-- test_environment.py
|   |-- test_lexer.py
|   |-- test_parser.py
|   |-- test_evaluator.py
|   |-- test_diagnostics.py
|   `-- test_integration.py
|-- README.md
|-- RUNTIME.md
`-- .gitignore
```

## Errors, limitations, and future improvements

Expected DSL errors include the file path and, for source errors, a one-based line/column. `--show-source` optionally adds the source line and a caret. Evaluation stops at the first failure. Previously printed output and completed mutations are not rolled back. A missing semicolon is a syntax error; an undefined variable or nonboolean condition is a runtime error.

This teaching implementation has no functions, collections, classes, input statement, `break`/`continue`, imports, or persistent rule agenda. It reports one syntax error at a time. Extremely deep syntax trees or scope chains are constrained by Python's recursion limit; the CLI reports excessive nesting gracefully. Integers and their conversion to/from text remain subject to the host runtime's resource limits. The loop limit is per encounter and does not provide a global time or memory sandbox.

The two graded laboratory requirements are recursive parent-pointer environments and tree-walk conditionals/loops. Else-if syntax, optional caret diagnostics, and the loop safety limit are supporting conveniences. Built-in functions, `break`/`continue`, function declarations and closures, static analysis, and inference-engine features remain optional future proposals outside those requirements; none are implemented here. Parser error recovery and a total execution-step budget could also be considered separately. A reactive inference engine would require a separately designed rule lifecycle rather than changing the documented immediate rule semantics implicitly.
