"""
A prompt management module using Jinja to generate complex prompts with simple templates.
"""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Union

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, Template
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

load_dotenv()

prompt_path = "/Users/luisnovo/dev/projetos/content-core/prompts"

env = Environment(loader=FileSystemLoader(prompt_path))


@dataclass
class Prompter:
    """
    A class for managing and rendering prompt templates.

    Attributes:
        prompt_template (str, optional): The name of the prompt template file.
        prompt_variation (str, optional): The variation of the prompt template.
        prompt_text (str, optional): The raw prompt text.
        template (Union[str, Template], optional): The Jinja2 template object.
    """

    prompt_template: Optional[str] = None
    prompt_variation: Optional[str] = "default"
    prompt_text: Optional[str] = None
    template: Optional[Union[str, Template]] = None
    parser: Optional[Any] = None

    def __init__(self, prompt_template=None, prompt_text=None, parser=None):
        """
        Initialize the Prompter with either a template file or raw text.

        Args:
            prompt_template (str, optional): The name of the prompt template file.
            prompt_text (str, optional): The raw prompt text.
        """
        self.prompt_template = prompt_template
        self.prompt_text = prompt_text
        self.parser = parser
        self.setup()

    def setup(self):
        """
        Set up the Jinja2 template based on the provided template file or text.
        Raises:
            ValueError: If neither prompt_template nor prompt_text is provided.
        """
        if self.prompt_template:
            self.template = env.get_template(f"{self.prompt_template}.jinja")
        elif self.prompt_text:
            self.template = Template(self.prompt_text)
        else:
            raise ValueError("Prompter must have a prompt_template or prompt_text")

        assert self.prompt_template or self.prompt_text, "Prompt is required"

    def to_langchain(self):
        if isinstance(self.template, str):
            template_text = self.template
        else:
            # For file-based templates, read the raw content
            template_path = os.path.join("prompts", f"{self.prompt_template}.jinja")
            with open(template_path, "r") as f:
                template_text = f.read()
        return ChatPromptTemplate.from_template(template_text, template_format="jinja2")

    @classmethod
    def from_text(cls, text: str):
        """
        Create a Prompter instance from raw text, which can contain Jinja code.

        Args:
            text (str): The raw prompt text.

        Returns:
            Prompter: A new Prompter instance.
        """

        return cls(prompt_text=text)

    def render(self, data: Optional[Union[Dict, BaseModel]] = {}) -> str:
        """
        Render the prompt template with the given data.

        Args:
            data (Union[Dict, BaseModel]): The data to be used in rendering the template.
                Can be either a dictionary or a Pydantic BaseModel.

        Returns:
            str: The rendered prompt text.

        Raises:
            AssertionError: If the template is not defined or not a Jinja2 Template.
        """
        # Convert Pydantic model to dict if necessary
        data_dict = data.model_dump() if isinstance(data, BaseModel) else data
        data_dict["current_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.parser:
            data_dict["format_instructions"] = self.parser.get_format_instructions()
        assert self.template, "Prompter template is not defined"
        assert isinstance(self.template, Template), (
            "Prompter template is not a Jinja2 Template"
        )
        return self.template.render(data_dict)
