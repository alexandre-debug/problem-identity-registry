# 05-hybrid-search: round 12 (frozen, not yet run)

Do the confirmed links still help over a better search? The confirmation measured the links over plain search with `nomic-embed-text`. Round 12 repeats the comparison over a hybrid search that fuses word search (BM25) with the embedding model selected by a pilot on exploratory data, on the same confirmation data. The selected model is not called stronger before it is measured. The pre-registration is in [../../docs/protocolo-continuacao.pt-BR.md](../../docs/protocolo-continuacao.pt-BR.md) (Portuguese) and summarised in [../../docs/experiment-log.md](../../docs/experiment-log.md), Part 5.

**Status:** frozen on 1 October 2026 at 08:06 (+02:00) and published in version 0.2.2 **before running**. There are no results yet.

| Script | SHA-256 |
|---|---|
| `gc_r12.py` | `3414f6b24daa3ed3cc971a7590876220fd6a8c2458c66178daeb65ce98eda832` |

## Before you start

- Run the confirmation first ([../03-confirmation](../03-confirmation)) and run this script in the same folder. It reuses `gc_data/au24_*`, the `nomic-embed-text` embeddings in `gc_cache/` and `gc_conf_result.json`, and it imports `gc_conf`.
- The script checks that the data have the confirmation's SHA-256 and that its `nomic-embed-text` methods reproduce the confirmation's numbers (tolerance 0.0001) before comparing anything.
- Pull the candidate embedding models in Ollama:
  ```
  ollama pull mxbai-embed-large
  ollama pull bge-m3
  ollama pull embeddinggemma
  ollama pull qwen3-embedding:0.6b
  ollama pull qwen3-embedding:4b
  ```

## Commands

```
python3 gc_r12.py piloto     # selects the model by the frozen rule -> r12_piloto.json
python3 gc_r12.py rodar      # embeddings of the whole archive (one night, or up to 24 h under the fallback rule; resumable) and the comparison -> r12_resultado.json
```

- **Pilot:** scores each candidate by MAP on the dev set of the AskUbuntu dataset of Lei et al. (exploratory data, downloaded if missing) and measures its embedding time on 1,000 confirmation texts with the same batch size as the full run. Rule: the highest MAP among the candidates estimated to finish within 10 hours (tie: the faster); otherwise the fastest within 24 hours; otherwise the round does not run.
- **Run:** builds BM25 (k1 = 1.2, b = 0.75, scikit-learn English stop words, IDF and average length from questions before 2020), the hybrid fusion (RRF, k = 60, top 100 of each list) and the frozen relation ranking M1 in the selected model's space. The main criterion compares H1(HIB_E) with HIB_E on the marked family in the top 5.

Both outputs contain numbers only. Script output messages are in Portuguese.
