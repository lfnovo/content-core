.PHONY: tag test build-docs ruff mcp-server

tag:
	@version=$$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/'); \
	echo "Creating tag v$$version"; \
	git tag "v$$version"; \
	git push origin "v$$version"

test:
	uv run pytest -v
    
build-docs:
	repomix . --include "**/*.py,**/*.yaml" --compress --style xml -o ai_docs/core.txt

ruff:
	ruff check . --fix

mcp-server:
	uv run content-core-mcp
