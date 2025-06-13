from functools import partial

from content_core.models import ModelFactory
from content_core.templated_message import TemplatedMessageInput, templated_message


async def summarize(content: str, context: str) -> str:
    templated_message_fn = partial(templated_message, model=ModelFactory.get_model('summary_model'))
    response = await templated_message_fn(
        TemplatedMessageInput(
            user_prompt_template="prompts/content/summarize",
            data={"content": content, "context": context},
        )
    )
    return response
