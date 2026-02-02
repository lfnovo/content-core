# PDF Extraction Benchmark

Comparison of PDF extraction engines in Content Core using a synthetic benchmark document with headers, tables, formulas, and figures.

## Latest Results

**Test File:** benchmark.pdf (37.4 KB)
**Date:** 2026-02-02

### Performance Summary

| Engine | Time | Memory | Quality | License |
|--------|------|--------|---------|---------|
| **docling** | 13.5s | 266MB | 100% | MIT |
| **docling-vlm** | 8.6s | 149MB | 96% | MIT |
| pymupdf4llm* | ~0.2s | ~15MB | 100% | AGPL-3.0 |
| marker* | ~45s | ~2GB | 95%+ | GPL-3.0 |

*Estimated from previous runs. PyMuPDF and Marker require separate installation.

### Quality Score Breakdown

The quality score measures how many expected elements were found in the extracted content:

| Category | Elements Checked |
|----------|------------------|
| Title | "Benchmark Document for PDF Extraction" |
| Sections | Introduction, Mathematical Formulas, Data Table, Figure, Conclusion, References |
| Subsections | Famous Equations, LaTeX Block Formula |
| Formulas | E=mc², Euler's identity, Pythagorean theorem, Quadratic formula |
| Table Data | Quick Sort, Merge Sort, Bubble Sort, Neural Net, specific values |
| Figure | Figure 1, sin(x), cos(x) |

### Engine Analysis

#### Docling (Recommended)

- **Strengths:** Excellent table extraction, 100% quality score, MIT license
- **Weaknesses:** Moderate memory usage, slower than PyMuPDF
- **Best For:** Production use, commercial applications

#### Docling-VLM

- **Strengths:** Vision-language understanding, handles complex layouts
- **Weaknesses:** Slightly lower quality score (missed 1 formula variant)
- **Best For:** Documents with complex layouts, diagrams, figures

#### PyMuPDF4LLM (Not Installed)

- **Strengths:** Fastest extraction, low memory
- **Weaknesses:** AGPL-3.0 license, basic table support
- **Best For:** Speed-critical applications with AGPL compliance

#### Marker (Not Installed)

- **Strengths:** Deep learning models, excellent formula support
- **Weaknesses:** GPL-3.0 license, large model downloads, slow
- **Best For:** Scientific papers, math-heavy documents

## Running Benchmarks

### Run All PDF Engines

```bash
uv run python scripts/benchmark.py --type pdf --files benchmark.pdf
```

### Run Specific Engines

```bash
uv run python scripts/benchmark.py --type pdf --engines docling,docling-vlm
```

### Run with Image Description

```bash
uv run python scripts/benchmark.py --type pdf --engines docling --describe-images
```

## Benchmark Methodology

### Test Document

The benchmark uses a synthetic PDF (`tests/input_content/benchmark.pdf`) containing:

- **Headers:** Multiple levels (H1, H2)
- **Mathematical Formulas:** LaTeX equations (E=mc², Euler's identity, etc.)
- **Tables:** Algorithm comparison table with numeric data
- **Figure:** Trigonometric function graph with caption
- **References:** Formatted reference list

### Scoring Algorithm

```python
score = found_elements / total_elements

# Elements checked:
# - Title presence
# - Section headings
# - Formula patterns (multiple variants for LaTeX/ASCII)
# - Table data values
# - Figure references
```

### Metrics Collected

| Metric | Description |
|--------|-------------|
| Time | Total extraction time in seconds |
| Memory | Peak memory usage during extraction |
| Size | Output file size in KB |
| Quality | Percentage of expected elements found |

## Historical Results

Results may vary based on:
- Hardware (CPU, RAM, GPU)
- Model versions
- Document complexity

## Contributing

To add new benchmark files or improve scoring:

1. Add test files to `tests/input_content/`
2. Add expected data to `scripts/benchmarks/test_data/pdf_expected.py`
3. Run benchmarks and submit results

## Related Documentation

- [Engine Overview](../engines/overview.md)
- [Docling Engine](../engines/docling.md)
- [Docling VLM Engine](../engines/docling-vlm.md)
- [PyMuPDF Engine](../engines/pymupdf.md)
- [Marker Engine](../engines/marker.md)
