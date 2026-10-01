# Framework: a shared registry of problem identities

**Author:** Alexandre Cardoso Rego · version 0.2.2 · 1 October 2026 (first version 29 September 2026) · [Português](framework.pt-BR.md)

Sections 1 and 2 describe the motivation and the design. From section 3 on, each point carries one of four labels:

- **[Evidence]** was measured, and the experiment log says where.
- **[Interpretation]** is our reading of the evidence; it is plausible but not directly measured.
- **[Hypothesis]** is a testable claim that has not been tested yet.
- **[Proposal]** is a design choice, not a claim about the world.

---

## 1. Motivation

People and AI systems keep solving problems that were already solved elsewhere. The solutions live in forums, tickets and private conversations, where they are hard to find again. With large language models, repeated problems are also regenerated from scratch, at a cost in compute and with the risk of a different, possibly wrong, answer each time.

The project asks a simple question: **what if recurring problems had an identity of their own, shared across applications, so that known solutions could be found and reused?**

## 2. Core concepts [Proposal]

**Problem identity.** A persistent identifier that groups **situations considered equivalent under explicit criteria**, such as the same symptom, the same cause and the same context. **Procedures (solutions) are linked to these situations**, each with the conditions under which it applies.

- Identity is **not** defined by a shared solution. A broad procedure can serve different problems, as the general "umbrella" guides did in the experiments (section 3.5).
- The identifier plays the role that the ICD plays for diseases or CVE for software vulnerabilities, applied to everyday technical problems.
- It is not assigned by a central authority. It emerges from confirmations, whose types are defined below.

**Confirmation (link).** A statement that two reported problems are related, stored with:

- a **type**: *same problem*, *the same solution applies*, or *related*. These behave differently: "same problem" is close to transitive, "same solution applies" is not;
- **provenance**: who confirmed it (a person, or an AI system with its model and version), when, and on what evidence. The strongest evidence is an outcome ("this solved it"), not an opinion;
- a **confidence** and the possibility of being **contested** and corrected, with history kept.

**Registry.** A shared store of identities and confirmations used by many applications. It is auditable wherever the content allows. Private problems enter only with consent and anonymisation.

**Retrieval layer.** How an application uses the registry when a new problem arrives. The design currently supported by evidence is described in section 3.

## 3. What the experiments taught about the design

1. **Confirmed relations help find the right family of problems. [Evidence, confirmed on independent data]**
   - On 2020–2024 AskUbuntu questions, adding confirmed duplicate relations to plain semantic search raised the retrieval of the marked family among five suggestions by 41% (relations only) to 59% (interleaved design).
   - These are discussions, not verified solutions.
2. **Keep the closest case first and add the family around it. [Evidence plus a prudent decision]**
   - The interleaved design keeps the first suggestion identical to plain search.
   - Whether the network alone can safely choose the first suggestion is still unresolved: the interval from the judge that passed its controls runs from −4.8 to +0.7 points.
   - **Preserving the first suggestion does not guarantee preserving the quality of the final answer. [Evidence, round 9]** On AskUbuntu questions without a marked duplicate, answers written with H's context (first suggestion identical to plain search) failed the pre-registered non-inferiority margin against plain search: −0.070 [−0.138; 0.000]. The other suggestions also enter the context and can hurt. [Interpretation]
3. **A global popularity weight is double-edged. [Evidence, exploratory; same direction, descriptively, in the confirmation]**
   - A bonus based on how many links a node has, a kind of "fame", pulled famous general guides into unrelated questions. It was the main source of damage to the first suggestion (56 of 67 degraded cases in the exploratory diagnostic).
   - The same term supplied 44% of the family gain in that diagnostic. [Evidence, exploratory] Our reading is that it brings the family's canonical guides into the list. [Interpretation]
   - The confirmed design H, defined in round 8 before this diagnostic, happens to use M2 only after the plain first suggestion. Without the term (H1, reported descriptively in the confirmation), the gain is +31% instead of +59%.
   - **On final answers, removing the term helped relative to H. [Evidence, pre-registered, round 11, Super User only]** On questions without a marked duplicate, answers with H1's context were preferred to answers with H's: +0.060 [+0.013; +0.109]. Across the eligible questions, H1 stayed within the 3-point margin of plain search (+0.006 [−0.016; +0.029]). Superiority of H1 over plain search was **not** shown, and this comparison has not yet been run on AskUbuntu.
