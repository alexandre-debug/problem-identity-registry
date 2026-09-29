"""Rodada 3: a memória compensa quando o normalizador tem pouco dado?

Frações 2%, 10% e 50% dos diálogos de treino (três sorteios aninhados cada) e 100%
(normalizador da rodada 2). Para cada normalizador: V0, V2 e V3 no desenvolvimento
de Events, com a mesma memória (MemoryOwnVec). Parâmetros fixos antes de rodar.
"""
import json, os, pickle, random, time, collections
import numpy as np
from gc_common import *
from gc_train import split_ids, examples, simulate, out_pool, copy_rule, fit_models, fit_stage1
from gc_memory import MemoryOwnVec
from run_round2 import condition, M, D
from run_v0 import score_turn

FRACS, SEEDS = [0.02, 0.10, 0.50], [0, 1, 2]
A, B = SERVICES
os.makedirs('curve', exist_ok=True)

train_dids = sorted(k for k, d in D.items() if len(d['services']) > 1 and set(d['services']) & set(SERVICES))
assert not (set(train_dids) & split_ids())
_r = random.Random(20260928); _r.shuffle(train_dids)
fit_dids = train_dids[len(train_dids) // 10:]            # mesma separação das rodadas 1 e 2
POOL = out_pool(D)
_EX = {}
def EX(k):
    if k not in _EX: _EX[k] = examples(k, D[k])
    return _EX[k]

def train(frac, seed):
    path = f'curve/normalizer_{int(frac * 100):03d}_s{seed}.pkl'
    if os.path.exists(path): return pickle.load(open(path, 'rb'))
    order = fit_dids[:]; random.Random(1000 + seed).shuffle(order)
    sub = order[:max(2, round(frac * len(order)))]        # aninhado: mesma ordem para todas as frações
    fit = [e for k in sub for e in EX(k)]
    out_fit = POOL[:max(50, round(4000 * frac))]
    COPY = copy_rule(fit)
    N1 = fit_stage1(fit, out_fit, COPY); tagger = (N1['tok_vec'], N1['tagger'])
    halves = [sub[0::2], sub[1::2]]; pred = {}
    for h in (0, 1):
        Nh = fit_stage1([e for k in halves[1 - h] for e in EX(k)], out_fit, COPY, tagger)
        for k in halves[h]: pred[k] = simulate(Nh, D[k])
    texts, intents, acts, cats, dfeats, calls = [], [], [], [], [], []
    for k in sub:
        for e, s in zip(EX(k), pred[k]):
            for tx, df in ((e['text'], e['dfeat']), (text_features(e['utt'], e['prev_acts'], s['pred_prev_intent']), s['dfeat'])):
                texts.append(tx); intents.append(e['intent']); acts.append(e['act']); cats.append(e['cat'])
                dfeats.append(df); calls.append(e['call'])
    N = fit_models(texts, intents, acts, cats, out_fit, dfeats, calls, fit, COPY, tagger)
    N['report'] = dict(frac=frac, seed=seed, dialogues=len(sub), turns=len(fit), out_examples=len(out_fit), copy_on_accept=COPY)
    pickle.dump(N, open(path, 'wb'))
    return N

def per_dialogue(rows, app):
    agg = collections.defaultdict(lambda: np.zeros(7))
    for r in rows:
        if r['app'] != app: continue
        s = score_turn(r, app); direct = r['pred']['path'] == 'sem_llm_final'
        ok_call = bool(s['call_gold'] and s['call_pred'] and s.get('method_ok') and s.get('args_ok'))
        agg[r['dialogue']] += [1, s['Q'], s['call_gold'], s['call_gold'] and s['Q'], direct, direct and ok_call, s['intent_ok']]
    return agg

NAMES = ['Q', 'Q_turnos_com_chamada', 'fracao_sem_llm_final', 'acerto_sem_llm_final', 'acuracia_intencao']
def stats(Z):
    s = Z.sum(0)
    return np.array([s[1] / s[0], s[3] / s[2], s[4] / s[0], s[5] / max(s[4], 1), s[6] / s[0]])

def boot_diff(rows_by_seed, x, y, app, n=2000):
    """Diferença média entre sorteios (y - x), reamostrando os mesmos diálogos em todos os sorteios."""
    ids = sorted(per_dialogue(rows_by_seed[0][x], app))
    arr = {}
    for c in (x, y):
        arr[c] = []
        for rs in rows_by_seed:
            pdg = per_dialogue(rs[c], app); arr[c].append(np.array([pdg[i] for i in ids]))
    point = np.mean([stats(Y) - stats(X) for X, Y in zip(arr[x], arr[y])], 0)
    rng = np.random.default_rng(0); diffs = []
    for _ in range(n):
        k = rng.integers(0, len(ids), len(ids))
        diffs.append(np.mean([stats(Y[k]) - stats(X[k]) for X, Y in zip(arr[x], arr[y])], 0))
    diffs = np.array(diffs)
    return {nm: {'diferenca': round(float(point[j]), 4),
                 'ic95': [round(float(np.percentile(diffs[:, j], 2.5)), 4), round(float(np.percentile(diffs[:, j], 97.5)), 4)]}
            for j, nm in enumerate(NAMES)}

if __name__ == '__main__':
    t0 = time.time()
    mem = MemoryOwnVec(D, M['memory_stream_order'])
    plan = [(f, s) for f in FRACS for s in SEEDS] + [(1.0, 0)]
    results = {}
    for frac, seed in plan:
        N = pickle.load(open('normalizer_r2.pkl', 'rb')) if frac == 1.0 else train(frac, seed)
        rows = {}
        summ = {}
        for name, (m, sc) in {'V0': (None, lambda a: None), 'V2': (mem, lambda a: {a}), 'V3': (mem, lambda a: {A, B})}.items():
            summ[name], rows[name] = condition(N, m, sc)
        results.setdefault(frac, []).append(dict(seed=seed, summary=summ, rows=rows, report=N.get('report', {})))
        print(f'{frac:.2f} s{seed} ok {time.time() - t0:.0f}s', flush=True)
    out = {'parametros_memoria': 'rodada 2, com TF-IDF próprio da memória', 'registros_memoria': int(len(mem.app)), 'fracoes': {}}
    for frac, runs in results.items():
        rs = [r['rows'] for r in runs]
        entry = {'sorteios': [dict(seed=r['seed'], treino=r['report'],
                                   metricas={c: {app: {k: v for k, v in r['summary'][c][app].items() if k in
                                                       ('acuracia_intencao', 'Q', 'caminho_sem_llm_final', 'caminho_sem_llm_final_chamada_certa', 'origem')}
                                                 for app in SERVICES} | {'recusa': r['summary'][c]['recusa'], 'sonda': r['summary'][c]['sonda_nao_suportada_em_A']}
                                             for c in ('V0', 'V2', 'V3')}) for r in runs],
                 'comparacoes': {f'{y} - {x}': {app: boot_diff(rs, x, y, app) for app in SERVICES}
                                 for x, y in (('V0', 'V2'), ('V0', 'V3'), ('V2', 'V3'))},
                 'niveis_V0': {app: {nm: round(float(np.mean([stats(np.array(list(per_dialogue(r['V0'], app).values())))[j] for r in rs])), 4)
                                     for j, nm in enumerate(NAMES)} for app in SERVICES}}
        out['fracoes'][str(frac)] = entry
    out['segundos'] = round(time.time() - t0, 1)
    json.dump(out, open('r3_curve_summary.json', 'w'), indent=1, ensure_ascii=False)
    print('fim', out['segundos'])
