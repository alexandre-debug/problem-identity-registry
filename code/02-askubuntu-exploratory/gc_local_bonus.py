"""Grande Cérebro, diagnóstico 8b: o que prejudica a 1a sugestão, as relações ou o bônus de popularidade?

Pergunta do GPT Astra. Mesmos embeddings e mesma rede da rodada 7 (V3):
  M0  busca plana
  M1  relações sem bônus (beta = 0)
  M2  relações + bônus de popularidade (beta = 0,02)
A. Sem LLM: quando a 1a sugestão do M2 difere da do M0, qual componente trocou o 1o colocado
   (só o bônus, só as relações ou os dois) e qual foi o tamanho do bônus. Acerto pela família de M1 e M2.
B. Juiz (mesmo prompt e mesmas perguntas da rodada 8; reaproveita os julgamentos já salvos):
   M1 contra M0 e M2 contra M1. Nos casos em que o M2 piorou ou melhorou, de onde veio a mudança.
C. Curva de beta (0; 0,005; 0,01; 0,02; 0,04): que beta cada régua escolheria na calibração.
D. Arquivo cego com 40 pares (1a sugestão do M0 e do M2, em ordem sorteada) para um segundo juiz.

Uso: python3 gc_local_bonus.py --judge gemma4:latest
Saídas: gc_local_bonus_result.json e gc_local_bonus_cegos.txt (envie os dois).
"""
import argparse, gzip, json, os, random, re, sys, time, collections, urllib.request, urllib.error
import numpy as np
from scipy.sparse import csr_matrix

EVAL_FRAC, CALIB_FRAC, B2 = 0.20, 0.10, 0.02
BETAS = [0.0, 0.005, 0.01, 0.02, 0.04]
N_CAL_L, N_CAL_U, N_EV_L, N_EV_U, N_CTRL, NBOOT, N_BLIND = 100, 200, 150, 300, 60, 2000, 40
C1_MIN, C2_MIN = 0.010, -0.03
PROMPT = ('Question A: {a}\n\nQuestion B: {b}\n\nAre A and B about the same technical problem, so that a correct '
          'answer to B would also solve A? Reply with exactly one word: YES or NO.')

