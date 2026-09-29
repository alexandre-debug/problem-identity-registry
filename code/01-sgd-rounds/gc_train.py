"""Funções de treino compartilhadas pela rodada 2 do normalizador."""
import json, random, re, collections
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression, SGDClassifier
from gc_common import *
from gc_features import token_feats, decision_features, requested_in
from gc_v0 import infer_turn

def split_ids():
    ids = set()
    for mf in ('manifest.json', 'manifest_flights.json'):
        m = json.load(open(mf))
        for s in m['splits'].values():
            for v in s.values(): ids |= set(v)
        for v in m['out_of_catalog'].values(): ids |= set(v['dialogues'])
    return ids

def examples(did, d):
    """Exemplos supervisionados com contexto anotado, na mesma ordem que simulate()."""
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
            out.append(dict(did=did, svc=svc, utt=t['utterance'], prev_acts=prev_acts,
                            text=text_features(t['utterance'], prev_acts, prev_intent),
                            intent=intent, act=act, cat=cat, toks=toks, labels=labels, req=requested_in(prev_acts),
                            call=int(bool(nfr and 'service_call' in nfr)),
                            dfeat=decision_features(svc, intent, state, new, intent != prev_intent, prev_acts, act),
                            offered=offered_values(svc, prev_sys), state=state, prev_state=dict(prev_state)))
            prev_state, prev_intent = state, intent
    return out

def simulate(N, d):
    """Roda o normalizador como na inferência (contexto previsto) e devolve, por turno, a intenção anterior prevista e os atributos de decisão previstos."""
    out = []
    for svc in [s for s in d['services'] if s in SERVICES]:
        prev_acts, prev_sys, state, pint = ['START'], None, {}, 'NONE'
        for t in d['turns']:
            fr = next((f for f in t['frames'] if f['service'] == svc), None)
            if t['speaker'] == 'SYSTEM':
                prev_acts = sys_acts(svc, fr) if fr else ['OTHER_SERVICE']; prev_sys = fr; continue
            if fr is None: continue
            rep, state, new_pint, _, dfeat = infer_turn(N, svc, svc, t['utterance'], prev_sys, state, pint, prev_acts=prev_acts)
            out.append(dict(pred_prev_intent=pint, pred_intent=new_pint, dfeat=dfeat)); pint = new_pint
    return out

def out_pool(D, seed=20260928):
    pool = []
    for k, d in D.items():
        if set(d['services']) & (RESERVED | set(SERVICES)): continue
        for t in d['turns']:
            if t['speaker'] == 'USER' and any(a['act'] == 'INFORM_INTENT' for fr in t['frames'] for a in fr['actions']):
                pool.append(text_features(t['utterance'], ['START'], 'NONE'))
    random.Random(seed).shuffle(pool)
    return pool

def copy_rule(fit):
    cp, tt = collections.Counter(), collections.Counter()
    for e in fit:
        if e['act'] != 'accept': continue
        for c, v in e['offered'].items():
            if not re.search(r'__pa_OFFER_' + c.replace('.', '_') + r'\b', e['text']): continue
            tt[c] += 1; cp[c] += e['state'].get(c) == v and e['prev_state'].get(c) != v
    return sorted(c for c in tt if cp[c] / tt[c] > 0.5)

def fit_models(texts, intents, acts, cats, out_texts, dfeats, calls, tok_examples, copy_on_accept, tagger=None):
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, token_pattern=r'(?u)\b\w+\b')
    Xf = vec.fit_transform(texts + out_texts); Xe = Xf[:len(texts)]
    N = dict(vec=vec, copy_on_accept=copy_on_accept)
    N['intent_clf'] = LogisticRegression(max_iter=3000, C=4).fit(Xf, intents + ['OUT'] * len(out_texts))
    N['act_clf'] = LogisticRegression(max_iter=3000, C=4).fit(Xe, acts)
    N['cat_clf'] = {c: LogisticRegression(max_iter=3000, C=4).fit(Xe, [x[c] for x in cats]) for c in CATEGORICAL}
    if tagger is None:
        tok_vec = DictVectorizer()
        TX = tok_vec.fit_transform([token_feats(e['toks'], i, e['req']) for e in tok_examples for i in range(len(e['toks']))])
        tagger = (tok_vec, SGDClassifier(loss='log_loss', alpha=2e-6, max_iter=30, tol=None, random_state=0, n_jobs=2).fit(
            TX, [l for e in tok_examples for l in e['labels']]))
    N['tok_vec'], N['tagger'] = tagger
    N['dec_vec'] = DictVectorizer()
    N['dec_clf'] = LogisticRegression(max_iter=3000, C=1).fit(N['dec_vec'].fit_transform(dfeats), calls)
    return N

def fit_stage1(fit, out_texts, copy_on_accept, tagger=None):
    return fit_models([e['text'] for e in fit], [e['intent'] for e in fit], [e['act'] for e in fit], [e['cat'] for e in fit],
                      out_texts, [e['dfeat'] for e in fit], [e['call'] for e in fit], fit, copy_on_accept, tagger)
