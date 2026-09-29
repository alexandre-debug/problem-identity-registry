# Changelog

## v0.1.1 (29 September 2026)

Clarifications after an external review of v0.1.0. No results changed.

- **Framework: definition of problem identity.** An identity now groups situations considered equivalent under explicit criteria. Procedures (solutions) are linked to those situations, with conditions of application. The previous text, "a class of problems that share a solution", mixed problem and solution: a broad procedure can serve different problems, as the "umbrella" guides showed.
- **README: the 6.21% ceiling.** It is now described as a limit of this evaluation, which is based on the available markings, not of the system's real usefulness. The README also states that a discussion from the marked family is not automatically an applicable solution.
- **Reproducibility.**
  - Added `code/ENVIRONMENT.md` with the exact environments, model digests and step-by-step instructions for a clean run.
  - Added pinned requirement files `code/requirements-mac.txt` and `code/requirements-sandbox.txt`.
- **Zenodo archiving.** The Zenodo import of the v0.1.0 release stalled in the "Received" state. The licence identifier in `.zenodo.json` was changed from `MIT` to `mit`, the form Zenodo expects, which is the likely cause. The DOI will be added to the README and `CITATION.cff` once Zenodo archives this release.

## v0.1.0 (29 September 2026)

First public research record.
