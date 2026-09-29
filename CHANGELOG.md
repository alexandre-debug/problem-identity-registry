# Changelog

## v0.1.2 (29 September 2026)

Archiving metadata only. No results or documents changed.

- **Zenodo archiving.** The Zenodo import of v0.1.0 stalled in the "Received" state. In `.zenodo.json`, the licence identifier was changed from `MIT` to `mit`, the form Zenodo expects, which is the likely cause. The corrected file was meant to be part of v0.1.1 but was left out of that upload, so v0.1.1 carried the same metadata as v0.1.0 and the fix takes effect in this release.
- Version numbers updated in the README and `CITATION.cff`. The DOI will be added once Zenodo archives this release.

## v0.1.1 (29 September 2026)

Clarifications after an external review of v0.1.0. No results changed.

- **Framework: definition of problem identity.** An identity now groups situations considered equivalent under explicit criteria. Procedures (solutions) are linked to those situations, with conditions of application. The previous text, "a class of problems that share a solution", mixed problem and solution: a broad procedure can serve different problems, as the "umbrella" guides showed.
- **README: the 6.21% ceiling.** It is now described as a limit of this evaluation, which is based on the available markings, not of the system's real usefulness. The README also states that a discussion from the marked family is not automatically an applicable solution.
- **Reproducibility.**
  - Added `code/ENVIRONMENT.md` with the exact environments, model digests and step-by-step instructions for a clean run.
  - Added pinned requirement files `code/requirements-mac.txt` and `code/requirements-sandbox.txt`.

## v0.1.0 (29 September 2026)

First public research record.
