"""Grande Cérebro, Rodada 10, etapa B: calibração do portão (só dados de recuperação do AskUbuntu, sem LLM).

Rode na mesma pasta do gc_conf.py e do gc_r9.py (usa gc_data, gc_cache e gc_conf_result.json).
Não precisa do Ollama. Leva alguns minutos (recalcula as sugestões e lê o Posts.xml).

Uso:    python3 gc_r10_portao.py
Saída:  r10_portao_resultado.json (só números) -> ENVIE

Regra congelada no protocolo em 30/09/2026, 03h20:
  método liberado pelo portão: H1 (M0 intercalado com M1, sem popularidade)
  sinal S(q) = max m1(d) - s(1a sugestão de M0), sobre as discussões d do top-5 de H1 fora do top-5 de M0
  grade de tau: -0,10 a +0,10 de 0,02 em 0,02; o portão abre se S(q) >= tau
  metades: Random(1010); desenvolvimento escolhe tau, verificação confere sem reajuste
  tau admissível: fração de ganhos >= 2x a de H1 sem portão (na mesma metade), ganhos > perdas, cobertura >= 2%
  escolha: o tau admissível de maior cobertura; nenhum admissível -> portão não calibrável
"""
import argparse, collections, gzip, hashlib, json, os, random, sys, time
import numpy as np
from scipy.sparse import csr_matrix
import gc_conf as G

VERSAO = 'r10-B-v1'
TAUS = [round(-0.10 + 0.02 * k, 2) for k in range(11)]
SEED_SPLIT, FATOR_FRACAO, COBERTURA_MIN = 1010, 2.0, 0.02
OUT = 'r10_portao_resultado.json'

def file_sha(path): return hashlib.sha256(open(path, 'rb').read()).hexdigest()

def load(embed):
    qpath, lpath, mpath = 'gc_data/au24_perguntas.jsonl.gz', 'gc_data/au24_duplicatas.tsv', 'gc_data/au24_meta.json'
    for p in (qpath, lpath, mpath, 'gc_conf_result.json'):
        if not os.path.exists(p): sys.exit(f'Falta {p}. Rode na mesma pasta do gc_conf.py, depois da confirmação.')
    meta = json.load(open(mpath)); res = json.load(open('gc_conf_result.json'))
    if meta.get('preproc') != G.PREPROC or meta.get('T0') != G.T0: sys.exit('Os dados lidos não correspondem a este gc_conf.py.')
    ids, dates, texts = [], [], []
    for line in gzip.open(qpath, 'rt', encoding='utf-8'): i, d, t = json.loads(line); ids.append(i); dates.append(d); texts.append(t)
    data_sha = G.sha(f'{i}|{d}|{t}' for i, d, t in zip(ids, dates, texts))
    if data_sha != res['reproducao']['dados_sha256']: sys.exit('Os dados não são os mesmos da confirmação (SHA-256 diferente).')
    pos = {q: k for k, q in enumerate(ids)}; n = len(ids)
    dups = collections.defaultdict(set); mem_pairs = set()
    for line in open(lpath):
        p, q, d = line.rstrip('\n').split('\t'); p, q = int(p), int(q)
        if p in pos and q in pos and p != q:
            dups[p].add(q); dups[q].add(p); x, y = sorted((pos[p], pos[q]))
            if d < G.T0 and dates[y] < G.T0: mem_pairs.add((x, y))
    e0 = next((k for k, d in enumerate(dates) if d >= G.T0), n)
    earlier = lambda i: {pos[s] for s in dups.get(ids[i], ()) if pos[s] < i}
    lab = [i for i in range(e0, n) if earlier(i)]; unl_all = [i for i in range(e0, n) if not earlier(i)]
    N = n - e0; unl = random.Random(2024).sample(unl_all, min(G.N_UNL, len(unl_all)))
    tag = embed.replace(':', '_').replace('/', '_'); qrows = sorted(set(lab) | set(unl)); qidx = {i: j for j, i in enumerate(qrows)}
    pre_q, pre_d = ('search_query: ', 'search_document: ') if 'nomic' in embed else ('', '')
    emb = {}
    for name, rows_, pre in (('q', qrows, pre_q), ('d', range(n), pre_d)):
        path = f'gc_cache/au24_{name}_{tag}.npy'
        if not os.path.exists(path + '.meta.json'): sys.exit(f'Faltam os embeddings {path}.')
        mm = json.load(open(path + '.meta.json'))
        if mm['linhas'] != len(rows_) or mm['textos_sha256'] != G.sha(pre + texts[i] for i in rows_) or int(open(path + '.done').read()) != len(rows_):
            sys.exit(f'Os embeddings {path} não correspondem aos dados da confirmação.')
        emb[name] = np.asarray(np.load(path, mmap_mode='r'), dtype=np.float32)
    return dict(ids=ids, n=n, e0=e0, N=N, lab=lab, unl=unl, earlier=earlier, mem_pairs=mem_pairs, Q=emb['q'], D=emb['d'],
                qidx=qidx, data_sha=data_sha)

