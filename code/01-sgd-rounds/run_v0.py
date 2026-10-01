"""V0: normalizador local + mapeamentos + caminho sem LLM final, SEM memória de episódios.

Na inferência, cada turno recebe só: a frase do usuário, o turno anterior do sistema
(atos e valores que o próprio sistema produziu) e o estado previsto pela própria V0 nos
turnos anteriores. Nenhuma anotação do usuário é consultada. O gabarito entra apenas
na função evaluate(), depois da previsão.

Uso: python3 run_v0.py [dev]   (o teste de Events é exploratório e não é usado aqui)
"""
import json, pickle, time, statistics, sys, collections
from gc_common import *
from gc_features import token_feats, decision_features, requested_in

N = pickle.load(open('normalizer.pkl', 'rb'))
M = json.load(open('manifest.json'))
THR = {'identity': 0.2, 'applicability': 0.2}   # fixados antes da execução

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
    # uma ocorrência por conceito: a de maior confiança
    return {c: (utt[s:e], conf) for c, spans in vals.items() for _, s, e, conf in [max(spans, key=lambda x: x[3])]}

def infer_turn(app, ctx_svc, utt, prev_sys, state, prev_intent):
    """app: serviço que atende; ctx_svc: esquema dos atos do sistema anterior (igual a app, exceto na sonda)."""
    t0 = time.perf_counter()
    prev_acts = sys_acts(ctx_svc, prev_sys)
    X = N['vec'].transform([text_features(utt, prev_acts, prev_intent)])
    ip = N['intent_clf'].predict_proba(X)[0]; ic = N['intent_clf'].classes_
    intent = ic[ip.argmax()]; pmax = float(ip.max())
    act = N['act_clf'].predict(X)[0]
    toks = tokenize(utt); vals = {}
    if toks:
        TP = N['tagger'].predict_proba(N['tok_vec'].transform([token_feats(toks, i, requested_in(prev_acts)) for i in range(len(toks))]))
        vals = decode_spans(utt, toks, TP, N['tagger'].classes_)
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
    pcall = float(N['dec_clf'].predict_proba(N['dec_vec'].transform(
        [decision_features(app, eff_intent, new_state, new, eff_intent != prev_intent, prev_acts, act)]))[0][1])
    blocked = act == 'negate' and eff_intent == 'events.buy'
    decision = 'call' if pcall >= 0.5 and support == 'supported' and not blocked else 'wait'
    call = {'method': method, 'parameters': {c: new_state[c] for c in req_c + opt_c if c in new_state}} if decision == 'call' else None
    unc = {'identity': round(1 - pmax, 4),
           'applicability': round(1 - min((v[1] for c, v in vals.items() if c in new), default=1.0), 4),
           'decision': round(1 - max(pcall, 1 - pcall), 4)}
    direct = decision == 'call' and unc['identity'] < THR['identity'] and unc['applicability'] < THR['applicability'] \
        and all(c in new_state for c in req_c)
    rep = {'intent': eff_intent, 'slots': new_state,
           'action': {'decision': decision, 'confirmation_pending': any(a.startswith('CONFIRM') for a in prev_acts) and act != 'accept',
                      'execution_blocked': blocked},
           'support': support, 'uncertainty': unc, 'source': 'normalizer', 'path': 'sem_llm_final' if direct else 'encaminhar_llm',
           'call': call}
    return rep, new_state, eff_intent, (time.perf_counter() - t0) * 1000

# ---------------- avaliação (o gabarito só entra aqui) ----------------
def canon_map(d):
    cm = {}
    for t in d['turns']:
        for fr in t['frames']:
            for a in fr['actions']:
                for v, cv in zip(a.get('values', []), a.get('canonical_values', [])): cm[v.lower()] = cv.lower()
    return cm

def eqv(pred, golds, cm):
    p = pred.lower(); gs = {g.lower() for g in golds}
    return p in gs or cm.get(p, p) in {cm.get(g, g) for g in gs}

def run_dialogue(app, ctx_svc, did, D):
    d = D[did]; cm = canon_map(d); prev_sys, state, pint = None, {}, 'NONE'
    gstate_prev, rows = {}, []
    for i, t in enumerate(d['turns']):
        if t['speaker'] == 'SYSTEM': prev_sys = t['frames'][0]; continue
        rep, state, pint, ms = infer_turn(app, ctx_svc, t['utterance'], prev_sys, state, pint)
        g = t['frames'][0]; gs = {map_slot(ctx_svc, k): v for k, v in g['state']['slot_values'].items()}
        gint = int2c[ctx_svc].get(g['state']['active_intent'], 'NONE')
        nxt = d['turns'][i + 1]['frames'][0] if i + 1 < len(d['turns']) else {}
        gcall = nxt.get('service_call')
        gnew = {c: v for c, v in gs.items() if gstate_prev.get(c) != v}
        pnew = {c: rep['slots'][c] for c in rep['slots'] if c not in gstate_prev or True}
        rows.append(dict(dialogue=did, app=app, turn=i, utterance=t['utterance'], prev_system_acts=sys_acts(ctx_svc, d['turns'][i - 1]['frames'][0] if i else None),
                         pred=rep, ms=round(ms, 3), gold={'intent': gint, 'state': gs, 'new': gnew, 'call': gcall},
                         _cm=cm))
        gstate_prev = gs
    return rows