def normalize(M): return (M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)).astype(np.float32)
def top5(v): t = np.argpartition(-v, 5)[:5]; return [int(x) for x in t[np.argsort(-v[t])]]
def ci(x): return [round(float(np.percentile(x, 2.5)), 4), round(float(np.percentile(x, 97.5)), 4)]
def bname(b): return 'M0' if b == 'M0' else ('M1' if b == 0 else ('M2' if b == B2 else f'beta={b}'))

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

    # ---------- pontuação (sem LLM) ----------
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
                r = dict(l={'M0': top5(s)}); r['l'].update({b: top5(m1 + b * logdeg) for b in BETAS})
                tops = {r['l'][k][0] for k in r['l']}
                # pontuação de cada 1o colocado: própria, com relações, bônus (beta = 0,02), ligações
                r['sc'] = {x: (round(float(s[x]), 3), round(float(m1[x]), 3), round(float(B2 * logdeg[x]), 3), int(deg[x])) for x in tops}
                gold = earlier(i)
                if gold:
                    fam = set(gold)
                    for x in gold: fam |= set(A.indices[A.indptr[x]:A.indptr[x + 1]].tolist())
                    r['gold'], r['fam'] = gold, fam
                rec[i] = r
        print(f'  {w}: {len(rows)} perguntas pontuadas', flush=True)
    t1 = lambda i, k: rec[i]['l'][k][0]
    def hits(labs, k, key='fam', top=5): return np.array([bool(set(rec[i]['l'][k][:top]) & rec[i][key]) for i in labs], dtype=np.float64)

    # ---------- A. quem trocou o 1o colocado (avaliação, sem LLM) ----------
    pe = proc['avaliacao']; N = pe['n_total']; labs = pe['lab']
    def cause(i):
        a0, a1, a2 = t1(i, 'M0'), t1(i, 0.0), t1(i, B2)
        if a2 == a0: return None
        return 'so_o_bonus' if a1 == a0 else ('so_as_relacoes' if a1 == a2 else 'relacoes_e_bonus')
    partA = {}
    for gname, rows in (('marcadas_todas', labs), ('sem_marcacao_amostra_5000', pe['unl'])):
        cs = collections.Counter(cause(i) for i in rows); ch = sum(v for k, v in cs.items() if k)
        bon = [(rec[i]['sc'][t1(i, B2)][2] - rec[i]['sc'][t1(i, 0.0)][2], rec[i]['sc'][t1(i, 0.0)][1] - rec[i]['sc'][t1(i, B2)][1], rec[i]['sc'][t1(i, B2)][3])
               for i in rows if t1(i, B2) != t1(i, 0.0)]
        partA[gname] = {'M2_troca_a_1a_sugestao_do_M0': round(ch / len(rows), 4),
                        'causa_da_troca': {k: f'{v} ({v / ch:.0%})' for k, v in cs.most_common() if k} if ch else {},
                        'quando_o_bonus_muda_o_1o_colocado': {
                            'casos': len(bon), 'bonus_liquido_mediana': round(float(np.median([b[0] for b in bon])), 3) if bon else None,
                            'correspondencia_sacrificada_mediana': round(float(np.median([b[1] for b in bon])), 3) if bon else None,
                            'ligacoes_do_vencedor_mediana': int(np.median([b[2] for b in bon])) if bon else None}}
    fam = {bname(k): {'familia_top1': round(float(hits(labs, k, 'fam', 1).sum() / N), 4), 'familia_top5': round(float(hits(labs, k).sum() / N), 4),
                      'marcada_top5': round(float(hits(labs, k, 'gold').sum() / N), 4)} for k in ['M0'] + BETAS}
    bt = np.random.default_rng(3); idx = [bt.integers(0, len(labs), len(labs)) for _ in range(NBOOT)]
    def fam_diff(k, ref):
        d = hits(labs, k) - hits(labs, ref); return dict(pontos=round(float(d.sum() / N), 4), ic95=ci([d[ix].sum() / N for ix in idx]))

    # ---------- amostras: as mesmas da rodada 8 ----------
    g = random.Random(29); le, ue = pe['lab'], pe['unl']
    used = set(g.sample(le, 100)) | set(g.sample(ue, 100)) | set(g.sample(le, 60)) | set(g.sample(ue, 60))
    g = random.Random(88)
    CAL_L = g.sample(proc['calibracao']['lab'], N_CAL_L); CAL_U = g.sample(proc['calibracao']['unl'], N_CAL_U)
    EV_L = g.sample([i for i in le if i not in used], N_EV_L); EV_U = g.sample([i for i in ue if i not in used], N_EV_U)
    POS = g.sample([i for i in le if i not in used and i not in EV_L], N_CTRL)
    NEG = g.sample([i for i in ue if i not in used and i not in EV_U], N_CTRL); NEGj = [g.randrange(0, i) for i in NEG]

    # ---------- juiz com cache em disco (o mesmo arquivo da rodada 8) ----------
    cpath = f"gc_cache/juiz_{a.judge.replace(':', '_').replace('/', '_')}.jsonl"; cache = {}
    if os.path.exists(cpath):
        for line in open(cpath, encoding='utf-8'):
            try: d = json.loads(line); cache[(d['a'], d['b'])] = d['v']
            except Exception: pass
    print(f'  juiz: {len(cache)} julgamentos já salvos', flush=True)
    cfile = open(cpath, 'a', encoding='utf-8'); words = lambda i, k=70: ' '.join(texts[i].split()[:k])
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
            out[i] = {m: judge(i, t1(i, m)) for m in ['M0'] + BETAS}
            if (k + 1) % 50 == 0: print(f'  juiz ({label}): {k + 1}/{len(rows)}', flush=True)
        return out
    def wdiff(JL, JU, wL, wU, m, ref):
        grp = lambda J: np.array([float(v[m]) - float(v[ref]) for v in J.values() if v[m] is not None and v[ref] is not None])
        dL, dU = grp(JL), grp(JU); b = np.random.default_rng(5)
        boots = [wL * dL[b.integers(0, len(dL), len(dL))].mean() + wU * dU[b.integers(0, len(dU), len(dU))].mean() for _ in range(NBOOT)]
        return dict(diferenca_ponderada=round(float(wL * dL.mean() + wU * dU.mean()), 4), ic95=ci(boots),
                    discordantes={'marcada': [int((dL < 0).sum()), int((dL > 0).sum())], 'sem_marcacao': [int((dU < 0).sum()), int((dU > 0).sum())]})

    # ---------- C. calibração: que beta cada régua escolheria ----------
    print('juiz: janela de calibração', flush=True)
    JcL, JcU = judge_rows(CAL_L, 'calibração, marcadas'), judge_rows(CAL_U, 'calibração, sem marcação')
    pc = proc['calibracao']; Nc = pc['n_total']; wLc, wUc = len(pc['lab']) / Nc, pc['n_unl'] / Nc
    curve = []
    for b in BETAS:
        curve.append(dict(beta=b, marcada_top5=round(float(hits(pc['lab'], b, 'gold').sum() / Nc), 4),
                          familia_top5=round(float(hits(pc['lab'], b).sum() / Nc), 4),
                          juiz_menos_M0=wdiff(JcL, JcU, wLc, wUc, b, 'M0')['diferenca_ponderada']))
    pick = lambda key: min((c for c in curve if c[key] == max(x[key] for x in curve)), key=lambda c: c['beta'])['beta']
    choice = {'pela_duplicata_marcada (régua da rodada 7)': pick('marcada_top5'), 'pela_familia': pick('familia_top5'), 'pelo_juiz': pick('juiz_menos_M0')}
    print(f'  beta escolhido por régua: {choice}', flush=True)

    # ---------- B. avaliação com o juiz ----------
    print('juiz: janela de avaliação', flush=True)
    JeL, JeU = judge_rows(EV_L, 'avaliação, marcadas'), judge_rows(EV_U, 'avaliação, sem marcação')
    print('juiz: controles', flush=True)
    yP = [v for v in (judge(i, sorted(earlier(i))[0]) for i in POS) if v is not None]
    yN = [v for v in (judge(i, j) for i, j in zip(NEG, NEGj)) if v is not None]
    tot = st['new']
    if tot and st['invalid'] > 0.2 * tot: sys.exit(f'O juiz não respondeu YES/NO em {st["invalid"]} de {tot} julgamentos novos.')
    wL, wU = len(labs) / N, pe['n_unl'] / N
    Je = {**JeL, **JeU}; grp_of = {i: 'marcada' for i in JeL}; grp_of.update({i: 'sem_marcacao' for i in JeU})
    origin = collections.defaultdict(collections.Counter); worse_ex = []
    for i, v in Je.items():
        if None in (v['M0'], v[0.0], v[B2]) or t1(i, B2) == t1(i, 'M0'): continue
        if v['M0'] and not v[B2]:
            o = 'bonus (M1 acerta)' if v[0.0] else ('relacoes (M1 = M2)' if t1(i, 0.0) == t1(i, B2) else 'relacoes_e_bonus (M1 também erra)')
            origin[f'M2_piorou_{grp_of[i]}'][o] += 1; worse_ex.append((i, o))
        elif v[B2] and not v['M0']:
            o = 'relacoes (M1 já acerta)' if v[0.0] else 'bonus (M1 erra)'
            origin[f'M2_melhorou_{grp_of[i]}'][o] += 1
    def show(i, k):
        x = t1(i, k); s_, m_, b_, d_ = rec[i]['sc'][x]
        return {'texto': texts[x][:100], 'propria': s_, 'com_relacoes': m_, 'bonus_que_recebe_no_M2': b_,
                'total_no_M2': round(m_ + b_, 3), 'ligacoes': d_, 'juiz': Je[i][k]}
    g3 = random.Random(5); exs = g3.sample(worse_ex, min(15, len(worse_ex)))
    examples = [{'pergunta': texts[i][:110], 'origem': o, 'M0': show(i, 'M0'), 'M1': show(i, 0.0), 'M2': show(i, B2)} for i, o in exs]

    # ---------- D. arquivo cego para um segundo juiz ----------
    cand = [i for i in list(JeL) + list(JeU) if t1(i, 'M0') != t1(i, B2)]
    blind = random.Random(123).sample(cand, min(N_BLIND, len(cand))); key = []
    with open('gc_local_bonus_cegos.txt', 'w', encoding='utf-8') as f:
        f.write('Para cada pergunta: a sugestão A resolve? a sugestão B resolve? (ordem sorteada)\n')
        for k, i in enumerate(blind, 1):
            flip = random.Random(1000 + k).random() < 0.5; A_, B_ = (B2, 'M0') if flip else ('M0', B2)
            f.write(f'\n#{k} PERGUNTA: {words(i, 90)}\n  A: {words(t1(i, A_), 90)}\n  B: {words(t1(i, B_), 90)}\n')
            key.append({'n': k, 'A': bname(A_), 'B': bname(B_), 'grupo': grp_of[i], 'gemma_M0': Je[i]['M0'], 'gemma_M2': Je[i][B2],
                        'M0_na_familia_marcada': (t1(i, 'M0') in rec[i]['fam']) if 'fam' in rec[i] else None,
                        'M2_na_familia_marcada': (t1(i, B2) in rec[i]['fam']) if 'fam' in rec[i] else None})

    tpr, fpr = float(np.mean(yP)), float(np.mean(yN))
    d10 = wdiff(JeL, JeU, wL, wU, 0.0, 'M0'); f10 = fam_diff(0.0, 'M0')
    out = {'modelo': a.judge, 'julgamentos_novos': tot, 'respostas_invalidas_novas': st['invalid'],
           'A_quem_troca_o_1o_colocado': partA,
           'acerto_sem_llm_avaliacao': fam,
           'familia_top5_diferencas': {'M1_menos_M0': f10, 'M2_menos_M0': fam_diff(B2, 'M0'), 'M2_menos_M1': fam_diff(B2, 0.0)},
           'B_juiz_1a_sugestao_bruto_ponderado': {'M1_menos_M0': d10, 'M2_menos_M0': wdiff(JeL, JeU, wL, wU, B2, 'M0'),
                                                  'M2_menos_M1 (efeito do bonus)': wdiff(JeL, JeU, wL, wU, B2, 0.0)},
           'B_origem_das_mudancas_do_M2': {k: dict(v) for k, v in sorted(origin.items())},
           'C_curva_de_beta_calibracao': curve, 'C_beta_escolhido_por_regua': choice,
           'C_curva_de_beta_avaliacao_descritiva': [{'beta': b, 'familia_top5_menos_M0': fam_diff(b, 'M0')['pontos'],
                                                     'juiz_menos_M0': wdiff(JeL, JeU, wL, wU, b, 'M0')['diferenca_ponderada']} for b in BETAS],
           'M1_nos_criterios_da_rodada_8': {'C1_familia': f10['pontos'] >= C1_MIN and f10['ic95'][0] > 0, 'C2_juiz': d10['ic95'][0] >= C2_MIN},
           'juiz': {'sensibilidade': round(tpr, 3), 'falsos_positivos': round(fpr, 3)},
           'exemplos_M2_piorou': examples,
           'chave_cegos': key,
           'minutos': round((time.time() - t0) / 60, 1)}
    json.dump(out, open('gc_local_bonus_result.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in out.items() if k not in ('exemplos_M2_piorou', 'chave_cegos')}, ensure_ascii=False, indent=1))
    print('\nPronto. Envie gc_local_bonus_result.json e gc_local_bonus_cegos.txt.')

if __name__ == '__main__':
    main()
