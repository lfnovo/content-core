# Release gotchas

- `make release` publishes the existing draft GitHub Release and starts PyPI
  distribution through `release: published`. It requires the exact candidate GO.
  `make tag` only creates/pushes the version tag under the current workflow; saving
  a draft release does not distribute to PyPI. Tags pointing to old workflow
  revisions can still carry the former tag-push trigger; do not use them for a cut.
- The GitHub Release must reference the validated candidate. Verify the remote
  tag's resolved commit before publication. The Package job rejects a release tag
  that differs from the project version (with or without the `v` prefix).
- `published` covers releases published directly or from drafts, including
  prereleases. Editing an already published release does not trigger a new upload.
- `Publish` builds again in its reusable Package job, then uploads those validated
  bytes to PyPI without rebuilding in the publish job. Pre-GO and release-run builds
  are separate artifacts; compare hashes and verify the actual registry files.
- `uv build` alone is not the package gate. Exercise the installed library, CLI
  and real MCP initialization response outside the checkout.
- `uv run --isolated --no-project` does not itself isolate Python imports. Use
  a temporary working directory, absolute wheel/fixture paths and `python -I`.
- `make ruff` modifies files. Lint and mypy are not release gates (`AGENTS.md`).
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
