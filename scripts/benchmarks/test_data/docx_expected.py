"""Expected content for DOCX benchmark scoring."""

# Expected content for benchmark.docx
# This mirrors the structure of benchmark.pdf for consistent testing
BENCHMARK_DOCX_EXPECTED = {
    "title": "Benchmark Document for DOCX Extraction",
    "sections": [
        "Introduction",
        "Mathematical Formulas",
        "Data Table",
        "Figure",
        "Conclusion",
        "References",
    ],
    "subsections": [
        "Famous Equations",
        "Block Formula",
    ],
    # Each formula entry is a tuple: (key_name, [pattern_variants])
    # DOCX may render formulas differently than PDF
    "formulas": [
        ("E=mc2", ["E = mc", "E=mc", "E = mc²", "E=mc²"]),
        ("euler", ["e^(i", "e^{(i", "e^{i", "e^iπ"]),
        ("pythagorean", ["a^2 + b^2", "a^{2} + b^{2}", "a² + b²"]),
        ("quadratic", ["sqrt(b^2", "sqrt{b^2", "\\sqrt{b", "√"]),
    ],
    "table_data": [
        "Quick Sort",
        "Merge Sort",
        "Bubble Sort",
        "Neural Net",
        "45.2",  # Quick Sort time
        "98.7",  # Neural Net accuracy
    ],
    "figure": [
        "Figure 1",
        "sin(x)",
        "cos(x)",
    ],
    # DOCX-specific elements
    "formatting": [
        "bold",
        "italic",
    ],
    "lists": [
        "First item",
        "Second item",
    ],
}
