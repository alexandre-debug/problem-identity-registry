# Results

Files are published as they were produced, except that third-party text was removed (see the last section). Field names are in Portuguese; the meaning of each figure is explained in [../docs/experiment-log.md](../docs/experiment-log.md).

## 01-sgd-rounds: rounds 1–4 (Schema-Guided Dialogue)

| File | Content |
|---|---|
| `manifest.json`, `manifest_flights.json`, `mapping.json` | Frozen splits and schema mapping. |
| `hash_diag.txt`, `hash_diag_raw.json`, `hash_space*.txt` | Exact-key diagnostics. |
| `normalizer_report.json`, `normalizer_r2_report.json` | Normaliser training reports. |
| `v0_dev_summary.json` | Round 1. |
| `r2_dev_summary.json` | Round 2. |
| `r3_curve_summary.json` | Round 3. |
| `r4_values_summary.json` | Round 4. |

## 02-askubuntu-exploratory

| File | Content |
|---|---|
| `r5_support_summary.json` | Round 5 (TF-IDF and pre-trained word vectors). |
| `gc_local_explain_result.json` | Mechanisms behind M2's gains. |
| `gc_local_judge_result.json` | Comparative judge M0 × M2 and the family metric. |
| `gc_local_gate_result.json` | Round 8. |
| `gc_local_bonus_result.json` | Diagnostic 8b. |
| `gc_local_rede_result.json` | Network-effect curves, transcribed from the terminal output. |

The numbers of rounds 6 and 7 and of round 5 repeated with embeddings are recorded in the protocol. Their outputs were reported from the terminal and are not stored as separate files here.

## 03-confirmation

| File | Content |
|---|---|
| `gc_conf_result.json` | Confirmation: data counts, all methods, judge controls, criteria and the official outcome (INCONCLUSIVE), plus fingerprints (data SHA-256, model digests, Ollama version). |
| `gc_conf_chave.json` | Key of the first blind set of the confirmation. **Compromised, not used**: the key was sent together with the items. |
| `juiz2_rotulos.json` | The second judge's labels for the 370 blind items. |
| `juiz2_resultado.json` | Aggregates computed locally by the author: validity of both judges, the complementary P2 and agreement between the judges. |

## 04-answer-quality: rounds 9–11

| File | Content |
|---|---|
| `r9_amostra.json` | Round 9: strata, sample sizes and the Stack Exchange question numbers of the sample (no text). |
| `r9_piloto.json` | Round 9 pilot: time per answer, answer length, model digest and Ollama version. The pilot's text output is omitted (see below). |
| `r9_controles_aprovados.json` | Round 9: the prior review's decision (APPROVED or REJECTED) for each judge-control pair, by identifier only (deviation 1). |
| `r9_rotulos.json` | Round 9: the blind judges' labels for the 1,050 items. |
| `r9_resultado.json` | Round 9: aggregates computed locally by the author (judge controls, criteria, secondary results). |
| `r10_portao_resultado.json` | Round 10, stage B: calibration of the gate on AskUbuntu (outcome: not calibratable). |
| `r10A_resultado.json` | Round 10, stage A: confirmed relations on Super User (retrieval only, no language model). |
| `r11_amostra.json` | Round 11: strata, sample sizes and question numbers (no text). |
| `r11_controles_aprovados.json` | Round 11: the prior review's decision for each judge-control pair, by identifier only (63 approved: K4 37, K5 26; deviation 2). |
| `r11_rotulos.json` | Round 11: the blind judges' labels for the 2,070 items. |
| `r11_resultado_original.json` | Round 11 as first computed, with the sign error in P1 (script `6e6ec634…`). Kept for the record. |
| `r11_resultado.json` | Round 11 corrected according to Erratum 1 (script `0783fb6b…`). This is the official result. |

The answer keys (`r9_chave_NAO_ENVIAR.json`, `r11_chave_NAO_ENVIAR.json`) never left the author's machine and are not published.

## Third-party text removed, with SHA-256 of the originals

Files and fields that contained excerpts of askubuntu.com or superuser.com posts, or model rewrites of them, were removed from this public version, so that everything published here can be released under CC BY 4.0. The author keeps the originals, and the SHA-256 hashes below identify them.

The files can be produced again by the scripts from the public data, but only with the same model digests and with the caches saved locally during the original runs (embeddings, and for `gc_conf_juiz2.py` also the gemma judgements). Bit-identical regeneration on other hardware is not guaranteed.

**Omitted files**

