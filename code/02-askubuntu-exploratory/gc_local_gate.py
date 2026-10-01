"""Grande Cérebro, rodada 8: portão de familiaridade (roda na SUA máquina).

Hipótese: usar a rede de ligações confirmadas só quando a pergunta nova pertence de fato a uma
família mantém o ganho de família do M2 sem piorar a primeira sugestão.

Métodos (condição V3, mesma rede e embeddings da rodada 7):
  M0     busca plana.
  M2     rede em toda pergunta (beta = 0,02, como na rodada 7).
  G(tau) caso parecido + família, com portão: as 5 sugestões intercalam M0 e M2. A 1a vem do M2 só
         se a evidência da rede para ela, SEM o bônus de peso, supera a similaridade da 1a sugestão
         plana por pelo menos tau (M2-1, M0-1, M2-2, ...); senão vem do M0 (M0-1, M2-1, M0-2, ...).
         tau é escolhido só na janela de calibração.
  H      = G sem portão (tau infinito): M0-1, M2-1, M0-2, M2-2, ... (a 1a sugestão é sempre a do M0).

Medidas: acerto pela família (sem LLM, todas as perguntas marcadas) e juiz LLM local na 1a
sugestão, em amostras NOVAS (exclui as 320 usadas no juiz comparativo). Critérios no protocolo.

Uso: python3 gc_local_gate.py --judge gemma4:latest
Retomável: os julgamentos ficam em gc_cache/juiz_<modelo>.jsonl. Saída: gc_local_gate_result.json.
"""
import argparse, gzip, json, os, random, re, sys, time, collections, urllib.request, urllib.error
import numpy as np
from scipy.sparse import csr_matrix

EVAL_FRAC, CALIB_FRAC, BETA = 0.20, 0.10, 0.02
TAUS = [float('-inf'), -0.02, 0.0, 0.02, 0.04, 0.06, 0.08, 0.10, float('inf')]
N_CAL_L, N_CAL_U, N_EV_L, N_EV_U, N_CTRL, NBOOT = 100, 200, 150, 300, 60, 2000
C1_MIN, C2_MIN = 0.010, -0.03
PROMPT = ('Question A: {a}\n\nQuestion B: {b}\n\nAre A and B about the same technical problem, so that a correct '
          'answer to B would also solve A? Reply with exactly one word: YES or NO.')

def normalize(M): return (M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)).astype(np.float32)
def top5(v): t = np.argpartition(-v, 5)[:5]; return [int(x) for x in t[np.argsort(-v[t])]]
def ci(x): return [round(float(np.percentile(x, 2.5)), 4), round(float(np.percentile(x, 97.5)), 4)]
def tau_name(t): return '1a_sempre_da_rede' if t == float('-inf') else ('1a_sempre_plana(H)' if t == float('inf') else f'{t:+.2f}')

