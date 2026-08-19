"""Image processing using vision models via Esperanto."""
import os

from content_core.common.state import ExtractionOutput
from content_core.config import ContentCoreConfig
from content_core.logging import logger


SUPPORTED_IMAGE_TYPES = [
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/tiff",
    "image/bmp",
]


async def extract_image(file_path: str, config: ContentCoreConfig) -> ExtractionOutput:
    """Extract content from an image file using a vision model.

    If `vision_provider` and `vision_model` are configured, uses Esperanto to
    analyze the image. Otherwise returns a placeholder.
    """
    title = os.path.basename(file_path)

    if not config.vision_provider or not config.vision_model:
        logger.info("No vision model configured, skipping image analysis")
        return ExtractionOutput(
            content=f"[Image: {title} - no vision model configured]",
            title=title,
            source_type="file",
        )

    try:
        from esperanto import AIFactory
        from esperanto.utils.vision import create_image_message

        logger.info(
            f"Analyzing image with {config.vision_provider}/{config.vision_model}"
        )

        model = AIFactory.create_language(
            config.vision_provider, config.vision_model, config=config.vision_config
        )

        message = create_image_message(
            file_path,
            prompt=(
                "Describe this image in detail. Include any text, diagrams, "
                "charts, or visual elements you can identify."
            ),
        )

        response = await model.achat_complete([message])
        description = response.choices[0].message.content or ""

        return ExtractionOutput(
            content=f"# Image Analysis: {title}\n\n{description}",
            title=title,
            source_type="file",
        )

    except Exception as e:
        logger.error(f"Image analysis failed: {e}")
        return ExtractionOutput(
            content=f"[Image: {title} - analysis failed: {e}]",
            title=title,
            source_type="file",
        )
