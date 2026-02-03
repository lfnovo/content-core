#!/usr/bin/env python
"""
Create a synthetic benchmark PDF for testing PDF extraction engines.

This PDF contains:
- Multiple heading levels
- Text paragraphs
- A data table
- Mathematical formulas (LaTeX-style text)
- An embedded image/figure

Usage:
    uv run python scripts/create_benchmark_pdf.py [output_path]
"""

import io
import sys

from fpdf import FPDF
from fpdf.enums import XPos, YPos


def create_sample_image():
    """Create a simple chart image using matplotlib if available."""
    try:
        import matplotlib.pyplot as plt
        import numpy as np

        fig, ax = plt.subplots(figsize=(4, 3))
        x = np.linspace(0, 2 * np.pi, 100)
        ax.plot(x, np.sin(x), label="sin(x)", linewidth=2)
        ax.plot(x, np.cos(x), label="cos(x)", linewidth=2)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_title("Trigonometric Functions")
        ax.legend()
        ax.grid(True, alpha=0.3)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        plt.close()
        buf.seek(0)
        return buf
    except ImportError:
        return None


def create_benchmark_pdf(output_path: str):
    """Create a benchmark PDF with various content types."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Page 1
    pdf.add_page()

    # Title (H1)
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(0, 15, "Benchmark Document for PDF Extraction", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(5)

    # Subtitle
    pdf.set_font("Helvetica", "I", 12)
    pdf.cell(0, 8, "A synthetic test document with headers, tables, formulas, and images", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(10)

    # Section 1: Introduction (H2)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "1. Introduction", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 11)
    intro_text = (
        "This document is designed to test PDF extraction engines. It contains various "
        "elements commonly found in technical documents: headings at multiple levels, "
        "paragraphs of text, data tables, mathematical formulas, and figures. "
        "The goal is to evaluate how well each extraction engine preserves the structure "
        "and content of the original document."
    )
    pdf.multi_cell(0, 6, intro_text)
    pdf.ln(5)

    # Section 2: Mathematical Formulas (H2)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "2. Mathematical Formulas", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, "This section contains mathematical formulas in LaTeX notation:")
    pdf.ln(3)

    # Subsection 2.1 (H3)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "2.1 Famous Equations", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 11)
    formulas = [
        ("Einstein's mass-energy equivalence:", "E = mc^2"),
        ("Euler's identity:", "e^(i*pi) + 1 = 0"),
        ("Pythagorean theorem:", "a^2 + b^2 = c^2"),
        ("Quadratic formula:", "x = (-b +/- sqrt(b^2 - 4ac)) / 2a"),
    ]

    for desc, formula in formulas:
        pdf.cell(0, 6, f"  - {desc}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Courier", "", 11)
        pdf.cell(0, 6, f"      {formula}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 11)

    pdf.ln(3)

    # Subsection 2.2 (H3)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "2.2 LaTeX Block Formula", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, "The Schrodinger equation in Dirac notation:")
    pdf.ln(2)

    pdf.set_font("Courier", "", 10)
    pdf.cell(0, 6, "    $$i*hbar * d/dt |psi(t)> = H |psi(t)>$$", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 11)
    pdf.ln(5)

    # Section 3: Data Table (H2)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "3. Data Table", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, "The following table shows benchmark results for different algorithms:")
    pdf.ln(3)

    # Table header
    col_widths = [50, 35, 35, 35]
    headers = ["Algorithm", "Time (ms)", "Memory (MB)", "Accuracy (%)"]

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(220, 220, 220)
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 8, header, border=1, fill=True, align="C")
    pdf.ln()

    # Table data
    pdf.set_font("Helvetica", "", 10)
    data = [
        ["Quick Sort", "45.2", "12.5", "100.0"],
        ["Merge Sort", "52.8", "24.0", "100.0"],
        ["Bubble Sort", "1250.3", "8.2", "100.0"],
        ["Neural Net", "89.5", "256.0", "98.7"],
    ]

    for row in data:
        for i, cell in enumerate(row):
            align = "L" if i == 0 else "R"
            pdf.cell(col_widths[i], 7, cell, border=1, align=align)
        pdf.ln()

    pdf.ln(5)

    # Section 4: Figure (H2)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "4. Figure", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, "Figure 1 below shows a plot of trigonometric functions:")
    pdf.ln(3)

    # Add image if matplotlib is available
    image_buf = create_sample_image()
    if image_buf:
        pdf.image(image_buf, x=30, w=150)
        pdf.ln(5)
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 6, "Figure 1: Plot of sin(x) and cos(x) functions over [0, 2*pi]", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    else:
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 6, "[Image placeholder - matplotlib not available]", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

    pdf.ln(5)

    # Section 5: Conclusion (H2)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "5. Conclusion", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 11)
    conclusion_text = (
        "This benchmark document provides a standardized test case for evaluating PDF "
        "extraction engines. A successful extraction should preserve:\n\n"
        "  1. Document structure (headings, sections)\n"
        "  2. Table formatting and data\n"
        "  3. Mathematical formulas\n"
        "  4. Figure references\n"
        "  5. Text formatting (bold, italic)\n\n"
        "The extracted content can be compared against this source to measure extraction quality."
    )
    pdf.multi_cell(0, 6, conclusion_text)
    pdf.ln(5)

    # References section
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "References", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 10)
    references = [
        "[1] Smith, J. (2024). PDF Extraction Methods. Journal of Document Processing, 15(3), 45-67.",
        "[2] Johnson, A. & Lee, B. (2023). Benchmarking Document AI Systems. arXiv:2301.12345.",
        "[3] Williams, C. (2024). OCR in the Age of Large Language Models. ACM Computing Surveys.",
    ]
    for ref in references:
        pdf.multi_cell(0, 5, ref)
        pdf.ln(1)

    # Save
    pdf.output(output_path)
    print(f"Created benchmark PDF: {output_path}")

    # Report stats
    import os
    size_kb = os.path.getsize(output_path) / 1024
    print(f"Size: {size_kb:.1f} KB")
    print(f"Pages: {pdf.page}")


if __name__ == "__main__":
    output_path = sys.argv[1] if len(sys.argv) > 1 else "tests/input_content/benchmark.pdf"
    create_benchmark_pdf(output_path)
