from typing import Dict, Optional, Union

from esperanto import LanguageModel
from esperanto.common_types import Message
from pydantic import BaseModel, Field

from content_core.models import ModelFactory
from content_core.prompter import Prompter


class TemplatedMessageInput(BaseModel):
    system_prompt_template: Optional[str] = ""
    system_prompt_text: Optional[str] = ""
    user_prompt_template: Optional[str] = ""
    user_prompt_text: Optional[str] = ""
    data: Optional[Union[Dict, BaseModel]] = Field(default_factory=lambda: {})
    config: Dict = Field(
        description="The config for the LLM",
        default={
            "temperature": 0,
            "top_p": 1,
            "max_tokens": 600,
        },
    )


async def templated_message(
    input: TemplatedMessageInput, model: Optional[LanguageModel] = None
) -> str:
    if not model:
        model = ModelFactory.get_model('default_model')

    msgs = []
    if input.system_prompt_template or input.system_prompt_text:
        msgs.append(
            Message(
                role="system",
                content=Prompter(
                    prompt_template=input.system_prompt_template,
                    prompt_text=input.system_prompt_text,
                ).render(data=input.data),
            )
        )

    if input.user_prompt_template or input.user_prompt_text:
        msgs.append(
            Message(
                role="user",
                content=Prompter(
                    prompt_template=input.user_prompt_template,
                    prompt_text=input.user_prompt_text,
                ).render(data=input.data),
            )
        )

    result = await model.achat_complete(msgs)
    return result.content
