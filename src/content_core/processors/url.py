import os

import aiohttp
from bs4 import BeautifulSoup
from readability import Document

from content_core.common import ProcessSourceState
from content_core.common.retry import retry_url_api, retry_url_network
from content_core.config import (
    DEFAULT_FIRECRAWL_API_URL,
    get_firecrawl_api_url,
    get_url_engine,
)
from content_core.logging import logger
from content_core.processors.docling import DOCLING_SUPPORTED
from content_core.processors.office import SUPPORTED_OFFICE_TYPES
from content_core.processors.pdf import SUPPORTED_FITZ_TYPES


@retry_url_network()
async def _fetch_url_mime_type(url: str) -> str:
    """Internal function to fetch URL MIME type - wrapped with retry logic."""
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.head(url, timeout=10, allow_redirects=True) as resp:
            mime = resp.headers.get("content-type", "").split(";", 1)[0]
            logger.debug(f"MIME type for {url}: {mime}")
            return mime


async def url_provider(state: ProcessSourceState):
    """
    Identify the provider with retry logic for network requests.
    """
    return_dict = {}
    url = state.url
    if url:
        if "youtube.com" in url or "youtu.be" in url:
            return_dict["identified_type"] = "youtube"
        else:
            # remote URL: check content-type to catch PDFs
            try:
                mime = await _fetch_url_mime_type(url)
            except Exception as e:
                logger.warning(f"HEAD check failed for {url} after retries: {e}")
                mime = "article"
            if (
                mime in DOCLING_SUPPORTED
                or mime in SUPPORTED_FITZ_TYPES
                or mime in SUPPORTED_OFFICE_TYPES
            ):
                logger.debug(f"Identified type for {url}: {mime}")
                return_dict["identified_type"] = mime
            else:
                logger.debug(f"Identified type for {url}: article")
                return_dict["identified_type"] = "article"
    return return_dict


@retry_url_network()
async def _fetch_url_html(url: str) -> str:
    """Internal function to fetch URL HTML content - wrapped with retry logic."""
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get(url, timeout=10) as response:
            # Raise ClientResponseError so retry logic can inspect status code
            # (5xx and 429 will be retried, 4xx will not)
            response.raise_for_status()
            return await response.text()


async def extract_url_bs4(url: str) -> dict:
    """
    Get the title and content of a URL using readability with a fallback to BeautifulSoup.
    Includes retry logic for network failures.

    Args:
        url (str): The URL of the webpage to extract content from.

    Returns:
        dict: A dictionary containing the 'title' and 'content' of the webpage.
    """
    try:
        # Fetch the webpage content with retry
        html = await _fetch_url_html(url)

        # Try extracting with readability
        try:
            doc = Document(html)
            title = doc.title() or "No title found"
            # Extract content as plain text by parsing the cleaned HTML
            soup = BeautifulSoup(doc.summary(), "lxml")
            content = soup.get_text(separator=" ", strip=True)
            if not content.strip():
                raise ValueError("No content extracted by readability")
        except Exception as e:
            logger.debug(f"Readability failed: {e}")
            # Fallback to BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            # Extract title
            title_tag = (
                soup.find("title")
                or soup.find("h1")
                or soup.find("meta", property="og:title")
            )
            title = (
                title_tag.get_text(strip=True) if title_tag else "No title found"
            )
            # Extract content from common content tags
            content_tags = soup.select(
                'article, .content, .post, main, [role="main"], div[class*="content"], div[class*="article"]'
            )
            content = (
                " ".join(
                    tag.get_text(separator=" ", strip=True) for tag in content_tags
                )
                if content_tags
                else soup.get_text(separator=" ", strip=True)
            )
            content = content.strip() or "No content found"

        return {
            "title": title,
            "content": content,
        }

    except Exception as e:
        logger.error(f"Error processing URL {url} after retries: {e}")
        return {
            "title": "Error",
            "content": f"Failed to extract content: {str(e)}",
        }


@retry_url_api()
async def _fetch_url_jina(url: str, headers: dict) -> str:
    """Internal function to fetch URL content via Jina - wrapped with retry logic."""
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get(
            f"https://r.jina.ai/{url}", headers=headers
        ) as response:
            # Raise ClientResponseError so retry logic can inspect status code
            # (5xx and 429 will be retried, 4xx will not)
            response.raise_for_status()
            return await response.text()


