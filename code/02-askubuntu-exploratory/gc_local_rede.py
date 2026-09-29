"""Grande Cérebro: curvas de efeito de rede (sem LLM, roda na SUA máquina, poucos minutos).

Pergunta: o sistema fica melhor quanto mais gente contribui, sem estabilizar cedo?
Mede, nas perguntas marcadas da janela de avaliação, o acerto pela família entre as 5 sugestões
(família fixa, definida pela rede completa), dividido pelo total de perguntas da janela.
Métodos: M0 busca plana; M1 relações sem bônus; M2 relações + bônus (0,02); H = M0 e M2 intercalados.

Curva A, densidade de confirmações: todas as perguntas antigas continuam na memória; muda só a fração
  f das ligações confirmadas que a memória conhece (0, 10, 25, 50, 75, 100%; 3 sorteios).
Curva B, participantes: as perguntas antigas são repartidas ao acaso entre 10 "aplicações"; a memória
  tem só as perguntas e as ligações (entre perguntas presentes) de 1, 2, 5 ou 10 aplicações (3 sorteios).
  A pergunta nova só pode achar o que está na memória.

Uso: python3 gc_local_rede.py
Saída: gc_local_rede_result.json
"""
import gzip, json, os, random, sys, time, collections
import numpy as np
from scipy.sparse import csr_matrix

EVAL_FRAC, CALIB_FRAC, BETA = 0.20, 0.10, 0.02
FRACS, SOURCES, KS, SEEDS, NBOOT = [0.0, 0.1, 0.25, 0.5, 0.75, 1.0], 10, [1, 2, 5, 10], 3, 2000
METHODS = ['M0', 'M1', 'M2', 'H']

def normalize(M): return (M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)).astype(np.float32)
def top5(v): t = np.argpartition(-v, 5)[:5]; return [int(x) for x in t[np.argsort(-v[t])]]
def inter(a, b):
    out = []
    for x in [v for pair in zip(a, b) for v in pair]:
        if x not in out: out.append(x)
    return out[:5]
def ci(x): x = [v for v in x if np.isfinite(v)]; return [round(float(np.percentile(x, 2.5)), 3), round(float(np.percentile(x, 97.5)), 3)] if x else None

