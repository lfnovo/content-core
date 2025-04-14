from functools import partial

from content_core.config import SUMMARY_MODEL
from content_core.templated_message import TemplatedMessageInput, templated_message


async def summarize(content: str, context: str) -> str:
    templated_message_fn = partial(templated_message, model=SUMMARY_MODEL)
    response = await templated_message_fn(
        TemplatedMessageInput(
            user_prompt_template="content/summarize",
            data={"content": content, "context": context},
        )
    )
    return response
