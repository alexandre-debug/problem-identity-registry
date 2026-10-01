# Environment and clean-run instructions

The work ran in two environments. The versions below are the ones actually used. They were recorded on 29 September 2026, in the same environments, just after the runs.

## Environments

| | Rounds 1–5 (SGD; AskUbuntu with TF-IDF and word vectors) | Round 6 onward and the confirmation (local models) |
|---|---|---|
| Machine | Assistant's cloud sandbox (Linux, 2 CPUs, 7 GB RAM, no GPU) | Author's MacBook Pro, macOS 26.5 (build 25F71) |
| Python | 3.11.15 | 3.14.6 (virtual environment) |
| Libraries | numpy 2.4.4, scipy 1.17.1, scikit-learn 1.8.0 ([requirements-sandbox.txt](requirements-sandbox.txt)) | numpy 2.5.3, scipy 1.18.1, scikit-learn 1.9.1, py7zr 1.1.3, and dependencies ([requirements-mac.txt](requirements-mac.txt)) |
| Ollama | — | 0.30.10 |

## Models (Ollama)

| Model | Used in | Digest |
|---|---|---|
| `nomic-embed-text` | Round 6 onward (embeddings) | `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f` (recorded in the confirmation) |
| `gemma4:latest` | Judges (exploratory stages and confirmation) | `c6eb396dbd5992bbe3f5cdb947e8bbc0ee413d7c17e2beaae69f5d569cf982eb` (recorded in the confirmation) |
| `llama3.1:8b` | Round 6 pilot only (canonical rewriting) | not recorded |

Digests were recorded automatically only in the confirmation. The exploratory AskUbuntu stages used the same local models by name, but their digests were not stored.

## Clean run (macOS or Linux)

1. **Get the code.**
   ```
   git clone https://github.com/alexandre-debug/problem-identity-registry.git
   cd problem-identity-registry
   ```
2. **Create an isolated Python environment** and install the exact versions:
   ```
   python3 -m venv env
   source env/bin/activate
   pip install -r code/requirements-mac.txt
   ```
3. **Install Ollama** (version 0.30.10 was used) and pull the models:
   ```
   ollama pull nomic-embed-text
   ollama pull gemma4:latest
   ollama list
   ```
   In the `ID` column, `nomic-embed-text` should start with `0a109f422b47` and `gemma4:latest` with `c6eb396dbd59`. If the IDs differ, the registry has published a new version of the model. The scripts will still run, but the results may differ, and the confirmation script refuses to reuse caches built with another digest.
4. **Confirmation** (about 10 GB of free disk; about 1.5 hours on the author's Mac):
   - Download `askubuntu.com.7z` from the Stack Exchange data dump of 2024-04-02: https://archive.org/details/stackexchange
   - Put it in `code/03-confirmation/`, then run:
   ```
   cd code/03-confirmation
   python3 gc_conf.py --judge gemma4:latest
   ```
   The result is `gc_conf_result.json`. Its field `reproducao.dados_sha256` should be `951a20e2e4b6866d79954cf06a338148bd8829f90e36bcb27f01670336928fe7` if the data and processing are identical.
5. **Exploratory AskUbuntu stages** (run in this order, inside `code/02-askubuntu-exploratory`):
   ```
   python3 gc_local_support.py --embed nomic-embed-text   # downloads data, embeddings (~1 h)
   python3 gc_local_brain.py                              # round 7
   python3 gc_local_explain.py
   python3 gc_local_judge.py --judge gemma4:latest
   python3 gc_local_gate.py --judge gemma4:latest         # round 8
   python3 gc_local_bonus.py --judge gemma4:latest        # diagnostic 8b
   python3 gc_local_rede.py                               # network curves
   ```
   The round 6 pilot is `python3 gc_local_pilot.py --llm llama3.1:8b --embed nomic-embed-text --limit 60`.
6. **SGD rounds 1–4** (inside `code/01-sgd-rounds`, with `requirements-sandbox.txt`):
   - Clone `google-research-datasets/dstc8-schema-guided-dialogue` and set `SGD_ROOT` to its folder.
   - Then run `split.py`, `train_normalizer.py`, `run_v0.py`, `train_normalizer_r2.py`, `run_round2.py`, `run_curve.py` and `run_values.py`.
7. **Round 5 (TF-IDF):** set `ASKUBUNTU_ROOT` to a clone of `taolei87/askubuntu` and run `run_support.py`.

## Notes on determinism

- **Seeds are fixed** in every script, so samples and splits are reproducible.
- **Embeddings and judge outputs** come from Ollama with temperature 0. They are pinned by model digest, but they are not guaranteed to be bit-identical across hardware or Ollama versions. Small numerical differences can change a few rankings.
