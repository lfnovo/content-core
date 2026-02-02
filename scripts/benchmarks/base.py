"""Base classes for the benchmark framework."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class QualityScore:
    """Quality metrics for extraction accuracy."""

    score: float  # 0.0 to 1.0
    found: int  # Number of expected elements found
    total: int  # Total expected elements
    details: Dict[str, bool]  # Which elements were found


@dataclass
class BenchmarkResult:
    """Results from benchmarking a single engine on a single file."""

    engine: str
    file: str
    file_type: str

    # Performance
    time_seconds: float
    memory_peak_mb: float

    # Output
    output_size_bytes: int
    output_lines: int

    # Validation
    has_content: bool
    error: Optional[str] = None

    # Quality score (for files with known content)
    quality_score: Optional[float] = None
    quality_found: Optional[int] = None
    quality_total: Optional[int] = None

    # Type-specific metrics (headers, tables, formulas, etc.)
    extra_metrics: Dict[str, Any] = field(default_factory=dict)


class Engine(ABC):
    """Abstract base class for extraction engines."""

    name: str
    supported_types: List[str]  # ["pdf"], ["docx"], ["pdf", "docx"]

    @abstractmethod
    async def extract(self, file_path: str, options: Dict[str, Any]) -> str:
        """Extract content from file, return markdown.

        Args:
            file_path: Path to the file to extract
            options: Engine-specific options (e.g., describe_images)

        Returns:
            Extracted content as markdown string
        """
        pass

    def supports(self, file_type: str) -> bool:
        """Check if this engine supports the given file type."""
        return file_type.lower() in [t.lower() for t in self.supported_types]


class QualityScorer(ABC):
    """Abstract base class for quality scoring."""

    file_type: str

    @abstractmethod
    def score(self, content: str, file_name: str) -> Optional[QualityScore]:
        """Score extraction quality against expected content.

        Args:
            content: Extracted content to score
            file_name: Name of the source file (used to match expected data)

        Returns:
            QualityScore if expected data exists for this file, None otherwise
        """
        pass


class ContentAnalyzer(ABC):
    """Abstract base class for content analysis."""

    file_type: str

    @abstractmethod
    def analyze(self, content: str) -> Dict[str, Any]:
        """Extract metrics from content (headers, tables, etc).

        Args:
            content: Extracted content to analyze

        Returns:
            Dictionary of metrics
        """
        pass
