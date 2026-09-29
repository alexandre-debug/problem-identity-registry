"""Rodada 5: memória compartilhada de problemas resolvidos em suporte técnico real (AskUbuntu).

Fluxo por ordem de ID; duas centrais sorteadas; V2 = memória da própria central, V3 = das duas.
Gabarito: duplicatas marcadas pelos usuários (limite inferior). Parâmetros fixos antes de rodar.
"""
import gzip, json, random, subprocess, time, collections
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = __import__('os').environ.get('ASKUBUNTU_ROOT', 'askubuntu')
EVAL_FRAC, CALIB_FRAC, SEEDS, TOPK = 0.20, 0.10, [0, 1, 2], 5
UNLAB_EVAL, UNLAB_CALIB, MIN_PREC, BATCH = 5000, 3000, 0.5, 256
t0 = time.time()

ids, texts = [], []
for line in gzip.open(f'{ROOT}/text_tokenized.txt.gz', 'rt', encoding='utf-8'):
    p = line.rstrip('\n').split('\t')
    ids.append(int(p[0])); texts.append((p[1] if len(p) > 1 else '') + ' ' + (p[2] if len(p) > 2 else ''))
order = np.argsort(ids); ids = np.array(ids)[order]; texts = [texts[i] for i in order]
pos = {q: i for i, q in enumerate(ids)}; n = len(ids)
dups = collections.defaultdict(set)                      # pares marcados, nos dois sentidos
for line in open(f'{ROOT}/train_random.txt'):
    p = line.rstrip('\n').split('\t'); q = int(p[0])
    for s in map(int, p[1].split()):
        if q in pos and s in pos: dups[q].add(s); dups[s].add(q)
e0, c0 = int((1 - EVAL_FRAC) * n), int((1 - EVAL_FRAC - CALIB_FRAC) * n)
windows = {'calibracao': range(c0, e0), 'avaliacao': range(e0, n)}
earlier = lambda i: {pos[s] for s in dups.get(ids[i], ()) if pos[s] < i}

# buscadores: TF-IDF com IDF só do período anterior à avaliação; média de vetores pré-treinados
tfv = TfidfVectorizer(sublinear_tf=True, min_df=2, token_pattern=r'\S+').fit(texts[:e0])
X_tfidf = tfv.transform(texts)
W = {}
for line in gzip.open(f'{ROOT}/vector/vectors_pruned.200.txt.gz', 'rt', encoding='utf-8'):
    p = line.rstrip().split(' ')
    if len(p) == 201: W[p[0]] = np.array(p[1:], dtype=np.float32)
X_vec = np.zeros((n, 200), dtype=np.float32)
for i, t in enumerate(texts):
    vs = [W[w] for w in t.split() if w in W]
    if vs: v = np.mean(vs, 0); X_vec[i] = v / (np.linalg.norm(v) + 1e-9)
print(f'corpus {n}, vetores {len(W)}, {time.time() - t0:.0f}s', flush=True)

def sims(name, rows):
    if name == 'tfidf': return (X_tfidf[rows] @ X_tfidf.T).toarray()
    return X_vec[rows] @ X_vec.T

desks = {s: np.random.default_rng(100 + s).integers(0, 2, n) for s in SEEDS}
rng = random.Random(20260928)
proc = {}
for w, rg in windows.items():
    lab = [i for i in rg if earlier(i)]
    unl = [i for i in rg if not earlier(i)]
    k = UNLAB_EVAL if w == 'avaliacao' else UNLAB_CALIB
    proc[w] = dict(lab=lab, unl=rng.sample(unl, min(k, len(unl))), n_total=len(rg), n_unl=len(unl))

def run(name, w):
    """Para cada pergunta processada: acerto no top-5 e (similaridade, acerto) do top-1, por condição e sorteio."""
    rows = proc[w]['lab'] + proc[w]['unl']; res = {}
    for b in range(0, len(rows), BATCH):
        R = rows[b:b + BATCH]; S = sims(name, R)
        for j, i in enumerate(R):
            s = S[j].copy(); s[i:] = -np.inf                 # só perguntas anteriores
            gold = earlier(i)
            top = np.argpartition(-s, TOPK)[:TOPK]; top = top[np.argsort(-s[top])]
            out = {'V3': (any(t in gold for t in top), float(s[top[0]]), top[0] in gold)}
            for sd in SEEDS:
                s2 = s.copy(); s2[desks[sd] != desks[sd][i]] = -np.inf
                t2 = np.argpartition(-s2, TOPK)[:TOPK]; t2 = t2[np.argsort(-s2[t2])]
                out[f'V2_s{sd}'] = (any(t in gold for t in t2), float(s2[t2[0]]), t2[0] in gold)
            res[i] = out
    return res

def suggestion_rate(res, w, cond):
    return sum(res[i][cond][0] for i in proc[w]['lab']) / proc[w]['n_total']

