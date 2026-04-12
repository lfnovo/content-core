"""Reddit post extraction via public JSON endpoint."""
import re
from urllib.parse import urlparse, urlunparse

import aiohttp

from content_core.common.retry import retry_url_network
from content_core.config import ContentCoreConfig
from content_core.logging import logger
from content_core.common.state import ExtractionOutput

# Matches reddit.com post URLs (with or without trailing slug/slash)
REDDIT_POST_PATTERN = re.compile(
    r"https?://(?:www\.|old\.|new\.)?reddit\.com/r/\w+/comments/\w+"
)


def is_reddit_post(url: str) -> bool:
    """Check if a URL is a Reddit post."""
    return bool(REDDIT_POST_PATTERN.match(url))


@retry_url_network()
async def _fetch_reddit_json(url: str) -> dict:
    """Fetch Reddit post data via the public .json endpoint."""
    parsed = urlparse(url)
    clean_path = parsed.path.rstrip("/")
    clean_url = urlunparse((parsed.scheme, parsed.netloc, clean_path, "", "", ""))
    json_url = clean_url + ".json"

    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get(
            json_url,
            headers={"User-Agent": "content-core/2.0"},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            resp.raise_for_status()
            return await resp.json()


def _format_comment(comment_data: dict, depth: int = 0) -> str:
    """Format a single comment and its replies recursively."""
    if comment_data.get("kind") != "t1":
        return ""

    data = comment_data["data"]
    author = data.get("author", "[deleted]")
    body = data.get("body", "").strip()
    score = data.get("score", 0)

    if not body or body == "[deleted]" or body == "[removed]":
        return ""

    indent = "  " * depth
    lines = [f"{indent}**u/{author}** (score: {score}):", ""]
    for line in body.split("\n"):
        lines.append(f"{indent}> {line}")
    lines.append("")

    # Recurse into replies
    replies = data.get("replies")
    if isinstance(replies, dict):
        for child in replies["data"]["children"]:
            reply_text = _format_comment(child, depth + 1)
            if reply_text:
                lines.append(reply_text)

    return "\n".join(lines)


def _format_reddit_post(data: list) -> tuple[str, str]:
    """Format Reddit JSON response into markdown.

    Returns (title, content) tuple.
    """
    # First listing: the post itself
    post = data[0]["data"]["children"][0]["data"]
    title = post.get("title", "")
    author = post.get("author", "[deleted]")
    subreddit = post.get("subreddit", "")
    score = post.get("score", 0)
    selftext = post.get("selftext", "")
    url = post.get("url", "")

    lines = [
        f"# {title}",
        "",
        f"**r/{subreddit}** | **u/{author}** | score: {score}",
        "",
    ]

    if selftext:
        lines.extend([selftext, ""])

    # If it's a link post (not self-post), include the linked URL
    if not post.get("is_self", True) and url:
        lines.extend([f"Link: {url}", ""])

    # Second listing: comments
    if len(data) > 1:
        comments = data[1]["data"]["children"]
        comment_texts = []
        for comment in comments:
            formatted = _format_comment(comment)
            if formatted:
                comment_texts.append(formatted)

        if comment_texts:
            lines.extend(["---", "", "## Comments", ""])
            lines.extend(comment_texts)

    return title, "\n".join(lines)


async def extract_reddit(url: str, config: ContentCoreConfig) -> ExtractionOutput:
    """Extract a Reddit post with comments via the public JSON endpoint."""
    try:
        data = await _fetch_reddit_json(url)
        title, content = _format_reddit_post(data)

        return ExtractionOutput(
            content=content,
            title=title,
            source_type="url",
            identified_type="reddit",
        )
    except Exception as e:
        logger.warning(f"Reddit JSON extraction failed for {url}: {e}")
        # Return empty — the caller can fall back to normal URL extraction
        return None
