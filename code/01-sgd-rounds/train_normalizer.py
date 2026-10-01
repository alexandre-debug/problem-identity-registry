"""Treina o normalizador local da V0 (scikit-learn, pesos fixos depois do treino).

Dados de treino: quadros de Events_1 e Events_2 em diálogos com MAIS de um serviço.
As divisões do experimento só usam diálogos de um serviço, então esses diálogos
ficam fora de desenvolvimento, memória e teste (verificado abaixo). Exemplos da
classe OUT vêm de outros serviços, excluindo os reservados (Flights, Events_3 e os
conjuntos fora do catálogo). 10% dos diálogos de treino ficam para validação interna.
"""
import json, pickle, random, re, time, collections
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression, SGDClassifier
from gc_common import *

t0 = time.time()
D = load_all()
split_ids = set()
for mf in ('manifest.json', 'manifest_flights.json'):
    m = json.load(open(mf))
    for s in m['splits'].values():
        for ids in s.values(): split_ids |= set(ids)
    for v in m['out_of_catalog'].values(): split_ids |= set(v['dialogues'])

from gc_features import shape, token_feats, decision_features, requested_in

def examples(did, d):
    """Exemplos supervisionados de um diálogo, com contexto e estado anterior anotados (teacher forcing)."""
    out = []
    for svc in [s for s in d['services'] if s in SERVICES]:
        prev_acts, prev_state, prev_intent, prev_sys = ['START'], {}, 'NONE', None
        for i, t in enumerate(d['turns']):
            fr = next((f for f in t['frames'] if f['service'] == svc), None)
            if t['speaker'] == 'SYSTEM':
                prev_acts = sys_acts(svc, fr) if fr else ['OTHER_SERVICE']; prev_sys = fr; continue
            if fr is None: continue
            st = fr['state']; intent = int2c[svc].get(st['active_intent'], 'NONE')
            state = {map_slot(svc, k): v[0] for k, v in st['slot_values'].items()}
            new = [c for c, v in state.items() if prev_state.get(c) != v]
            nxt = d['turns'][i + 1] if i + 1 < len(d['turns']) else None
            nfr = next((f for f in nxt['frames'] if f['service'] == svc), None) if nxt else None
            toks = tokenize(t['utterance']); labels = ['O'] * len(toks)
            for sl in fr['slots']:
                c = map_slot(svc, sl['slot'])
                if c not in SPAN_CONCEPTS: continue
                first = True
                for k, (w, s0, e0) in enumerate(toks):
                    if s0 >= sl['start'] and e0 <= sl['exclusive_end']:
                        labels[k] = ('B-' if first else 'I-') + c; first = False
            cat = {c: 'NONE' for c in CATEGORICAL}
            for a in fr['actions']:
                c = map_slot(svc, a['slot'])
                if a['act'] == 'INFORM' and c in CATEGORICAL and a['values']: cat[c] = a['values'][0]
            act = user_act_class(fr)
            out.append(dict(did=did, svc=svc, text=text_features(t['utterance'], prev_acts, prev_intent),
                            intent=intent, act=act, cat=cat, toks=toks, labels=labels, req=requested_in(prev_acts),
                            call=int(bool(nfr and 'service_call' in nfr)),
                            dfeat=decision_features(svc, intent, state, new, intent != prev_intent, prev_acts, act),
                            offered=offered_values(svc, prev_sys),
                            state=state, prev_state=dict(prev_state)))
            prev_state, prev_intent = state, intent
    return out

train_dids = sorted(k for k, d in D.items() if len(d['services']) > 1 and set(d['services']) & set(SERVICES))
assert not (set(train_dids) & split_ids), 'diálogo de treino dentro de uma divisão'
rng = random.Random(20260928); rng.shuffle(train_dids)
nval = len(train_dids) // 10
val_dids, fit_dids = set(train_dids[:nval]), train_dids[nval:]
EX = {k: examples(k, D[k]) for k in train_dids}
fit = [e for k in fit_dids for e in EX[k]]; val = [e for k in val_dids for e in EX[k]]

# classe OUT: pedidos de tarefa em outros domínios, sem contexto (início de conversa)
out_pool = []
for k, d in D.items():
    if set(d['services']) & (RESERVED | set(SERVICES) | {'Events_3'}): continue
    for t in d['turns']:
        if t['speaker'] == 'USER' and any(a['act'] == 'INFORM_INTENT' for fr in t['frames'] for a in fr['actions']):
            out_pool.append(text_features(t['utterance'], ['START'], 'NONE'))
