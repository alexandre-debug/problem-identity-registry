"""Rodada 2 do normalizador: dois estágios com validação cruzada em duas partes.

Estágio 1 treina com o contexto anotado. Cada metade dos diálogos de treino é então
processada pelo modelo treinado na outra metade, como na inferência, para obter a
intenção anterior e os atributos de decisão PREVISTOS. O estágio 2 aprende com os
exemplos de contexto anotado e de contexto previsto juntos.
"""
import json, pickle, random, time
from gc_common import *
from gc_train import split_ids, examples, simulate, out_pool, copy_rule, fit_models, fit_stage1
from gc_v0 import infer_turn

t0 = time.time()
D = load_all()
train_dids = sorted(k for k, d in D.items() if len(d['services']) > 1 and set(d['services']) & set(SERVICES))
assert not (set(train_dids) & split_ids()), 'diálogo de treino dentro de uma divisão'
rng = random.Random(20260928); rng.shuffle(train_dids)
nval = len(train_dids) // 10
val_dids, fit_dids = train_dids[:nval], train_dids[nval:]   # mesma separação da rodada 1
EX = {k: examples(k, D[k]) for k in train_dids}
fit = [e for k in fit_dids for e in EX[k]]
pool = out_pool(D); out_fit, out_val = pool[:4000], pool[4000:4500]
COPY = copy_rule(fit)

# estágio 1 completo (também serve de comparação na validação) e tagger reaproveitado
N1 = fit_stage1(fit, out_fit, COPY)
tagger = (N1['tok_vec'], N1['tagger'])

# validação cruzada em duas partes para obter contexto previsto nos próprios dados de treino
halves = [fit_dids[0::2], fit_dids[1::2]]
pred = {}
for h in (0, 1):
    Nh = fit_stage1([e for k in halves[1 - h] for e in EX[k]], out_fit, COPY, tagger)
    for k in halves[h]:
        sim = simulate(Nh, D[k]); assert len(sim) == len(EX[k]); pred[k] = sim

texts, intents, acts, cats, dfeats, calls = [], [], [], [], [], []
for k in fit_dids:
    for e, s in zip(EX[k], pred[k]):
        for tx, df in ((e['text'], e['dfeat']), (text_features(e['utt'], e['prev_acts'], s['pred_prev_intent']), s['dfeat'])):
            texts.append(tx); intents.append(e['intent']); acts.append(e['act']); cats.append(e['cat'])
            dfeats.append(df); calls.append(e['call'])
N2 = fit_models(texts, intents, acts, cats, out_fit, dfeats, calls, fit, COPY, tagger)

def realistic(N, dids):
    """Acurácia de intenção e decisão com contexto previsto, nos diálogos de validação interna."""
    ok = okd = n = 0
    for k in dids:
        for e, s in zip(EX[k], simulate(N, D[k])):
            n += 1; ok += s['pred_intent'] == e['intent']
            okd += (N['dec_clf'].predict(N['dec_vec'].transform([s['dfeat']]))[0]) == e['call']
    return round(ok / n, 4), round(okd / n, 4)

r1, r2 = realistic(N1, val_dids), realistic(N2, val_dids)
report = dict(train_dialogues=len(fit_dids), val_dialogues=len(val_dids), stage2_examples=len(texts), copy_on_accept=COPY,
              val_realista_estagio1={'intencao': r1[0], 'decisao': r1[1]},
              val_realista_estagio2={'intencao': r2[0], 'decisao': r2[1]},
              train_seconds=round(time.time() - t0, 1))
N2['report'] = report
pickle.dump(N2, open('normalizer_r2.pkl', 'wb'))
json.dump(report, open('normalizer_r2_report.json', 'w'), indent=1, ensure_ascii=False)
print(json.dumps(report, indent=1, ensure_ascii=False))