| File | Produced by | SHA-256 of the original |
|---|---|---|
| `juiz2_itens.txt` (370 blind items, complementary second judge) | `gc_conf_juiz2.py gerar` | `87d80f9bc877c1909af036bfb12269c0982fd215c9655174e2fbb0c09a46d848` |
| `gc_conf_cegos.txt` (first blind set of the confirmation; compromised, not used) | `gc_conf.py` | `b1ffd471b2e5263f7ff95221b535297057715071b02dbf09f96c5ccd19bbb7d5` |
| `gc_local_bonus_cegos.txt` (8b blind set; compromised, not used; its key is inside `gc_local_bonus_result.json`) | `gc_local_bonus.py` | `9f257926542a66deeffdb7ad06d288f9167dccdcd503b44884b7f37698b7bbae` |
| `gc_local_explain_exemplos.txt` (25 sampled examples of M2's gains) | `gc_local_explain.py` | `49ad9d1628ae23a162de2a61cfb613ccb522bd4325bb8ec66f3e063d9ad1f3e8` |
| `r9_piloto.txt` (pilot answers, round 9) | `gc_r9.py piloto` | `64506e8900bc3a1eb925b2c7bece348fa40224206997199100863a9a1ec29038` |
| `r9_controles_revisao.txt` (first control pairs, all written by gemma) | `gc_r9.py controles` (frozen `08963d0a…`) | `e6026ad36d7f5eb515289062392636fc9cd0f836553254432e87fb95b244858d` |
| `r9_k4_erros.json` (K4 errors inserted by a separate agent, deviation 1) | Claude agent | `17bd985ae3e73fd226c05062693c71d68fa27c868d3565595be36992db955ddf` |
| `r9_controles_revisao.txt` (control pairs after deviation 1, as reviewed; computed by the assistant from the same inputs) | `gc_r9.py controles` (`e1dbbe2c…`) | `1bbf38211918c1b36dd6a6334dc9ee0a75270e3ee9d502c2433e0b46a4125ecf` |
| `r9_controles_revisao.txt` (as produced on the author's machine and used for the items: the reviewed set without pair C032) | `gc_r9.py controles` (`e1dbbe2c…`) | `bf8040391215ab998181f7c4b9ef91f12b7206ad237e261d085bf7a0bc8e8502` |
| `r9_itens.txt` (1,050 blind items, round 9) | `gc_r9.py itens` | `d1fb1aa08ccabc1ab686b71681a52afe6a9fea9fec8819db1849dca6621a0086` |
| `r11_k4_base.txt` (faithful versions for K4, round 11) | `gc_r11.py controles` | `6855ce431ce1e6c99b7edcc3082217ae89d4b201ad6e16b4635cde3122e815a5` |
| `r11_k4_erros.json` (K4 errors inserted by a separate agent) | Claude agent | `39f83b8824acb3dcaf56ff4f8107d9d9aad009d36cf6bf6d5d628b0dd944bef6` |
| `r11_k4_erros_descricao.json` (what each inserted error changes) | Claude agent | `c19afa538c6ff29bfa34eda848e2be8af689a6d9e5048f160ec61203466f3f7b` |
| `r11_controles_revisao.txt` (control pairs, first review) | `gc_r11.py controles` (`ab436f92…`) | `a948756b5a49cae40caf5cbd2dfb4cb75eb37e553f1647330166c3fcb1aa0133` |
| `r11_k5_versoes.json` (new K5 second versions, deviation 2) | Claude agent | `a60cf2732221dd6a675fce7e1c9e861faba5d26b2b39328f2c2c294030194676` |
| `r11_k5_versoes_descricao.json` (notes on those versions) | Claude agent | `df5a12d73b190728b961a82940e966d780db761bc34f4039f59229d96cf67238` |
| `r11_controles_revisao.txt` (control pairs after deviation 2, as reviewed) | `gc_r11.py controles` (`6e6ec634…`) | `5c54da1bbdac0653353e6f248b2d0596ec3093899ead5c885d2df4ab10212c32` |
| `r11_itens.txt` (2,070 blind items, round 11) | `gc_r11.py itens` | `3f13b88dca2392e431f4617ba6a181c3bf047dd4de47fbd95a46e2e815eced29` |

For rounds 9 and 11, regenerating these files also needs the gemma generation caches saved on the author's machine (`r9_geracoes_e25567e4cc702dff.jsonl`, `r11_geracoes_ab105a1cef7d9d26.jsonl`). The files written by Claude agents cannot be regenerated by a script; their hashes identify the versions that were used.

**Example fields removed from included files.** Each removed field was replaced by a note giving the SHA-256 of the original file.

| File | Removed field | Examples | SHA-256 of the original file |
|---|---|---|---|
| `gc_conf_result.json` | `exemplos_M2_piorou` | 10 | `c6cb76cc180789f1281a9df1c52c0585d5c6c923686abba7c48dc75d96781a80` |
| `gc_local_judge_result.json` | `exemplos_de_discordancia` | 12 | `a45f10d53a2fc0718a290748eeb253d40fce78c42bcc117807f7adfbcbb749d8` |
| `gc_local_gate_result.json` | `exemplos_G_diferente_de_M0` | 12 | `b45a3c100d4a5a30aa562d5e4fa1d001dc87855b0982509f469138d99456f057` |
| `gc_local_bonus_result.json` | `exemplos_M2_piorou` | 15 | `ccf498786ee9f7a4ad906b0d7142365786a5713596fe2a23ba25b7ad2dcfe302` |

The per-turn outputs of rounds 1–2 (`v0_dev_turns.jsonl`, `r2_dev_turns.jsonl`) contain SGD dialogue text. They are also omitted and can be regenerated by the scripts.
