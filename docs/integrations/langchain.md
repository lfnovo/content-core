# LangChain Integration

Content Core provides LangChain-compatible tools for use in agents and chains.

## Available Tools

| Tool | Description |
|------|-------------|
| `extract_content_tool` | Extract content from URLs, files, or text |
| `cleanup_content_tool` | Clean and format extracted content |
| `summarize_content_tool` | Generate AI summaries |

## Installation

```bash
pip install content-core langchain
```

## Basic Usage

```python
from content_core.tools import (
    extract_content_tool,
    cleanup_content_tool,
    summarize_content_tool
)
from langchain.agents import initialize_agent, AgentType

# Create tools list
tools = [extract_content_tool, cleanup_content_tool, summarize_content_tool]

# Initialize agent
agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Run agent
result = agent.run("Extract the content from https://example.com and summarize it.")
```

## Tool Details

### extract_content_tool

Extracts content from various sources:

```python
from content_core.tools import extract_content_tool

# Extract from URL
result = extract_content_tool.run("https://example.com/article")

# Extract from file
result = extract_content_tool.run("/path/to/document.pdf")

# Extract from text
result = extract_content_tool.run("Raw text content here")
```

### cleanup_content_tool

Cleans and formats content:

```python
from content_core.tools import cleanup_content_tool

result = cleanup_content_tool.run("  Messy   content with   extra spaces  ")
```

### summarize_content_tool

Generates AI-powered summaries:

```python
from content_core.tools import summarize_content_tool

# Basic summary
result = summarize_content_tool.run("Long article text here...")

# With context
result = summarize_content_tool.run({
    "content": "Long article text here...",
    "context": "bullet points"
})
```

## Using with LangChain Agents

### ReAct Agent

```python
from langchain.agents import create_react_agent
from langchain_openai import ChatOpenAI
from content_core.tools import extract_content_tool, summarize_content_tool

llm = ChatOpenAI(model="gpt-4")
tools = [extract_content_tool, summarize_content_tool]

agent = create_react_agent(llm, tools, prompt)
result = agent.invoke({"input": "Summarize https://example.com"})
```

### Tool Calling Agent

```python
from langchain.agents import create_tool_calling_agent
from langchain_openai import ChatOpenAI
from content_core.tools import extract_content_tool

llm = ChatOpenAI(model="gpt-4")
tools = [extract_content_tool]

agent = create_tool_calling_agent(llm, tools, prompt)
```

## Configuration

Tools use Content Core's global configuration:

```python
from content_core.config import set_document_engine, set_url_engine

# Configure engines before using tools
set_document_engine("docling")
set_url_engine("firecrawl")
```

## Error Handling

Tools handle errors gracefully and return error messages:

```python
result = extract_content_tool.run("invalid://url")
# Returns error message instead of raising exception
```

## Source Code

Tools are located in `src/content_core/tools/`:

- `extract.py` - Extract content tool
- `cleanup.py` - Cleanup content tool
- `summarize.py` - Summarize content tool
