"""Grande Cérebro, rodada 7: as três peças do cérebro, rodando na SUA máquina.

Reaproveita os embeddings salvos pelo teste completo (gc_local_support.py) e testa:
  M0 busca plana (repete o teste completo)
  P0 controle: popularidade pura (as perguntas com mais duplicatas validadas, para todo mundo)
  M1 identidade: cada pergunta antiga é reconhecida também pelas suas duplicatas diretas validadas
  M2 identidade + peso de recorrência (beta x log(1 + nº de duplicatas validadas))
  M3 aprendizado: transformação dos embeddings aprendida com as ligações validadas (KISSME)
  M4 cérebro completo: M2 sobre os embeddings transformados
Mesmas janelas, sorteios e critério da rodada 5. Ligações só entram se as duas perguntas forem
anteriores à janela em uso; em V2, cada central só conhece as ligações entre as próprias perguntas.

Uso (na Área de Trabalho, com o gc-env ativo):
  python3 gc_local_brain.py
  python3 gc_local_brain.py --judge gemma4:latest     # também roda o juiz exploratório (~15 min)
No fim, envie gc_local_brain_result.json.
"""
import argparse, gzip, json, os, platform, random, sys, time, urllib.request, collections
import numpy as np
from scipy.sparse import csr_matrix

EVAL_FRAC, CALIB_FRAC, SEEDS, TOPK = 0.20, 0.10, [0, 1, 2], 5
UNLAB_EVAL, UNLAB_CALIB, BATCH_Q = 5000, 3000, 256
BETAS = [0.0, 0.005, 0.01, 0.02, 0.04, 0.08]

def normalize(M):
    return (M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)).astype(np.float32)

def load_matrix(path, n):
    done = path + '.done'
    if not (os.path.exists(path) and os.path.exists(done) and int(open(done).read()) == n):
        sys.exit(f'Não encontrei os embeddings completos em {path}. Rode antes: python3 gc_local_support.py --embed nomic-embed-text')
    return np.asarray(np.load(path, mmap_mode='r'), dtype=np.float32)

def kissme(X, pairs, pool, rng, eps_frac=0.01):
    """Métrica aprendida em forma fechada: aproxima pares 'mesmo problema', afasta pares aleatórios."""
    a, b = np.array([p[0] for p in pairs]), np.array([p[1] for p in pairs])
    dS = X[a] - X[b]
    na = rng.choice(pool, len(pairs)); nb = rng.choice(pool, len(pairs)); dD = X[na] - X[nb]
    d = X.shape[1]
    SS = dS.T @ dS / len(dS); SD = dD.T @ dD / len(dD)
    SS += np.eye(d) * eps_frac * np.trace(SS) / d; SD += np.eye(d) * eps_frac * np.trace(SD) / d
    Mm = np.linalg.inv(SS) - np.linalg.inv(SD); Mm = (Mm + Mm.T) / 2
    w, V = np.linalg.eigh(Mm); keep = w > 0
    return (V[:, keep] * np.sqrt(w[keep])).astype(np.float32), int(keep.sum())

class Graph:
    """Duplicatas diretas validadas de cada pergunta (sem encadear) e o 'centro' de cada uma com elas."""
    def __init__(self, n, pairs, X):
        rows = [a for a, b in pairs] + [b for a, b in pairs]; cols = [b for a, b in pairs] + [a for a, b in pairs]
        A = csr_matrix((np.ones(len(rows), dtype=np.float32), (rows, cols)), shape=(n, n)); A.sum_duplicates(); A.data[:] = 1
        self.indptr, self.indices = A.indptr, A.indices
        self.deg = np.diff(A.indptr).astype(np.float32)
        self.H = np.where(self.deg > 0)[0]; self.starts = self.indptr[self.H]
        self.A = A; self.logdeg = np.log1p(self.deg).astype(np.float32)
        self.set_space(X)
    def set_space(self, X):
        self.C = normalize(X[self.H] + np.asarray(self.A[self.H] @ X))
    def identity_scores(self, s, qv):
        """s: similaridades (−inf fora do escopo). Retorna a pontuação M1."""
        out = s.copy()
        if len(self.H):
            nb = np.maximum.reduceat(s[self.indices], self.starts)
            cs = self.C @ qv
            out[self.H] = np.maximum(np.maximum(out[self.H], nb), cs)
            out[self.H] = np.where(np.isfinite(s[self.H]), out[self.H], -np.inf)
        return out