def post(host, payload):
    req = urllib.request.Request(host + '/api/generate', data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=600) as r: return json.loads(r.read())

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
    for f, m in ((f'gc_cache/support_q_{tag}.npy', len(qrows)), (f'gc_cache/support_d_{tag}.npy', n)):
        if not os.path.exists(f + '.done') or int(open(f + '.done').read()) != m: sys.exit(f'Faltam os embeddings em {f}.')
    Q = np.asarray(np.load(f'gc_cache/support_q_{tag}.npy', mmap_mode='r'), dtype=np.float32)
    D = np.asarray(np.load(f'gc_cache/support_d_{tag}.npy', mmap_mode='r'), dtype=np.float32)

    # ---------- pontuação de todas as perguntas das duas janelas (sem LLM) ----------
    rec = {}
    for w, cut in (('calibracao', c0), ('avaliacao', e0)):
        P = [p for p in pairs if p[1] < cut]
        A = csr_matrix((np.ones(2 * len(P), dtype=np.float32), ([x for x, y in P] + [y for x, y in P], [y for x, y in P] + [x for x, y in P])), shape=(n, n))
        A.sum_duplicates(); A.data[:] = 1
        deg = np.diff(A.indptr).astype(np.float32); H = np.where(deg > 0)[0]; starts = A.indptr[H]
        C = normalize(D[H] + np.asarray(A[H] @ D)); logdeg = np.log1p(deg)
        rows = proc[w]['lab'] + proc[w]['unl']
        for b0 in range(0, len(rows), 256):
            R = rows[b0:b0 + 256]; QV = Q[[qidx[i] for i in R]]; SB = QV @ D.T
            for j, i in enumerate(R):
                s = SB[j]; s[i:] = -np.inf
                m1 = s.copy(); m1[H] = np.maximum(np.maximum(m1[H], np.maximum.reduceat(s[A.indices], starts)), C @ QV[j])
                m1[H] = np.where(np.isfinite(s[H]), m1[H], -np.inf)
                l0 = top5(s); l2 = top5(m1 + BETA * logdeg)
                r = dict(l0=l0, l2=l2, gate=float(m1[l2[0]] - s[l0[0]]))
                gold = earlier(i)
                if gold:
                    fam = set(gold)
                    for x in gold: fam |= set(A.indices[A.indptr[x]:A.indptr[x + 1]].tolist())
                    r['gold'], r['fam'] = gold, fam
                rec[i] = r
        print(f'  {w}: {len(rows)} perguntas pontuadas', flush=True)

    def lst(i, m, tau=None):
        r = rec[i]
        if m == 'M0': return r['l0']
        if m == 'M2': return r['l2']
        if m == 'H': tau = float('inf')
        first, other = (r['l2'], r['l0']) if r['gate'] >= tau else (r['l0'], r['l2'])
        out = []
        for x in [v for pair in zip(first, other) for v in pair]:
            if x not in out: out.append(x)
        return out[:5]
    def fam_hits(labs, m, tau=None, k=5, key='fam'):
        return np.array([bool(set(lst(i, m, tau)[:k]) & rec[i][key]) for i in labs], dtype=np.float64)

    # ---------- amostras do juiz (novas; exclui as do juiz comparativo) ----------
    g = random.Random(29); le, ue = proc['avaliacao']['lab'], proc['avaliacao']['unl']
    used = set(g.sample(le, 100)) | set(g.sample(ue, 100)) | set(g.sample(le, 60)) | set(g.sample(ue, 60))
    g = random.Random(88)
    CAL_L = g.sample(proc['calibracao']['lab'], N_CAL_L); CAL_U = g.sample(proc['calibracao']['unl'], N_CAL_U)
    EV_L = g.sample([i for i in le if i not in used], N_EV_L); EV_U = g.sample([i for i in ue if i not in used], N_EV_U)
    POS = g.sample([i for i in le if i not in used and i not in EV_L], N_CTRL)
    NEG = g.sample([i for i in ue if i not in used and i not in EV_U], N_CTRL); NEGj = [g.randrange(0, i) for i in NEG]

    # ---------- juiz com cache em disco ----------
    cpath = f"gc_cache/juiz_{a.judge.replace(':', '_').replace('/', '_')}.jsonl"; cache = {}
    if os.path.exists(cpath):
        for line in open(cpath, encoding='utf-8'):
            try: d = json.loads(line); cache[(d['a'], d['b'])] = d['v']
            except Exception: pass
        print(f'  juiz: {len(cache)} julgamentos já salvos', flush=True)
    cfile = open(cpath, 'a', encoding='utf-8'); words = lambda i: ' '.join(texts[i].split()[:70])
    st = dict(shown=0, new=0, invalid=0, think=True)
    def judge(i, j):
        key = (int(ids[i]), int(ids[j]))
        if key in cache: return cache[key]
        payload = {'model': a.judge, 'stream': False, 'prompt': PROMPT.format(a=words(i), b=words(j)), 'options': {'temperature': 0, 'num_predict': 64}}
        if st['think']: payload['think'] = False
        try:
            try: r = post(a.host, payload)
            except urllib.error.HTTPError:
                if not st['think']: raise
                st['think'] = False; payload.pop('think'); r = post(a.host, payload)
        except urllib.error.URLError as e:
            sys.exit(f'O Ollama não respondeu ({e}). Abra o Ollama e rode de novo: os julgamentos já feitos ficam salvos.')
        raw = (r.get('response') or '').strip()
        if st['shown'] < 3: print(f'  resposta crua {st["shown"] + 1}: {raw[:80]!r}', flush=True); st['shown'] += 1
        m = re.search(r'\b(YES|NO)\b', raw.upper()); v = None if m is None else m.group(1) == 'YES'
        st['new'] += 1; st['invalid'] += v is None
        if st['new'] == 20 and st['invalid'] >= 10:
            sys.exit(f'O juiz não respondeu YES/NO em {st["invalid"]} dos primeiros 20 julgamentos. Veja as respostas cruas acima.')
        cache[key] = v
        if v is not None: cfile.write(json.dumps({'a': key[0], 'b': key[1], 'v': v, 'raw': raw[:40]}) + '\n'); cfile.flush()
        return v
    def judge_rows(rows, label):
        out = {}
        for k, i in enumerate(rows):
            r = rec[i]; out[i] = (judge(i, r['l0'][0]), judge(i, r['l2'][0]))
            if (k + 1) % 50 == 0: print(f'  juiz ({label}): {k + 1}/{len(rows)}', flush=True)
        return out

    def weighted_diff(JL, JU, wL, wU, m, tau=None):
        """diferença ponderada da taxa bruta de 'sim' na 1a sugestão: método m menos M0 (pares válidos)."""
        def grp(J):
            d = []
            for i, (v0, v2) in J.items():
                f = lst(i, m, tau)[0]; vf = v0 if f == rec[i]['l0'][0] else v2
                if v0 is not None and vf is not None: d.append(float(vf) - float(v0))
            return np.array(d)
        dL, dU = grp(JL), grp(JU)
        return wL * dL.mean() + wU * dU.mean(), dL, dU
    def boot_diff(dL, dU, wL, wU, seed):
        b = np.random.default_rng(seed)
        return [wL * dL[b.integers(0, len(dL), len(dL))].mean() + wU * dU[b.integers(0, len(dU), len(dU))].mean() for _ in range(NBOOT)]

    # ---------- calibração: escolhe tau ----------
    print('juiz: janela de calibração', flush=True)
    JcL, JcU = judge_rows(CAL_L, 'calibração, marcadas'), judge_rows(CAL_U, 'calibração, sem marcação')
    pc = proc['calibracao']; wLc, wUc = len(pc['lab']) / pc['n_total'], pc['n_unl'] / pc['n_total']
    table = []
    for tau in TAUS:
        fam5 = fam_hits(pc['lab'], 'G', tau).sum() / pc['n_total']; dj, _, _ = weighted_diff(JcL, JcU, wLc, wUc, 'G', tau)
        table.append(dict(tau=tau, familia_top5=fam5, juiz_G_menos_M0=dj))
    ok = [t for t in table if t['juiz_G_menos_M0'] >= 0]
    best = max(ok, key=lambda t: (round(t['familia_top5'], 6), t['tau']))
    TAU = best['tau']; print(f'  tau escolhido: {tau_name(TAU)}', flush=True)

    # ---------- avaliação ----------
    print('juiz: janela de avaliação', flush=True)
    JeL, JeU = judge_rows(EV_L, 'avaliação, marcadas'), judge_rows(EV_U, 'avaliação, sem marcação')
    print('juiz: controles', flush=True)
    yP = [v for v in (judge(i, sorted(earlier(i))[0]) for i in POS) if v is not None]
    yN = [v for v in (judge(i, j) for i, j in zip(NEG, NEGj)) if v is not None]
    tot = st['new']
    if tot and st['invalid'] > 0.2 * tot: sys.exit(f'O juiz não respondeu YES/NO em {st["invalid"]} de {tot} julgamentos novos.')
    pe = proc['avaliacao']; N = pe['n_total']; wL, wU = len(pe['lab']) / N, pe['n_unl'] / N; labs = pe['lab']
    methods = [('M0', None), ('M2', None), ('G', TAU), ('H', None)]
    hits = {(m, key, k): fam_hits(labs, m, t, k, key) for m, t in methods for key in ('fam', 'gold') for k in (1, 5)}
    b = np.random.default_rng(3); idx = [b.integers(0, len(labs), len(labs)) for _ in range(NBOOT)]
    fam = {}
    for m, t in methods:
        fam[m] = {f'{"familia" if key == "fam" else "marcada"}_top{k}': round(float(hits[(m, key, k)].sum() / N), 4) for key in ('fam', 'gold') for k in (1, 5)}
    fam_diff = {}
    for m in ('G', 'H', 'M2'):
        d = hits[(m, 'fam', 5)] - hits[('M0', 'fam', 5)]
        fam_diff[m + '_menos_M0'] = dict(pontos=round(float(d.sum() / N), 4), ic95=ci([d[ix].sum() / N for ix in idx]))
    judge_out = {}
    for m, t in (('M2', None), ('G', TAU)):
        dj, dL, dU = weighted_diff(JeL, JeU, wL, wU, m, t)
        judge_out[m + '_menos_M0'] = dict(diferenca_ponderada=round(float(dj), 4), ic95=ci(boot_diff(dL, dU, wL, wU, 5)),
                                         mudou_a_1a_sugestao={'marcada': int(sum(lst(i, m, t)[0] != rec[i]['l0'][0] for i in JeL)),
                                                              'sem_marcacao': int(sum(lst(i, m, t)[0] != rec[i]['l0'][0] for i in JeU))},
                                         discordantes={'marcada': [int((dL < 0).sum()), int((dL > 0).sum())], 'sem_marcacao': [int((dU < 0).sum()), int((dU > 0).sum())]})
    def raw_yes(J, m, t=None):
        v = [(J[i][0] if lst(i, m, t)[0] == rec[i]['l0'][0] else J[i][1]) for i in J]; v = [x for x in v if x is not None]
        return round(float(np.mean(v)), 3)
    tpr, fpr = float(np.mean(yP)), float(np.mean(yN))
    gate_rate = lambda rows, t: round(float(np.mean([rec[i]['gate'] >= t and rec[i]['l2'][0] != rec[i]['l0'][0] for i in rows])), 4)
    c1 = fam_diff['G_menos_M0']['pontos'] >= C1_MIN and fam_diff['G_menos_M0']['ic95'][0] > 0
    c2 = judge_out['G_menos_M0']['ic95'][0] >= C2_MIN
    diffG = [i for i in list(JeL) + list(JeU) if lst(i, 'G', TAU)[0] != rec[i]['l0'][0]]
    ex = g.sample(diffG, min(12, len(diffG)))
    out = {'modelo': a.judge, 'julgamentos_novos': tot, 'respostas_invalidas_novas': st['invalid'],
           'calibracao': {'tabela': [{'tau': tau_name(t['tau']), 'familia_top5': round(float(t['familia_top5']), 4),
                                      'juiz_G_menos_M0': round(float(t['juiz_G_menos_M0']), 4)} for t in table],
                          'tau_escolhido': tau_name(TAU)},
           'avaliacao': {
               'acerto_sem_llm': fam, 'familia_top5_diferencas': fam_diff,
               'juiz_1a_sugestao_bruto_ponderado': judge_out,
               'juiz_sim_bruto': {gname: {m: raw_yes(J, m, t) for m, t in (('M0', None), ('M2', None), ('G', TAU))}
                                  for gname, J in (('marcada', JeL), ('sem_marcacao', JeU))},
               'portao_troca_a_1a_sugestao': {'marcadas_todas': gate_rate(labs, TAU), 'sem_marcacao_amostra_5000': gate_rate(pe['unl'], TAU)},
               'juiz': {'sensibilidade': round(tpr, 3), 'falsos_positivos': round(fpr, 3)},
               'G_menos_M0_corrigido_pelo_juiz': round(float(judge_out['G_menos_M0']['diferenca_ponderada'] / (tpr - fpr)), 4) if tpr > fpr else None},
           'criterios': {'C1_familia_top5_G_menos_M0_>=1pp_e_IC>0': c1, 'C2_juiz_IC_inferior_>=-0,03': c2, 'rodada_8_passa': c1 and c2},
           'exemplos_G_diferente_de_M0': [{'pergunta': texts[i][:110], 'M0': texts[rec[i]['l0'][0]][:110], 'G': texts[rec[i]['l2'][0]][:110],
                                           'juiz_M0': (JeL.get(i) or JeU.get(i))[0], 'juiz_G': (JeL.get(i) or JeU.get(i))[1]} for i in ex],
           'minutos': round((time.time() - t0) / 60, 1)}
    json.dump(out, open('gc_local_gate_result.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in out.items() if k != 'exemplos_G_diferente_de_M0'}, ensure_ascii=False, indent=1))
    print('\nPronto. Envie gc_local_gate_result.json.')

if __name__ == '__main__':
    main()
