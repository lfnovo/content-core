import aiohttp
from bs4 import BeautifulSoup
from readability import Document

from content_core.common.retry import retry_url_network
from content_core.logging import logger


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
            if title_tag:
                title = title_tag.get("content", "") or title_tag.get_text(strip=True)
            else:
                title = "No title found"
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
