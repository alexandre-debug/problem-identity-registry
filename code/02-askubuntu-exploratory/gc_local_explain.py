"""Grande Cérebro: o que o M2 está reconhecendo? (análise, roda na SUA máquina, depois da rodada 7)

Responde, com os embeddings reais:
  1. Casos em que M2 acertou e a busca plana (M0) errou: qual informação permitiu o acerto
     (ponte por uma duplicata confirmada, centro do grupo, peso de recorrência, pergunta ampla).
  2. As 5 sugestões do M2 são alternativas diferentes ou a mesma família repetida?
  3. Quanto custa a consulta (tempo por pergunta) com e sem a rede de confirmações.
Não muda nenhum resultado da rodada 7: usa a mesma configuração (V3, beta = 0,02).

Uso: python3 gc_local_explain.py
Saídas: gc_local_explain_result.json e gc_local_explain_exemplos.txt (envie os dois).
"""
import gzip, json, random, sys, time, collections, os
import numpy as np
from scipy.sparse import csr_matrix

EVAL_FRAC, CALIB_FRAC, TOPK, N_EXAMPLES = 0.20, 0.10, 5, 25
BETA = float(os.environ.get('GC_BETA', 0.02))   # 0,02 = escolhido na calibração da rodada 7

def normalize(M): return (M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)).astype(np.float32)
def top5(s): t = np.argpartition(-s, TOPK)[:TOPK]; return t[np.argsort(-s[t])]

