"""Rodada 2 no desenvolvimento de Events: V0 ajustada, V2 (memória local) e V3 (compartilhada).

Condições:
  V0_r1aj  normalizador da rodada 1 com os ajustes de hipótese e desempate (ablação)
  V0       normalizador da rodada 2 (dois estágios) com os ajustes
  V2       V0 + memória só da própria aplicação
  V3       V0 + memória de A e de B
Tudo fixo antes de rodar (ver protocolo). O gabarito só entra na avaliação.
"""
import json, pickle, random, time, collections
import numpy as np
from gc_common import *
from gc_v0 import infer_turn, THR, MARGIN
from gc_memory import Memory, HASH_MIN, HASH_AGREE, HASH_W, K, SIM_MIN, RET_W
from run_v0 import canon_map, score_turn, summarize

M = json.load(open('manifest.json'))
D = load_all()
A, B = SERVICES

def run_dialogue(N, app, ctx_svc, did, memory=None, scope=None):
    d = D[did]; cm = canon_map(d); prev_sys, state, pint, rows = None, {}, 'NONE', []
    for i, t in enumerate(d['turns']):
        if t['speaker'] == 'SYSTEM': prev_sys = t['frames'][0]; continue
        rep, state, pint, ms, _ = infer_turn(N, app, ctx_svc, t['utterance'], prev_sys, state, pint, memory=memory, scope=scope)
        g = t['frames'][0]
        nxt = d['turns'][i + 1]['frames'][0] if i + 1 < len(d['turns']) else {}
        rows.append(dict(dialogue=did, app=app, turn=i, utterance=t['utterance'], pred=rep, ms=round(ms, 3),
                         gold={'intent': int2c[ctx_svc].get(g['state']['active_intent'], 'NONE'),
                               'state': {map_slot(ctx_svc, k): v for k, v in g['state']['slot_values'].items()},
                               'call': nxt.get('service_call')}, _cm=cm))
    return rows

def condition(N, memory, scope_of):
    res, rows_all = {}, []
    for app in SERVICES:
        rows = [r for did in M['splits'][app]['dev'] for r in run_dialogue(N, app, app, did, memory, scope_of(app))]
        s = summarize(rows, app)
        s['origem'] = dict(collections.Counter(r['pred']['source'] for r in rows))
        s['com_hipotese'] = sum(bool(r['pred']['hypotheses']) for r in rows) / len(rows)
        res[app] = s; rows_all += rows
    ooc = []
    for did in M['out_of_catalog']['dev']['dialogues']:
        for t in D[did]['turns']:
            if t['speaker'] == 'USER' and any(a['act'] == 'INFORM_INTENT' for a in t['frames'][0]['actions']):
                ooc.append(infer_turn(N, A, A, t['utterance'], None, {}, 'NONE', memory=memory, scope=scope_of(A))[0]['support'])
    res['recusa'] = {'pedidos': len(ooc), 'recusa_correta': ooc.count('out_of_catalog') / len(ooc),
                     'recusa_indevida_em_events': sum(r['pred']['support'] == 'out_of_catalog' for r in rows_all) / len(rows_all)}
    probe = []
    for did in M['splits'][B]['dev']:
        if any(t['speaker'] == 'USER' and t['frames'][0]['state']['active_intent'] == 'GetEventDates' for t in D[did]['turns']):
            probe += [r for r in run_dialogue(N, A, B, did, memory, scope_of(A)) if r['gold']['intent'] == 'events.get_dates']
    res['sonda_nao_suportada_em_A'] = {'turnos': len(probe),
                                       'sinalizada': sum(r['pred']['support'] == 'known_unsupported' for r in probe) / len(probe)}
    return res, rows_all

def per_dialogue(rows):
    agg = collections.defaultdict(lambda: np.zeros(6))
    for r in rows:
        s = score_turn(r, r['app']); direct = r['pred']['path'] == 'sem_llm_final'
        ok_call = bool(s['call_gold'] and s['call_pred'] and s.get('method_ok') and s.get('args_ok'))
        agg[r['dialogue']] += [1, s['Q'], s['call_gold'], s['call_gold'] and s['Q'], direct, direct and ok_call]
    return agg

def bootstrap(rows_x, rows_y, app, n=2000, seed=0):
    """Diferença (y - x) de razões de somas, reamostrando diálogos pareados."""
    ax = per_dialogue([r for r in rows_x if r['app'] == app]); ay = per_dialogue([r for r in rows_y if r['app'] == app])
    ids = sorted(ax); X = np.array([ax[i] for i in ids]); Y = np.array([ay[i] for i in ids])
    def stats(Z):
        s = Z.sum(0); return np.array([s[1] / s[0], s[3] / s[2], s[4] / s[0], s[5] / max(s[4], 1)])
    rng = np.random.default_rng(seed); diffs = []
    for _ in range(n):
        k = rng.integers(0, len(ids), len(ids)); diffs.append(stats(Y[k]) - stats(X[k]))
    diffs = np.array(diffs); point = stats(Y) - stats(X)
    names = ['Q', 'Q_turnos_com_chamada', 'fracao_sem_llm_final', 'acerto_sem_llm_final']
    return {nm: {'diferenca': round(float(p), 4), 'ic95': [round(float(np.percentile(diffs[:, j], 2.5)), 4),
                                                           round(float(np.percentile(diffs[:, j], 97.5)), 4)]}
            for j, (nm, p) in enumerate(zip(names, point))}

if __name__ == '__main__':
    N1 = pickle.load(open('normalizer.pkl', 'rb')); N2 = pickle.load(open('normalizer_r2.pkl', 'rb'))
    t0 = time.time()
    mem = Memory(N2, D, M['memory_stream_order'])
    build_s = round(time.time() - t0, 2)
    conds = {'V0_r1aj': (N1, None, lambda a: None), 'V0': (N2, None, lambda a: None),
             'V2': (N2, mem, lambda a: {a}), 'V3': (N2, mem, lambda a: {A, B})}
    out, rows = {}, {}
    for name, (N, m, sc) in conds.items():
        out[name], rows[name] = condition(N, m, sc); print(name, 'ok', flush=True)
    comp = {f'{y} - {x}': {app: bootstrap(rows[x], rows[y], app) for app in SERVICES}
            for x, y in (('V0', 'V2'), ('V2', 'V3'), ('V0', 'V3'), ('V0_r1aj', 'V0'))}
    params = dict(MARGIN=MARGIN, THR=THR, HASH_MIN=HASH_MIN, HASH_AGREE=HASH_AGREE, HASH_W=HASH_W, K=K, SIM_MIN=SIM_MIN, RET_W=RET_W,
                  memoria_registros=int(len(mem.app)), memoria_construcao_s=build_s)
    json.dump(dict(parametros=params, condicoes=out, comparacoes=comp), open('r2_dev_summary.json', 'w'), indent=1, ensure_ascii=False)
    with open('r2_dev_turns.jsonl', 'w') as f:
        for name, rs in rows.items():
            for r in rs:
                r = dict(r); r['score'] = score_turn(r, r['app']); r.pop('_cm'); r['condicao'] = name
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(json.dumps(dict(parametros=params, comparacoes=comp), indent=1, ensure_ascii=False))
