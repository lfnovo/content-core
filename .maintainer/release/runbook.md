# Release runbook

## Agreement and versioning

Follow `CONTRIBUTING.md` for PR delivery, `CLAUDE.md` for canonical validation,
`ARCHITECTURE.md` for compatibility decisions and `CHANGELOG.md` for SemVer.
The existing architecture decision treats fixes to hidden extraction errors as
2.x fixes. New supported formats and public API additions are minor changes;
breaking supported consumer contracts require explicit version review. The owner
decides the release number. Confirmed artifact: pypi-library; trigger: `make tag`.

Prepare changes in a branch and PR. Required branch protections and review remain
binding. Ask once per session before merging qualifying own PRs. A merge to main
runs tests but does not currently publish. Only the exact final candidate GO
permits `make tag`.

## Scope and source validation

Fetch tags after bootstrap. Compare the latest release with the candidate; audit
all behavior changes and their issue/PR references against the changelog. Record
the candidate SHA, pre-existing working-tree changes and chosen checks under
`.maintainer/state/`. Keep user files, including untracked files, intact.

Run `make test` from the candidate checkout and retain the log/exit status.
Require successful Test workflow jobs for Python 3.10, 3.11 and 3.12, plus Package,
on the final integrated candidate. `CLAUDE.md` explicitly excludes ruff, mypy and
broad external-service E2E suites from validator gates. The selected plan defines
any optional external checks and authorized costs before those checks run.

## Artifact gate

The canonical builder is `uv build`; the canonical smoke implementations are
in `.github/workflows/package.yml`. A successful build alone is insufficient.

1. Use a fresh candidate checkout or an empty release-owned `dist/`; run `uv build`.
2. Require exactly one wheel and one sdist. Compare their version with
   `pyproject.toml`, both plugin manifests and the content-core entry in `uv.lock`.
3. Run the workflow's runtime-assets inspection against this wheel. Inspect the
   sdist too; exclude local state, credentials and accidental development artifacts.
4. Resolve the wheel and fixture paths to absolute paths. In a fresh temporary
   working directory, use the workflow's `uv run --isolated --no-project --with`
   commands against that wheel; use `python -I` for Python probes. Prove the module
   origin is an installed environment, not this checkout. Import `content_core`,
   its public API and public exception exports. Call `extract_content` on the
   existing `tests/input_content/file.txt` fixture and assert non-empty content.
5. Exercise `content-core --help`, `content-core --version`, and the workflow's
   real TXT and PDF extraction commands using absolute fixture paths. Check that
   the JSON result contains expected extracted content.
6. Run the workflow's real stdio `initialize` handshake with `content-core-mcp`
   from the isolated directory. Require a JSON-RPC result without an error and
   `serverInfo.version` equal to the candidate version. Retain stdout/stderr.
7. Install each declared extra (`docling`, `crawl4ai`, `langchain`) with the exact
   wheel in an isolated environment and check the dependency installation succeeds.
   Installation is not evidence of successful live provider calls or model runs.
8. Record SHA-256 for both artifacts and link every result to the tested bytes.
   Retain artifacts until post-publication verification finishes.

The release agent adapts the existing workflow commands to absolute paths in the
execution plan, before running them. It must not substitute editable/source tests
for these checks. Re-run affected checks after fixes and the full final artifact
gate after the version cut is integrated.

## Manual scope

The matrix distinguishes automated regression coverage from optional live checks.
The owner reviews results and explicit unverified paths; that acknowledgment is
`bucket-c`. If a manual check is made mandatory for the candidate, it must actually
pass. Missing credentials remain unverified and never receive an inferred pass.
Neither this profile nor its approval authorizes paid calls or large model runs.

## Cut and notes

Bump `pyproject.toml`, `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`
together, then use the existing `uv sync` command to update `uv.lock`. Confirm only
intended lock changes and verify all package-version values agree. Leave the
marketplace's independent schema/catalog version unchanged.

Date the versioned changelog in the owner's timezone and open a fresh Unreleased
section. Commit all cut files together through the PR process. Do not create a tag
here. Collect contributor credits and approve the exact notes before publication.

## Publish — only after GO

Present all mandatory results, manual acknowledgment, security visibility, exact
candidate SHA, wheel/sdist SHA-256 and `make tag`. Recheck the candidate, versions,
remote base and absence of the proposed tag immediately before the trigger.

Run `make tag` once on the approved commit. Observe `.github/workflows/publish.yml`
to completion. A failure requires an owner decision; do not retry distribution
through a different path or overwrite a version. Attach the approved notes to the
existing tag, checking the release page after writing them.

## Post-publication verification

Download both published files from PyPI for the exact version and record their
SHA-256 separately from tested hashes. Compare them with the pre-GO artifacts and
the tag-run Package artifact. The tag workflow builds afresh, so report differences
and repeat the artifact smokes on the actual published wheel. Install the exact
version from PyPI in a fresh environment outside the checkout and repeat library,
CLI and MCP probes. Check the release page's tag, approved notes and latest status.

## Cleanup and closure

Record announcement disposition (none configured; the owner posts any later
approved text). Do not create/apply release labels without agreement.
Stop only processes started by this run and remove only its temporary environments,
fixtures and artifacts after retaining required evidence. Check the working tree
against its initial state. Record publish, verify, announcement disposition and
cleanup before closing the run with GO. Retro work is independent of delivery.
