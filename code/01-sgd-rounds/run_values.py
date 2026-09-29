"""Rodada 4: a memória de valores validados compensa a falta de dados?

Mesmos normalizadores da rodada 3 (2%, 10%, 50% com três sorteios; 100% da rodada 2).
Condições: V0, V3, V2+valores, V3+valores, V3+valores+outros. Parâmetros fixos antes de rodar.
"""
import json, pickle, time, collections
import numpy as np
from gc_common import *
from gc_v0 import infer_turn
from gc_memory import MemoryOwnVec
from gc_values import ValueMemory, other_services, MIN_VALIDATIONS, MIN_CHARS, VAL_CONF
from run_v0 import canon_map, score_turn, summarize
from run_curve import train, boot_diff, per_dialogue, stats, NAMES, FRACS, SEEDS, M, D

A, B = SERVICES

def run_dialogue(N, app, ctx_svc, did, memory, scope, values):
    d = D[did]; cm = canon_map(d); prev_sys, state, pint, rows = None, {}, 'NONE', []
    for i, t in enumerate(d['turns']):
        if t['speaker'] == 'SYSTEM': prev_sys = t['frames'][0]; continue
        rep, state, pint, ms, _ = infer_turn(N, app, ctx_svc, t['utterance'], prev_sys, state, pint,
                                             memory=memory, scope=scope, values=values)
        g = t['frames'][0]; nxt = d['turns'][i + 1]['frames'][0] if i + 1 < len(d['turns']) else {}
        rows.append(dict(dialogue=did, app=app, turn=i, utterance=t['utterance'], pred=rep, ms=round(ms, 3),
                         gold={'intent': int2c[ctx_svc].get(g['state']['active_intent'], 'NONE'),
                               'state': {map_slot(ctx_svc, k): v for k, v in g['state']['slot_values'].items()},
                               'call': nxt.get('service_call')}, _cm=cm))
    return rows

def condition(N, memory, scope_of, values_of):
    res, rows_all = {}, []
    for app in SERVICES:
        rows = [r for did in M['splits'][app]['dev'] for r in run_dialogue(N, app, app, did, memory, scope_of(app), values_of(app))]
        res[app] = summarize(rows, app); rows_all += rows
    ooc = []
    for did in M['out_of_catalog']['dev']['dialogues']:
        for t in D[did]['turns']:
            if t['speaker'] == 'USER' and any(a['act'] == 'INFORM_INTENT' for a in t['frames'][0]['actions']):
                ooc.append(infer_turn(N, A, A, t['utterance'], None, {}, 'NONE', memory=memory, scope=scope_of(A), values=values_of(A))[0]['support'])
    res['recusa'] = {'recusa_correta': ooc.count('out_of_catalog') / len(ooc),
                     'recusa_indevida_em_events': sum(r['pred']['support'] == 'out_of_catalog' for r in rows_all) / len(rows_all)}
    return res, rows_all

def call_breakdown(rows, app):
    c = collections.Counter(); g = [r for r in rows if r['app'] == app and r['gold']['call']]
    for r in g:
        s = score_turn(r, app)
        c['omitida' if not s['call_pred'] else ('metodo_errado' if not s['method_ok'] else ('argumentos_errados' if not s['args_ok'] else 'certa'))] += 1
    return {k: round(v / len(g), 4) for k, v in c.items()}

if __name__ == '__main__':
    t0 = time.time()
    VM = ValueMemory()
    for item in M['memory_stream_order']:
        svc, did = item.split(':', 1); VM.add_dialogue(svc, svc, D[did])
    others = set(other_services()); n_other = 0
    for k, d in D.items():
        if len(d['services']) == 1 and d['services'][0] in others:
            VM.add_dialogue('outros', d['services'][0], d); n_other += 1
    IDX = {'own_A': VM.index([A]), 'own_B': VM.index([B]), 'AB': VM.index([A, B]), 'ABO': VM.index([A, B, 'outros'])}
    mem = MemoryOwnVec(D, M['memory_stream_order'])
    conds = {
        'V0': (None, lambda a: None, lambda a: None),
        'V3': (mem, lambda a: {A, B}, lambda a: None),
        'V2+valores': (mem, lambda a: {a}, lambda a: IDX['own_A'] if a == A else IDX['own_B']),
        'V3+valores': (mem, lambda a: {A, B}, lambda a: IDX['AB']),
        'V3+valores+outros': (mem, lambda a: {A, B}, lambda a: IDX['ABO']),
    }
    runs = collections.defaultdict(list)
    for frac, seed in [(f, s) for f in FRACS for s in SEEDS] + [(1.0, 0)]:
        N = pickle.load(open('normalizer_r2.pkl', 'rb')) if frac == 1.0 else train(frac, seed)
        summ, rows = {}, {}
        for name, (m, sc, vo) in conds.items():
            summ[name], rows[name] = condition(N, m, sc, vo)
        runs[frac].append(dict(seed=seed, summ=summ, rows=rows))
        print(f'{frac:.2f} s{seed} ok {time.time() - t0:.0f}s', flush=True)

    out = {'memoria_valores': {'dialogos_outros_dominios': n_other, 'servicos_outros': len(others),
                               'valores_indexados': {k: len(v) for k, v in IDX.items()},
                               'parametros': dict(MIN_VALIDATIONS=MIN_VALIDATIONS, MIN_CHARS=MIN_CHARS, VAL_CONF=VAL_CONF)},
           'fracoes': {}}
    for frac, rs in runs.items():
        R = [r['rows'] for r in rs]
        out['fracoes'][str(frac)] = {
            'niveis': {c: {app: {nm: round(float(np.mean([stats(np.array(list(per_dialogue(x[c], app).values())))[j] for x in R])), 4)
                                 for j, nm in enumerate(NAMES)} for app in SERVICES} for c in conds},
            'comparacoes': {f'{y} - {x}': {app: boot_diff(R, x, y, app) for app in SERVICES}
                            for x, y in (('V0', 'V3+valores+outros'), ('V0', 'V3+valores'), ('V0', 'V3'),
                                         ('V2+valores', 'V3+valores'), ('V3+valores', 'V3+valores+outros'), ('V3', 'V3+valores'))},
            'chamadas_sorteio0': {c: {app: call_breakdown(R[0][c], app) for app in SERVICES} for c in ('V0', 'V3+valores+outros')},
            'recusa': {c: [r['summ'][c]['recusa'] for r in rs] for c in conds}}
    # critério registrado: fração da lacuna recuperada com 2%
    crit = {}
    for app in SERVICES:
        lo = out['fracoes']['0.02']['niveis']['V0'][app]['Q_turnos_com_chamada']
        hi = out['fracoes']['1.0']['niveis']['V0'][app]['Q_turnos_com_chamada']
        d = out['fracoes']['0.02']['comparacoes']['V3+valores+outros - V0'][app]['Q_turnos_com_chamada']
        crit[app] = {'lacuna': round(hi - lo, 4), 'ganho': d['diferenca'], 'ic95': d['ic95'],
                     'fracao_recuperada': round(d['diferenca'] / (hi - lo), 4),
                     'atinge': d['diferenca'] >= 0.25 * (hi - lo) and d['ic95'][0] > 0}
    out['criterio'] = crit | {'atingido': any(v['atinge'] for v in crit.values())}
    out['segundos'] = round(time.time() - t0, 1)
    json.dump(out, open('r4_values_summary.json', 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(out['criterio'], indent=1, ensure_ascii=False))
