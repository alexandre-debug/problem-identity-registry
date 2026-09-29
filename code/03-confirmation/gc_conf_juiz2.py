"""Grande Cérebro: SEGUNDO JUIZ (Claude), às cegas, para a questão em aberto da confirmação (P2).

Etapa complementar pré-registrada. NÃO muda o resultado oficial da confirmação (INCONCLUSIVO).
Rode na mesma pasta do gc_conf.py, depois da confirmação (usa gc_data, gc_cache e gc_conf_result.json).
Não precisa do Ollama.

Passo 1:  python3 gc_conf_juiz2.py gerar
          cria juiz2_itens.txt               -> ENVIE ESTE ao Claude
          cria juiz2_chave_NAO_ENVIAR.json   -> NUNCA envie
Passo 2:  salve na pasta o juiz2_rotulos.json que o Claude devolver e rode:
          python3 gc_conf_juiz2.py comparar juiz2_rotulos.json
          cria juiz2_resultado.json (só números agregados) -> envie este
"""
import argparse, collections, gzip, hashlib, json, os, random, sys
import numpy as np
from scipy.sparse import csr_matrix
import gc_conf as G

CAP, N_POS, N_NEG, WORDS, NBOOT = 250, 40, 40, 90, 2000
KEY, ITEMS, OUT = 'juiz2_chave_NAO_ENVIAR.json', 'juiz2_itens.txt', 'juiz2_resultado.json'
RUBRICA = ('Uma resposta correta à pergunta B resolveria o problema da pergunta A? Responda SIM se o problema técnico '
           'central é o mesmo e a solução de B se aplicaria a A, mesmo com pequenas diferenças de versão ou de hardware; '
           'NÃO caso contrário.')

def file_sha(path): return hashlib.sha256(open(path, 'rb').read()).hexdigest()

