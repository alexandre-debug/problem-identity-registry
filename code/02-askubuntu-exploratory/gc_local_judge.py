"""Grande Cérebro: juiz comparativo (exploratório), roda na SUA máquina.

Pergunta: independentemente de os moderadores terem marcado a duplicata, a primeira sugestão
do M2 é mais útil que a da busca plana (M0)? O mesmo LLM local julga a primeira sugestão dos
dois métodos, nas mesmas perguntas:
  - 100 perguntas com duplicata marcada e 100 sem marcação (sorteadas), pesadas pela proporção
    real de cada grupo na janela de avaliação;
  - controles: 60 pares de duplicatas marcadas (sensibilidade) e 60 pares aleatórios (falsos positivos);
  - a taxa de "sim" é corrigida pela sensibilidade e pelos falsos positivos do juiz.
Também calcula, sem LLM, o "acerto pela família": vale sugerir a duplicata marcada ou uma
duplicata já confirmada dela. Não entra no critério da rodada 7. Configuração: V3, beta = 0,02.

Uso: python3 gc_local_judge.py --judge gemma4:latest
Mostra as 3 primeiras respostas cruas. Saída: gc_local_judge_result.json.
"""
import argparse, gzip, json, random, re, sys, time, collections, urllib.request, urllib.error
import numpy as np
from scipy.sparse import csr_matrix

EVAL_FRAC, CALIB_FRAC, BETA, N_LAB, N_UNL, N_CTRL = 0.20, 0.10, 0.02, 100, 100, 60
PROMPT = ('Question A: {a}\n\nQuestion B: {b}\n\nAre A and B about the same technical problem, so that a correct '
          'answer to B would also solve A? Reply with exactly one word: YES or NO.')

def normalize(M): return (M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)).astype(np.float32)

def post(host, payload):
    req = urllib.request.Request(host + '/api/generate', data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=600) as r: return json.loads(r.read())

