# Experiment log (English summary)

**Author:** Alexandre Cardoso Rego · research conducted 28–29 September 2026 · summary of version 0.1.0

This is a condensed English summary of every stage. The source of record is the original dated protocol, in Portuguese: [protocolo-original.pt-BR.md](protocolo-original.pt-BR.md). For each round, the question and the method were written there **before** running. Rounds meant to decide something also had their success criteria fixed in advance, and those criteria were never changed after seeing results. Diagnostic and exploratory stages had no criterion, as marked below. The protocol is a living document with day-level dates and no external time stamp before this release. Result files are in [`../results`](../results).

## Glossary

**Datasets**

| Term | Meaning |
|---|---|
| SGD | Schema-Guided Dialogue dataset. Events_1 and Events_2 act as applications A and B. |
| AskUbuntu (Lei et al.) | 167,765 questions with user-marked duplicates, IDs ordered in time. Used for all exploratory AskUbuntu work. |
| AskUbuntu 2024 dump | 414,451 questions from the Stack Exchange dump of 2024-04-02. Used only for the confirmation. |

**Conditions and methods**

| Term | Meaning |
|---|---|
| V2 / V3 | Memory of one application ("desk") only / memory shared by both. |
| M0 | Plain retrieval: cosine similarity of `nomic-embed-text` embeddings. |
| M1 | M0 plus confirmed relations. The score of an old question is the maximum of its own similarity, the similarity of any directly confirmed duplicate of it, and the similarity of the centroid of the question and its confirmed duplicates. |
| M2 | M1 + β·ln(1 + number of confirmed links), with β = 0.02: a global popularity bonus. |
| M3 / M4 | Learned metric (KISSME) / M2 on the learned metric. |
| P0 | Control: always suggest the most-linked questions. |
| H | Five suggestions alternating M0 and M2 (M0-1, M2-1, M0-2, …). The first suggestion is always M0's. |
| H1 | The same as H, alternating M0 and M1. |
| G | H with a familiarity gate: the network's pick may go first only if its evidence without the bonus beats plain similarity. |

**Metrics**

| Term | Meaning |
|---|---|
| Marked hit | An earlier user-marked duplicate appears among the 5 suggestions, divided by **all** new questions in the window. |
| Family hit | The marked duplicate, or an already-confirmed duplicate of it, appears among the 5 suggestions. |
| Judge | A model answers "would a correct answer to B solve A? YES/NO" for the first suggestion. It is checked on controls: marked-duplicate pairs (sensitivity) and random pairs (false positives). |

---

## Part 1 — Schema-Guided Dialogue (can a shared memory of interpretations reduce work?)

The first framing was a shared cache of validated interpretations of user requests between two applications. It started with hashes of phrases.

| Stage | Question (and criterion, when pre-registered) | Result | Decision |
|---|---|---|---|
| Hash diagnostics (dev set) | Diagnostic, no criterion. How often do exact keys recur, and how precise are they? | Partial keys covered 15–25% of turns with 61–82% precision. The key with values and prior state covered ~1% (it uses gold state, so it is diagnostic only). | The Events test set was contaminated by an earlier analysis and was reclassified as exploratory. Flights splits were frozen for later. |
| Round 1: V0 small model | Exploratory trial, no criterion. Baseline quality of a small, locally trained normaliser. | Intent accuracy 91.4% (A) / 79.5% (B). Q 94.1% / 87.5% (always-wait baseline 75.6% / 71.6%). | Continue. |
| Round 2: V0 fixes + memory (V2, V3) | Registered before running; exploratory, no hypothesis test. Does episodic memory add to a well-trained small model? | V0 improved (Q 96.0% / 90.9%). Memory was consulted in 24–27% of turns but agreed with the model 98% of the time. V2 − V0 on Q: −0.3 [−1.1; 0.0] (A), −0.1 [−0.6; 0.3] (B). | Memory is redundant when the model already knows the domain. |
| Round 3: low-data curve | With 2% of training data, is V3 − V0 on Q entirely above zero in at least one application? | Met in B by a minimal margin: +0.9 [0.1; 1.7]; A: +1.0 [0.0; 2.1]. With 2% of the data, V0 loses ~19 points in B (~17 in A), and memory recovers about 1. | Criterion met, practical effect negligible. |
| Round 4: shared memory of validated values | Recover ≥ 25% of the low-data gap on call turns, CI above zero. | A: 10.7% (+5.4 [1.5; 9.7] of a 50.5-point gap). B: 2.8%. | **Not met.** This form of shared memory was abandoned. |