def main():
    tag = (sys.argv[1] if len(sys.argv) > 1 else 'nomic-embed-text').replace(':', '_').replace('/', '_')
    ids, texts = [], []
    for line in gzip.open('gc_data/text_tokenized.txt.gz', 'rt', encoding='utf-8'):
        p = line.rstrip('\n').split('\t'); ids.append(int(p[0])); texts.append((p[1] if len(p) > 1 else '', p[2] if len(p) > 2 else ''))
    order = np.argsort(ids); ids = np.array(ids)[order]; texts = [texts[i] for i in order]; title = [t[0] for t in texts]
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
        proc[w] = dict(lab=lab, unl=rng.sample(unl, min(k, len(unl))), n_total=len(rg))
    qrows = sorted({i for w in proc for i in proc[w]['lab'] + proc[w]['unl']}); qidx = {i: j for j, i in enumerate(qrows)}
    for f, m in ((f'gc_cache/support_q_{tag}.npy', len(qrows)), (f'gc_cache/support_d_{tag}.npy', n)):
        if not os.path.exists(f + '.done') or int(open(f + '.done').read()) != m: sys.exit(f'Faltam os embeddings em {f}.')
    Q = np.asarray(np.load(f'gc_cache/support_q_{tag}.npy', mmap_mode='r'), dtype=np.float32)
    D = np.asarray(np.load(f'gc_cache/support_d_{tag}.npy', mmap_mode='r'), dtype=np.float32)

    P = [p for p in pairs if p[1] < e0]
    A = csr_matrix((np.ones(2 * len(P), dtype=np.float32), ([a for a, b in P] + [b for a, b in P], [b for a, b in P] + [a for a, b in P])), shape=(n, n))
    A.sum_duplicates(); A.data[:] = 1
    deg = np.diff(A.indptr).astype(np.float32); H = np.where(deg > 0)[0]; starts = A.indptr[H]
    C = normalize(D[H] + np.asarray(A[H] @ D)); hpos = {h: k for k, h in enumerate(H)}; logdeg = np.log1p(deg)
    broad = set(np.argsort(-deg)[:50])                      # as 50 perguntas mais ligadas = "guarda-chuva"
    neigh = lambda x: set(A.indices[A.indptr[x]:A.indptr[x + 1]])
    same_family = lambda x, y: y in neigh(x) or bool(neigh(x) & neigh(y))

    lab = proc['avaliacao']['lab']; rows = lab + proc['avaliacao']['unl']
    gold = {i: earlier(i) for i in lab}
    rec, t_m0, t_m2 = {}, [], []
    mech = collections.Counter(); rows_ex = []
    for b0 in range(0, len(rows), 256):
        R = rows[b0:b0 + 256]; QV = Q[[qidx[i] for i in R]]; SB = QV @ D.T
        for j, i in enumerate(R):
            t = time.perf_counter(); s = SB[j].copy(); s[i:] = -np.inf; m0 = top5(s); t_m0.append(time.perf_counter() - t)
            t = time.perf_counter()
            nb = np.maximum.reduceat(s[A.indices], starts); cs = C @ QV[j]
            m1 = s.copy(); m1[H] = np.maximum(np.maximum(m1[H], nb), cs); m1[H] = np.where(np.isfinite(s[H]), m1[H], -np.inf)
            m2s = m1 + BETA * logdeg; m2 = top5(m2s); t_m2.append(time.perf_counter() - t)
            r = dict(m0=[int(x) for x in m0], m1=[int(x) for x in top5(m1)], m2=[int(x) for x in m2])
            if i in gold and set(r['m2']) & gold[i] and not set(r['m0']) & gold[i]:
                # ganho do M2 sobre a busca plana: registra de onde veio a pontuação da pergunta recuperada
                h = next(x for x in r['m2'] if x in gold[i])
                own = float(s[h]); nbrs = sorted(neigh(h), key=lambda x: -s[x]); bridge = int(nbrs[0]) if nbrs else None
                nb_s = float(s[bridge]) if bridge is not None else -1.0; c_s = float(cs[hpos[h]]) if h in hpos else -1.0
                via = 'ponte (duplicata confirmada)' if nb_s >= max(own, c_s) and nb_s > own else ('centro do grupo' if c_s > own else 'própria pergunta')
                weight_decisive = h not in set(r['m1'])
                mech[via] += 1; mech['peso foi decisivo'] += weight_decisive; mech['pergunta guarda-chuva (top-50 em ligações)'] += h in broad
                rows_ex.append(dict(i=i, h=h, bridge=bridge, own=own, nb=nb_s, cen=c_s, bonus=float(BETA * logdeg[h]), deg=int(deg[h]),
                                    via=via, peso=weight_decisive, broad=h in broad))
            rec[i] = r
        print(f'  {min(b0 + 256, len(rows))}/{len(rows)}', flush=True)

    hitm0 = {i: bool(set(rec[i]['m0']) & gold[i]) for i in lab}; hitm2 = {i: bool(set(rec[i]['m2']) & gold[i]) for i in lab}
    wins = [i for i in lab if hitm2[i] and not hitm0[i]]; losses = [i for i in lab if hitm0[i] and not hitm2[i]]
    fam = collections.Counter(); fam_hit = collections.Counter(); fam_miss = collections.Counter()
    for i in rows:
        t5 = rec[i]['m2']
        biggest = max(sum(same_family(x, y) or x == y for y in t5) for x in t5)
        fam[min(biggest, 5)] += 1
        if i in gold: (fam_hit if hitm2[i] else fam_miss)[min(biggest, 5)] += 1
    N = proc['avaliacao']['n_total']
    out = {'config': {'metodo': 'M2', 'beta': BETA, 'condicao': 'V3'},
           'acertos_M2_V3': round(sum(hitm2.values()) / N, 4), 'acertos_M0_V3': round(sum(hitm0.values()) / N, 4),
           'M2_acerta_e_M0_erra': len(wins), 'M0_acerta_e_M2_erra': len(losses),
           'mecanismo_nos_ganhos': {k: f'{v} ({v / len(wins):.0%})' for k, v in mech.items()} if wins else {},
           'diversidade_das_5_sugestoes_M2': {
               'maior_familia_entre_as_5_todas': {str(k): v for k, v in sorted(fam.items())},
               'quando_acerta': {str(k): v for k, v in sorted(fam_hit.items())},
               'quando_erra': {str(k): v for k, v in sorted(fam_miss.items())}},
           'custo_por_pergunta_ms': {'M0_mediana': round(float(np.median(t_m0)) * 1000, 2), 'M2_mediana': round(float(np.median(t_m2)) * 1000, 2),
                                     'ligacoes_na_memoria': len(P), 'perguntas_com_ligacoes': int(len(H))}}
    json.dump(out, open('gc_local_explain_result.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    g = random.Random(11); sample = g.sample(rows_ex, min(N_EXAMPLES, len(rows_ex)))
    with open('gc_local_explain_exemplos.txt', 'w', encoding='utf-8') as f:
        f.write(f'Casos sorteados em que M2 acertou e a busca plana errou ({len(sample)} de {len(wins)})\n')
        for k, e in enumerate(sample, 1):
            i = e['i']
            f.write(f'\n#{k}  PERGUNTA NOVA: {title[i]}\n')
            f.write('    busca plana sugeriu:\n' + ''.join(f'      - {title[x]}\n' for x in rec[i]['m0']))
            f.write(f"    M2 recuperou: {title[e['h']]}  (ligações validadas: {e['deg']}{', guarda-chuva' if e['broad'] else ''})\n")
            if e['bridge'] is not None: f.write(f"    ponte (duplicata confirmada dela): {title[e['bridge']]}\n")
            f.write(f"    similaridade própria {e['own']:.3f} | pela ponte {e['nb']:.3f} | pelo centro {e['cen']:.3f} | bônus de peso {e['bonus']:.3f}\n")
            f.write(f"    mecanismo: {e['via']}{'; peso foi decisivo' if e['peso'] else ''}\n")
    print(json.dumps(out, ensure_ascii=False, indent=1)); print('\nPronto. Envie gc_local_explain_result.json e gc_local_explain_exemplos.txt.')

if __name__ == '__main__':
    main()