def top5(score):
    t = np.argpartition(-score, TOPK)[:TOPK]; return t[np.argsort(-score[t])]

def post(host, route, payload, timeout=600):
    req = urllib.request.Request(host + route, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--embed', default='nomic-embed-text'); ap.add_argument('--host', default='http://localhost:11434')
    ap.add_argument('--judge', default=None, help='modelo do Ollama para o juiz exploratório, ex.: gemma4:latest')
    a = ap.parse_args(); t0 = time.time(); rng_np = np.random.default_rng(20260928)

    ids, texts = [], []
    for line in gzip.open('gc_data/text_tokenized.txt.gz', 'rt', encoding='utf-8'):
        p = line.rstrip('\n').split('\t'); ids.append(int(p[0])); texts.append((p[1] if len(p) > 1 else '') + ' ' + (p[2] if len(p) > 2 else ''))
    order = np.argsort(ids); ids = np.array(ids)[order]; texts = [texts[i] for i in order]
    pos = {q: i for i, q in enumerate(ids)}; n = len(ids)
    dups = collections.defaultdict(set); pairs_all = set()
    for line in open('gc_data/train_random.txt', encoding='utf-8'):
        p = line.rstrip('\n').split('\t'); q = int(p[0])
        for s in map(int, p[1].split()):
            if q in pos and s in pos:
                dups[q].add(s); dups[s].add(q); pairs_all.add(tuple(sorted((pos[q], pos[s]))))
    e0, c0 = int((1 - EVAL_FRAC) * n), int((1 - EVAL_FRAC - CALIB_FRAC) * n)
    windows = {'calibracao': range(c0, e0), 'avaliacao': range(e0, n)}
    earlier = lambda i: {pos[s] for s in dups.get(ids[i], ()) if pos[s] < i}
    desks = {s: np.random.default_rng(100 + s).integers(0, 2, n) for s in SEEDS}
    rng = random.Random(20260928); proc = {}
    for w, rg in windows.items():
        lab = [i for i in rg if earlier(i)]; unl = [i for i in rg if not earlier(i)]
        k = UNLAB_EVAL if w == 'avaliacao' else UNLAB_CALIB
        proc[w] = dict(lab=lab, unl=rng.sample(unl, min(k, len(unl))), n_total=len(rg), n_unl=len(unl))
    tag = a.embed.replace(':', '_').replace('/', '_')
    qrows = sorted({i for w in proc for i in proc[w]['lab'] + proc[w]['unl']}); qidx = {i: j for j, i in enumerate(qrows)}
    Q = load_matrix(f'gc_cache/support_q_{tag}.npy', len(qrows)); D = load_matrix(f'gc_cache/support_d_{tag}.npy', n)
    print(f'{n} perguntas, embeddings carregados ({time.time() - t0:.0f}s)', flush=True)

    def setup(cut, with_v2):
        """Grafos e transformações com ligações anteriores ao corte."""
        P = [p for p in pairs_all if p[1] < cut]
        S = {}
        L, r = kissme(D, P, np.arange(cut), rng_np)
        DL = normalize(D @ L)
        S['V3'] = dict(rows=None, G=Graph(n, P, D), L=L, DLr=DL, r=r, GL=Graph(n, P, DL))
        if with_v2:
            for sd in SEEDS:
                for dk in (0, 1):
                    Pd = [p for p in P if desks[sd][p[0]] == dk and desks[sd][p[1]] == dk]
                    rows = np.where(desks[sd] == dk)[0]
                    Ld, rd = kissme(D, Pd, rows[rows < cut], rng_np)
                    DLr = normalize(D[rows] @ Ld)
                    tmp = np.zeros((n, Ld.shape[1]), dtype=np.float32); tmp[rows] = DLr
                    S[(sd, dk)] = dict(rows=rows, G=Graph(n, Pd, D), L=Ld, DLr=DLr, r=rd, GL=Graph(n, Pd, tmp))
                    del tmp
        return S, len(P)

    def score_query(i, qv, s_base, qL, sL, st, betas):
        """Retorna top-5 por método (e por beta em M2/M4) para uma condição."""
        out = {}
        out['P0'] = top5(np.where(np.isfinite(s_base), st['G'].logdeg + 1e-3 * s_base, -np.inf))   # controle: popularidade
        out['M0'] = top5(s_base)
        m1 = st['G'].identity_scores(s_base, qv); out['M1'] = top5(m1)
        for b in betas: out[('M2', b)] = top5(m1 + b * st['G'].logdeg)
        out['M3'] = top5(sL)
        m4 = st['GL'].identity_scores(sL, qL)
        for b in betas: out[('M4', b)] = top5(m4 + b * st['GL'].logdeg)
        return out

    def run(w, S, conds, betas):
        rows = proc[w]['lab'] + proc[w]['unl']; res = {}
        for b0 in range(0, len(rows), BATCH_Q):
            R = rows[b0:b0 + BATCH_Q]; QV = Q[[qidx[i] for i in R]]; SB = QV @ D.T
            QL3 = normalize(QV @ S['V3']['L']); SL3 = QL3 @ S['V3']['DLr'].T
            v2 = {}
            for c in conds:
                if c == 'V3': continue
                sd = int(c.split('_s')[1])
                for dk in (0, 1):
                    st = S[(sd, dk)]; js = [j for j, i in enumerate(R) if desks[sd][i] == dk]
                    if not js: continue
                    QLd = normalize(QV[js] @ st['L']); SLd = QLd @ st['DLr'].T
                    for k, j in enumerate(js): v2[(sd, j)] = (QLd[k], SLd[k])
            for j, i in enumerate(R):
                s = SB[j].copy(); s[i:] = -np.inf; r = {}
                for c in conds:
                    if c == 'V3':
                        sL = SL3[j].copy(); sL[i:] = -np.inf
                        r[c] = score_query(i, QV[j], s, QL3[j], sL, S['V3'], betas)
                    else:
                        sd = int(c.split('_s')[1]); st = S[(sd, desks[sd][i])]
                        sb = s.copy(); sb[desks[sd] != desks[sd][i]] = -np.inf
                        qL, sub = v2[(sd, j)]
                        sL = np.full(n, -np.inf, dtype=np.float32); sL[st['rows']] = sub; sL[i:] = -np.inf
                        r[c] = score_query(i, QV[j], sb, qL, sL, st, betas)
                res[i] = r
            print(f'  {w}: {min(b0 + BATCH_Q, len(rows))}/{len(rows)}  ({time.time() - t0:.0f}s)', flush=True)
        return res

    hit = lambda i, top: bool(any(t in earlier(i) for t in top))
    def rate(res, w, c, m): return sum(hit(i, res[i][c][m]) for i in proc[w]['lab']) / proc[w]['n_total']

    # calibração: escolhe beta e o método principal só com V3
    Sc, nlc = setup(c0, with_v2=False)
    cal = run('calibracao', Sc, ['V3'], BETAS)
    grid = {m: {b: rate(cal, 'calibracao', 'V3', (m, b)) for b in BETAS} for m in ('M2', 'M4')}
    best_b = {m: max(BETAS, key=lambda b: (grid[m][b], -b)) for m in grid}
    primary = max(('M2', 'M4'), key=lambda m: grid[m][best_b[m]])
    print('calibração:', {m: {str(b): round(v, 4) for b, v in g.items()} for m, g in grid.items()}, '-> principal', primary, flush=True)
    del Sc, cal

    Se, nle = setup(e0, with_v2=True)
    conds = ['V3'] + [f'V2_s{s}' for s in SEEDS]
    ev = run('avaliacao', Se, conds, sorted(set(best_b.values())))
    methods = {'P0': 'P0', 'M0': 'M0', 'M1': 'M1', 'M2': ('M2', best_b['M2']), 'M3': 'M3', 'M4': ('M4', best_b['M4'])}
    w = 'avaliacao'; N = proc[w]['n_total']; lab = proc[w]['lab']
    def vec(c, m):
        v = np.zeros(N); v[:len(lab)] = [hit(i, ev[i][c][m]) for i in lab]; return v
    def boot(pairs_ab, B=2000):
        g = np.random.default_rng(0); A_ = np.array([p[0] for p in pairs_ab]); B_ = np.array([p[1] for p in pairs_ab])
        point = (B_.mean(1) - A_.mean(1)).mean(); diffs = []
        for _ in range(B):
            idx = g.integers(0, N, N); diffs.append((B_[:, idx].mean(1) - A_[:, idx].mean(1)).mean())
        return round(float(point), 4), [round(float(np.percentile(diffs, 2.5)), 4), round(float(np.percentile(diffs, 97.5)), 4)]
    table = {}
    for name, m in methods.items():
        v3 = vec('V3', m); v2s = [vec(f'V2_s{s}', m) for s in SEEDS]
        table[name] = {'sugestao_util_V2': round(float(np.mean([v.mean() for v in v2s])), 4), 'sugestao_util_V3': round(float(v3.mean()), 4),
                       'V3_menos_V2': boot([(v2, v3) for v2 in v2s]),
                       'V3_contra_M0': boot([(vec('V3', 'M0'), v3)]) if name != 'M0' else None}
    p = table[primary]
    out = {'modelo_embeddings': a.embed, 'maquina': platform.platform(),
           'ligacoes_validadas': {'antes_da_calibracao': nlc, 'antes_da_avaliacao': nle},
           'dimensoes_aprendidas_V3': Se['V3']['r'],
           'calibracao': {'grade_beta_V3': {m: {str(b): round(v, 4) for b, v in g.items()} for m, g in grid.items()},
                          'beta_escolhido': best_b, 'metodo_principal': primary},
           'avaliacao': {'teto_V3': round(len(lab) / N, 4), 'metodos': table},
           'criterio': {'metodo': primary, 'sugestao_util_V3': p['sugestao_util_V3'], 'V3_menos_V2': p['V3_menos_V2'],
                        'atingido': bool(p['sugestao_util_V3'] >= 0.05 and p['V3_menos_V2'][0] >= 0.02 and p['V3_menos_V2'][1][0] > 0)}}
    print(json.dumps(out['avaliacao'], ensure_ascii=False), flush=True)

    if a.judge:
        pm = methods[primary]; words = lambda i: ' '.join(texts[i].split()[:70])
        prompt = ('Question A: {a}\n\nQuestion B: {b}\n\nAre A and B about the same technical problem, so that a correct '
                  'answer to B would also solve A? Answer only YES or NO.')
        def judge(i, j):
            r = post(a.host, '/api/generate', {'model': a.judge, 'stream': False, 'options': {'temperature': 0, 'num_predict': 4},
                                               'prompt': prompt.format(a=words(i), b=words(j))})
            return 'YES' in r['response'].upper()
        g = random.Random(7)
        U = g.sample(proc[w]['unl'], 150); POS = g.sample(lab, 60); NEG = g.sample(proc[w]['unl'], 60)
        yU = [judge(i, int(ev[i]['V3'][pm][0])) for i in U]; print('  juiz: sugestões ok', flush=True)
        yP = [judge(i, sorted(earlier(i))[0]) for i in POS]
        yN = [judge(i, int(g.randrange(0, i))) for i in NEG]
        tpr, fpr, yu = float(np.mean(yP)), float(np.mean(yN)), float(np.mean(yU))
        est = min(max((yu - fpr) / (tpr - fpr), 0.0), 1.0) if tpr > fpr else None
        lab_top1 = sum(int(ev[i]['V3'][pm][0]) in earlier(i) for i in lab)
        gb = np.random.default_rng(1); ests = []
        for _ in range(2000):
            u = np.mean(gb.choice(yU, len(yU))); tp = np.mean(gb.choice(yP, len(yP))); fp = np.mean(gb.choice(yN, len(yN)))
            if tp > fp: ests.append(min(max((u - fp) / (tp - fp), 0.0), 1.0))
        ci = [round(float(np.percentile(ests, 2.5)), 3), round(float(np.percentile(ests, 97.5)), 3)] if ests else None
        out['juiz_exploratorio'] = {'modelo': a.judge, 'sensibilidade': round(tpr, 3), 'falsos_positivos': round(fpr, 3),
                                    'sim_nas_sugestoes_sem_marcacao': round(yu, 3), 'taxa_corrigida_sem_marcacao': est and round(est, 3),
                                    'taxa_corrigida_ic95': ci,
                                    'primeira_sugestao_util_estimada_V3': est is not None and round((lab_top1 + est * proc[w]['n_unl']) / N, 4)}
        print(json.dumps(out['juiz_exploratorio'], ensure_ascii=False), flush=True)
    out['minutos_totais'] = round((time.time() - t0) / 60, 1)
    json.dump(out, open('gc_local_brain_result.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print('\ncritério atingido:', out['criterio']['atingido'], '\nPronto. Envie o arquivo gc_local_brain_result.json.')

if __name__ == '__main__':
    main()