def corrected(y, tpr, fpr): return min(max((y - fpr) / (tpr - fpr), 0.0), 1.0) if tpr > fpr else float('nan')

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--judge', required=True); ap.add_argument('--host', default='http://localhost:11434')
    ap.add_argument('--embed', default='nomic-embed-text'); a = ap.parse_args(); t0 = time.time()
    ids, texts = [], []
    for line in gzip.open('gc_data/text_tokenized.txt.gz', 'rt', encoding='utf-8'):
        p = line.rstrip('\n').split('\t'); ids.append(int(p[0])); texts.append((p[1] if len(p) > 1 else '') + ' ' + (p[2] if len(p) > 2 else ''))
    order = np.argsort(ids); ids = np.array(ids)[order]; texts = [texts[i] for i in order]
    pos = {q: i for i, q in enumerate(ids)}; n = len(ids)
    dups = collections.defaultdict(set); pairs = set()
    for line in open('gc_data/train_random.txt', encoding='utf-8'):
        p = line.rstrip('\n').split('\t'); q = int(p[0])
        for s in map(int, p[1].split()):
            if q in pos and s in pos: dups[q].add(s); dups[s].add(q); pairs.add(tuple(sorted((pos[q], pos[s]))))
    e0, c0 = int((1 - EVAL_FRAC) * n), int((1 - EVAL_FRAC - CALIB_FRAC) * n)
    earlier = lambda i: {pos[s] for s in dups.get(ids[i], ()) if pos[s] < i}
    rng = random.Random(20260928); proc = {}
    for w, rg, k in (('calibracao', range(c0, e0), 3000), ('avaliacao', range(e0, n), 5000)):
        lab = [i for i in rg if earlier(i)]; unl = [i for i in rg if not earlier(i)]
        proc[w] = dict(lab=lab, unl=rng.sample(unl, min(k, len(unl))), n_total=len(rg), n_unl=len(unl))
    tag = a.embed.replace(':', '_').replace('/', '_')
    qrows = sorted({i for w in proc for i in proc[w]['lab'] + proc[w]['unl']}); qidx = {i: j for j, i in enumerate(qrows)}
    Q = np.asarray(np.load(f'gc_cache/support_q_{tag}.npy', mmap_mode='r'), dtype=np.float32)
    D = np.asarray(np.load(f'gc_cache/support_d_{tag}.npy', mmap_mode='r'), dtype=np.float32)
    P = [p for p in pairs if p[1] < e0]
    A = csr_matrix((np.ones(2 * len(P), dtype=np.float32), ([x for x, y in P] + [y for x, y in P], [y for x, y in P] + [x for x, y in P])), shape=(n, n))
    A.sum_duplicates(); A.data[:] = 1
    deg = np.diff(A.indptr).astype(np.float32); H = np.where(deg > 0)[0]; starts = A.indptr[H]
    C = normalize(D[H] + np.asarray(A[H] @ D)); logdeg = np.log1p(deg)
    def top1s(i):
        qv = Q[qidx[i]]; s = D @ qv; s[i:] = -np.inf
        m1 = s.copy(); m1[H] = np.maximum(np.maximum(m1[H], np.maximum.reduceat(s[A.indices], starts)), C @ qv)
        m1[H] = np.where(np.isfinite(s[H]), m1[H], -np.inf)
        return int(np.argmax(s)), int(np.argmax(m1 + BETA * logdeg))

    # acerto pela família (sem LLM): conta como acerto sugerir a duplicata marcada OU uma duplicata já
    # confirmada dela (vizinha na rede anterior ao corte). Todas as perguntas marcadas da janela.
    def top5(v): t = np.argpartition(-v, 5)[:5]; return t[np.argsort(-v[t])]
    labs = proc['avaliacao']['lab']; fam_hits = collections.Counter()
    for b0 in range(0, len(labs), 256):
        Rb = labs[b0:b0 + 256]; SB = Q[[qidx[i] for i in Rb]] @ D.T
        for j, i in enumerate(Rb):
            s = SB[j]; s[i:] = -np.inf
            m1 = s.copy(); m1[H] = np.maximum(np.maximum(m1[H], np.maximum.reduceat(s[A.indices], starts)), C @ Q[qidx[i]])
            m1[H] = np.where(np.isfinite(s[H]), m1[H], -np.inf)
            gold = earlier(i); fam = set(gold)
            for x in gold: fam |= set(A.indices[A.indptr[x]:A.indptr[x + 1]].tolist())
            for name, v in (('M0', s), ('M2', m1 + BETA * logdeg)):
                t = [int(x) for x in top5(v)]
                fam_hits[name + '_marcada_top5'] += bool(set(t) & gold); fam_hits[name + '_familia_top5'] += bool(set(t) & fam)
                fam_hits[name + '_marcada_top1'] += t[0] in gold; fam_hits[name + '_familia_top1'] += t[0] in fam
    print('  acerto pela família: calculado', flush=True)

    w = 'avaliacao'; lab = proc[w]['lab']; N = proc[w]['n_total']; wL = len(lab) / N; wU = proc[w]['n_unl'] / N
    g = random.Random(29)
    L = g.sample(lab, N_LAB); U = g.sample(proc[w]['unl'], N_UNL)
    POS = g.sample(lab, N_CTRL); NEG = g.sample(proc[w]['unl'], N_CTRL); NEGj = [g.randrange(0, i) for i in NEG]
    words = lambda i: ' '.join(texts[i].split()[:70]); shown = [0]; invalid = [0]; cache = {}; use_think = [True]
    def judge(i, j):
        if (i, j) in cache: return cache[(i, j)]
        payload = {'model': a.judge, 'stream': False, 'prompt': PROMPT.format(a=words(i), b=words(j)), 'options': {'temperature': 0, 'num_predict': 64}}
        if use_think[0]: payload['think'] = False
        try: r = post(a.host, payload)
        except urllib.error.HTTPError:
            if not use_think[0]: raise
            use_think[0] = False; payload.pop('think'); r = post(a.host, payload)
        raw = (r.get('response') or '').strip()
        if shown[0] < 3: print(f'  resposta crua {shown[0] + 1}: {raw[:80]!r}', flush=True); shown[0] += 1
        m = re.search(r'\b(YES|NO)\b', raw.upper())
        if m is None: invalid[0] += 1; v = None
        else: v = m.group(1) == 'YES'
        cache[(i, j)] = v
        if len(cache) == 20 and invalid[0] >= 10:
            sys.exit(f'O juiz não respondeu YES/NO em {invalid[0]} dos primeiros 20 julgamentos. Veja as respostas cruas acima.')
        return v

    print('juiz: controles', flush=True)
    yP = [judge(i, sorted(earlier(i))[0]) for i in POS]; yN = [judge(i, j) for i, j in zip(NEG, NEGj)]
    rows = []
    for k, i in enumerate(L + U):
        m0, m2 = top1s(i)
        rows.append(dict(i=i, grupo='marcada' if k < N_LAB else 'sem_marcacao', m0=m0, m2=m2,
                         v0=judge(i, m0), v2=judge(i, m2), g0=m0 in earlier(i), g2=m2 in earlier(i)))
        if (k + 1) % 25 == 0: print(f'  juiz: {k + 1}/{len(L) + len(U)} perguntas', flush=True)
    tot = len(cache)
    if invalid[0] > 0.2 * tot: sys.exit(f'O juiz não respondeu YES/NO em {invalid[0]} de {tot} julgamentos. Veja as respostas cruas acima.')
    ok = lambda v: v is not None
    yP = [v for v in yP if ok(v)]; yN = [v for v in yN if ok(v)]
    R = [r for r in rows if ok(r['v0']) and ok(r['v2'])]
    def estimate(Rs, P_, N_):
        tpr, fpr = np.mean(P_), np.mean(N_); out = {}
        for m in ('v0', 'v2'):
            per = {gname: corrected(np.mean([r[m] for r in Rs if r['grupo'] == gname]), tpr, fpr) for gname in ('marcada', 'sem_marcacao')}
            out[m] = wL * per['marcada'] + wU * per['sem_marcacao']; out[m + '_grupos'] = per
        return out, tpr, fpr
    est, tpr, fpr = estimate(R, yP, yN)
    gb = np.random.default_rng(1); diffs = []; Lr = [r for r in R if r['grupo'] == 'marcada']; Ur = [r for r in R if r['grupo'] == 'sem_marcacao']
    for _ in range(2000):
        Rs = [Lr[k] for k in gb.integers(0, len(Lr), len(Lr))] + [Ur[k] for k in gb.integers(0, len(Ur), len(Ur))]
        e, _, _ = estimate(Rs, list(gb.choice(yP, len(yP))), list(gb.choice(yN, len(yN))))
        if np.isfinite(e['v2']) and np.isfinite(e['v0']): diffs.append(e['v2'] - e['v0'])
    r3 = lambda x: None if x is None or not np.isfinite(x) else round(float(x), 3)
    disagree = [r for r in R if r['v0'] != r['v2']][:12]
    out = {'modelo': a.judge, 'julgamentos': tot, 'respostas_invalidas': invalid[0],
           'juiz': {'sensibilidade_em_duplicatas_marcadas': r3(tpr), 'falsos_positivos_em_pares_aleatorios': r3(fpr)},
           'primeira_sugestao_util_corrigida': {
               'busca_plana_M0': r3(est['v0']), 'M2': r3(est['v2']), 'M2_menos_M0': r3(est['v2'] - est['v0']),
               'M2_menos_M0_ic95': [r3(np.percentile(diffs, 2.5)), r3(np.percentile(diffs, 97.5))] if diffs else None,
               'por_grupo': {'M0': {k: r3(v) for k, v in est['v0_grupos'].items()}, 'M2': {k: r3(v) for k, v in est['v2_grupos'].items()}}},
           'sim_bruto': {gname: {'M0': r3(np.mean([r['v0'] for r in R if r['grupo'] == gname])), 'M2': r3(np.mean([r['v2'] for r in R if r['grupo'] == gname]))}
                         for gname in ('marcada', 'sem_marcacao')},
           'acerto_pela_marcacao_top1_grupo_marcado': {'M0': r3(np.mean([r['g0'] for r in Lr])), 'M2': r3(np.mean([r['g2'] for r in Lr]))},
           'acerto_sem_llm_sobre_todas_as_perguntas_da_janela': {k: round(v / N, 4) for k, v in sorted(fam_hits.items())},
           'mesma_primeira_sugestao': r3(np.mean([r['m0'] == r['m2'] for r in R])),
           'pares_discordantes_pelo_juiz': {gname: {'so_M0_util': sum(r['v0'] and not r['v2'] for r in R if r['grupo'] == gname),
                                                    'so_M2_util': sum(r['v2'] and not r['v0'] for r in R if r['grupo'] == gname)}
                                            for gname in ('marcada', 'sem_marcacao')},
           'pesos': {'com_marcacao': round(wL, 4), 'sem_marcacao': round(wU, 4)},
           'exemplos_de_discordancia': [{'pergunta': texts[r['i']][:110], 'M0': texts[r['m0']][:110], 'juiz_M0': r['v0'],
                                         'M2': texts[r['m2']][:110], 'juiz_M2': r['v2']} for r in disagree],
           'minutos': round((time.time() - t0) / 60, 1)}
    json.dump(out, open('gc_local_judge_result.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in out.items() if k != 'exemplos_de_discordancia'}, ensure_ascii=False, indent=1))
    print('\nPronto. Envie gc_local_judge_result.json.')

if __name__ == '__main__':
    main()
