"""LangChain tool wrappers for content-core (optional dependency)."""
try:
    from .extract import extract_content_tool
    from .summarize import summarize_content_tool

    __all__ = ["extract_content_tool", "summarize_content_tool"]
except ImportError:
    __all__ = []