def main():
    tag = (sys.argv[1] if len(sys.argv) > 1 else 'nomic-embed-text').replace(':', '_').replace('/', '_'); t0 = time.time()
    ids = []
    for line in gzip.open('gc_data/text_tokenized.txt.gz', 'rt', encoding='utf-8'): ids.append(int(line.split('\t', 1)[0]))
    ids = np.array(sorted(ids)); pos = {q: i for i, q in enumerate(ids)}; n = len(ids)
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
        proc[w] = dict(lab=lab, unl=rng.sample(unl, min(k, len(unl))), n_total=len(rg))
    qrows = sorted({i for w in proc for i in proc[w]['lab'] + proc[w]['unl']}); qidx = {i: j for j, i in enumerate(qrows)}
    for f, m in ((f'gc_cache/support_q_{tag}.npy', len(qrows)), (f'gc_cache/support_d_{tag}.npy', n)):
        if not os.path.exists(f + '.done') or int(open(f + '.done').read()) != m: sys.exit(f'Faltam os embeddings em {f}.')
    Q = np.asarray(np.load(f'gc_cache/support_q_{tag}.npy', mmap_mode='r'), dtype=np.float32)
    D = np.asarray(np.load(f'gc_cache/support_d_{tag}.npy', mmap_mode='r'), dtype=np.float32)

    PF = sorted(p for p in pairs if p[1] < e0); L = len(PF)
    def build(P):
        if not P: return None
        A = csr_matrix((np.ones(2 * len(P), dtype=np.float32), ([x for x, y in P] + [y for x, y in P], [y for x, y in P] + [x for x, y in P])), shape=(n, n))
        A.sum_duplicates(); A.data[:] = 1
        deg = np.diff(A.indptr).astype(np.float32); H = np.where(deg > 0)[0]
        return dict(A=A, H=H, starts=A.indptr[H], C=normalize(D[H] + np.asarray(A[H] @ D)), logdeg=np.log1p(deg))
    graphs = []                                                    # (curva, nível, semente, grafo, máscara)
    for f in FRACS:
        for sd in ([0] if f in (0.0, 1.0) else range(SEEDS)):
            P = PF if f == 1.0 else random.Random(1000 * sd + int(round(f * 100))).sample(PF, int(round(f * L)))
            graphs.append(('A', f, sd, build(P), None))
    src = np.random.default_rng(77).integers(0, SOURCES, n)
    for k in KS[:-1]:                                              # 10 de 10 = curva A com 100%
        for sd in range(SEEDS):
            S = random.Random(500 + 10 * k + sd).sample(range(SOURCES), k); mask = np.isin(src, S)
            graphs.append(('B', k, sd, build([p for p in PF if mask[p[0]] and mask[p[1]]]), mask))
    print(f'  {len(graphs)} memórias montadas ({L} ligações na rede completa)', flush=True)
    Af = [g for g in graphs if g[0] == 'A' and g[1] == 1.0][0][3]['A']
    labs = proc['avaliacao']['lab']; N = proc['avaliacao']['n_total']; fam = {}
    for i in labs:
        fs = set(earlier(i))
        for x in list(fs): fs |= set(Af.indices[Af.indptr[x]:Af.indptr[x + 1]].tolist())
        fam[i] = fs

    hits = np.zeros((len(graphs), len(labs), len(METHODS)), dtype=bool)
    for b0 in range(0, len(labs), 256):
        R = labs[b0:b0 + 256]; QV = Q[[qidx[i] for i in R]]; SB = QV @ D.T
        for j, i in enumerate(R):
            s = SB[j]; s[i:] = -np.inf; l0_full = top5(s); fs = fam[i]; qi = b0 + j
            for gi, (cv, lv, sd, G, mask) in enumerate(graphs):
                if mask is None: sq, l0, fq = s, l0_full, fs
                else: sq = s.copy(); sq[~mask] = -np.inf; l0 = top5(sq); fq = {x for x in fs if mask[x]}
                if G is None: l1 = l2 = l0
                else:
                    H = G['H']; m1 = sq.copy()
                    m1[H] = np.maximum(np.maximum(m1[H], np.maximum.reduceat(sq[G['A'].indices], G['starts'])), G['C'] @ QV[j])
                    m1[H] = np.where(np.isfinite(sq[H]), m1[H], -np.inf)
                    l1 = top5(m1); l2 = top5(m1 + BETA * G['logdeg'])
                for mi, lst in enumerate((l0, l1, l2, inter(l0, l2))): hits[gi, qi, mi] = bool(set(lst) & fq)
        print(f'  {min(b0 + 256, len(labs))}/{len(labs)} perguntas marcadas', flush=True)

    def level(cv, lv):                                             # média dos sorteios, por pergunta: [pergunta, método]
        if cv == 'B' and lv == SOURCES: cv, lv = 'A', 1.0
        return hits[[gi for gi, g in enumerate(graphs) if g[0] == cv and g[1] == lv]].mean(axis=0)
    PA = {f: level('A', f) for f in FRACS}; PB = {k: level('B', k) for k in KS}
    b = np.random.default_rng(7); boots = [b.integers(0, len(labs), len(labs)) for _ in range(NBOOT)]
    r = lambda M, mi, ix=None: float((M[:, mi] if ix is None else M[ix, mi]).sum() / N)

    # curva A: índice de saturação = [ganho(100%) - ganho(50%)] / [ganho(50%) - ganho(0)]
    def satA(mi, ix=None):
        g = lambda f: r(PA[f], mi, ix) - r(PA[f], 0, ix); den = g(0.5) - g(0.0)
        return (g(1.0) - g(0.5)) / den if den > 0 else float('nan')
    curveA = [{'fracao_das_ligacoes': f, 'ligacoes': int(round(f * L)), **{m: round(r(PA[f], mi), 4) for mi, m in enumerate(METHODS)}} for f in FRACS]
    # curva B: ganho relativo das confirmações = (M1 - M0) / M0 em cada tamanho
    def relB(k, mi, ix=None): m0 = r(PB[k], 0, ix); return (r(PB[k], mi, ix) - m0) / m0 if m0 > 0 else float('nan')
    curveB = [{'aplicacoes': k, 'fracao_das_perguntas_antigas': k / SOURCES,
               **{m: round(r(PB[k], mi), 4) for mi, m in enumerate(METHODS)},
               'ganho_relativo_M1': round(relB(k, 1), 3), 'ganho_relativo_H': round(relB(k, 3), 3)} for k in KS]
    out = {'curva_A_densidade_de_confirmacoes': curveA,
           'A_indice_de_saturacao': {m: {'valor': round(satA(mi), 3), 'ic95': ci([satA(mi, ix) for ix in boots])} for mi, m in enumerate(METHODS) if mi},
           'curva_B_participantes': curveB,
           'B_ganho_relativo_10_menos_5_aplicacoes': {m: {'valor': round(relB(10, mi) - relB(5, mi), 3), 'ic95': ci([relB(10, mi, ix) - relB(5, mi, ix) for ix in boots])}
                                                      for mi, m in enumerate(METHODS) if mi},
           'B_acerto_somado_por_aplicacao_nova_em_pontos': {m: {'de_1_a_2': round(100 * (r(PB[2], mi) - r(PB[1], mi)), 3),
                                                                'de_2_a_5': round(100 * (r(PB[5], mi) - r(PB[2], mi)) / 3, 3),
                                                                'de_5_a_10': round(100 * (r(PB[10], mi) - r(PB[5], mi)) / 5, 3)} for mi, m in enumerate(METHODS)}}
    sA = out['A_indice_de_saturacao']['M1']['valor']
    out['leitura'] = {'A_M1': 'sem sinal de saturação' if sA >= 0.7 else ('desacelerando' if sA >= 0.3 else 'saturando'),
                      'B_M1': ('efeito de rede: confirmações valem proporcionalmente mais com mais participantes'
                               if (out['B_ganho_relativo_10_menos_5_aplicacoes']['M1']['ic95'] or [0])[0] > 0 else 'sem evidência de efeito de rede além do conteúdo'),
                      'B_retornos_H': ('crescentes: cada aplicação nova acrescenta mais que as primeiras'
                                       if out['B_acerto_somado_por_aplicacao_nova_em_pontos']['H']['de_5_a_10'] >= out['B_acerto_somado_por_aplicacao_nova_em_pontos']['H']['de_1_a_2']
                                       else 'decrescentes: cada aplicação nova acrescenta menos que as primeiras')}
    out['minutos'] = round((time.time() - t0) / 60, 1)
    json.dump(out, open('gc_local_rede_result.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(json.dumps(out, ensure_ascii=False, indent=1)); print('\nPronto. Envie gc_local_rede_result.json.')

if __name__ == '__main__':
    main()
