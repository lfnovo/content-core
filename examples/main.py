#!/usr/bin/env python3
"""Content Core — Usage Examples"""
import asyncio

from content_core import extract_content, summarize, ContentCoreConfig


async def main():
    # Extract from text
    result = await extract_content(content="Hello, world!")
    print(f"Text: {result.content}")
    print()

    # Extract from URL
    result = await extract_content(url="https://example.com")
    print(f"URL title: {result.title}")
    print(f"URL content: {result.content[:200]}...")
    print()

    # Extract from file
    result = await extract_content(file_path="document.pdf")
    print(f"File content: {result.content[:200]}...")
    print()

    # Extract with engine override
    config = ContentCoreConfig(url_engine="simple")
    result = await extract_content(url="https://example.com", config=config)
    print(f"Simple engine: {result.content[:200]}...")
    print()

    # Summarize (requires OPENAI_API_KEY)
    long_text = "..."  # some long text
    summary = await summarize(long_text, context="bullet points")
    print(f"Summary: {summary}")


if __name__ == "__main__":
    asyncio.run(main())