## Part 2 — AskUbuntu, exploratory (can shared memory find known solutions to real problems?)

**Simulation.** Questions are ordered by ID (time). The last 20% form the evaluation window (33,553 questions) and the previous 10% the calibration window. There are two simulated desks, with 3 random draws. Pre-registered criterion (rounds 5–7): V3 marked hit ≥ 5% of new questions **and** V3 − V2 ≥ 2 points with CI above zero.

| Stage | Result | Decision |
|---|---|---|
| Round 5: TF-IDF | Ceiling (an earlier marked duplicate exists): 3.75% (V2), 7.19% (V3). Marked hit: 0.50% / 0.80%. Sharing +0.30 [0.24; 0.35]. Sanity check on the standard benchmark: P@1 0.543, MAP 0.557 (close to published BM25). | **Not met.** Repeated problems exist, but retrieval fails to find them. |
| Round 6: local pilot (Ollama) | On 60 benchmark questions: embeddings P@1 73.3% vs TF-IDF 51.7%. Rewriting questions into a canonical form with `llama3.1:8b` did worse (60.0%; with 60 questions, an indication rather than proof): the model invented and erased details. | Rerun round 5 with embeddings. |
| Round 5 with embeddings | Marked hit 0.79% (V2), 1.19% (V3). Sharing +0.40 [0.32; 0.47]. | **Not met.** |
| Round 7: identity, weight, learning | M0 1.19%, M1 3.65%, **M2 4.84%** (primary, β = 0.02 chosen in calibration), M3 2.36%, M4 4.67%, P0 control 1.03%. M2 sharing: +2.26 [2.11; 2.40]. | **Not met by 0.16 points** (5% required). The sharing part was met. Recorded as not met. |

**Exploratory analyses after round 7** (none changes the round-7 result):

- **What M2 recognises.**
  - M2 won in 1,293 cases where M0 missed, and lost in 67.
  - The gains came from the group centroid in 68% of cases and from a bridge through a confirmed duplicate in 32%. The popularity weight was decisive in 34%.
  - In 78% of the gains, the retrieved item was among the 50 most-linked "umbrella" guides.
  - Chaining links creates one giant component of 3,712 questions.
- **Comparative judge and family metric.**
  - With the family metric, M0 rises from 1.19% to 3.19% while M2 stays at 4.91%. About half of the apparent 4× gain came from moderators marking canonical guides.
  - The judge (gemma4; sensitivity 0.45, false positives 0.00) rated M2's first suggestion worse: corrected difference −0.149 [−0.307; 0.000], with the upper bound touching zero.
- **Round 8: familiarity gate** (pre-registered criteria C1: family gain ≥ 1 point with CI above zero; C2: judge difference lower bound ≥ −0.03).
  - G − M0 on family: +1.41 [1.30; 1.53]. Judge: −0.003 [−0.010; +0.002]. **Both passed.**
  - The gate was nearly inert: it changed the first suggestion in 2.8% of unmarked questions. H without the gate matched G (4.59% vs 4.60%). What works is interleaving.
  - Replication on a new sample: M2 − M0 on the judge = −0.077 [−0.118; −0.031].
