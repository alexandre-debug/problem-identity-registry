# Problem Identity Registry

*A research record on giving recurring problems a shared, verifiable identity, so that people and AI systems can reuse known solutions instead of solving the same problems again.*

**Status:** work in progress · version 0.1.1 · 29 September 2026 · [changelog](CHANGELOG.md)
**Author:** Alexandre Cardoso Rego (the project was first conceived, in Portuguese, as *Grande Cérebro*)
**Português:** [README.pt-BR.md](README.pt-BR.md)

---

## The idea

Every day, people and AI systems solve problems that have already been solved somewhere else. The solutions stay scattered across forums, support tickets and private conversations, and each new case starts almost from zero.

This project proposes that recurring problems should have an **identity of their own**, built from confirmations such as "this problem is the same as that one". That identity would live in a **shared, auditable registry**, used by many applications. Think of what the ICD does for diseases or CVE does for software vulnerabilities, applied to everyday technical problems. The registry records who confirmed each link, with what evidence, and lets any link be contested.

The full proposal, including what is a hypothesis and what is evidence, is in [docs/framework.md](docs/framework.md).

## What has been shown so far

This is the only claim this repository presents as confirmed, in the form we consider defensible:

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

## What did not work, or is still unresolved

Negative and inconclusive results are part of the record:

