# Release gotchas

- `make tag` creates AND pushes a tag derived from `pyproject.toml`. It starts
  distribution and requires the final candidate GO. Creating tags through another
  command or the Create Tag workflow is not a preparation step.
- `Publish` builds again in its reusable Package job, then uploads those validated
  bytes to PyPI without rebuilding in the publish job. Pre-GO and tag-run builds
  are separate artifacts; compare hashes and verify the actual registry files.
- `uv build` alone is not the package gate. Exercise the installed library, CLI
  and real MCP initialization response outside the checkout.
- `uv run --isolated --no-project` does not itself isolate Python imports. Use
  a temporary working directory, absolute wheel/fixture paths and `python -I`.
- `make ruff` modifies files. Lint and mypy are not release gates (`CLAUDE.md`).
- E2E suites may call paid services or download large models. Select and authorize
  their scope before execution; skips and missing credentials are not passes.
- The default `python3` on the current maintainer machine is older than the plugin
  scripts require. Use an available Python >=3.11 for profile/run-record scripts;
  this does not change the package's Python >=3.10 compatibility requirement.
- On 2026-09-05 the Dependabot API returned HTTP 403 with alerts disabled. Security
  alerts were unverified, not absent. Recheck on each release.
- `released` is not currently a repository label. Creating it or applying release
  labels requires the owner's agreement; do not create labels during bootstrap.
- `.gitattributes` export-ignore affects Git archives, not necessarily Hatch's
  sdist selection. Inspect the built sdist for accidental local-state inclusion.
