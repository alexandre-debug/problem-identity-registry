# 04-answer-quality: rounds 9–11

Does the retrieved discussion improve the final answer? A local model (gemma4, through [Ollama](https://ollama.com)) answers new questions with five retrieved discussions as context. Blind judges then compare pairs of answers, with the asker's accepted answer as a reference. The pre-registered designs, criteria and results are in [../../docs/protocolo-continuacao.pt-BR.md](../../docs/protocolo-continuacao.pt-BR.md) (Portuguese) and summarised in [../../docs/experiment-log.md](../../docs/experiment-log.md), Part 4.

## Before you start

- Run the confirmation first ([../03-confirmation](../03-confirmation)). These scripts reuse its `gc_data/`, `gc_cache/` and `gc_conf_result.json`.
- Copy `gc_conf.py` from `../03-confirmation/` into this folder, or run everything from one folder that holds all the scripts. Every script here imports `gc_conf`; `gc_r10_portao.py` and `gc_r11.py` also import `gc_r9`.
- Ollama with `nomic-embed-text` (embeddings) and `gemma4:latest` (answers). The digests used are recorded in each result file.
- Round 9 also needs `Votes.xml` from `askubuntu.com.7z`. Rounds 10A and 11 need `superuser.com.7z` from the same Stack Exchange dump (2024-04-02). The scripts extract what they need, with the `7z` command or `py7zr`.

## Commands

**Round 9 (AskUbuntu): does the network's context improve the answer?**

```
python3 gc_r9.py preparar                                   # strata and samples -> r9_amostra.json
python3 gc_r9.py piloto --modelo gemma4:latest              # 10 questions outside the sample: time and format
python3 gc_r9.py gerar --modelo gemma4:latest --pre-registro-congelado   # all answers; resumable
python3 gc_r9.py controles                                  # judge-control pairs for prior review
python3 gc_r9.py itens                                      # blind items + the key (keep the key local)
python3 gc_r9.py comparar r9_rotulos.json                   # aggregates only -> r9_resultado.json
```

**Round 10, stage B (AskUbuntu, no language model): can a gate say in advance when to use the network?**

```
python3 gc_r10_portao.py                                    # -> r10_portao_resultado.json
```

**Round 10, stage A (Super User, embeddings only): do confirmed relations help on another site?**

```
python3 gc_r10_A.py                                         # -> r10A_resultado.json; resumable
```

**Round 11 (Super User): plain search (M0), H1 and H on the same new questions.** Run after stage A.

```
python3 gc_r11.py preparar                                  # -> r11_amostra.json
python3 gc_r11.py gerar --modelo gemma4:latest --pre-registro-congelado
python3 gc_r11.py controles                                 # 1st time: r11_k4_base.txt; with r11_k4_erros.json: review file
python3 gc_r11.py itens
python3 gc_r11.py comparar r11_rotulos.json                 # -> r11_resultado.json
```

## Blind judging

- `itens` writes the items file, which starts with the rubric, and a key file named `*_chave_NAO_ENVIAR.json` ("do not send").
- The key never leaves the author's machine. Only the items file goes to the judges.
- The judges were fresh Claude subagents. Each received only the rubric and a batch of 35 items, and answered `A`, `B` or `TIE` for each item. Version and independence caveats are in [../ENVIRONMENT.md](../ENVIRONMENT.md).
- The labels are joined into one JSON file, `{"1": "A", "2": "TIE", ...}`. `comparar` reads it next to the key and writes only aggregates.
- The judge must pass its controls before any criterion counts: K1 easy discrimination (≥ 0.85), K2 order consistency (≥ 0.75), K4 decisive error (≥ 0.80, at least 30 pairs) and K5 equivalent answers judged a tie (≥ 0.50, at least 20 pairs). Otherwise the result is invalid, never a pass.
- Control pairs are reviewed before judging (`*_controles_revisao.txt` → `*_controles_aprovados.json`). In round 9, the local model could not insert usable K4 errors, and in round 11 it could not write enough usable K5 pairs, so separate Claude agents wrote those parts (deviations 1 and 2). In round 11, the K4 errors were written by an agent by design. The pair texts hold third-party text and are not published; only the review decisions (`*_controles_aprovados.json`) are. The SHA-256 hashes of the unpublished files are in [../../results/README.md](../../results/README.md).

## Script versions

Each script was registered with its SHA-256 before it ran. Later changes are recorded in the protocol as deviations or errata. Earlier versions are in `versions/`.

| Script | SHA-256 | Status |
|---|---|---|
| `versions/gc_r9_frozen_08963d0a.py` | `08963d0a10333741a0d71850e2756a2bf9af8d6bcab1ca4c43e20dd732b5947e` | Round 9 as frozen (29 Sep 2026). |
| `gc_r9.py` | `e1dbbe2cd3b04dce163a842c085b190c18b77d4e03cdcc3d7228c154f491e997` | Deviation 1: reads `r9_k4_erros.json`. Without that file, its output is byte-identical to the frozen version. Used for the round 9 result. |
| `gc_r10_portao.py` | `790fd9c56498435d4f891bb7fe50de844fca82042d2278aeb38da65876332b55` | Round 10, stage B, as frozen and run. |
| `gc_r10_A.py` | `6b744b417a36b5b32e3facdca0392910bd1b06f6dbe87262a41ee9633cca933e` | Round 10, stage A, as frozen and run. |
| `versions/gc_r11_frozen_ab436f92.py` | `ab436f92b8ec48db0384604a656cef7fec6df7bf12558c7fcbb1086c76b3d477` | Round 11 as frozen (30 Sep 2026). |
| `versions/gc_r11_deviation2_6e6ec634.py` | `6e6ec634e00c1dcc029965e98e77c43d90f5984706f16535af10f7c9044cf96e` | Deviation 2: reads `r11_k5_versoes.json`. Produced the items and `r11_resultado_original.json`, whose P1 has the wrong sign. |
| `gc_r11.py` | `0783fb6b1dd8392b34c45b2717829568410ee047d5a0b2951cd02dc1de0c6e21` | Erratum 1: P1 computed as Δ(CH1 − CH), as pre-registered. Produced `r11_resultado.json`; every other figure is identical to the original output. |

The version files in `versions/` are renamed copies; their content is byte-identical to the registered scripts. To run one, copy it here as `gc_r9.py` or `gc_r11.py`, since the other scripts import those names.

Script output messages are in Portuguese.
