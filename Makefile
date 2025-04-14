test:
	uv run pytest -v
    
build-docs:
	repomix . --include "**/*.py,**/*.yaml" --compress --style xml -o ai_docs/core.txt

ruff:
	ruff check . --fix