def threshold(res, cond):
    """Menor limiar com precisão conservadora >= MIN_PREC na calibração (sem marcação conta como erro)."""
    w = 'calibracao'; scale = proc[w]['n_unl'] / len(proc[w]['unl'])
    pts = [(res[i][cond][1], 1.0 if res[i][cond][2] else 0.0, 1.0) for i in proc[w]['lab']] + \
          [(res[i][cond][1], 0.0, scale) for i in proc[w]['unl']]
    pts.sort(key=lambda x: -x[0]); ok = tot = 0.0; best = float('inf')
    for sim, c, wgt in pts:
        ok += c; tot += wgt
        if tot > 0 and ok / tot >= MIN_PREC: best = sim
    return best

def auto_rate(res, w, cond, tau):
    lab = sum(1 for i in proc[w]['lab'] if res[i][cond][1] >= tau and res[i][cond][2])
    conf_unl = sum(1 for i in proc[w]['unl'] if res[i][cond][1] >= tau) * proc[w]['n_unl'] / len(proc[w]['unl'])
    conf_lab = sum(1 for i in proc[w]['lab'] if res[i][cond][1] >= tau)
    return lab / proc[w]['n_total'], (lab / (conf_lab + conf_unl) if conf_lab + conf_unl else None)

def boot(res, w, a, b, B=2000):
    """Diferença (b - a) na taxa de sugestão útil, média entre sorteios, reamostrando perguntas da janela."""
    N = proc[w]['n_total']; lab = proc[w]['lab']
    va = np.zeros((len(SEEDS), N)); vb = np.zeros((len(SEEDS), N))
    for k, sd in enumerate(SEEDS):
        for j, i in enumerate(lab):
            va[k, j] = res[i][a.format(sd)][0]; vb[k, j] = res[i][b.format(sd)][0]
    point = (vb.mean(1) - va.mean(1)).mean()
    g = np.random.default_rng(0); diffs = []
    for _ in range(B):
        idx = g.integers(0, N, N); diffs.append((vb[:, idx].mean(1) - va[:, idx].mean(1)).mean())
    return round(float(point), 4), [round(float(np.percentile(diffs, 2.5)), 4), round(float(np.percentile(diffs, 97.5)), 4)]

out = {'dataset_commit': subprocess.run(['git', '-C', ROOT, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip(),
       'perguntas': n, 'janelas': {w: {'total': proc[w]['n_total'], 'com_duplicata_anterior_marcada': len(proc[w]['lab']),
                                       'sem_marcacao_amostradas': len(proc[w]['unl'])} for w in proc}, 'buscadores': {}}
R = {}
for name in ('tfidf', 'vetores'):
    R[name] = {w: run(name, w) for w in proc}
    cal = np.mean([suggestion_rate(R[name]['calibracao'], 'calibracao', 'V3')] +
                  [suggestion_rate(R[name]['calibracao'], 'calibracao', f'V2_s{s}') for s in SEEDS])
    ev = R[name]['avaliacao']
    v2 = float(np.mean([suggestion_rate(ev, 'avaliacao', f'V2_s{s}') for s in SEEDS])); v3 = suggestion_rate(ev, 'avaliacao', 'V3')
    tau3 = threshold(R[name]['calibracao'], 'V3')
    a3 = auto_rate(ev, 'avaliacao', 'V3', tau3)
    a2 = [auto_rate(ev, 'avaliacao', f'V2_s{s}', threshold(R[name]['calibracao'], f'V2_s{s}')) for s in SEEDS]
    teto3 = len(proc['avaliacao']['lab']) / proc['avaliacao']['n_total']
    out['buscadores'][name] = {
        'sugestao_util_calibracao_media_V2_V3': round(float(cal), 4),
        'avaliacao': {'teto_V3_duplicata_marcada_existe': round(teto3, 4),
                      'sugestao_util_V2': round(v2, 4), 'sugestao_util_V3': round(v3, 4),
                      'V3_menos_V2': boot(ev, 'avaliacao', 'V2_s{}', 'V3'),
                      'reuso_automatico_V2': round(float(np.mean([x[0] for x in a2])), 4),
                      'reuso_automatico_V3': round(a3[0], 4), 'precisao_conservadora_V3': a3[1] and round(a3[1], 4),
                      'limiar_V3': tau3}}
    print(name, json.dumps(out['buscadores'][name], ensure_ascii=False), f'{time.time() - t0:.0f}s', flush=True)

# note: 'V3' does not depend on seed; boot() formats 'V3'.format(sd) -> 'V3'
best = max(out['buscadores'], key=lambda k: out['buscadores'][k]['sugestao_util_calibracao_media_V2_V3'])
ev = out['buscadores'][best]['avaliacao']
out['criterio'] = {'buscador': best, 'sugestao_util_V3': ev['sugestao_util_V3'], 'V3_menos_V2': ev['V3_menos_V2'],
                   'atingido': ev['sugestao_util_V3'] >= 0.05 and ev['V3_menos_V2'][0] >= 0.02 and ev['V3_menos_V2'][1][0] > 0}
out['segundos'] = round(time.time() - t0, 1)
json.dump(out, open('r5_support_summary.json', 'w'), indent=1, ensure_ascii=False)
print(json.dumps(out['criterio'], ensure_ascii=False))
