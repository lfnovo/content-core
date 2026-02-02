"""Expected content for PDF benchmark scoring."""

# Expected content for benchmark.pdf (our synthetic test file)
# Formulas use pattern lists to handle both ASCII and LaTeX variations
BENCHMARK_PDF_EXPECTED = {
    "title": "Benchmark Document for PDF Extraction",
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
        "LaTeX Block Formula",
    ],
    # Each formula entry is a tuple: (key_name, [pattern_variants])
    # This handles both ASCII (e.g., e^(i) and LaTeX (e.g., e^{(i}) formats
    "formulas": [
        ("E=mc2", ["E = mc", "E=mc"]),  # E = mc^2
        ("euler", ["e^(i", "e^{(i", "e^{i"]),  # Euler's identity: e^(i*pi) or e^{(i*pi)}
        ("pythagorean", ["a^2 + b^2", "a^{2} + b^{2}", "a² + b²"]),  # Pythagorean theorem
        ("quadratic", ["sqrt(b^2", "sqrt{b^2", "\\sqrt{b", "√"]),  # Quadratic formula
    ],
    "table_data": [
        "Quick Sort",
        "Merge Sort",
        "Bubble Sort",
        "Neural Net",
        "45.2",  # Quick Sort time
        "98.7",  # Neural Net accuracy (unique value)
    ],
    "figure": [
        "Figure 1",
        "sin(x)",
        "cos(x)",
    ],
}