def signals(S):
    n, Q, D, qidx = S['n'], S['Q'], S['D'], S['qidx']
    P = sorted(S['mem_pairs'])
    A = csr_matrix((np.ones(2 * len(P), dtype=np.float32), ([x for x, y in P] + [y for x, y in P], [y for x, y in P] + [x for x, y in P])), shape=(n, n))
    A.sum_duplicates(); A.data[:] = 1
    deg = np.diff(A.indptr).astype(np.float32); H = np.where(deg > 0)[0]; starts = A.indptr[H]
    hpos = np.full(n, -1, dtype=np.int64); hpos[H] = np.arange(len(H))
    C = G.normalize(D[H] + np.asarray(A[H] @ D))
    out = {}; rows_eval = S['lab'] + S['unl']; t0 = time.time()
    for b0 in range(0, len(rows_eval), 128):
        R = rows_eval[b0:b0 + 128]; QV = Q[[qidx[i] for i in R]]; SB = QV @ D.T
        for j, i in enumerate(R):
            s = SB[j]; s[i:] = -np.inf
            nb = np.maximum.reduceat(s[A.indices], starts); ce = C @ QV[j]
            m1 = s.copy(); m1[H] = np.maximum(np.maximum(m1[H], nb), ce)
            m1[H] = np.where(np.isfinite(s[H]), m1[H], -np.inf)
            M0 = G.top5(s); M1 = G.top5(m1); H1 = G.inter(M0, M1); new = [d for d in H1 if d not in set(M0)]
            r = {'novas': len(new)}
            if new:
                best = max(new, key=lambda d: m1[d]); r['S'] = float(m1[best] - s[M0[0]])
                k = hpos[best]
                if k < 0: r['fonte'] = 'direta'
                else:
                    comp = {'direta': float(s[best]), 'duplicata': float(nb[k]), 'centro': float(ce[k])}
                    r['fonte'] = max(comp, key=comp.get)
            g = S['earlier'](i)
            if g:
                fs = set(g)
                for x in g: fs |= set(A.indices[A.indptr[x]:A.indptr[x + 1]].tolist())
                f0, f1 = bool(fs & set(M0)), bool(fs & set(H1))
                r['grupo'] = 'ganho' if f1 and not f0 else ('perda' if f0 and not f1 else 'neutro')
            out[i] = r
        if (b0 // 128) % 20 == 0: print(f'  {min(b0 + 128, len(rows_eval))}/{len(rows_eval)}', flush=True)
    return out

def accepted(S):
    import gc_r9 as R9
    found = R9.find_xml(('Posts.xml',))
    U = set(S['ids'][i] for i in S['lab'] + S['unl']); acc, ans = {}, collections.defaultdict(set)
    print('  lendo respostas aceitas (Posts.xml)', flush=True)
    for r in G.rows(found['Posts.xml']):
        t = r.get('PostTypeId')
        if t == '1':
            q = int(r['Id'])
            if q in U and r.get('AcceptedAnswerId'): acc[q] = int(r['AcceptedAnswerId'])
        elif t == '2':
            p = int(r.get('ParentId', -1))
            if p in U: ans[p].add(int(r['Id']))
    return {q for q, a in acc.items() if a in ans.get(q, ())}

def table(rows, lab_set, acc_ok, ids, sc, tau):
    """rows: índices de uma metade. tau=None -> H1 sem portão (abre sempre que há discussão nova)."""
    opened = lambda r: r['novas'] > 0 and (tau is None or r['S'] >= tau - 1e-12)
    c = collections.Counter(); fontes = collections.Counter()
    for i, r in rows:
        o = opened(r); m = i in lab_set; a = ids[i] in acc_ok
        if m:
            c['marcadas'] += 1
            if o: c['abertas_' + r['grupo']] += 1
        else:
            c['sem_marcacao'] += 1; c['sem_marcacao_abertas'] += o
        if a:
            c['aceitas_marcadas' if m else 'aceitas_sem_marcacao'] += 1
            if o: c['aceitas_abertas_marcadas' if m else 'aceitas_abertas_sem_marcacao'] += 1
        if o: fontes[r.get('fonte')] += 1
    ab = c['abertas_ganho'] + c['abertas_perda'] + c['abertas_neutro']
    den = c['aceitas_marcadas'] + sc * c['aceitas_sem_marcacao']
    cob = (c['aceitas_abertas_marcadas'] + sc * c['aceitas_abertas_sem_marcacao']) / den if den else 0.0
    return {'tau': tau, 'abertas_marcadas': ab, 'ganho': c['abertas_ganho'], 'perda': c['abertas_perda'], 'neutro': c['abertas_neutro'],
            'fracao_de_ganhos': round(c['abertas_ganho'] / ab, 4) if ab else None, 'cobertura': round(cob, 4),
            'abertas_sem_marcacao': c['sem_marcacao_abertas'], 'sem_marcacao': c['sem_marcacao'], 'marcadas': c['marcadas'],
            'aceitas_abertas': {'marcadas': c['aceitas_abertas_marcadas'], 'sem_marcacao': c['aceitas_abertas_sem_marcacao']},
            'fonte_do_sinal_nas_aberturas': dict(fontes)}

def admissible(t, base):
    f = t['fracao_de_ganhos']
    conds = {'fracao_>=_2x_H1_sem_portao': bool(f is not None and base is not None and f >= FATOR_FRACAO * base),
             'ganhos_>_perdas': t['ganho'] > t['perda'], 'cobertura_>=_2%': t['cobertura'] >= COBERTURA_MIN}
    return all(conds.values()), conds

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--embed', default='nomic-embed-text'); a = ap.parse_args(); t_start = time.time()
    print('1. dados da confirmação', flush=True); S = load(a.embed)
    print('2. sinal do portão para cada pergunta avaliada', flush=True); sig = signals(S)
    print('3. respostas aceitas', flush=True); acc_ok = accepted(S)
    U = sorted(S['lab'] + S['unl']); r = random.Random(SEED_SPLIT); shuffled = U[:]; r.shuffle(shuffled)
    half = {'desenvolvimento': set(shuffled[:len(U) // 2]), 'verificacao': set(shuffled[len(U) // 2:])}
    lab_set = set(S['lab']); sc = (S['N'] - len(S['lab'])) / max(len(S['unl']), 1); ids = S['ids']
    res = {}
    for name, hs in half.items():
        rows = [(i, sig[i]) for i in U if i in hs]
        base = table(rows, lab_set, acc_ok, ids, sc, None)
        grid = []
        for tau in TAUS:
            t = table(rows, lab_set, acc_ok, ids, sc, tau); ok, conds = admissible(t, base['fracao_de_ganhos'])
            grid.append({**t, 'admissivel': ok, 'condicoes': conds})
        res[name] = {'H1_sem_portao': base, 'grade': grid}
    dev = res['desenvolvimento']['grade']; adm = [t for t in dev if t['admissivel']]
    chosen = max(adm, key=lambda t: (t['cobertura'], t['fracao_de_ganhos'] or 0, -t['tau']))['tau'] if adm else None
    ver = None
    if chosen is not None:
        vt = next(t for t in res['verificacao']['grade'] if t['tau'] == chosen)
        ver = {'tau': chosen, 'admissivel_na_verificacao': vt['admissivel'], 'condicoes': vt['condicoes']}
    out = {'versao': VERSAO,
           'regra': {'taus': TAUS, 'fator_fracao': FATOR_FRACAO, 'cobertura_minima': COBERTURA_MIN, 'semente_metades': SEED_SPLIT,
                     'escolha': 'tau admissivel de maior cobertura na metade de desenvolvimento'},
           'metades': {k: {'perguntas': len(v), 'marcadas': sum(1 for i in v if i in lab_set)} for k, v in half.items()},
           'resultado': {'portao_calibravel': chosen is not None, 'tau_escolhido': chosen,
                         'verificacao': ver, 'calibracao_estavel': bool(ver and ver['admissivel_na_verificacao']),
                         'consequencia': ('etapa C confirmatoria' if ver and ver['admissivel_na_verificacao'] else
                                          ('etapa C so exploratoria (calibracao nao estavel)' if chosen is not None else 'etapa C nao roda (portao nao calibravel)'))},
           'tabelas': res,
           'reproducao': {'dados_sha256': S['data_sha'], 'script_sha256': file_sha(os.path.abspath(__file__)),
                          'minutos': round((time.time() - t_start) / 60, 1)}}
    json.dump(out, open(OUT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(json.dumps(out['resultado'], ensure_ascii=False, indent=1))
    print(f'\nPronto. Envie {OUT} (só números).')

if __name__ == '__main__':
    main()