rng.shuffle(out_pool); out_fit, out_val = out_pool[:4000], out_pool[4000:4500]

# quanto do estado novo vem de valores oferecidos pelo sistema e aceitos pelo usuário;
# conceitos OFERECIDOS que entram no estado em mais da metade das aceitações viram regra de cópia
acc = [e for e in fit if e['act'] == 'accept' and e['offered']]
copied = sum(sum(1 for c, v in e['offered'].items() if e['state'].get(c) == v and e['prev_state'].get(c) != v) for e in acc)
offered = sum(len(e['offered']) for e in acc)
cp, tt = collections.Counter(), collections.Counter()
for e in acc:
    for c, v in e['offered'].items():
        if not re.search(r'__pa_OFFER_' + c.replace('.', '_') + r'\b', e['text']): continue
        tt[c] += 1; cp[c] += e['state'].get(c) == v and e['prev_state'].get(c) != v
COPY_ON_ACCEPT = sorted(c for c in tt if cp[c] / tt[c] > 0.5)

vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, token_pattern=r'(?u)\b\w+\b')
Xf = vec.fit_transform([e['text'] for e in fit] + out_fit)
intent_clf = LogisticRegression(max_iter=3000, C=4).fit(Xf, [e['intent'] for e in fit] + ['OUT'] * len(out_fit))
Xe = Xf[:len(fit)]
act_clf = LogisticRegression(max_iter=3000, C=4).fit(Xe, [e['act'] for e in fit])
cat_clf = {c: LogisticRegression(max_iter=3000, C=4).fit(Xe, [e['cat'][c] for e in fit]) for c in CATEGORICAL}

tok_vec = DictVectorizer()
TX = tok_vec.fit_transform([token_feats(e['toks'], i, e['req']) for e in fit for i in range(len(e['toks']))])
tagger = SGDClassifier(loss='log_loss', alpha=2e-6, max_iter=30, tol=None, random_state=0, n_jobs=2).fit(
    TX, [l for e in fit for l in e['labels']])

dec_vec = DictVectorizer()
dec_clf = LogisticRegression(max_iter=3000, C=1).fit(dec_vec.fit_transform([e['dfeat'] for e in fit]), [e['call'] for e in fit])

# validação interna, em diálogos de treino separados (não é o desenvolvimento do experimento)
Xv = vec.transform([e['text'] for e in val]); Xo = vec.transform(out_val)
pi = intent_clf.predict(Xv); po = intent_clf.predict(Xo)
tl = tagger.predict(tok_vec.transform([token_feats(e['toks'], i, e['req']) for e in val for i in range(len(e['toks']))]))
gold_tl = [l for e in val for l in e['labels']]
ent = [(p, g) for p, g in zip(tl, gold_tl) if p != 'O' or g != 'O']
report = dict(
    train_dialogues=len(fit_dids), val_dialogues=len(val_dids), train_turns=len(fit), val_turns=len(val),
    out_train=len(out_fit), out_val=len(out_val),
    val_intent_acc=float((pi == [e['intent'] for e in val]).mean()),
    val_out_recall=float((po == 'OUT').mean()),
    val_false_out=float((pi == 'OUT').mean()),
    val_act_acc=float((act_clf.predict(Xv) == [e['act'] for e in val]).mean()),
    val_token_acc_on_entities=sum(p == g for p, g in ent) / len(ent),
    val_decision_acc=float((dec_clf.predict(dec_vec.transform([e['dfeat'] for e in val])) == [e['call'] for e in val]).mean()),
    offered_values_copied_on_accept=f'{copied}/{offered}', copy_on_accept=COPY_ON_ACCEPT,
    train_seconds=round(time.time() - t0, 1))
pickle.dump(dict(vec=vec, intent_clf=intent_clf, act_clf=act_clf, cat_clf=cat_clf, tok_vec=tok_vec, tagger=tagger,
                 dec_vec=dec_vec, dec_clf=dec_clf, copy_on_accept=COPY_ON_ACCEPT, report=report), open('normalizer.pkl', 'wb'))
json.dump(report, open('normalizer_report.json', 'w'), indent=1)
print(json.dumps(report, indent=1, ensure_ascii=False))
