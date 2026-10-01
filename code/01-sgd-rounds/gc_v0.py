"""Motor de inferência da rodada 2: V0 ajustada, com gancho para a memória de V2/V3.

A inferência recebe só a frase, o turno anterior do sistema (atos e valores que o
próprio sistema produziu) e o estado previsto nos turnos anteriores.
"""
import time
import numpy as np
from gc_common import *
from gc_features import token_feats, decision_features, requested_in

THR = {'identity': 0.2, 'applicability': 0.2}
MARGIN = 0.3   # abaixo disso, a segunda intenção vira hipótese

def decode_spans(utt, toks, probs, classes):
    vals, cur = {}, None
    for (w, s0, e0), p in zip(toks, probs):
        k = p.argmax(); lab = classes[k]
        if lab == 'O': cur = None; continue
        tag, c = lab.split('-', 1)
        if tag == 'B' or cur is None or cur[0] != c:
            cur = [c, s0, e0, p[k]]; vals.setdefault(c, []).append(cur)
        else:
            cur[2] = e0; cur[3] = min(cur[3], p[k])
    return {c: (utt[s:e], conf) for c, spans in vals.items() for _, s, e, conf in [max(spans, key=lambda x: x[3])]}

def infer_turn(N, app, ctx_svc, utt, prev_sys, state, prev_intent, prev_acts=None, memory=None, scope=None, values=None):
    t0 = time.perf_counter()
    if prev_acts is None: prev_acts = sys_acts(ctx_svc, prev_sys)
    X = N['vec'].transform([text := text_features(utt, prev_acts, prev_intent)])
    ic = list(N['intent_clf'].classes_); ip = N['intent_clf'].predict_proba(X)[0]
    ac = list(N['act_clf'].classes_); ap = N['act_clf'].predict_proba(X)[0]
    source, w, mem = 'normalizer', 0.0, None
    if memory is not None:
        mem = memory.consult(scope, utt, prev_acts, X, text)
        if mem:
            source, w = mem['source'], mem['weight']
            ip = (1 - w) * ip + w * np.array([mem['intent'].get(c, 0.0) for c in ic])
            ap = (1 - w) * ap + w * np.array([mem['act'].get(c, 0.0) for c in ac])
    order = np.argsort(-ip); top, second = ic[order[0]], ic[order[1]]
    hypotheses = [second] if ip[order[0]] - ip[order[1]] < MARGIN and second != 'OUT' else []
    intent = top
    if hypotheses and top not in ('NONE', 'OUT') and not c2int[app].get(top) and c2int[app].get(second):
        intent, hypotheses = second, [top]
    p_int = float(ip[ic.index(intent)])
    act = ac[int(ap.argmax())]
    toks = tokenize(utt); vals = {}
    if toks:
        TP = N['tagger'].predict_proba(N['tok_vec'].transform([token_feats(toks, i, requested_in(prev_acts)) for i in range(len(toks))]))
        vals = decode_spans(utt, toks, TP, N['tagger'].classes_)
    if values is not None and intent not in ('OUT', 'NONE'):
        # rodada 4: valores validados preenchem conceitos do método que o extrator não achou neste turno
        from gc_values import match, VAL_CONF
        _, req_v, opt_v = intent_slots(app, intent)
        for c, v in match(values, utt, toks, set(req_v + opt_v)).items():
            if c not in vals and state.get(c, '').lower() != v.lower(): vals[c] = (v, VAL_CONF)
    for c in CATEGORICAL:
        cp = N['cat_clf'][c].predict_proba(X)[0]; cv = N['cat_clf'][c].classes_[cp.argmax()]
        if cv != 'NONE': vals[c] = (cv, float(cp.max()))
    if act == 'accept':
        off = offered_values(ctx_svc, prev_sys)
        for c in N['copy_on_accept']:
            if c in off and c not in vals: vals[c] = (off[c], 1.0)
    if intent == 'OUT':
        support, new_state, eff_intent = 'out_of_catalog', dict(state), prev_intent
    else:
        eff_intent = intent
        new_state = dict(state); new_state.update({c: v for c, (v, _) in vals.items()})
        support = 'no_intent' if intent == 'NONE' else ('supported' if c2int[app].get(intent) else 'known_unsupported')
    new = [c for c in new_state if state.get(c) != new_state[c]]
    method, req_c, opt_c = intent_slots(app, eff_intent)
    dfeat = decision_features(app, eff_intent, new_state, new, eff_intent != prev_intent, prev_acts, act)
    pcall = float(N['dec_clf'].predict_proba(N['dec_vec'].transform([dfeat]))[0][1])
    if mem and 'call' in mem: pcall = (1 - w) * pcall + w * mem['call']
    blocked = act == 'negate' and eff_intent == 'events.buy'
    decision = 'call' if pcall >= 0.5 and support == 'supported' and not blocked else 'wait'
    call = {'method': method, 'parameters': {c: new_state[c] for c in req_c + opt_c if c in new_state}} if decision == 'call' else None
    unc = {'identity': round(1 - p_int, 4),
           'applicability': round(1 - min((v[1] for c, v in vals.items() if c in new), default=1.0), 4),
           'decision': round(1 - max(pcall, 1 - pcall), 4)}
    direct = decision == 'call' and not hypotheses and unc['identity'] < THR['identity'] \
        and unc['applicability'] < THR['applicability'] and all(c in new_state for c in req_c)
    rep = {'intent': eff_intent, 'hypotheses': hypotheses, 'slots': new_state,
           'action': {'decision': decision,
                      'confirmation_pending': any(a.startswith('CONFIRM') for a in prev_acts) and act != 'accept',
                      'execution_blocked': blocked},
           'support': support, 'uncertainty': unc, 'source': source,
           'path': 'sem_llm_final' if direct else 'encaminhar_llm', 'call': call}
    return rep, new_state, eff_intent, (time.perf_counter() - t0) * 1000, dfeat
