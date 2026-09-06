# Release test matrix

Instantiate against the final candidate before execution. Current scope proposal:
v2.0.7 through e82abfd (HTML ingestion, engine/configuration errors, public
exceptions, logging, MCP version and packaging). Recompute when the SHA changes.

| Bucket / risk | Command or concrete action | Expected evidence | Resources / authority | Timing / disposition |
|---|---|---|---|---|
| A: shared routing/configuration, exception, HTML, logging and MCP regressions | `make test` | No unit/integration failures; log and candidate SHA | Local fixtures, no API calls | Pre-GO, mandatory validator |
| A: Python compatibility | Existing Test workflow on final candidate, Python 3.10/3.11/3.12 | All three jobs passed with matching SHA | GitHub CI | Pre-GO, required project checks |
| A: wheel/sdist and consumer surfaces | `uv build`, then every Artifact gate step in runbook; existing Package workflow | Installed library call, CLI TXT/PDF extraction, real MCP response, assets/version agreement and both SHA-256 values | Isolated environments; package downloads; no paid API calls | Pre-GO, mandatory package-gate |
| A: optional dependency installation | Install exact wheel with each of docling/crawl4ai/langchain, as runbook specifies | All extras install; do not claim live engine coverage | Package downloads, potentially large ML dependencies; no model inference | Pre-GO, part of package-gate |
| C: owner review of evidence and gaps | Review results and named unverified provider paths; approve exact notes including credits | Owner acknowledgment and exact approved text | Owner | Pre-GO, bucket-c and notes-approved |
| C: optional live URL routing | After scoped approval: `uv run pytest tests/e2e/test_url_engines.py -v -m e2e` | Per-test results; skips explicitly unverified | Network; Firecrawl credentials/usage, Jina and Crawl4AI environment; execution/count/cost requires separate agreement | Pre-GO signal; not a mandatory broad E2E gate |
| C: optional real Docling baseline | After scoped approval: `uv run pytest tests/e2e/test_docling.py::test_docling_pdf_extraction -v -m e2e_heavy` | Non-empty PDF extraction via explicit Docling | Large model downloads and local compute; separate scope approval | Pre-GO signal; unrun means unverified |
| C: unchanged media/network baselines | Select existing node IDs from tests/e2e/test_media.py, test_youtube.py and test_remote.py after credential/cost review | Per-test observed outcomes | Network; STT provider may incur cost | Optional; unrun means unverified |
| Signal: security alerts | Read repository Dependabot alerts; report unavailable API separately | Alert details or explicit not-run reason | Read-only GitHub access | Pre-GO, optional signal requiring honest disclosure |
| A: registry delivery | Download exact PyPI version, compare hashes and repeat isolated library/CLI/MCP smokes | Actual published digests, working surfaces, correct release page | Network, fresh environment | Post-publication, required delivery verification |

Bucket B: no new automation project is selected. Existing unit/integration and CI
packaging checks cover the deterministic changes. Any investment proposal is a
separate owner decision. This plan does not authorize paid/live suite execution.
