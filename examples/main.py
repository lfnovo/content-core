#!/usr/bin/env python3
"""
MarkDowny - Convert files and URLs to Markdown using Microsoft's MarkItDown library.

This script processes all files in the input_content/ directory and URLs from urls.txt,
converting them to Markdown format and saving the results to separate files.
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple
from urllib.parse import urlparse

from loguru import logger
from markitdown import MarkItDown


def setup_logging() -> None:
    """Configure logging with loguru."""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    logger.add(
        "processing.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="10 MB"
    )


def create_output_directory(output_dir: Path) -> None:
    """Create output directory if it doesn't exist."""
    output_dir.mkdir(exist_ok=True)
    logger.info(f"Output directory: {output_dir}")


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage."""
    # Remove or replace problematic characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename.strip()


def process_file(md_converter: MarkItDown, file_path: Path, output_dir: Path) -> bool:
    """
    Process a single file and convert it to Markdown.
    
    Args:
        md_converter: MarkItDown instance
        file_path: Path to the input file
        output_dir: Directory to save the output
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Processing file: {file_path.name}")
        
        # Convert file to markdown
        result = md_converter.convert(str(file_path))
        
        # Create output filename
        base_name = file_path.name  # Use full filename with extension
        safe_name = sanitize_filename(base_name.replace('.', '_'))
        output_filename = f"{safe_name}_converted.md"
        output_path = output_dir / output_filename
        
        # Create markdown content with metadata
        content = f"""# Converted from: {file_path.name}

**Source File:** {file_path.name}  
**Source Path:** {file_path}  
**Conversion Date:** {result.title if hasattr(result, 'title') else 'N/A'}  
**File Size:** {file_path.stat().st_size} bytes  

---

{result.text_content}
"""
        
        # Write to output file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logger.success(f"Successfully converted {file_path.name} -> {output_filename}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to process {file_path.name}: {str(e)}")
        return False


def process_url(md_converter: MarkItDown, url: str, output_dir: Path, index: int) -> bool:
    """
    Process a single URL and convert it to Markdown.
    
    Args:
        md_converter: MarkItDown instance
        url: URL to process
        output_dir: Directory to save the output
        index: Index for naming the output file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Processing URL: {url}")
        
        # Convert URL to markdown
        result = md_converter.convert(url)
        
        # Create output filename based on URL
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('www.', '')
        safe_domain = sanitize_filename(domain)
        output_filename = f"url_{index:02d}_{safe_domain}_converted.md"
        output_path = output_dir / output_filename
        
        # Create markdown content with metadata
        content = f"""# Converted from URL: {url}

**Source URL:** {url}  
**Domain:** {parsed_url.netloc}  
**Conversion Date:** {result.title if hasattr(result, 'title') else 'N/A'}  

---

{result.text_content}
"""
        
        # Write to output file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logger.success(f"Successfully converted {url} -> {output_filename}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to process URL {url}: {str(e)}")
        return False


def load_urls(urls_file: Path) -> List[str]:
    """Load URLs from the urls.txt file."""
    try:
        with open(urls_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        logger.info(f"Loaded {len(urls)} URLs from {urls_file}")
        return urls
    except Exception as e:
        logger.error(f"Failed to load URLs from {urls_file}: {str(e)}")
        return []


def get_input_files(input_dir: Path) -> List[Path]:
    """Get all files from the input directory, excluding audio/video files."""
    try:
        # Skip audio/video files for now
        skip_extensions = [] #{'.mp3', '.mp4', '.wav', '.avi', '.mov', '.mkv', '.m4a'}
        files = [f for f in input_dir.iterdir() 
                if f.is_file() and f.suffix.lower() not in skip_extensions]
        logger.info(f"Found {len(files)} files in {input_dir} (excluding audio/video)")
        return files
    except Exception as e:
        logger.error(f"Failed to read files from {input_dir}: {str(e)}")
        return []


def main():
    """Main function to orchestrate the conversion process."""
    setup_logging()
    logger.info("Starting MarkDowny processing...")
    
    # Setup paths
    project_root = Path(__file__).parent
    input_dir = project_root / "input_content"
    urls_file = project_root / "urls.txt"
    output_dir = project_root / "output"
    
    # Create output directory
    create_output_directory(output_dir)
    
    # Initialize MarkItDown
    md_converter = MarkItDown()
    
    # Process files
    files_processed = 0
    files_failed = 0
    
    if input_dir.exists():
        input_files = get_input_files(input_dir)
        logger.info(f"Processing {len(input_files)} files...")
        
        for file_path in input_files:
            if process_file(md_converter, file_path, output_dir):
                files_processed += 1
            else:
                files_failed += 1
    else:
        logger.warning(f"Input directory {input_dir} does not exist")
    
    # Process URLs
    urls_processed = 0
    urls_failed = 0
    
    if urls_file.exists():
        urls = load_urls(urls_file)
        logger.info(f"Processing {len(urls)} URLs...")
        
        for index, url in enumerate(urls, 1):
            if process_url(md_converter, url, output_dir, index):
                urls_processed += 1
            else:
                urls_failed += 1
    else:
        logger.warning(f"URLs file {urls_file} does not exist")
    
    # Summary
    logger.info("=" * 50)
    logger.info("PROCESSING SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Files: {files_processed} successful, {files_failed} failed")
    logger.info(f"URLs: {urls_processed} successful, {urls_failed} failed")
    logger.info(f"Total: {files_processed + urls_processed} successful, {files_failed + urls_failed} failed")
    logger.info(f"Output directory: {output_dir}")
    
    if files_failed + urls_failed > 0:
        logger.warning("Some items failed to process. Check the logs for details.")
        sys.exit(1)
    else:
        logger.success("All items processed successfully!")


if __name__ == "__main__":
    main()
