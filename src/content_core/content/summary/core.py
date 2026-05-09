from functools import partial
from typing import Optional

from content_core.config import ContentCoreConfig
from content_core.models import ModelFactory
from content_core.templated_message import TemplatedMessageInput, templated_message

SUMMARIZE_TEMPLATE = """\
You are an AI assistant for a personal study platform.

In this platform, your user collects various articles and content from the Internet for reference and study.

Your role is to summarize the selected content as densely as possible, helping the reader extract maximum value from it without reading the full text.
Focus solely on the content's value, avoiding unnecessary comments or messages.

The summary should be dense, rich in characters, and designed to create a powerful vector representation.
If the user provided additional context, follow its instructions. Otherwise, summary the whole content.

Do not return any acknowledgments or greetings—only the summary.

CONTENT:

{{ content }}

{% if context %}
CONTEXT:

User has provided the aditional context for your task:
{{context}}
{% endif %}

SUMMARY:"""


async def summarize(
    content: str, context: str, config: Optional[ContentCoreConfig] = None
) -> str:
    model = ModelFactory.get_model("summary_model", config=config)
    templated_message_fn = partial(templated_message, model=model)
    response = await templated_message_fn(
        TemplatedMessageInput(
            user_prompt_text=SUMMARIZE_TEMPLATE,
            data={"content": content, "context": context},
        )
    )
    return response
