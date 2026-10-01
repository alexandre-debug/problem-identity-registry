# Problem Identity Registry

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23037099.svg)](https://doi.org/10.5281/zenodo.23037099)

*A research record on giving recurring problems a shared, verifiable identity, so that people and AI systems can reuse known solutions instead of solving the same problems again.*

**Status:** work in progress · version 0.2.2 · 1 October 2026 · [changelog](CHANGELOG.md)
**Author:** Alexandre Cardoso Rego (the project was first conceived, in Portuguese, as *Grande Cérebro*)
**Português:** [README.pt-BR.md](README.pt-BR.md)

---

## The idea

Every day, people and AI systems solve problems that have already been solved somewhere else. The solutions stay scattered across forums, support tickets and private conversations, and each new case starts almost from zero.

This project proposes that recurring problems should have an **identity of their own**, built from confirmations such as "this problem is the same as that one". That identity would live in a **shared, auditable registry**, used by many applications. Think of what the ICD does for diseases or CVE does for software vulnerabilities, applied to everyday technical problems. The registry records who confirmed each link, with what evidence, and lets any link be contested.

The full proposal, including what is a hypothesis and what is evidence, is in [docs/framework.md](docs/framework.md).

## What has been shown so far

This is the main confirmed retrieval result, in the form we consider defensible:

> On new AskUbuntu questions (January 2020 to March 2024, never used during the exploratory phase), using previously recorded duplicate relations increased the retrieval of discussions from the marked family among five suggestions. The interleaved combination went from 1.61% to 2.57% of all new questions (+59% relative; 95% CI of the relative gain +54% to +65%), while keeping the first suggestion identical to plain semantic search. We have **not** measured whether problems were actually solved, nor any saving of work.

| Method (confirmation data, 96,333 new questions) | Marked family among top 5 | Relative gain over plain search (95% CI) |
|---|---|---|
| M0: plain semantic search (nomic-embed-text) | 1.61% | — |
| M1: plain search + confirmed relations, no popularity term | 2.28% | +41.4% (+36.7% to +45.9%) |
| H1: M0 first, alternating with M1 | 2.12% | +31.3% (+27.6% to +35.0%) |
| **H: M0 first, alternating with M2** | **2.57%** | **+59.3% (+54.2% to +65.0%)** |
| M2: confirmed relations + global popularity term | 2.84% | +76.0% (+69.0% to +83.5%) |

- **Ceiling of this evaluation.** Only 6.21% of the new questions had an earlier marked duplicate, so in this evaluation, which is based on the markings available, no method can score above 6.21%. This is a limit of the metric, not of the real usefulness of the system. User-marked duplicates are incomplete, so all numbers are lower bounds of "a relevant earlier discussion exists".
- **A discussion is not a solution.** A discussion from the marked family is not automatically a solution that applies to the new question; that was not measured.
- **What H is.**
  - H takes its first suggestion from plain search, then alternates M2 and M0 in the remaining positions.
  - M2 adds a global popularity term (the number of confirmed links of a question) to the confirmed relations.
  - The popularity term is double-edged:
    - After the first position, it adds to recall: without it (H1, reported descriptively), the gain is +31% instead of +59%. Our reading of the exploratory diagnostic is that it helps bring the family's canonical guides into the list.
    - Used alone, M2's first suggestion scored worse than plain search in every judged comparison. The difference was statistically clear in exploratory round 8; the first comparative judge's interval touched zero.
  - H keeps the plain first suggestion by construction.
- **Methods were frozen before the run.** Data, text versions, criteria and methods were registered before the confirmation run. Texts were taken in their historical versions: new questions as originally written, older questions as they stood on 1 January 2020. No later edit, such as an added solution or a duplicate notice, could leak into the test.

### Does it improve the final answer? (rounds 9–11)

Retrieval is a means; the answer is what matters. In two pre-registered rounds, 9 and 11, a local language model (gemma4) answered new questions with five retrieved discussions as context. Blind judges compared the answers with the help of the asker's accepted answer. Round 10, between them, tested a gate and retrieval on Super User, without answers. The judges were fresh Claude subagents that saw only a rubric and the items, and the answer key stayed on the author's machine. The judges passed all their controls in both judged rounds. These are a judge's preferences, not problems verified as solved.

| Round, site | Comparison | Net preference Δ [95% CI] | Pre-registered outcome |
|---|---|---|---|
| 9, AskUbuntu | H vs plain search, when H brings the marked family that plain search missed (124 questions) | +0.153 [+0.024; +0.282] | passed |
| 9, AskUbuntu | H vs plain search, questions without a marked duplicate, different contexts (400) | −0.070 [−0.138; 0.000] | failed (margin −0.10) |
| 11, Super User | H1 vs H, questions without a marked duplicate where the two differ (838) | +0.060 [+0.013; +0.109] | passed |
| 11, Super User | H1 vs plain search, population of eligible questions | +0.006 [−0.016; +0.029] | no loss beyond 3 points: passed; superiority: not shown |

- **What this means.**
  - In round 9 (AskUbuntu), when the network brought the marked family that plain search missed, the judges preferred its answers.
  - In round 11 (Super User), on questions without a marked duplicate, removing the popularity term (H1) improved answers relative to H, the same design with the term. This is the first direct test of the term on answers.
  - Without the term, the network kept answer quality within 3 points of plain search across the eligible questions of Super User.
  - A benefit over plain search, in quality, work saved or total cost, has **not** been shown.
- **Erratum.** The round 11 script computed its first criterion as H − H1 while labelling it H1 − H. After the result, the sign was corrected according to the pre-registered text, and an external review recomputed the aggregates. Both outputs are published.
- **Deviations.** In round 9, the local model could not insert usable errors into the decisive-error control pairs (K4); in round 11, it could not write enough usable equivalent pairs (K5). Before any judging, separate Claude agents filled those gaps (deviations 1 and 2), and other agents reviewed the pairs. In round 11, the K4 errors were written by an agent, as the frozen design specified. The judges belong to the same model family.

## What did not work, or is still unresolved

Negative and inconclusive results are part of the record:

- **Caching identical phrases did not help.** In the first rounds, on the Schema-Guided Dialogue dataset, a memory of validated interpretations added nothing to a small model already trained on the domain. It agreed with the model 98% of the time. A shared memory of validated values helped only marginally and failed its pre-registered threshold.
- **Plain retrieval rarely finds the marked earlier duplicate.** On AskUbuntu, TF-IDF and embeddings retrieved it for only 0.8% and 1.2% of new questions, against a ceiling of 7.2%.
- **An exploratory "4× gain" was about half an artifact of the metric.** Moderators tend to mark the canonical guide as the duplicate, and plain search often found equally close but unmarked siblings. Crediting the whole confirmed family cut the apparent gain roughly in half. The comparison in the table above uses that family metric.
- **A global popularity weight harms the first suggestion.** In the exploratory diagnostic, most of the degraded first suggestions (56 of 67) were caused by that term, which pulls famous guides into unrelated questions. The same term supplied 44% of the family gain. Round 11 then found the same on final answers, on Super User: on questions without a marked duplicate, answers were preferred without the term. A weight that depends on context, rather than on global fame, is still a proposal, not yet tested.
- **Can the network choose the first suggestion by itself? Unresolved.**
  - In the confirmation, the pre-registered judge (a local gemma4 model with a fixed prompt) failed its control checks: it recognised only 27% of true duplicates. The official outcome of the confirmation is therefore **INCONCLUSIVE**.
  - In a pre-registered complementary step, a second blind judge (Claude, with the answer key kept on the author's machine) passed the same kind of controls. It found M1 − M0 = −1.9 points (95% CI −4.8 to +0.7) on the first suggestion.
  - That interval is compatible with both a relevant loss and a negligible difference. There is not yet enough evidence to let the network pick the first suggestion, so keeping plain search first is the prudent choice.
- **Knowing in advance when to use the network: not achieved.**
  - In round 9, the network helped when it brought the marked family and may have worsened the answer slightly on questions without a marked duplicate. A real application cannot see the marked family in advance.
  - In round 10, a gate based on how much the network's candidate beat plain search reached at best 17.6% gains among its openings on questions with a marked duplicate (development half, coverage ≥ 2%), against 12.5% for H1 without a gate. The pre-registered requirement was at least twice that, 25.1%. The gate is "not calibratable" for that signal, grid and requirements.
- **Smaller gains on a sparser network.** On Super User, only 1.89% of new questions have an earlier marked duplicate. There, relations improved retrieval much less: M1 +15.5%, against +41.4% on AskUbuntu. H1 gained +11.6%, but the lower bound of its CI (+7.9%) fell short of the pre-registered minimum of 10%.
- **Network effect: only a moderate signal.**
  - In a simulation that split one community into ten "applications", confirmations became proportionally more valuable with more participants: the relative gain grew from +3% with one application to +31% with ten.
  - Part of this is expected by construction, because a link can exist only when both questions are in the memory.
  - The absolute gain per new participant decreased.

## What is still open

- Whether the links still add something over a **hybrid search**. Round 12 compares them with a fusion of word search (BM25) and an embedding model selected by a pilot on exploratory data. It was frozen and published in version 0.2.2 before running.
- Whether the network gives a **benefit over plain search**, not only no loss: better answers, work saved or lower total cost.
- Whether the round 11 result **holds on AskUbuntu** and other sites.
- Whether the retrieved discussions actually **resolve** the new problem, and how much **work or compute** reuse would save.
- Whether the effect holds **across different applications and domains**, beyond a single community split at random.
- Whether an **AI curator** can create reliable links. A judge that passes easy controls, which reject random pairs, is not yet validated for hard cases: very similar problems that need different solutions. This is the author's hypothesis *"generate once, validate many, reuse always"*, described in the framework document. A draft of round 13, already reviewed externally, would test it with small local models.
- Whether **context-dependent weights** can keep the recall benefit of the popularity term without its harm.
- **Governance:** false or malicious confirmations, privacy of the problems people report, and incentives to contribute.

## How the research was conducted

- **A dated protocol.** Before each round, the question, the data and the methods were written in a dated protocol. Rounds meant to decide something had their success criteria fixed in advance, and the criteria were never changed after seeing results. When a result missed a threshold, for example by 0.16 points in round 7, it was recorded as missed. Some stages were explicitly exploratory and had no criterion; the experiment log says which.
  - The protocol is a living document, dated to the day and, from round 9 on, often to the hour. It had no external time stamp before v0.1.0 (29 September 2026), its first dated public record; each release archives its state at that date. The continuation, with the pre-registrations of rounds 9 to 11, is first published in v0.2.0, after their results; its dates are the author's own record.
- **Exploratory and confirmatory work are separated.** All tuning happened on the exploratory data (Lei et al. AskUbuntu, an older snapshot of the site). The confirmation used untouched 2020–2024 questions from the April 2024 Stack Exchange dump, with everything frozen.
- **Blind judging, including the failures.**
  - Two blind checks were compromised because the answer key reached the evaluator before labelling. Both are recorded as compromised and were not used.
  - The procedure was then changed: the key never leaves the author's machine, and a local script returns only aggregate numbers.
  - In the complementary step, the labels came from Claude subagents that received only the rubric and the items. The orchestrating assistant, which knew the hypotheses and the first judge's aggregate result, only merged the batches.
- **Corrections as errata.** After external review, interpretations that went beyond the data were corrected in dated errata at the end of the protocol, without deleting earlier text. This covers statements both in the protocol and in the conversation that accompanied the work.
- **Deviations recorded, not hidden.** Some changes were needed after a design was frozen but before any result, such as how judge-control pairs were produced. Each was recorded as a numbered deviation with the author's decision. Each script change got a new SHA-256 and was tested to reproduce the frozen output where it was not meant to change anything.

The full English summary of every round is in [docs/experiment-log.md](docs/experiment-log.md). The original dated protocol, in Portuguese, is in [docs/protocolo-original.pt-BR.md](docs/protocolo-original.pt-BR.md); its final section lists the few changes made for publication. Rounds 9 to 13 continue in [docs/protocolo-continuacao.pt-BR.md](docs/protocolo-continuacao.pt-BR.md).

## Repository layout

```
README.md, README.pt-BR.md       this overview
docs/framework.md (+ .pt-BR)     the proposal: problem identities, confirmations, AI curator hypothesis, risks
docs/experiment-log.md           English summary of every round, with criteria and results
docs/protocolo-original.pt-BR.md the original dated protocol (source of record), up to the confirmation
docs/protocolo-continuacao.pt-BR.md  its continuation: rounds 9–13
code/01-sgd-rounds/              rounds 1–4 (Schema-Guided Dialogue)
code/02-askubuntu-exploratory/   rounds 5–8, diagnostics and network curves (AskUbuntu, Lei et al.)
code/03-confirmation/            independent confirmation (AskUbuntu 2020–2024) and blind second judge
code/04-answer-quality/          rounds 9–11: answers with retrieved context, blind judging, gate, Super User
code/05-hybrid-search/           round 12 (frozen, not yet run): links over a hybrid search
results/                         result files of each stage
```

## Reproducing

- **Requirements:** Python 3.10+ with `numpy`, `scipy`, `scikit-learn`, and optionally `py7zr`. The exact versions used, pinned requirement files and step-by-step instructions for a clean run are in [code/ENVIRONMENT.md](code/ENVIRONMENT.md).
- **Where each stage ran:**
  - Rounds 1–5 (small scikit-learn models, TF-IDF and the dataset's pre-trained word vectors) ran in the assistant's cloud sandbox.
  - From round 6 on, embeddings and LLM judges via [Ollama](https://ollama.com) (`nomic-embed-text` for embeddings, `gemma4` as judge) ran locally on the author's Mac. The confirmation's result file records the exact model digests and the Ollama version.
  - The complementary second judge's labelling was done by Claude subagents in the assistant's environment, while the answer key stayed on the author's machine.
- **Time:** the confirmation took about 94 minutes in total for 414,451 questions. The terminal's own estimate for the embedding step was about an hour of that.
- **Confirmation data:** `askubuntu.com.7z` from the Stack Exchange data dump of 2 April 2024, on the [Internet Archive](https://archive.org/details/stackexchange).
- **Commands:** `python3 gc_conf.py --judge gemma4:latest`, then `python3 gc_conf_juiz2.py gerar` / `comparar juiz2_rotulos.json`.
- **Rounds 9–11:** see [code/04-answer-quality/README.md](code/04-answer-quality/README.md). The answers were generated by gemma4 on the author's Mac (about 4.5 hours for the 1,540 answers of round 9; 2,846 distinct prompts in round 11), and the judging was done by Claude subagents, with the key kept on the author's machine. Super User data: `superuser.com.7z` from the same dump.
- **Round 12:** see [code/05-hybrid-search/README.md](code/05-hybrid-search/README.md). Frozen on 1 October 2026 and published before running; no results yet.
- **Omitted files with third-party text:** the blind-judging item files, the pilot answers, the control-pair review files, the agent-written control edits, the example file and the example fields of four result files are not included, because they contain excerpts of askubuntu.com or superuser.com posts, or model rewrites of them. Except for the agent-written files, the scripts produce them from the public data, given the same model digests and the locally saved caches. Bit-identical regeneration on other hardware is not guaranteed. Their SHA-256 hashes are listed in [results/README.md](results/README.md), and the author keeps the originals for verification on request.

## Data and licenses

- **Code:** MIT License ([LICENSE](LICENSE)).
- **Documentation and result files:** CC BY 4.0 ([LICENSE-docs.md](LICENSE-docs.md)). Third-party text from askubuntu.com and superuser.com was removed from the published files.
- **Datasets:** none are redistributed here.
  - Schema-Guided Dialogue (Rastogi et al., 2020).
  - AskUbuntu duplicate-question dataset (Lei et al., NAACL 2016).
  - Stack Exchange data dump, 2024-04-02 (AskUbuntu and Super User).

## Authorship and AI assistance

- **Author:** the idea, its direction and the decisions in this project belong to Alexandre Cardoso Rego.
- **Claude (Anthropic):** the experimental design, the code, the analyses and the documentation were developed with Claude, which acted as research assistant.
- **ChatGPT (OpenAI):** the author relayed critical reviews from ChatGPT, several of which changed the protocol before runs and corrected interpretations after them.
- **Judges:** the local model gemma4 (on the author's machine) and, in the complementary step and in rounds 9 and 11, Claude subagents that received only the labelling rubric and the items. When this was recorded (1 October 2026), the working session was configured as `claude-opus-5-5`; the version that served each judging call was not exposed and is not recorded. Separate subagents help preserve blinding, but they are not independent models. Details in [code/ENVIRONMENT.md](code/ENVIRONMENT.md).
- **Rounds 9–11:** the answers were generated by gemma4. Some judge-control pairs were written and reviewed by separate Claude agents (deviations 1 and 2).
- **Separate review:** before publication, a separate Claude agent (same model family) that had not written the documentation checked it against the result files and the protocol. It reviewed the documentation, not the code. For version 0.2.0, an external review (ChatGPT) recomputed the aggregates of round 11 and checked its erratum.

## How to cite

Please cite the archived record on Zenodo:

> Rego, A. C. (2026). *Problem Identity Registry: a research record on shared, verifiable identities for recurring problems*. Zenodo. https://doi.org/10.5281/zenodo.23037099

- The DOI above represents all versions and always resolves to the latest one.
- To cite a specific version, use that version's own DOI, listed on the Zenodo page. Version 0.1.0: [10.5281/zenodo.23037100](https://doi.org/10.5281/zenodo.23037100).
- The same information is in [CITATION.cff](CITATION.cff), which GitHub shows under "Cite this repository".
