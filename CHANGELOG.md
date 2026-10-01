# Changelog

## v0.2.2 (1 October 2026)

Documentation corrections after an external review of v0.2.1, and the round 12 pre-registration published before it runs. No published result changed.

- **Round 12 published before running.** The pre-registration (in `docs/protocolo-continuacao.pt-BR.md`) and its frozen script (`code/05-hybrid-search/gc_r12.py`, SHA-256 `3414f6b2…`) test whether the confirmed links still help over a hybrid search that fuses word search (BM25) with an embedding model selected by a pilot on exploratory data. For the first time, a round's pre-registration has a public, dated record before its result.
- **Framework updated with rounds 9–11.** Preserving the first suggestion does not guarantee preserving the quality of the final answer; removing the popularity term helped H1 against H on Super User, without showing superiority over plain search; a gate to predict when the network helps was not achieved; gains were smaller on a sparser site.
- **Correction: curve A.** "A few confirmations per family capture most of the value" went beyond the test, which removed links from the whole network. It shows that a fraction of the links captured much of the gain, not how many confirmations each family needs. Prioritising new families remains a hypothesis. Corrected in the framework and the experiment log; recorded as an erratum in the protocol.
- **Correction: the AI curator.** "Attacks exactly that bottleneck" became "could reduce the dependence on human moderation to extend the network".
- **Round 13 draft (the AI curator, previously numbered 12).** The relation is now the same everywhere ("the answers of B solve A"), "coverage" became sensitivity with a defined denominator, and a promise stronger than the design allows was removed.
- **Judges identified more reproducibly.** `code/ENVIRONMENT.md` records how the Claude judges ran, which version was configured, that the serving version was not exposed, and that separate subagents are not independent models.
- **README.** "This is the only claim this repository presents as confirmed" became "This is the main confirmed retrieval result", since rounds 9–11 added other bounded results.
- **Protocol continuation** re-exported at revision 131.

## v0.2.1 (1 October 2026)

Repository fix. No results or documents changed.

- **Files restored.** The upload of v0.2.0 removed by mistake 63 files from earlier versions: the code and results of rounds 1–8 and of the confirmation, `docs/framework.md`, `docs/framework.pt-BR.md`, `docs/protocolo-original.pt-BR.md`, `code/ENVIRONMENT.md` and the requirement files. They are restored here unchanged, so this version contains the full research record. The GitHub release and the Zenodo archive of v0.2.0 are incomplete; cite v0.2.1 or the concept DOI.

## v0.2.0 (1 October 2026)

New results: rounds 9 to 11, which ask whether the retrieved discussions improve the final answer, not only retrieval. The confirmed claim of v0.1 did not change.

- **Round 9 (AskUbuntu).** A local model (gemma4) answered with five retrieved discussions as context, and blind judges compared the answers. When H brought the marked family that plain search missed, answers were preferred with H's context: +0.153 [+0.024; +0.282], 124 questions (passed). On questions without a marked duplicate, H's context did slightly worse: −0.070 [−0.138; 0.000], 400 questions, which failed the pre-registered margin of −0.10.
- **Round 10.** Stage B: a gate meant to open the network only when it helps was "not calibratable" for its signal, grid and requirements (with coverage ≥ 2%, at best 17.6% gains among its openings on questions with a marked duplicate, on the development half; at least 25.1% was required). Stage C did not run. Stage A: on Super User, a sparser network, confirmed relations gave smaller retrieval gains (M1 +15.5%, which passed; H1 +11.6%, whose CI lower bound of +7.9% fell short of the pre-registered 10%).
- **Round 11 (Super User).** On questions without a marked duplicate where the two differ, H1 (no popularity term) was preferred to H: +0.060 [+0.013; +0.109], 838 questions (passed). Across the eligible questions, H1 stayed within 3 points of plain search: +0.006 [−0.016; +0.029] (passed); superiority over plain search was not shown.
- **Erratum 1 (round 11).** The script computed the first criterion with the opposite sign under the pre-registered label. The sign was corrected according to the pre-registered text, and an external review recomputed the aggregates. The original output (`r11_resultado_original.json`) is published next to the corrected one.
- **Deviations 1 and 2.** In round 9, the local model could not insert usable errors into the K4 control pairs; in round 11, it could not write enough usable K5 pairs. Before any judging, separate Claude agents wrote those parts (the K4 errors; the second version of 10 K5 pairs) and other agents reviewed them. No threshold changed.
- **New files.**
  - `docs/protocolo-continuacao.pt-BR.md`: the dated protocol from round 9 to the draft of round 12, in Portuguese.
  - `code/04-answer-quality/`: the scripts of rounds 9–11, with their frozen and intermediate versions in `versions/`.
  - `results/04-answer-quality/`: samples (question numbers only), judge labels, control-pair approvals (identifiers and decisions only) and aggregate results. Files with third-party text are omitted and listed with their SHA-256 in `results/README.md`.
