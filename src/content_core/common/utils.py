import os
import re
import validators

from .state import ProcessSourceInput


async def process_input_content(content: str) -> str:
    """
    Process input content to handle URLs and file paths.
    If the input is a URL or file path, extract the content from it.
    """
    # Check if content is a URL
    if validators.url(content):
        from content_core.extraction import extract_content
        content_input = ProcessSourceInput(url=content)
        extracted = await extract_content(content_input)
        return extracted.content if extracted.content else str(extracted)

    # Check if content is a file path (simplified check for demonstration)
    if re.match(r"^[a-zA-Z0-9_/\-\.]+\.[a-zA-Z0-9]+$", content):
        if os.path.exists(content):
            from content_core.extraction import extract_content
            content_input = ProcessSourceInput(file_path=content)
            extracted = await extract_content(content_input)
            return extracted.content if extracted.content else str(extracted)
        else:
            raise ValueError(f"File not found: {content}")

    # If neither URL nor file path, return content as is
    return content
