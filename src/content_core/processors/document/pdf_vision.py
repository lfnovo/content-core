"""PDF processing with vision model analysis of rendered pages."""
import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from content_core.common.state import ExtractionOutput
from content_core.config import ContentCoreConfig
from content_core.logging import logger


async def get_pdf_page_count(file_path: str) -> int:
    """Get the number of pages in a PDF using pdfinfo."""
    cmd = ["pdfinfo", file_path]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(f"pdfinfo failed: {stderr.decode()}")

    for line in stdout.decode().split("\n"):
        if line.startswith("Pages:"):
            return int(line.split(":")[1].strip())

    raise RuntimeError("Could not determine page count from pdfinfo output")


def calculate_page_params(total_pages: int) -> Tuple[int, int]:
    """Return (step_size, max_pages) for PDF page sampling.

    Every page on every PDF. The earlier adaptive sampling
    (step=2 for medium docs, step=5/10 for large ones) was a cost
    guardrail from when vision output was the primary `full_text` and
    halving page count halved spend. With pdfplumber now providing
    full-text coverage and vision only enriching the "Visual analysis"
    insight, the insight needs to actually cover every page — otherwise
    figures/tables/layout from skipped pages are silently lost.

    No cap: a 500-page book yields 500 vision calls. If that becomes a
    problem in practice, gate large PDFs behind a user-confirmation step
    rather than silently truncating the analysis.
    """
    return (1, total_pages)


async def convert_pdf_to_images(
    file_path: str,
    dpi: int = 150,
    output_dir: Optional[str] = None,
) -> List[Tuple[str, int]]:
    """Convert PDF pages to images using pdftoppm with adaptive sampling.

    Returns:
        List of (image_path, page_number) tuples.
    """
    created_temp_dir = False
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="pdf_pages_")
        created_temp_dir = True

    try:
        total_pages = await get_pdf_page_count(file_path)
        logger.info(f"PDF has {total_pages} pages")

        step_size, max_pages = calculate_page_params(total_pages)
        logger.info(
            f"Using step_size={step_size}, max_pages={max_pages} for {total_pages} pages"
        )

        pages_to_convert = []
        for i in range(1, total_pages + 1, step_size):
            pages_to_convert.append(i)
            if len(pages_to_convert) >= max_pages:
                break

        logger.info(f"Converting {len(pages_to_convert)} pages from PDF")

        results = []
        for page_num in pages_to_convert:
            output_prefix = os.path.join(output_dir, f"page_{page_num:04d}")
            cmd = [
                "pdftoppm",
                "-png",
                "-r", str(dpi),
                "-f", str(page_num),
                "-l", str(page_num),
                file_path,
                output_prefix,
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.warning(f"pdftoppm failed for page {page_num}: {stderr.decode()}")
                continue

            output_files = list(Path(output_dir).glob(f"page_{page_num:04d}*.png"))
            if output_files:
                results.append((str(output_files[0]), page_num))

        logger.info(f"Successfully converted {len(results)} PDF pages to images")

        if not results and created_temp_dir and os.path.isdir(output_dir):
            shutil.rmtree(output_dir, ignore_errors=True)

        return results

    except Exception as e:
        logger.error(f"PDF conversion failed: {e}")
        if created_temp_dir and output_dir and os.path.isdir(output_dir):
            shutil.rmtree(output_dir, ignore_errors=True)
        raise


async def _analyze_page(
    image_path: str,
    page_num: int,
    model,
    semaphore: asyncio.Semaphore,
) -> Tuple[int, str]:
    """Analyze a single PDF page image with the vision model."""
    async with semaphore:
        try:
            from esperanto.utils.vision import create_image_message

            message = create_image_message(
                image_path,
                prompt=(
                    f"Describe the content of this PDF page (page {page_num}) in detail. "
                    "Include any text, tables, figures, charts, diagrams, or formulas you can identify. "
                    "Preserve the structure and meaning of the content."
                ),
            )

            response = await model.achat_complete([message])
            description = response.choices[0].message.content or ""
            return (page_num, description)

        except Exception as e:
            logger.warning(f"Page {page_num} analysis failed: {e}")
            return (page_num, f"[Page {page_num} analysis failed: {e}]")


async def extract_pdf_with_vision(
    file_path: str, config: ContentCoreConfig
) -> ExtractionOutput:
    """Process a PDF file using vision-model analysis of rendered pages.

    Pipeline:
      1. Convert pages to images (adaptive sampling).
      2. Analyze pages in parallel with vision model.
      3. Combine page descriptions into document content.
    """
    title = os.path.basename(file_path)
    pages_dir = None

    try:
        from esperanto import AIFactory

        pages_dir = tempfile.mkdtemp(prefix="pdf_pages_")
        page_images = await convert_pdf_to_images(file_path, output_dir=pages_dir)

        if not page_images:
            logger.warning("No pages converted from PDF")
            return ExtractionOutput(
                content=f"[PDF: {title} - no pages could be converted]",
                title=title,
                source_type="file",
            )

        model = AIFactory.create_language(
            config.vision_provider, config.vision_model, config=config.vision_config
        )

        semaphore = asyncio.Semaphore(5)
        tasks = [
            _analyze_page(image_path, page_num, model, semaphore)
            for image_path, page_num in page_images
        ]
        page_descriptions = await asyncio.gather(*tasks)

        content_parts = [f"# Document: {title}\n"]
        for page_num, desc in sorted(page_descriptions, key=lambda x: x[0]):
            content_parts.append(f"## Page {page_num}\n\n{desc}\n")

        return ExtractionOutput(
            content="\n".join(content_parts),
            title=title,
            source_type="file",
            metadata={"pages_analyzed": len(page_images)},
        )

    except Exception as e:
        logger.error(f"PDF vision processing failed: {e}")
        return ExtractionOutput(
            content=f"[PDF: {title} - vision processing failed: {e}]",
            title=title,
            source_type="file",
        )

    finally:
        if pages_dir and os.path.isdir(pages_dir):
            shutil.rmtree(pages_dir, ignore_errors=True)
