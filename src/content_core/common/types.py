from typing import Literal
import warnings

Engine = Literal[
    "auto",
    "simple",
    "legacy",
    "firecrawl",
    "jina",
    "docling",
]

DEPRECATED_ENGINES = {"legacy": "simple"}

def warn_if_deprecated_engine(engine: str):
    if engine in DEPRECATED_ENGINES:
        warnings.warn(
            f"Engine '{engine}' is deprecated and will be removed in a future release. Use '{DEPRECATED_ENGINES[engine]}' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
