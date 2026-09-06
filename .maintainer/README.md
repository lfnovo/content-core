# Maintainer workflows

This directory configures the oss-maintainer release workflow for Content Core.
It is not a list of maintainers.

- `profile.toml`: commands, required evidence, delivery and publication policy.
- `PROFILE.md`: scope and public communication conventions.
- `release/runbook.md`: release preparation, artifact checks and verification.
- `release/test-matrix.md`: risk-based checks; instantiate on each candidate.
- `gotchas.md`: verified limitations and lessons.
- `state/`: ignored run records, logs and artifact identities.
- `profile.local.toml`: optional ignored preferences; cannot weaken shared gates.

The canonical commands remain in `AGENTS.md`, `Makefile` and the existing GitHub
workflows. This profile configures releases only; other capabilities are not onboarded.
