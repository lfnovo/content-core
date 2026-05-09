"""LangChain tool wrappers for content-core (optional dependency)."""
try:
    import langchain_core  # noqa: F401
except ImportError:
    __all__ = []
else:
    from .extract import extract_content_tool
    from .summarize import summarize_content_tool

    __all__ = ["extract_content_tool", "summarize_content_tool"]
