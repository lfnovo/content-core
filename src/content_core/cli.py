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
    help="Override extraction engine (URL: firecrawl, jina, crawl4ai, simple; Document: docling, simple)",
)
@click.option("--formulas", is_flag=True, default=False, help="Enable formula extraction (Docling only)")
@click.option("--pictures", is_flag=True, default=False, help="Enable image description + chart extraction (Docling only)")
@click.option("--no-ocr", "no_ocr", is_flag=True, default=False, help="Disable OCR (Docling only)")
def extract(source, fmt, engine, formulas, pictures, no_ocr):
    """Extract content from a URL, file path, or text."""
    from content_core.extraction import extract_content

    inp = _build_input(source)
    config = _build_config(inp, engine, formulas=formulas, pictures=pictures, no_ocr=no_ocr)
    result = asyncio.run(extract_content(url=inp.url, file_path=inp.file_path, content=inp.content, config=config))

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


@cli.group()
def config():
    """Manage persistent configuration (~/.content-core/config.toml).

    \b
    Available keys:
      audio_concurrency    Parallel transcription limit (1-10, default: 3)
      crawl4ai_api_url     Crawl4AI Docker API URL (default: none, uses local mode)
      audio_model          Override STT model
      audio_provider       Override STT provider
      docling_output_format  Docling output format (default: markdown)
      document_engine      Document extraction engine (auto, simple, docling)
      firecrawl_api_url    Firecrawl API URL
      firecrawl_proxy      Firecrawl proxy mode: auto, basic, stealth (default: auto)
      firecrawl_wait_for   Firecrawl wait time in ms before extraction (default: 3000)
      llm_model            LLM model for summarization (default: gpt-4o-mini)
      llm_provider         LLM provider (default: openai)
      stt_model            Speech-to-text model (default: whisper-1)
      stt_provider         Speech-to-text provider (default: openai)
      stt_timeout          STT API timeout in seconds (default: 3600)
      summary_model        Override LLM model for summarization
      url_engine           URL extraction engine (auto, simple, firecrawl, jina, crawl4ai)
      youtube_languages    Transcript languages, comma-separated (default: en,es,pt)
      docling_formulas     Enable formula extraction (default: false)
      docling_ocr          Enable OCR for scanned PDFs (default: true)
      docling_vision       Enable image description + chart extraction (default: false)
    """
    pass


@config.command("list")
def config_list_cmd():
    """List all config values from the config file."""
    from content_core.config import config_list, CONFIG_FILE

    data = config_list()
    if not data:
        click.echo(f"No values set. Use 'content-core config set <key> <value>' to configure.")
        click.echo(f"File: {CONFIG_FILE}")
        click.echo(f"Run 'content-core config --help' to see available keys.")
        return
    for key, value in sorted(data.items()):
        click.echo(f"{key} = {value}")


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set_cmd(key, value):
    """Set a config value.

    \b
    Examples:
      content-core config set llm_provider anthropic
      content-core config set llm_model claude-sonnet-4-20250514
      content-core config set url_engine firecrawl
      content-core config set youtube_languages en,pt,es
    """
    from content_core.config import config_set

    try:
        config_set(key, value)
        click.echo(f"{key} = {value}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@config.command("delete")
@click.argument("key")
def config_delete_cmd(key):
    """Delete a config value from the config file."""
    from content_core.config import config_delete

    try:
        config_delete(key)
        click.echo(f"Deleted: {key}")
    except KeyError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


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


def _build_config(inp, engine, formulas=False, pictures=False, no_ocr=False):
    """Build ContentCoreConfig routing --engine and docling flags."""
    docling_overrides = {}
    if formulas:
        docling_overrides["docling_formulas"] = True
    if pictures:
        docling_overrides["docling_vision"] = True
    if no_ocr:
        docling_overrides["docling_ocr"] = False

    if not engine and not docling_overrides:
        return None

    from content_core.config import ContentCoreConfig

    kwargs = {**docling_overrides}
    if engine:
        if inp.file_path:
            kwargs["document_engine"] = engine
        else:
            kwargs["url_engine"] = engine

    return ContentCoreConfig(**kwargs) if kwargs else None


def _build_input(source):
    """Detect whether source is URL, file, or text and build ExtractionInput."""
    import os

    import validators

    from content_core.common.state import ExtractionInput

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

    if validators.url(content):
        result = await extract_content(url=content)
        return result.content or content
    if os.path.exists(content):
        result = await extract_content(file_path=content)
        return result.content or content
    return content