- **Updated.** Both READMEs (new section on answer quality, what did not work, what is still open), `docs/experiment-log.md` (Part 4), `code/README.md`, `results/README.md`, `LICENSE-docs.md` (superuser.com), `CITATION.cff` and `.zenodo.json`.

## v0.1.4 (29 September 2026)

Citation only. No results or documents changed.

- **DOI and citation.** Zenodo archived v0.1.0 as [10.5281/zenodo.23037100](https://doi.org/10.5281/zenodo.23037100). The concept DOI, which covers all versions, is [10.5281/zenodo.23037099](https://doi.org/10.5281/zenodo.23037099). Both were added to the READMEs, with a "How to cite" section, and to `CITATION.cff`.
- **Version labels, recorded later.** This release was published on GitHub with the tag `v0.1.5` by mistake; there is no `v0.1.4` tag. Its `.zenodo.json` says 0.1.4, while the README and `CITATION.cff` still said 0.1.2. This entry was written for v0.2.0, replacing the "Unreleased" heading it had.

## v0.1.2 (29 September 2026)

Archiving metadata only. No results or documents changed.

- **Zenodo archiving.** The Zenodo import of v0.1.0 stalled in the "Received" state. In `.zenodo.json`, the licence identifier was changed from `MIT` to `mit`, the form Zenodo expects, which is the likely cause. The corrected file was meant to be part of v0.1.1 but was left out of that upload, so v0.1.1 carried the same metadata as v0.1.0 and the fix takes effect in this release.
- Version numbers updated in the README and `CITATION.cff`. The DOI will be added once Zenodo archives this release.
- **Correction, added later the same day.** The licence identifier was not the cause of the delay. Zenodo archived v0.1.0 about an hour after its release, with the original `MIT` identifier: the import was only slow. The change to `mit` is harmless and was kept.
- **Tag name.** This release was published on GitHub with the tag `v0.1.3` by mistake; there is no `v0.1.2` tag. Its files and its `.zenodo.json` say 0.1.2.

## v0.1.1 (29 September 2026)

Clarifications after an external review of v0.1.0. No results changed.

- **Framework: definition of problem identity.** An identity now groups situations considered equivalent under explicit criteria. Procedures (solutions) are linked to those situations, with conditions of application. The previous text, "a class of problems that share a solution", mixed problem and solution: a broad procedure can serve different problems, as the "umbrella" guides showed.
- **README: the 6.21% ceiling.** It is now described as a limit of this evaluation, which is based on the available markings, not of the system's real usefulness. The README also states that a discussion from the marked family is not automatically an applicable solution.
- **Reproducibility.**
  - Added `code/ENVIRONMENT.md` with the exact environments, model digests and step-by-step instructions for a clean run.
  - Added pinned requirement files `code/requirements-mac.txt` and `code/requirements-sandbox.txt`.

## v0.1.0 (29 September 2026)

First public research record.
