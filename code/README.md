# Code

The scripts are published **as they were run**. The only change: hard-coded data paths in the early scripts were replaced with environment variables (`SGD_ROOT`, `ASKUBUNTU_ROOT`). The logic is untouched. Script output messages are in Portuguese.

Install the dependencies with `pip install -r requirements.txt` (Python 3.10+). The AskUbuntu stages from round 6 onward also need [Ollama](https://ollama.com) with `nomic-embed-text` (embeddings) and a judge model (`gemma4` was used).

## 01-sgd-rounds: rounds 1–4 (Schema-Guided Dialogue)

**Data.** Clone `google-research-datasets/dstc8-schema-guided-dialogue` and set `SGD_ROOT` to its folder.

| Script | Purpose |
|---|---|
| `split.py`, `split_pair.py` | Frozen splits (seed 20260928); reproduce `manifest.json` / `manifest_flights.json` byte for byte. |
| `hash_diag.py`, `hash_space.py`, `stats.py`, `pairs.py`, `informative.py`, `entity.py` | Diagnostics of exact-key reuse and of the data. |
| `gc_common.py`, `gc_features.py`, `gc_v0.py`, `gc_train.py`, `gc_memory.py`, `gc_values.py` | Small-model pipeline (V0) and memories (V2/V3). |
| `train_normalizer.py`, `train_normalizer_r2.py` | Train the scikit-learn normaliser. |
| `run_v0.py` | Round 1. |
| `run_round2.py` | Round 2. |
| `run_curve.py` | Round 3. |
| `run_values.py` | Round 4. |

## 02-askubuntu-exploratory: rounds 5–8, diagnostics and network curves

**Data.** The AskUbuntu dataset of Lei et al. (`taolei87/askubuntu` on GitHub). The local scripts download `text_tokenized.txt.gz`, `train_random.txt` and (pilot only) `test.txt` into `gc_data/` themselves. `run_support.py` and `check_support.py` read from `ASKUBUNTU_ROOT`.

| Script | Stage |
|---|---|
| `run_support.py`, `check_support.py` | Round 5 (TF-IDF, pre-trained word vectors) and a sanity check on the standard benchmark. |
| `gc_local_pilot.py` | Round 6 pilot (embeddings vs canonical rewriting). |
| `gc_local_support.py` | Round 5 repeated with embeddings. Computes and caches the embeddings (about an hour on the author's Mac for 167k questions; resumable). |
| `gc_local_brain.py` | Round 7 (M0–M4, popularity control P0). |
| `gc_local_explain.py` | What M2 recognises (mechanisms, diversity, cost). |
| `gc_local_judge.py` | Comparative judge M0 × M2 and the family metric. |
| `gc_local_gate.py` | Round 8 (familiarity gate G, interleaved H). |
| `gc_local_bonus.py` | Diagnostic 8b (relations vs popularity bonus; β curve). |
| `gc_local_rede.py` | Network-effect curves (confirmation density; simulated participants). |

Every script after `gc_local_support.py` reuses its cached embeddings in `gc_cache/`. Judge scripts share a judgement cache.

## 03-confirmation: independent confirmation (AskUbuntu 2020–2024)

**Data.** Download `askubuntu.com.7z` from the Stack Exchange data dump of 2024-04-02 (https://archive.org/details/stackexchange) and place it next to the scripts. About 10 GB of free disk space is needed.

```
python3 gc_conf.py --judge gemma4:latest       # extraction, historical texts, embeddings, evaluation, judge
python3 gc_conf_juiz2.py gerar                 # blind items for a second judge; the key stays local
python3 gc_conf_juiz2.py comparar juiz2_rotulos.json  # compares labels locally, outputs aggregates only
```

- **Resumable:** every step can be restarted with the same command.
- **Verified caches:** parsed data, embeddings (model digest, text SHA-256) and judgements (prompt, model digest, data SHA-256) are reused only if they match.
- **Judge validity gate:** a judge must reach sensitivity ≥ 0.30 on marked duplicates, ≤ 0.15 false positives on random pairs, and a gap of at least 0.25 between the two. Otherwise the judge-based criterion is INCONCLUSIVE, never a pass.

## 04-answer-quality: rounds 9–11 (answers with retrieved context)

**Data.** The confirmation's data and caches (run `03-confirmation` first) and, for rounds 10A and 11, `superuser.com.7z` from the same dump. Ollama with `nomic-embed-text` and `gemma4`.

| Script | Stage |
|---|---|
| `gc_r9.py` | Round 9 (AskUbuntu): plain search vs H as answer context, blind judging. |
| `gc_r10_portao.py` | Round 10, stage B: calibration of a gate that decides when to use the network (no language model). |
| `gc_r10_A.py` | Round 10, stage A: confirmed relations on Super User (embeddings only). |
| `gc_r11.py` | Round 11 (Super User): M0, H1 and H as answer context, blind judging. |

Commands, the blind-judging procedure and the SHA-256 of every script version, including the frozen ones in `versions/`, are in [04-answer-quality/README.md](04-answer-quality/README.md).

## 05-hybrid-search: round 12 (frozen, not yet run)

**Data.** The confirmation's data, caches and result (run `03-confirmation` first). Ollama with `nomic-embed-text` and the five candidate embedding models listed in [05-hybrid-search/README.md](05-hybrid-search/README.md).

| Script | Stage |
|---|---|
| `gc_r12.py` | Round 12: `piloto` selects the embedding model by a frozen rule on exploratory data; `rodar` compares the links over a hybrid search (BM25 + the selected model). Published before running. |