async def extract_url_jina(url: str) -> dict:
    """
    Get the content of a URL using Jina. Uses Bearer token if JINA_API_KEY is set.
    Includes retry logic for transient API failures.

    Args:
        url (str): The URL to extract content from.
    """
    headers = {}
    api_key = os.environ.get("JINA_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        text = await _fetch_url_jina(url, headers)
        if text.startswith("Title:") and "\n" in text:
            title_end = text.index("\n")
            title = text[6:title_end].strip()
            content = text[title_end + 1 :].strip()
            logger.debug(
                f"Processed url: {url}, found title: {title}, content: {content[:100]}..."
            )
            return {"title": title, "content": content}
        else:
            logger.debug(
                f"Processed url: {url}, does not have Title prefix, returning full content: {text[:100]}..."
            )
            return {"content": text}
    except Exception as e:
        logger.error(f"Jina extraction failed for {url} after retries: {e}")
        raise


@retry_url_api()
async def _fetch_url_firecrawl(url: str) -> dict:
    """Internal function to fetch URL content via Firecrawl - wrapped with retry logic."""
    from firecrawl import AsyncFirecrawlApp

    # Note: firecrawl-py does not support client-side proxy configuration
    # Proxy must be configured on the Firecrawl server side

    # Get custom API URL for self-hosted instances
    api_url = get_firecrawl_api_url()
    if api_url != DEFAULT_FIRECRAWL_API_URL:
        logger.debug(f"Using custom Firecrawl API URL: {api_url}")

    app = AsyncFirecrawlApp(
        api_key=os.environ.get("FIRECRAWL_API_KEY"),
        api_url=api_url,
    )
    scrape_result = await app.scrape(url, formats=["markdown", "html"])
    return {
        "title": scrape_result.metadata.title or "",
        "content": scrape_result.markdown or "",
    }


async def extract_url_firecrawl(url: str) -> dict | None:
    """
    Get the content of a URL using Firecrawl.
    Returns {"title": ..., "content": ...} or None on failure.
    Includes retry logic for transient API failures.

    Note: Firecrawl does not support client-side proxy configuration.
    """
    try:
        return await _fetch_url_firecrawl(url)
    except Exception as e:
        logger.error(f"Firecrawl extraction failed for {url} after retries: {e}")
        return None

@retry_url_api()
async def _fetch_url_crawl4ai(url: str) -> dict:
    """Internal function to fetch URL content via Crawl4AI - wrapped with retry logic."""
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, ProxyConfig
    except ImportError:
        raise ImportError(
            "Crawl4AI is not installed. Install it with: pip install content-core[crawl4ai]"
        )

    # Crawl4AI doesn't read env vars automatically, so we bridge HTTP_PROXY to ProxyConfig
    proxy_url = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")

    # Configure proxy if available
    run_config = None
    if proxy_url:
        try:
            run_config = CrawlerRunConfig(
                proxy_config=ProxyConfig.from_string(proxy_url)
            )
            logger.debug(f"Crawl4AI using proxy from environment")
        except Exception as e:
            logger.warning(f"Failed to configure proxy for Crawl4AI: {e}")

    async with AsyncWebCrawler() as crawler:
        if run_config:
            result = await crawler.arun(url=url, config=run_config)
        else:
            result = await crawler.arun(url=url)

        # Extract title from metadata if available
        title = ""
        if hasattr(result, "metadata") and result.metadata:
            title = result.metadata.get("title", "")

        # Get markdown content
        content = result.markdown if hasattr(result, "markdown") else ""

        return {
            "title": title or "No title found",
            "content": content,
        }


async def extract_url_crawl4ai(url: str) -> dict | None:
    """
    Get the content of a URL using Crawl4AI (local browser automation).
    Returns {"title": ..., "content": ...} or None on failure.
    Includes retry logic for transient failures.

    Args:
        url (str): The URL to extract content from.
    """
    try:
        return await _fetch_url_crawl4ai(url)
    except Exception:
        return None

async def extract_url(state: ProcessSourceState):
    """
    Extract content from a URL using the url_engine specified in the state.
    Supported engines: 'auto', 'simple', 'firecrawl', 'jina', 'crawl4ai'.

    Proxy is configured via standard HTTP_PROXY/HTTPS_PROXY environment variables.
    """
    assert state.url, "No URL provided"
    url = state.url
    # Use environment-aware engine selection
    engine = state.url_engine or get_url_engine()
    try:
        if engine == "auto":
            if os.environ.get("FIRECRAWL_API_KEY"):
                logger.debug(
                    "Engine 'auto' selected: using Firecrawl (FIRECRAWL_API_KEY detected)"
                )
                return await extract_url_firecrawl(url)
            else:
                try:
                    logger.debug("Trying to use Jina to extract URL")
                    return await extract_url_jina(url)
                except Exception as e:
                    logger.error(f"Jina extraction error for URL: {url}: {e}")
                    # Try Crawl4AI before falling back to BeautifulSoup
                    logger.debug("Trying to use Crawl4AI to extract URL")
                    result = await extract_url_crawl4ai(url)
                    if result is not None:
                        return result
                    logger.debug(
                        "Crawl4AI failed or not installed, falling back to BeautifulSoup"
                    )
                    return await extract_url_bs4(url)
        elif engine == "simple":
            return await extract_url_bs4(url)
        elif engine == "firecrawl":
            return await extract_url_firecrawl(url)
        elif engine == "jina":
            return await extract_url_jina(url)
        elif engine == "crawl4ai":
            return await extract_url_crawl4ai(url)
        else:
            raise ValueError(f"Unknown engine: {engine}")
    except Exception as e:
        logger.error(f"URL extraction failed for URL: {url}")
        logger.exception(e)
        return None

