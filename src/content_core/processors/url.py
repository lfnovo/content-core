import os

import aiohttp
from bs4 import BeautifulSoup
from readability import Document

from content_core.common import ProcessSourceState
from content_core.config import get_url_engine
from content_core.logging import logger
from content_core.processors.docling import DOCLING_SUPPORTED
from content_core.processors.office import SUPPORTED_OFFICE_TYPES
from content_core.processors.pdf import SUPPORTED_FITZ_TYPES


async def url_provider(state: ProcessSourceState):
    """
    Identify the provider
    """
    return_dict = {}
    url = state.url
    if url:
        if "youtube.com" in url or "youtu.be" in url:
            return_dict["identified_type"] = "youtube"
        else:
            # remote URL: check content-type to catch PDFs
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.head(
                        url, timeout=10, allow_redirects=True
                    ) as resp:
                        mime = resp.headers.get("content-type", "").split(";", 1)[0]
                        logger.debug(f"MIME type for {url}: {mime}")
            except Exception as e:
                logger.warning(f"HEAD check failed for {url}: {e}")
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


async def extract_url_bs4(url: str) -> dict:
    """
    Get the title and content of a URL using readability with a fallback to BeautifulSoup.

    Args:
        url (str): The URL of the webpage to extract content from.

    Returns:
        dict: A dictionary containing the 'title' and 'content' of the webpage.
    """
    async with aiohttp.ClientSession() as session:
        try:
            # Fetch the webpage content
            async with session.get(url, timeout=10) as response:
                if response.status != 200:
                    raise Exception(f"HTTP error: {response.status}")
                html = await response.text()

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
                print(f"Readability failed: {e}")
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
            print(f"Error processing URL {url}: {e}")
            return {
                "title": "Error",
                "content": f"Failed to extract content: {str(e)}",
            }


async def extract_url_jina(url: str):
    """
    Get the content of a URL using Jina. Uses Bearer token if JINA_API_KEY is set.
    """
    headers = {}
    api_key = os.environ.get("JINA_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://r.jina.ai/{url}", headers=headers) as response:
            text = await response.text()
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


async def extract_url_firecrawl(url: str):
    """
    Get the content of a URL using Firecrawl.
    Returns {"title": ..., "content": ...} or None on failure.
    """
    try:
        from firecrawl import AsyncFirecrawlApp

        app = AsyncFirecrawlApp(api_key=os.environ.get("FIRECRAWL_API_KEY"))
        scrape_result = await app.scrape_url(url, formats=["markdown", "html"])
        return {
            "title": scrape_result.metadata["title"] or scrape_result.title,
            "content": scrape_result.markdown,
        }

    except Exception as e:
        logger.error(f"Firecrawl extraction error for URL: {url}: {e}")
        return None


async def extract_url(state: ProcessSourceState):
    """
    Extract content from a URL using the url_engine specified in the state.
    Supported engines: 'auto', 'simple', 'firecrawl', 'jina'.
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
                    logger.debug("Falling back to BeautifulSoup")
                    return await extract_url_bs4(url)
        elif engine == "simple":
            return await extract_url_bs4(url)
        elif engine == "firecrawl":
            return await extract_url_firecrawl(url)
        elif engine == "jina":
            return await extract_url_jina(url)
        else:
            raise ValueError(f"Unknown engine: {engine}")
    except Exception as e:
        logger.error(f"URL extraction failed for URL: {url}")
        logger.exception(e)
        return None
