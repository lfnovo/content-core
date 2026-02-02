# DOCX Extraction Benchmark

Comparison of DOCX extraction engines in Content Core using a synthetic benchmark document with headers, tables, formulas, and formatting.

## Latest Results

**Test File:** benchmark.docx (37.2 KB)
**Date:** 2026-02-02

### Performance Summary

| Engine | Time | Memory | Quality | License |
|--------|------|--------|---------|---------|
| **python-docx** | 0.1s | 7MB | 100% | MIT |
| **docling** | 5.9s | 127MB | 100% | MIT |

### Quality Score Breakdown

The quality score measures how many expected elements were found in the extracted content:

| Category | Elements Checked |
|----------|------------------|
| Title | "Benchmark Document for DOCX Extraction" |
| Sections | Introduction, Mathematical Formulas, Data Table, Figure, Conclusion, References |
| Subsections | Famous Equations, Block Formula |
| Formulas | E=mc², Euler's identity, Pythagorean theorem, Quadratic formula |
| Table Data | Quick Sort, Merge Sort, Bubble Sort, Neural Net, specific values |
| Figure | Figure 1, sin(x), cos(x) |
| Formatting | bold, italic |
| Lists | First item, Second item |

### Engine Analysis

#### python-docx

- **Strengths:** Extremely fast (0.1s), low memory, simple API
- **Weaknesses:** Basic formatting, no advanced structure detection
- **Best For:** Simple documents, speed-critical applications

#### Docling

- **Strengths:** Full structure preservation, table detection, better formatting
- **Weaknesses:** Higher memory usage, slower than python-docx
- **Best For:** Complex documents, when structure matters

## When to Use Each Engine

| Use Case | Recommended Engine |
|----------|-------------------|
| Simple text extraction | python-docx |
| Table-heavy documents | docling |
| Speed priority | python-docx |
| Quality priority | docling |
| Low memory environment | python-docx |

## Running Benchmarks

### Run All DOCX Engines

```bash
uv run python scripts/benchmark.py --type docx --files benchmark.docx
```

### Run Specific Engine

```bash
uv run python scripts/benchmark.py --type docx --engines docling
```

## Benchmark Methodology

### Test Document

The benchmark uses a synthetic DOCX (`tests/input_content/benchmark.docx`) containing:

- **Headers:** Multiple levels (Heading 1, Heading 2)
- **Mathematical Formulas:** Text-based equations (E=mc², etc.)
- **Tables:** Algorithm comparison table
- **Formatting:** Bold, italic, underline text
- **Lists:** Numbered and bulleted lists
- **Figure Reference:** Trigonometric function description

### Scoring Algorithm

```python
score = found_elements / total_elements

# Elements checked:
# - Title presence
# - Section headings
# - Formula text patterns
# - Table data values
# - Formatting keywords
# - List items
```

### Metrics Collected

| Metric | Description |
|--------|-------------|
| Time | Total extraction time in seconds |
| Memory | Peak memory usage during extraction |
| Size | Output file size in KB |
| Quality | Percentage of expected elements found |

## Output Comparison

### python-docx Output

```markdown
# Benchmark Document for DOCX Extraction

## 1. Introduction

This document is designed to test DOCX extraction...

| Algorithm | Time (ms) | Memory (MB) |
|-----------|-----------|-------------|
| Quick Sort | 45.2 | 12.4 |
```

### Docling Output

```markdown
# Benchmark Document for DOCX Extraction

A synthetic test document with headers, tables...

## 1. Introduction

This document is designed to test DOCX extraction...

| **Algorithm** | **Time (ms)** | **Memory (MB)** |
|---------------|---------------|-----------------|
| Quick Sort | 45.2 | 12.4 |
```

**Note:** Docling preserves bold formatting in table headers.

## Historical Results

Results may vary based on:
- Hardware (CPU, RAM)
- Library versions
- Document complexity

## Related Documentation

- [Engine Overview](../engines/overview.md)
- [Docling Engine](../engines/docling.md)
- [PDF Benchmark](./pdf-benchmark.md)
