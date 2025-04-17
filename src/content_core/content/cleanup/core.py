from functools import partial

from content_core.models import ModelFactory
from content_core.templated_message import TemplatedMessageInput, templated_message


async def cleanup_content(content) -> str:
    templated_summary_fn = partial(templated_message, model=ModelFactory.get_model('cleanup_model'))
    input = TemplatedMessageInput(
        system_prompt_template="content/cleanup",
        user_prompt_text=content,
        data={"content": content},
    )
    result = await templated_summary_fn(input)
    return result