4. **Weights should depend on context. [Proposal / Hypothesis]**
   - A link, or a node, should gain weight only from confirmations that resemble the new problem.
   - This is the formal version of the original "synapse" intuition, close to spreading activation in cognitive models of memory and to personalised PageRank in graph theory.
5. **Identity is not the transitive closure of links. [Evidence]**
   - Chaining confirmations merged 3,712 AskUbuntu questions into one giant group through a few "umbrella" guides.
   - Identities should come from a partition that tolerates noisy and contradictory confirmations; correlation clustering is a natural formalisation. [Proposal]
6. **On AskUbuntu, "duplicate" often means "the answers there solve this". [Interpretation]**
   - That is closer to "the same solution applies" than to "same problem", which is one reason links need types.
7. **A fraction of the links captured much of the gain.**
   - With content fixed, removing links at random from the whole network, 10% of the confirmations gave about half of the gain and 25% gave 70%. [Evidence, exploratory]
   - This test reduced the links of the whole network. It does not determine how many confirmations each family needs. *Correction (1 October 2026): version 0.1.1 read "a few confirmations per family capture most of the value", which went beyond the test.*
   - Prioritising new families over densifying existing ones remains a hypothesis. [Hypothesis]
8. **The network effect signal is moderate. [Evidence, exploratory simulation]**
   - When one community was split into ten simulated applications, confirmations became proportionally more valuable as more applications joined: +3% relative gain with one, +31% with ten. Part of this is expected by construction, because a link can exist only when both questions are in the memory.
   - At the end of the curve, plain search gained much less per added application than the confirmation-based memory: 0.052 points against 0.195 for H.
   - The absolute gain per new application still decreased.
9. **The network helps the answer when it brings the right family, and knowing in advance when it will do so was not achieved. [Evidence, pre-registered, rounds 9 and 10]**
   - Round 9 (AskUbuntu): when the interleaved design brought the marked family that plain search missed, the judges preferred its answers: +0.153 [+0.024; +0.282], 124 questions.
   - Round 10: a gate based on how much the network's candidate beat plain search could not be calibrated for its signal, grid and requirements.
   - These are preferences of a blind judge, guided by the asker's accepted answer, not problems verified as solved.
10. **Smaller gains on a sparser network. [Evidence, round 10]** On Super User, where only 1.89% of new questions have an earlier marked duplicate, relations improved retrieval much less than on AskUbuntu (M1 +15.5% against +41.4%). This compares two sites; it does not isolate the effect of sparsity.

## 4. Hypothesis: AI as curator of the collective memory

*Proposed by Alexandre Cardoso Rego on 29 September 2026. Recorded as a hypothesis; not yet tested.* **[Hypothesis]**

**Original formulation.** Today, people use AI systems, and ever larger models, to generate answers, including answers to problems already solved. The main role of AI should instead be to validate and confirm the content of a shared base, improving it, rather than reprocessing everything on each request.

**Refined formulation: generate once, validate many, reuse always.** The AI generates only for what is genuinely new. For what already exists, its central role is curation:

- confirming or refuting links;
- detecting errors;
- consolidating families;
- recording evidence.

The registry stops being a passive cache and becomes a verifiable collective memory that is actively maintained.

**Why it fits the results.** The measured value comes from confirmations, and confirmations are scarce because they depend on human moderators. An AI curator could reduce the dependence on human moderation to extend the network. Even a good curator only judges the candidates that search brings, and rare families may remain uncovered. *Correction (1 October 2026): version 0.1.1 said that an AI curator "attacks exactly that bottleneck", which is stronger than the evidence allows.*

**Corrections built in.**

