# Architecture — Content Core

Principles accumulated from design sessions. Check here before opening an
architectural question: many already have an answer here.

## Routing

### Single source of truth for routing

The decision "which MIME type goes to which processor" lives in exactly one
place: `_route_for_mime()` in `extraction.py`. Every consumer of that
decision — `_extract_file`, `check_file_support` — calls this function
instead of reimplementing the table.

**Why:** `check_file_support` exists to promise the caller what extraction
will do. If the two tables diverge, the promise becomes a lie.

**Scope:** Any new format or engine. Adding a branch in `_extract_file`
without going through `_route_for_mime` is a bug, not a shortcut.

**Origin:** Encoded from the state of the code, 2026-07-20.

### Explicit choice is a requirement; `auto` is a preference

When the user names an engine explicitly, it is honored or the operation
raises an error. Only `auto` has license to fall back and degrade.

**Why:** The quality difference between engines is the reason the user
chose one. Silent substitution is indistinguishable from success — the
worst failure mode.

**Scope:** Any setting that selects an implementation (`url_engine`,
`document_engine`, future LLM/STT providers).

**Origin:** Issue #50, 2026-07-22.

## Processors

### Two-layer contract

A processor has two layers with deliberately different contracts:

- **Outer layer** (`extract_<fmt>_file(file_path, config) ->
  ExtractionOutput`) — called by the orchestrator, **raises** an exception
  on failure.
- **Inner layer** (`extract_<fmt>_content(file_path) -> str | None`) —
  library-level parsing; may degrade **per unit** (page, sheet, slide) by
  logging and skipping the unit, but failure of the **entire** file
  propagates to the outer layer to type and raise.

Normalization happens at the boundary: `content=content or ""`.

**Why:** The orchestrator needs to distinguish "I don't know how to
process this" from "I processed it and it was empty." And, per the
raise/degrade boundary, "I couldn't parse the file" is total failure — it
raises, it doesn't turn into an empty string.

**Scope:** Every document processor. Single-library formats (EPUB) may
collapse the two layers.

**Origin:** Encoded from the state of the code, 2026-07-20; amended by the
raise/degrade boundary review (issue #52), 2026-07-22.

### Synchronous parsing goes to the executor

Every synchronous parsing library is wrapped in an `_extract()` closure and
dispatched via `run_in_executor(None, _extract)`.

**Why:** The entire public API is async; synchronous parsing on the event
loop blocks every concurrent caller.

**Scope:** Any processor that calls a synchronous third-party library.

**Origin:** Encoded from the state of the code, 2026-07-20.

### Code doesn't declare contracts nobody enforces

An aspirational contract lives here, in `ARCHITECTURE.md`, as a principle;
code only declares contracts that are actually called or checked. A
`Protocol`/ABC/interface with no implementor and no `isinstance` check is
documentation pretending to be code — and it drifts into a lie.

**Why:** The dead `Processor` Protocol was born unused in the v2.0 rewrite,
got "legitimized" by self-referential coverage tests, and pointed agent
docs at the wrong contract for two release cycles (#53). Prose gets
reviewed as prose; dead code borrows credibility from the test suite.

**Scope:** Any `Protocol`, ABC, `Callable` alias, or interface. If nothing
calls it or checks against it, it doesn't merge.

**Origin:** Issue #53, 2026-07-22.

## Errors

### The raise/degrade boundary

**Total** failure raises; degrade only exists **within** the source. Any
failure to produce the requested content — routing, input, configuration,
network, parsing — raises a typed exception from `common/exceptions.py`.
Degradation is legitimate only intra-source: a PDF page that failed, an
audio chunk, the next engine in the `auto` chain (if **all** fail, it
raises). `content=""` means a genuinely empty source — never "something
went wrong."

**Why:** Returning empty when the network went down is hiding an error —
indistinguishable from an empty page to the caller. The old rationale
("don't bring down the whole extraction for one dead source") was
inherited from a batch context; `extract_content` processes one source per
call, and the per-source try/except belongs to the batch caller.

**Versioning:** Hiding an error is a bug. The fix ships in 2.x, no major —
decided with 2.0 freshly released and lightly adopted.

**Scope:** Every processor and the orchestrator.

**Origin:** Issue #52 + principle review, 2026-07-22. Supersedes the
version encoded from the state of the code on 2026-07-20.

## Dependencies

### Formats are core, engines are extras

A library for reading a **file format** (`python-docx`, `openpyxl`,
`pdfplumber`) goes into `[project.dependencies]`. A library that is an
**alternative engine** for something already supported (`docling`,
`crawl4ai`) becomes an optional extra with a guarded import.

**Why:** Format support is the product — a user who installs content-core
expects `.docx` to work. Engine is a tradeoff choice, and these libraries
are heavy.

**Scope:** Every new dependency. If it's heavy enough to hurt install
(ML models, browsers), reconsider even if it is a format.

**Origin:** Encoded from the state of the code, 2026-07-20.

### Missing-dependency error names the command and the escape hatch

An `ImportError` message for an optional dependency carries the exact
install command **and** how to proceed without it.

**Why:** The user is blocked right now; they need both exits.

**Scope:** Every guarded import.

**Origin:** Encoded from the state of the code, 2026-07-20.

## Configuration

### Precedence

Constructor arguments > env vars (`CCORE_*`) > `~/.content-core/config.toml`
> defaults.

**Scope:** Every new setting.

**Origin:** Encoded from the state of the code, 2026-07-20.

### Closed vocabulary is validated at the entry point

A config field with a closed set of valid values is declared
`Literal`/`Enum` on the model and validated at every write entry point
(constructor, env var, `config set`). Runtime checks remain as
defense-in-depth, not as primary validation.

**Why:** A typo discovered only at extraction time — or worse, swallowed —
is indistinguishable from an empty page. Failing at construction gives the
list of valid values at the moment the user is still configuring.

**Scope:** Every enumerable config field. Does not apply to open values
(URLs, third-party model names).

**Origin:** Issue #51, 2026-07-22.