- **Diagnostic 8b: relations or popularity bonus?**
  - M1 − M0 (judge): +0.010 [−0.012; 0.032]. M2 − M1: −0.087 [−0.129; −0.042].
  - Of the 67 cases where M2 degraded a good first suggestion, 56 were caused by the bonus alone. (The M2 − M0 comparison reuses round 8's judgements of the same questions, so it is not an independent replication.)
  - Calibrating β on marked hits chose 0.02; calibrating on the judge chose 0. **For the first suggestion, the popularity bonus, not the relations, was the problem.**
  - The bonus also supplied 44% of the family gain: M1 family gain +0.97 [0.86; 1.08], just under the 1-point bar, against +1.73 for M2.
- **Network-effect curves.**
  - *Density of confirmations* (content fixed): saturating, with saturation index 0.128 [0.068; 0.195]. 10% of the links gave ~46% of M1's gain.
  - *Participants* (one community split into 10 simulated applications): the relative gain of M1 over M0 grew from +3% (1 application) to +31% (10); for H, from +3% to +44%. Part of this growth is expected by construction, because a link can exist only when both questions are in the memory.
  - The absolute gain per new application decreased (H: 0.57 → 0.195 points), below the 50% bar set for a "strong" signal. Plain search saturated faster (M0: 0.332 → 0.052).
  - Pre-registered reading: **moderate** network-effect signal.

## Part 3 — Independent confirmation (AskUbuntu 2020–2024)

**Registered before running, then revised before any run after an external review.**

- **Data:** Stack Exchange dump of 2024-04-02, 414,451 questions. Evaluation covers questions created from 2020-01-01 (96,333; 5,982 with an earlier marked duplicate, a 6.21% ceiling).
- **Memory:** all earlier questions, plus the duplicate links created before 2020 between pre-2020 questions (32,864 links).
- **Historical text versions**, taken from the edit history: new questions as originally written; pre-2020 questions as they stood on 2020-01-01. Nothing edited later can leak into the test.
- **Frozen methods:** M0, M1, M2, H; H1 descriptive only.
- **Primary criteria:**
  - P1: family gain of M1 over M0, relative-gain CI lower bound > +10%.
  - P2: judge difference M1 − M0, CI lower bound ≥ −0.03, **only if the judge passes its controls** (sensitivity ≥ 0.30, false positives ≤ 0.15, gap ≥ 0.25).
  - P3: family gain of H over M0, relative-gain CI lower bound > +10%.
- **Outcomes:**
  - CONFIRMED if P1, P2 and P3 pass with a valid judge.
  - NOT CONFIRMED if P1 or P3 fails, or if the judge is valid and P2 fails.
  - INCONCLUSIVE if P1 and P3 pass but the judge fails its controls.
- **Fingerprints:** caches were checked by SHA-256 of data and texts and by model digest.

**Results**

| Method | Family hit (top 5) | Relative gain over M0 [95% CI] | Marked hit (top 5) |
|---|---|---|---|
| M0 | 1.61% | — | 0.80% |
| M1 | 2.28% | +41.4% [+36.7%; +45.9%] | 1.90% |
| H | 2.57% | +59.3% [+54.2%; +65.0%] | 2.45% |
| M2 | 2.84% | +76.0% [+69.0%; +83.5%] | 2.75% |
| H1 | 2.12% | +31.3% [+27.6%; +35.0%] | 1.64% |

- **P1 passed. P3 passed.**
- **The judge failed its controls** (gemma4: sensitivity 0.271, false positives 0.000). P2 is therefore inconclusive, and the **official outcome is INCONCLUSIVE**.
- Descriptive values only, with no criterion attached:
  - Judge M1 − M0: −0.019 [−0.044; +0.004].
  - Judge M2 − M1: −0.077 [−0.116; −0.039], the same direction as in the exploratory phase.

**Complementary step: blind second judge** (pre-registered; does not change the official outcome)

- **Items:**
  - 370 blind items: both first suggestions for the 145 questions where M0 and M1 differ;
  - 40 marked-duplicate controls and 40 random controls.
- **Labelling:** by Claude subagents that received only the rubric and the items. The answer key stayed on the author's machine, and a local script returned aggregates only. The orchestrating assistant knew the hypotheses and gemma's aggregate result; it only merged the label batches.
- **Controls (pre-registered validity gate):**
  - Second judge: sensitivity 0.575, false positives 0.000, **passed the controls**. Rejecting random pairs is an easy test, so this does not validate the judge for hard cases.
  - gemma4 on the same controls: 0.205, **failed**.
- **P2 (complementary):** M1 − M0 = −0.019 [−0.048; +0.007]. **Non-inferiority not shown.**
  - Discordant pairs: 8 vs 13 favouring M1 among marked questions, 18 vs 10 favouring M0 among unmarked ones.
- **Agreement between the judges:** 71.9%, Cohen's κ = 0.33.
- **Reading:** there is not enough evidence to let the network choose the first suggestion. Keeping plain search first (design H) is the prudent decision.

## Integrity notes

- **Two blind sets were compromised and not used.** Diagnostic 8b and the confirmation each had one: the answer key reached the evaluator before labelling. The procedure was changed: the key never leaves the author's machine.
- **External review changed the work before and after runs.** The author relayed critiques from ChatGPT.
  - Before runs, they changed the confirmation's design: the judge validity gate, the historical text versions and the cache fingerprints.
  - After runs, they prompted corrections of interpretation, recorded as dated errata at the end of the original protocol:
    - "no marked duplicate" does not mean "outside a known family";
    - not showing non-inferiority is not showing harm;
    - passing easy controls does not validate an AI as a curator;
    - the demonstrated gain is retrieval of discussions, not verified solutions.
- **A hypothesis added during the work:** "AI as curator of the collective memory" (the author, 29 September 2026), documented in [framework.md](framework.md). It is untested.
