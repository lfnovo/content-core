"""Content Core CLI — extract and summarize content."""
import asyncio
import sys

import click

from content_core.logging import configure_logging


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
def cli(debug):
    """Content Core — Extract and summarize content from any source."""
    if debug:
        configure_logging(debug=True)


@cli.command()
@click.argument("source")
@click.option(
    "-f",
    "--format",
    "fmt",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.option(
    "--engine",
    default=None,
    help="Override extraction engine (firecrawl, jina, crawl4ai, simple)",
)
def extract(source, fmt, engine):
    """Extract content from a URL, file path, or text."""
    from content_core.config import ContentCoreConfig
    from content_core.extraction import extract_content
    from content_core.models_v2 import ExtractionInput

    config = ContentCoreConfig(url_engine=engine) if engine else None
    inp = _build_input(source)
    result = asyncio.run(extract_content(inp, config=config))

    if fmt == "json":
        click.echo(result.model_dump_json(indent=2))
    else:
        click.echo(result.content)


@cli.command()
@click.argument("content", required=False)
@click.option("--context", default="", help="Context for summarization")
def summarize(content, context):
    """Summarize content using LLM with optional context."""
    from content_core.content.summary import summarize as summarize_fn

    content = _get_content(content)
    # If content looks like a URL or file, extract first
    content = asyncio.run(_maybe_extract(content))
    result = asyncio.run(summarize_fn(content, context))
    click.echo(result)


@cli.command()
def mcp():
    """Start the MCP server."""
    from content_core.mcp.server import main

    main()


def _get_content(content):
    """Get content from argument or stdin."""
    if content is None:
        if sys.stdin.isatty():
            click.echo(
                "Error: No content provided. Provide content or pipe input.", err=True
            )
            sys.exit(1)
        content = sys.stdin.read().strip()
    if not content:
        click.echo("Error: Empty input.", err=True)
        sys.exit(1)
    return content


def _build_input(source):
    """Detect whether source is URL, file, or text and build ExtractionInput."""
    import os

    import validators

    from content_core.models_v2 import ExtractionInput

    if validators.url(source):
        return ExtractionInput(url=source)
    if os.path.exists(source):
        return ExtractionInput(file_path=source)
    return ExtractionInput(content=source)


async def _maybe_extract(content: str) -> str:
    """If content is a URL or file path, extract it first."""
    import os

    import validators

    from content_core.extraction import extract_content
    from content_core.models_v2 import ExtractionInput

    if validators.url(content):
        result = await extract_content(ExtractionInput(url=content))
        return result.content or content
    if os.path.exists(content):
        result = await extract_content(ExtractionInput(file_path=content))
        return result.content or content
    return content