1. **Not "exclusively".** This applies to recurring problems with verifiable solutions, such as technical support, software errors and configuration. It does not apply to unique, personal or creative tasks.
2. **Validation is not always easy.**
   - In the confirmation, a small local judge in the configuration tested (gemma4, fixed prompt, 70-word excerpts) recognised only about a quarter of true duplicates. This applies to that configuration, not to every small or local model.
   - The economic argument is amortisation: a link is validated once, even by an expensive model, and reused many times.
3. **Passing easy controls is not validation as a curator.** Rejecting random pairs is easy. The decisive test is whether the curator creates correct links on hard cases: very similar problems that need different solutions. That test needs independent evaluation, before AI-created links are allowed to influence other answers.

**Risks and requirements.**

- **Risks:**
  - errors that propagate through links;
  - monoculture, where one model's biases become the "truth" of the base;
  - manipulation;
  - AI confirming AI-generated content.
- **Requirements:**
  - provenance for every confirmation;
  - more than one independent validator;
  - outcome evidence whenever possible;
  - the right to contest.

These requirements make the public, auditable character of the registry indispensable rather than optional.

**Possible benefits (not measured).**

- Less compute and energy spent regenerating answers to solved problems.
- Answers with provenance instead of fresh, possibly invented ones.
- Access: a verified public base that small models and inexpensive devices could use.

## 5. Governance and risks [Proposal]

- **Error propagation.** Links are not transitive by default; merges require stronger evidence than single links.
- **Manipulation.** Adversaries may plant false links or create variants to avoid true ones. Provenance, independent validation and contestation are the defences.
- **Privacy.** Problems often come from personal contexts. Content enters only with consent and anonymisation.
- **Concentration of authority.** Whoever controls the validator shapes what counts as "the same". Governance should be independent and auditable.

## 6. Beyond technical support [Hypothesis]

The general mechanism, giving an identity to things that appear scattered across sources through confirmed "this is the same as that" links, may apply elsewhere. Each application carries its own serious risks.

- **Fact-checking.** Recognising that a new claim is the same as one already checked, in other words.
- **Law.** Courts already group repetitive cases into numbered themes; a shared identity of legal questions generalises this.
- **Public administration.** Sharing which problems other municipalities solved, and how.
- **Public-records oversight, including anti-corruption.** Linking the same person, company or contract across fragmented databases.
  - An automated link can destroy an innocent person's reputation.
  - The same tool can be used for persecution.
  - Such a system should produce leads for investigation, never accusations, under strong legal safeguards and independent governance.

None of these uses has been tested here.

## 7. Relation to existing work

Many pieces exist:

- identifier systems (ICD, CVE);
- crash bucketing that groups identical failures across millions of machines;
- IT-service "known error" databases;
- duplicate-question detection in community Q&A;
- semantic caches and memory layers for AI agents;
- cluster-based retrieval;
- the literature on popularity bias and on hubs in high-dimensional spaces.

What seems uncommon is the combination: a **cross-application, public and auditable registry of problem identities, curated with the help of AI**, together with pre-registered evidence of what helps and what harms. No claim of priority is made beyond the dated record in this repository.

## 8. Next experiments

1. **Links over a hybrid search (round 12, frozen and published before running):** do confirmed links still add to a fusion of word search (BM25) and an embedding model selected by a pilot on exploratory data?
2. **AI curator on hard cases (round 13, draft):** can a low-cost local model create correct "the answers of B solve A" links between very similar questions, under independent evaluation, and how does that compare with training a metric on the same pairs?
3. **Contextual weights:** spreading activation or personalised PageRank from the query instead of global popularity. The goal is to keep the recall benefit of the popularity term without its harm.
4. **Identity as correlation clustering** instead of 1-hop neighbourhoods.
5. **Across real applications:** different Stack Exchange sites, or duplicate issues across GitHub repositories.
6. **Resolution and savings:** rounds 9–11 measured a blind judge's preferences between final answers. Whether the problems are actually solved, whether work is saved, and whether the total cost falls are still open.
