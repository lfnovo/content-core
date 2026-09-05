"""User-facing message constants shared across modules.

Lives outside the processor packages on purpose: these strings are needed by
call sites that may not be able to import the processor at all (a guarded
optional dependency), so the single source of truth must never be behind a
`try: import`.
"""

#: Every "docling was asked for but is not installed" failure. Names the
#: install command *and* the escape hatch, per the missing-dependency
#: principle in ARCHITECTURE.md.
DOCLING_MISSING_MESSAGE = (
    "Docling not installed. Install with: pip install content-core[docling] "
    "or use CCORE_DOCUMENT_ENGINE=simple to skip docling."
)