def score_turn(r, app):
    p, g, cm = r['pred'], r['gold'], r['_cm']
    s = {}
    s['intent_ok'] = p['intent'] == g['intent']
    ps = p['slots']; gs = g['state']
    s['state_ok'] = set(ps) == set(gs) and all(eqv(ps[c], gs[c], cm) for c in gs)
    s['slot_tp'] = sum(1 for c in gs if c in ps and eqv(ps[c], gs[c], cm)); s['slot_pred'] = len(ps); s['slot_gold'] = len(gs)
    gc = g['call']; pc = p['call']
    s['call_gold'] = gc is not None; s['call_pred'] = pc is not None
    if gc and pc:
        gp = {map_slot(app, k): v for k, v in gc['parameters'].items()}
        s['method_ok'] = pc['method'] == gc['method']
        s['args_ok'] = set(pc['parameters']) == set(gp) and all(eqv(pc['parameters'][c], [gp[c]], cm) for c in gp)
    s['Q'] = (not gc and not pc) or bool(gc and pc and s['method_ok'] and s['args_ok'])
    return s

def summarize(rows, app):
    S = [score_turn(r, app) for r in rows]; n = len(S)
    tp = sum(s['slot_tp'] for s in S); pp = sum(s['slot_pred'] for s in S); gg = sum(s['slot_gold'] for s in S)
    both = [s for s in S if s['call_gold'] and s['call_pred']]
    direct = [(r, s) for r, s in zip(rows, S) if r['pred']['path'] == 'sem_llm_final']
    ms = [r['ms'] for r in rows]
    return {'turnos': n, 'acuracia_intencao': sum(s['intent_ok'] for s in S) / n,
            'estado_completo_correto': sum(s['state_ok'] for s in S) / n,
            'parametros_precisao': tp / pp if pp else None, 'parametros_cobertura': tp / gg if gg else None,
            'chamadas_anotadas': sum(s['call_gold'] for s in S), 'chamadas_previstas': sum(s['call_pred'] for s in S),
            'chamadas_indevidas': sum(s['call_pred'] and not s['call_gold'] for s in S),
            'chamadas_omitidas': sum(s['call_gold'] and not s['call_pred'] for s in S),
            'metodo_correto_quando_ambos_chamam': sum(s['method_ok'] for s in both) / len(both) if both else None,
            'argumentos_corretos_quando_ambos_chamam': sum(s['args_ok'] for s in both) / len(both) if both else None,
            'Q': sum(s['Q'] for s in S) / n,
            'caminho_sem_llm_final': len(direct) / n,
            'caminho_sem_llm_final_chamada_certa': (sum(1 for r, s in direct if s['call_gold'] and s['method_ok'] and s['args_ok']) / len(direct)) if direct else None,
            'ms_mediana': statistics.median(ms), 'ms_p95': sorted(ms)[int(0.95 * (n - 1))], 'ms_media': statistics.mean(ms)}

if __name__ == '__main__':
    D = load_all(); cpu0 = time.process_time(); out = {}; all_rows = []
    for app in SERVICES:
        rows = [r for did in M['splits'][app]['dev'] for r in run_dialogue(app, app, did, D)]
        out[app] = summarize(rows, app); all_rows += rows
    # recusa: pedidos de tarefa fora do catálogo, como início de conversa (sem contexto)
    ooc = []
    for did in M['out_of_catalog']['dev']['dialogues']:
        for t in D[did]['turns']:
            if t['speaker'] == 'USER' and any(a['act'] == 'INFORM_INTENT' for a in t['frames'][0]['actions']):
                rep, *_ = infer_turn('Events_1', 'Events_1', t['utterance'], None, {}, 'NONE'); ooc.append(rep['support'])
    known = [r for r in all_rows]
    out['recusa'] = {'pedidos_fora_do_catalogo': len(ooc), 'recusa_correta': ooc.count('out_of_catalog') / len(ooc),
                     'recusa_indevida_em_events': sum(r['pred']['support'] == 'out_of_catalog' for r in known) / len(known)}
    # sonda: diálogos de B com GetEventDates atendidos pela aplicação A
    probe = []
    for did in M['splits']['Events_2']['dev']:
        if any(t['speaker'] == 'USER' and t['frames'][0]['state']['active_intent'] == 'GetEventDates' for t in D[did]['turns']):
            probe += [r for r in run_dialogue('Events_1', 'Events_2', did, D) if r['gold']['intent'] == 'events.get_dates']
    out['sonda_nao_suportada_em_A'] = {'turnos': len(probe),
                                       'sinalizada_como_nao_suportada': sum(r['pred']['support'] == 'known_unsupported' for r in probe) / max(len(probe), 1)}
    out['cpu_segundos'] = round(time.process_time() - cpu0, 2)
    out['limiares'] = THR
    with open('v0_dev_turns.jsonl', 'w') as f:
        for r in all_rows:
            r = dict(r); r.pop('_cm'); r['score'] = score_turn({**r, '_cm': canon_map(D[r['dialogue']])}, r['app'])
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    json.dump(out, open('v0_dev_summary.json', 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1, ensure_ascii=False))