def rebuild(embed):
    """Reconstrói exatamente as amostras e as 1as sugestões da confirmação, conferindo tudo por SHA-256."""
    qpath, lpath, mpath = 'gc_data/au24_perguntas.jsonl.gz', 'gc_data/au24_duplicatas.tsv', 'gc_data/au24_meta.json'
    for p in (qpath, lpath, mpath, 'gc_conf_result.json'):
        if not os.path.exists(p): sys.exit(f'Falta {p}. Rode na mesma pasta do gc_conf.py, depois da confirmação.')
    meta = json.load(open(mpath)); res = json.load(open('gc_conf_result.json'))
    if meta.get('preproc') != G.PREPROC or meta.get('T0') != G.T0: sys.exit('Os dados lidos não correspondem a este gc_conf.py.')
    ids, dates, texts = [], [], []
    for line in gzip.open(qpath, 'rt', encoding='utf-8'): i, d, t = json.loads(line); ids.append(i); dates.append(d); texts.append(t)
    if G.sha(f'{i}|{d}|{t}' for i, d, t in zip(ids, dates, texts)) != res['reproducao']['dados_sha256']:
        sys.exit('Os dados não são os mesmos da confirmação (SHA-256 diferente).')
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
    # amostras do juiz, na mesma ordem de sorteio do gc_conf
    g = random.Random(2025)
    JL = g.sample(lab, min(G.N_JL, len(lab))); JU = g.sample(unl, min(G.N_JU, len(unl)))
    POS = g.sample([i for i in lab if i not in set(JL)], G.N_CTRL); NEG = g.sample([i for i in unl if i not in set(JU)], G.N_CTRL)
    NEGj = [g.randrange(0, i) for i in NEG]
    # embeddings da confirmação, conferidos
    tag = embed.replace(':', '_').replace('/', '_'); qrows = sorted(set(lab) | set(unl)); qidx = {i: j for j, i in enumerate(qrows)}
    pre_q, pre_d = ('search_query: ', 'search_document: ') if 'nomic' in embed else ('', '')
    mats = {}
    for name, rows_, pre in (('q', qrows, pre_q), ('d', range(n), pre_d)):
        path = f'gc_cache/au24_{name}_{tag}.npy'
        if not os.path.exists(path + '.meta.json'): sys.exit(f'Faltam os embeddings {path}.')
        mm = json.load(open(path + '.meta.json'))
        if mm['linhas'] != len(rows_) or mm['textos_sha256'] != G.sha(pre + texts[i] for i in rows_) or int(open(path + '.done').read()) != len(rows_):
            sys.exit(f'Os embeddings {path} não correspondem aos dados da confirmação.')
        mats[name] = np.asarray(np.load(path, mmap_mode='r'), dtype=np.float32)
    Q, D = mats['q'], mats['d']
    P = sorted(mem_pairs)
    A = csr_matrix((np.ones(2 * len(P), dtype=np.float32), ([x for x, y in P] + [y for x, y in P], [y for x, y in P] + [x for x, y in P])), shape=(n, n))
    A.sum_duplicates(); A.data[:] = 1
    deg = np.diff(A.indptr).astype(np.float32); H = np.where(deg > 0)[0]; starts = A.indptr[H]
    C = G.normalize(D[H] + np.asarray(A[H] @ D)); logdeg = np.log1p(deg)
    top = {}; rows = JL + JU
    for b0 in range(0, len(rows), 128):
        R = rows[b0:b0 + 128]; QV = Q[[qidx[i] for i in R]]; SB = QV @ D.T
        for j, i in enumerate(R):
            s = SB[j]; s[i:] = -np.inf
            m1 = s.copy(); m1[H] = np.maximum(np.maximum(m1[H], np.maximum.reduceat(s[A.indices], starts)), C @ QV[j])
            m1[H] = np.where(np.isfinite(s[H]), m1[H], -np.inf)
            top[i] = {'M0': G.top5(s)[0], 'M1': G.top5(m1)[0], 'M2': G.top5(m1 + G.BETA * logdeg)[0]}
    # julgamentos do gemma na confirmação (para concordância e para conferir a reprodução)
    cpath = os.path.join('gc_cache', res['reproducao']['juiz']['cache']); gem = {}
    if os.path.exists(cpath):
        for line in open(cpath, encoding='utf-8'):
            try: d = json.loads(line); gem[(d['a'], d['b'])] = d['v']
            except Exception: pass
    gv = lambda i, j: gem.get((int(ids[i]), int(ids[j])))
    miss = sum(gv(i, top[i]['M0']) is None for i in rows)
    if miss > 0.05 * len(rows): sys.exit(f'A reprodução não bate com a confirmação ({miss} de {len(rows)} sugestões sem julgamento salvo).')
    # exclusões: perguntas do conjunto cego comprometido e dos exemplos mostrados no resultado
    gb = random.Random(4242); blind_q = set(POS[:G.N_BLIND_CTRL]); used_q = set(); pool = JL + JU
    for m in ('M0', 'M1', 'M2'):
        for i in [i for i in gb.sample(pool, len(pool)) if i not in used_q][:G.N_BLIND_SUG // 3]: used_q.add(i)
    blind_q |= used_q
    J = {i: {m: gv(i, top[i][m]) for m in ('M0', 'M1', 'M2')} for i in rows}
    worse = [i for i in rows if i not in blind_q and J[i]['M0'] and J[i]['M2'] is False and top[i]['M2'] != top[i]['M0']]
    shown = set(random.Random(9).sample(worse, min(10, len(worse))))
    return dict(ids=ids, texts=texts, earlier=earlier, JL=JL, JU=JU, POS=POS, NEG=NEG, NEGj=NEGj, top=top, gv=gv,
                excluded=blind_q | shown, wL=len(lab) / N, wU=(N - len(lab)) / N)

def gerar(a):
    if os.path.exists(KEY) and not a.refazer: sys.exit(f'{KEY} já existe. Para gerar de novo (invalida rótulos anteriores), use --refazer.')
    S = rebuild(a.embed); top, ex = S['top'], S['excluded']; items = []; info = {}
    for gname, Gq in (('marcada', S['JL']), ('sem_marcacao', S['JU'])):
        keep = [i for i in Gq if i not in ex]; diff = [i for i in keep if top[i]['M0'] != top[i]['M1']]
        sel = sorted(random.Random(77).sample(diff, CAP)) if len(diff) > CAP else diff
        info[gname] = {'perguntas_validas': len(keep), 'com_1a_sugestao_diferente': len(diff), 'rotuladas': len(sel)}
        for i in sel:
            for m in ('M0', 'M1'): items.append({'tipo': 'sugestao', 'grupo': gname, 'metodo': m, 'i': i, 'j': top[i][m]})
    pos_c = [i for i in S['POS'][G.N_BLIND_CTRL:] if i not in ex][:N_POS]
    for i in pos_c: items.append({'tipo': 'controle_positivo', 'i': i, 'j': sorted(S['earlier'](i))[0]})
    for i, j in list(zip(S['NEG'], S['NEGj']))[:N_NEG]: items.append({'tipo': 'controle_negativo', 'i': i, 'j': j})
    random.Random(31337).shuffle(items)
    w = lambda i: ' '.join(S['texts'][i].split()[:WORDS])
    with open(ITEMS, 'w', encoding='utf-8') as f:
        f.write('JUIZ 2 (cego). Para cada item, responda SIM ou NÃO.\n' + RUBRICA + '\n')
        for k, it in enumerate(items, 1): f.write(f'\n#{k}\n  A: {w(it["i"])}\n  B: {w(it["j"])}\n')
    key = {'itens_sha256': file_sha(ITEMS), 'rubrica': RUBRICA, 'contagens': info, 'wL': S['wL'], 'wU': S['wU'],
           'itens': [{**it, 'n': k, 'gemma': S['gv'](it['i'], it['j'])} for k, it in enumerate(items, 1)]}
    json.dump(key, open(KEY, 'w'), ensure_ascii=False)
    print(json.dumps({'itens': len(items), 'contagens': info, 'itens_sha256': key['itens_sha256']}, ensure_ascii=False, indent=1))
    print(f'\nEnvie SÓ o arquivo {ITEMS} ao Claude. NÃO envie {KEY}.')

def parse_labels(path, n):
    raw = json.load(open(path)); raw = raw.get('rotulos', raw) if isinstance(raw, dict) else raw
    if isinstance(raw, list): raw = {str(k): v for k, v in enumerate(raw, 1)}
    val = lambda v: True if str(v).strip().upper() in ('SIM', 'S', 'YES', 'TRUE', '1') else (False if str(v).strip().upper() in ('NÃO', 'NAO', 'N', 'NO', 'FALSE', '0') else None)
    lab = {int(k): val(v) for k, v in raw.items()}
    missing = [k for k in range(1, n + 1) if lab.get(k) is None]
    if missing: sys.exit(f'Faltam rótulos válidos para {len(missing)} itens (ex.: {missing[:10]}).')
    return lab

def kappa(x, y):
    x, y = np.array(x, float), np.array(y, float); po = np.mean(x == y); pe = x.mean() * y.mean() + (1 - x.mean()) * (1 - y.mean())
    return round(float((po - pe) / (1 - pe)), 3) if pe < 1 else None

def comparar(a):
    if not os.path.exists(KEY): sys.exit(f'Falta {KEY}. Rode primeiro: python3 gc_conf_juiz2.py gerar')
    key = json.load(open(KEY))
    if file_sha(ITEMS) != key['itens_sha256']: sys.exit(f'{ITEMS} foi alterado ou gerado de novo; os rótulos não correspondem.')
    its = key['itens']; lab = parse_labels(a.rotulos, len(its)); wL, wU = key['wL'], key['wU']
    for it in its: it['claude'] = lab[it['n']]
    ctrl = lambda t, who: [it[who] for it in its if it['tipo'] == t and it[who] is not None]
    def gate(pos_, neg_):
        s, f = float(np.mean(pos_)), float(np.mean(neg_))
        return {'sensibilidade': round(s, 3), 'falsos_positivos': round(f, 3),
                'valido': bool(s >= G.J_MIN_TPR and f <= G.J_MAX_FPR and s - f >= G.J_MIN_GAP)}
    gc, gg = gate(ctrl('controle_positivo', 'claude'), ctrl('controle_negativo', 'claude')), gate(ctrl('controle_positivo', 'gemma'), ctrl('controle_negativo', 'gemma'))
    def p2(who):
        per = {}
        for gname in ('marcada', 'sem_marcacao'):
            pairs = collections.defaultdict(dict)
            for it in its:
                if it['tipo'] == 'sugestao' and it['grupo'] == gname: pairs[it['i']][it['metodo']] = it[who]
            d = np.array([float(v['M1']) - float(v['M0']) for v in pairs.values() if v.get('M0') is not None and v.get('M1') is not None])
            c = key['contagens'][gname]; per[gname] = (d, c['com_1a_sugestao_diferente'], c['perguntas_validas'])
        def est(rng=None):
            tot = 0.0
            for gname, wg in (('marcada', wL), ('sem_marcacao', wU)):
                d, k, nv = per[gname]
                if rng is None: f, m = k / nv, d.mean() if len(d) else 0.0
                else: f = rng.binomial(nv, k / nv) / nv; m = d[rng.integers(0, len(d), len(d))].mean() if len(d) else 0.0
                tot += wg * f * m
            return tot
        b = np.random.default_rng(5); boots = [est(b) for _ in range(NBOOT)]
        return {'M1_menos_M0': round(float(est()), 4), 'ic95': G.ci(boots),
                'discordantes_so_M0_util_x_so_M1_util': {g_: [int((per[g_][0] < 0).sum()), int((per[g_][0] > 0).sum())] for g_ in per}}
    pc, pg = p2('claude'), p2('gemma')
    both = [it for it in its if it['gemma'] is not None]
    sug = [it for it in both if it['tipo'] == 'sugestao']
    yes = lambda who, m: round(float(np.mean([it[who] for it in its if it['tipo'] == 'sugestao' and it['metodo'] == m and it[who] is not None])), 3)
    out = {'itens': len(its), 'contagens': key['contagens'],
           'claude_controles': gc, 'gemma_nos_mesmos_controles': gg,
           'P2_complementar_claude': {**pc, 'passa': (bool(pc['ic95'] and pc['ic95'][0] >= G.P_MIN_JUDGE) if gc['valido'] else 'inconclusivo (Claude reprovado nos controles)')},
           'P2_mesmos_itens_gemma': pg,
           'sim_nas_sugestoes': {'claude': {'M0': yes('claude', 'M0'), 'M1': yes('claude', 'M1')}, 'gemma': {'M0': yes('gemma', 'M0'), 'M1': yes('gemma', 'M1')}},
           'concordancia_claude_gemma': {'todos_os_itens': {'n': len(both), 'acordo': round(float(np.mean([it['claude'] == it['gemma'] for it in both])), 3),
                                                            'kappa': kappa([it['claude'] for it in both], [it['gemma'] for it in both])},
                                         'so_sugestoes': {'n': len(sug), 'acordo': round(float(np.mean([it['claude'] == it['gemma'] for it in sug])), 3) if sug else None,
                                                          'kappa': kappa([it['claude'] for it in sug], [it['gemma'] for it in sug]) if sug else None},
                                         'gemma_sim_quando_claude_sim': round(float(np.mean([it['gemma'] for it in both if it['claude']])), 3) if any(it['claude'] for it in both) else None,
                                         'gemma_sim_quando_claude_nao': round(float(np.mean([it['gemma'] for it in both if not it['claude']])), 3) if any(not it['claude'] for it in both) else None},
           'itens_sha256': key['itens_sha256']}
    json.dump(out, open(OUT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(json.dumps(out, ensure_ascii=False, indent=1)); print(f'\nPronto. Envie {OUT} (só números agregados). NÃO envie {KEY}.')

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('acao', choices=['gerar', 'comparar']); ap.add_argument('rotulos', nargs='?')
    ap.add_argument('--embed', default='nomic-embed-text'); ap.add_argument('--refazer', action='store_true'); a = ap.parse_args()
    if a.acao == 'gerar': gerar(a)
    else:
        if not a.rotulos: sys.exit('Informe o arquivo de rótulos: python3 gc_conf_juiz2.py comparar juiz2_rotulos.json')
        comparar(a)

if __name__ == '__main__':
    main()
