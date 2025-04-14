from typing import Dict, Union

from content_core.common import ProcessSourceInput, ProcessSourceOutput
from content_core.content.extraction.graph import graph

# todo: input/output schema do langgraph


async def extract_content(data: Union[ProcessSourceInput, Dict]) -> ProcessSourceOutput:
    if isinstance(data, dict):
        data = ProcessSourceInput(**data)
    result = await graph.ainvoke(data)
    return ProcessSourceOutput(**result)
