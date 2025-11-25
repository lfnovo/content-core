from typing import Dict, Optional, Union

from ai_prompter import Prompter
from esperanto import LanguageModel
from pydantic import BaseModel, Field

from content_core.common.retry import retry_llm
from content_core.logging import logger
from content_core.models import ModelFactory


class TemplatedMessageInput(BaseModel):
    system_prompt_template: Optional[str] = None
    system_prompt_text: Optional[str] = None
    user_prompt_template: Optional[str] = None
    user_prompt_text: Optional[str] = None
    data: Optional[Union[Dict, BaseModel]] = Field(default_factory=lambda: {})
    config: Dict = Field(
        description="The config for the LLM",
        default={
            "temperature": 0,
            "top_p": 1,
            "max_tokens": 600,
        },
    )


@retry_llm()
async def _execute_llm_call(model: LanguageModel, msgs: list) -> str:
    """Internal function to execute LLM call - wrapped with retry logic."""
    result = await model.achat_complete(msgs)
    return result.content


async def templated_message(
    input: TemplatedMessageInput, model: Optional[LanguageModel] = None
) -> Optional[str]:
    """
    Execute a templated LLM message with retry logic for transient failures.

    Args:
        input: TemplatedMessageInput with prompt templates and data
        model: Optional LanguageModel instance (defaults to factory model)

    Returns:
        Optional[str]: LLM response content, or None if all retries exhausted
    """
    if not model:
        model = ModelFactory.get_model("default_model")

    msgs = []
    if input.system_prompt_template or input.system_prompt_text:
        system_prompt = Prompter(
            prompt_template=input.system_prompt_template,
            template_text=input.system_prompt_text,
        ).render(data=input.data)
        msgs.append({"role": "system", "content": system_prompt})

    if input.user_prompt_template or input.user_prompt_text:
        user_prompt = Prompter(
            prompt_template=input.user_prompt_template,
            template_text=input.user_prompt_text,
        ).render(data=input.data)
        msgs.append({"role": "user", "content": user_prompt})

    try:
        return await _execute_llm_call(model, msgs)
    except Exception as e:
        logger.error(f"LLM call failed after retries: {e}")
        return None
