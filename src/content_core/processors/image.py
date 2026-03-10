"""Image processing using vision models via Esperanto."""
import asyncio
import os
from typing import Any, Dict

from content_core.common import ProcessSourceState
from content_core.logging import logger


async def extract_image(data: ProcessSourceState) -> Dict[str, Any]:
    """
    Extract content from an image file using a vision model.

    If vision_provider and vision_model are configured in state,
    uses Esperanto to analyze the image. Otherwise returns a placeholder.

    Args:
        data: ProcessSourceState with file_path pointing to an image file.

    Returns:
        Dict with content (image description) and title.
    """
    file_path = data.file_path
    assert file_path, "No file path provided"

    title = os.path.basename(file_path)

    if not data.vision_provider or not data.vision_model:
        logger.info("No vision model configured, skipping image analysis")
        return {
            "content": f"[Image: {title} - no vision model configured]",
            "title": title,
        }

    try:
        from esperanto import AIFactory
        from esperanto.utils.vision import create_image_message

        logger.info(
            f"Analyzing image with {data.vision_provider}/{data.vision_model}"
        )

        model = AIFactory.create_language(
            data.vision_provider, data.vision_model, config=data.vision_config
        )

        message = create_image_message(
            file_path,
            prompt="Describe this image in detail. Include any text, diagrams, charts, or visual elements you can identify.",
        )

        response = await model.achat_complete([message])
        description = response.choices[0].message.content or ""

        return {
            "content": f"# Image Analysis: {title}\n\n{description}",
            "title": title,
        }

    except Exception as e:
        logger.error(f"Image analysis failed: {e}")
        return {
            "content": f"[Image: {title} - analysis failed: {e}]",
            "title": title,
        }
