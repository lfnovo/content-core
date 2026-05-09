.PHONY: tag test test-e2e test-e2e-heavy test-e2e-all test-all build-docs ruff mcp-server

tag:
	@version=$$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/'); \
	echo "Creating tag v$$version"; \
	git tag "v$$version"; \
	git push origin "v$$version"

test:
	uv run pytest tests/unit tests/integration -v

test-e2e:
	uv run pytest tests/e2e -v -m "e2e and not e2e_heavy"

test-e2e-heavy:
	uv run pytest tests/e2e -v -m e2e_heavy

test-e2e-all:
	uv run pytest tests/e2e -v -m "e2e or e2e_heavy"

test-all:
	uv run pytest -v -m ""

build-docs:
	repomix . --include "**/*.py,**/*.yaml" --compress --style xml -o ai_docs/core.txt

ruff:
	ruff check . --fix

mcp-server:
	uv run content-core-mcp
