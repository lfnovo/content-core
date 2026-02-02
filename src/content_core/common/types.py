from typing import Literal

DocumentEngine = Literal[
    "auto",
    "simple",
    "docling",
    "docling-vlm",
    "marker",
]

UrlEngine = Literal[
    "auto",
    "simple",
    "firecrawl",
    "jina",
    "crawl4ai",
]

# VLM-specific types
VlmInferenceMode = Literal["local", "remote"]
VlmBackend = Literal["auto", "transformers", "mlx"]
VlmModel = Literal["granite-docling", "smol-docling"]