- **Caching identical phrases did not help.** In the first rounds, on the Schema-Guided Dialogue dataset, a memory of validated interpretations added nothing to a small model already trained on the domain. It agreed with the model 98% of the time. A shared memory of validated values helped only marginally and failed its pre-registered threshold.
- **Plain retrieval rarely finds the marked earlier duplicate.** On AskUbuntu, TF-IDF and embeddings retrieved it for only 0.8% and 1.2% of new questions, against a ceiling of 7.2%.
- **An exploratory "4× gain" was about half an artifact of the metric.** Moderators tend to mark the canonical guide as the duplicate, and plain search often found equally close but unmarked siblings. Crediting the whole confirmed family cut the apparent gain roughly in half. The comparison in the table above uses that family metric.
- **A global popularity weight harms the first suggestion.** In the exploratory diagnostic, most of the degraded first suggestions (56 of 67) were caused by that term, which pulls famous guides into unrelated questions. The same term supplied 44% of the family gain. A link's weight should depend on context rather than on global fame; this is a proposal, not yet tested.
- **Can the network choose the first suggestion by itself? Unresolved.**
  - In the confirmation, the pre-registered judge (a local gemma4 model with a fixed prompt) failed its control checks: it recognised only 27% of true duplicates. The official outcome of the confirmation is therefore **INCONCLUSIVE**.
  - In a pre-registered complementary step, a second blind judge (Claude, with the answer key kept on the author's machine) passed the same kind of controls. It found M1 − M0 = −1.9 points (95% CI −4.8 to +0.7) on the first suggestion.
  - That interval is compatible with both a relevant loss and a negligible difference. There is not yet enough evidence to let the network pick the first suggestion, so keeping plain search first is the prudent choice.
- **Network effect: only a moderate signal.**
  - In a simulation that split one community into ten "applications", confirmations became proportionally more valuable with more participants: the relative gain grew from +3% with one application to +31% with ten.
  - Part of this is expected by construction, because a link can exist only when both questions are in the memory.
  - The absolute gain per new participant decreased.

## What is still open

- Whether the retrieved discussions actually **resolve** the new problem, and how much **work or compute** reuse would save.
- Whether the effect holds **across different applications and domains**, beyond a single community split at random.
- Whether an **AI curator** can create reliable links. A judge that passes easy controls, which reject random pairs, is not yet validated for hard cases: very similar problems that need different solutions. This is the author's hypothesis *"generate once, validate many, reuse always"*, described in the framework document.
- Whether **context-dependent weights** can keep the recall benefit of the popularity term without its harm.
- **Governance:** false or malicious confirmations, privacy of the problems people report, and incentives to contribute.

## How the research was conducted

- **A dated protocol.** Before each round, the question, the data and the methods were written in a dated protocol. Rounds meant to decide something had their success criteria fixed in advance, and the criteria were never changed after seeing results. When a result missed a threshold, for example by 0.16 points in round 7, it was recorded as missed. Some stages were explicitly exploratory and had no criterion; the experiment log says which.
  - The protocol is a living document with day-level dates. It had no external time stamp before this release, which is its first dated public record.
- **Exploratory and confirmatory work are separated.** All tuning happened on the exploratory data (Lei et al. AskUbuntu, an older snapshot of the site). The confirmation used untouched 2020–2024 questions from the April 2024 Stack Exchange dump, with everything frozen.
- **Blind judging, including the failures.**
  - Two blind checks were compromised because the answer key reached the evaluator before labelling. Both are recorded as compromised and were not used.
  - The procedure was then changed: the key never leaves the author's machine, and a local script returns only aggregate numbers.
  - In the complementary step, the labels came from Claude subagents that received only the rubric and the items. The orchestrating assistant, which knew the hypotheses and the first judge's aggregate result, only merged the batches.
- **Corrections as errata.** After external review, interpretations that went beyond the data were corrected in dated errata at the end of the protocol, without deleting earlier text. This covers statements both in the protocol and in the conversation that accompanied the work.

The full English summary of every round is in [docs/experiment-log.md](docs/experiment-log.md). The original dated protocol, in Portuguese, is in [docs/protocolo-original.pt-BR.md](docs/protocolo-original.pt-BR.md); its final section lists the few changes made for publication.

## Repository layout

```
README.md, README.pt-BR.md       this overview
docs/framework.md (+ .pt-BR)     the proposal: problem identities, confirmations, AI curator hypothesis, risks
docs/experiment-log.md           English summary of every round, with criteria and results
docs/protocolo-original.pt-BR.md the original dated protocol (source of record)
code/01-sgd-rounds/              rounds 1–4 (Schema-Guided Dialogue)
code/02-askubuntu-exploratory/   rounds 5–8, diagnostics and network curves (AskUbuntu, Lei et al.)
code/03-confirmation/            independent confirmation (AskUbuntu 2020–2024) and blind second judge
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
- **Omitted files with third-party text:** the blind-judging item files, the example file and the example fields of four result files are not included, because they contain excerpts of askubuntu.com posts. The scripts produce them from the public data, given the same model digests and the locally saved caches. Bit-identical regeneration on other hardware is not guaranteed. Their SHA-256 hashes are listed in [results/README.md](results/README.md), and the author keeps the originals for verification on request.

## Data and licenses

- **Code:** MIT License ([LICENSE](LICENSE)).
- **Documentation and result files:** CC BY 4.0 ([LICENSE-docs.md](LICENSE-docs.md)). Third-party text from askubuntu.com was removed from the published files.
- **Datasets:** none are redistributed here.
  - Schema-Guided Dialogue (Rastogi et al., 2020).
  - AskUbuntu duplicate-question dataset (Lei et al., NAACL 2016).
  - Stack Exchange data dump, 2024-04-02.

## Authorship and AI assistance

- **Author:** the idea, its direction and the decisions in this project belong to Alexandre Cardoso Rego.
- **Claude (Anthropic):** the experimental design, the code, the analyses and the documentation were developed with Claude, which acted as research assistant.
- **ChatGPT (OpenAI):** the author relayed critical reviews from ChatGPT, several of which changed the protocol before runs and corrected interpretations after them.
- **Judges:** the local model gemma4 (on the author's machine) and, in the complementary step, Claude subagents that received only the labelling rubric and the items.
- **Separate review:** before publication, a separate Claude agent (same model family) that had not written the documentation checked it against the result files and the protocol. It reviewed the documentation, not the code.

## How to cite

See [CITATION.cff](CITATION.cff). A DOI will be added after the first archived release on Zenodo.
