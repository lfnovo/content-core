from functools import partial
from typing import Optional

from content_core.config import ContentCoreConfig
from content_core.models import ModelFactory
from content_core.templated_message import TemplatedMessageInput, templated_message


async def summarize(
    content: str, context: str, config: Optional[ContentCoreConfig] = None
) -> str:
    model = ModelFactory.get_model("summary_model", config=config)
    templated_message_fn = partial(templated_message, model=model)
    response = await templated_message_fn(
        TemplatedMessageInput(
            user_prompt_template="content/summarize",
            data={"content": content, "context": context},
        )
    )
    return response
