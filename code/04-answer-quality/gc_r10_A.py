"""Grande Cérebro, Rodada 10, etapa A: a recuperação confirmada vale em outra comunidade (Super User)?

Mesmo método da confirmação do AskUbuntu, sem LLM e sem juiz. Rode na mesma pasta do gc_conf.py.
Precisa do Ollama aberto só para os embeddings (nomic-embed-text).

Antes: coloque o superuser.com.7z (dump do Stack Exchange de 02/04/2024) nesta pasta.
Uso:    python3 gc_r10_A.py
        pode parar e rodar de novo: os embeddings já feitos ficam salvos e ele continua de onde parou.
Saída:  r10A_resultado.json (só números) -> ENVIE

Critérios congelados no protocolo em 30/09/2026, 03h20:
  A1: ganho relativo de M1 sobre M0 na família marcada no top-5, limite inferior do IC 95% > 10%
  A2: o mesmo para H1 (M0 intercalado com M1)
  descritivos: H, M2, duplicata marcada no top-5, teto
"""
import argparse, collections, gzip, hashlib, json, os, random, shutil, subprocess, sys, time
import numpy as np
from scipy.sparse import csr_matrix
import gc_conf as G

VERSAO = 'r10-A-v1'
SITE, DUMP, XDIR, PFX = 'superuser.com', 'superuser.com.7z', 'gc_data/superuser2024', 'su24'
FILES = ('Posts.xml', 'PostLinks.xml', 'PostHistory.xml')
P_MIN_REL = 0.10
OUT = 'r10A_resultado.json'

def file_sha(path): return hashlib.sha256(open(path, 'rb').read()).hexdigest()

def extract():
    found = {}
    for d, _, fs in os.walk(XDIR) if os.path.isdir(XDIR) else []:
        for f in fs:
            if f in FILES: found[f] = os.path.join(d, f)
    if len(found) == 3: return found
    if not os.path.exists(DUMP): sys.exit(f'Não achei {DUMP} nesta pasta. Baixe em https://archive.org/details/stackexchange (arquivo {DUMP}) e coloque aqui.')
    manual = (f'Alternativa manual: abra {DUMP} com o Keka ou The Unarchiver e coloque Posts.xml, PostLinks.xml e PostHistory.xml '
              f'na pasta {XDIR}/. Depois rode o mesmo comando.')
    print('1. extraindo Posts.xml, PostLinks.xml e PostHistory.xml (alguns minutos; precisa de bastante espaço livre)', flush=True)
    os.makedirs(XDIR, exist_ok=True)
    binary = next((shutil.which(b) for b in ('7zz', '7z', '7za') if shutil.which(b)), None)
    try:
        if binary: subprocess.run([binary, 'x', DUMP, f'-o{XDIR}', *FILES, '-y'], check=True, stdout=subprocess.DEVNULL)
        else:
            try: import py7zr
            except ImportError: sys.exit('Falta o py7zr. Rode: pip install py7zr   (' + manual + ')')
            with py7zr.SevenZipFile(DUMP, 'r') as z: z.extract(path=XDIR, targets=[nm for nm in z.getnames() if os.path.basename(nm) in FILES])
    except SystemExit: raise
    except Exception as e: sys.exit(f'Não consegui extrair ({e}). ' + manual)
    for d, _, fs in os.walk(XDIR):
        for f in fs:
            if f in FILES: found[f] = os.path.join(d, f)
    if len(found) < 3: sys.exit(f'O arquivo não tem {FILES} (achei: {sorted(found)}).')
    return found

def read(found):
    qpath, lpath, mpath = f'gc_data/{PFX}_perguntas.jsonl.gz', f'gc_data/{PFX}_duplicatas.tsv', f'gc_data/{PFX}_meta.json'
    want = {'site': SITE, 'preproc': G.PREPROC, 'T0': G.T0, 'xml_bytes': {f: os.path.getsize(p) for f, p in sorted(found.items())}}
    have = json.load(open(mpath)) if os.path.exists(mpath) else None
    T0 = G.T0
    if not (os.path.exists(qpath) and os.path.exists(lpath) and have and {k: have.get(k) for k in want} == want):
        print('2. lendo perguntas e histórico de edições (pode levar 20 a 60 minutos)', flush=True)
        qdate, acc = {}, {}
        for r in G.rows(found['Posts.xml']):
            if r.get('PostTypeId') == '1':
                q = int(r['Id']); qdate[q] = r.get('CreationDate', '')
                if r.get('AcceptedAnswerId'): acc[q] = 1
        TITLE, BODY, ver = ('1', '4', '7'), ('2', '5', '8'), {}
        for r in G.rows(found['PostHistory.xml']):
            t = r.get('PostHistoryTypeId')
            if t not in TITLE and t not in BODY: continue
            p = int(r.get('PostId', -1)); cd = qdate.get(p)
            if cd is None: continue
            d = r.get('CreationDate', ''); v = ver.setdefault(p, ['', '', '', '']); k = 0 if t in TITLE else 2
            if cd >= T0: ok = t in ('1', '2') and not v[k + 1]
            else: ok = d < T0 and d >= v[k + 1]
            if ok: v[k], v[k + 1] = ((r.get('Text') or '')[:300] if k == 0 else G.clean_md((r.get('Text') or '')[:20000])), d
        missing = {p for p in qdate if p not in ver or not ver[p][1] or not ver[p][3]}
        fallback = {}
        if missing:
            for r in G.rows(found['Posts.xml']):
                p = int(r['Id'])
                if p in missing: fallback[p] = G.clean_html(r.get('Title'), r.get('Body'))
        Qs = sorted((qdate[p], p, fallback[p] if p in missing else G.final_text(ver[p][0], ver[p][2])) for p in qdate)
        L = [(int(r['PostId']), int(r['RelatedPostId']), r.get('CreationDate', '')) for r in G.rows(found['PostLinks.xml']) if r.get('LinkTypeId') == '3']
        with gzip.open(qpath + '.tmp', 'wt', encoding='utf-8') as f:
            for d, i, t in Qs: f.write(json.dumps([i, d, t]) + '\n')
        os.replace(qpath + '.tmp', qpath)
        with open(lpath + '.tmp', 'w') as f:
            for p, q, d in L: f.write(f'{p}\t{q}\t{d}\n')
        os.replace(lpath + '.tmp', lpath)
        json.dump({**want, 'sem_historico_usou_versao_atual': len(missing), 'com_resposta_aceita': sorted(acc)}, open(mpath, 'w'))
    return qpath, lpath, json.load(open(mpath))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--host', default='http://localhost:11434'); ap.add_argument('--embed', default='nomic-embed-text')
    a = ap.parse_args(); t_start = time.time(); T0 = G.T0
    os.makedirs('gc_data', exist_ok=True); os.makedirs('gc_cache', exist_ok=True)
    emb_digest, ollama_version = G.ollama(a.host, a.embed)
    found = extract(); qpath, lpath, meta = read(found)
    ids, dates, texts = [], [], []
    for line in gzip.open(qpath, 'rt', encoding='utf-8'): i, d, t = json.loads(line); ids.append(i); dates.append(d); texts.append(t)
    pos = {q: k for k, q in enumerate(ids)}; n = len(ids); acc = set(meta.get('com_resposta_aceita', []))
    dups = collections.defaultdict(set); mem_pairs = set(); n_links = 0
    for line in open(lpath):
        p, q, d = line.rstrip('\n').split('\t'); p, q = int(p), int(q)
        if p in pos and q in pos and p != q:
            n_links += 1; dups[p].add(q); dups[q].add(p)
            x, y = sorted((pos[p], pos[q]))
            if d < T0 and dates[y] < T0: mem_pairs.add((x, y))
    e0 = next((k for k, d in enumerate(dates) if d >= T0), n)
    earlier = lambda i: {pos[s] for s in dups.get(ids[i], ()) if pos[s] < i}
    lab = [i for i in range(e0, n) if earlier(i)]; unl_all = [i for i in range(e0, n) if not earlier(i)]
    N = n - e0; unl = random.Random(2024).sample(unl_all, min(G.N_UNL, len(unl_all)))
    info = {'site': SITE, 'perguntas': n, 'perguntas_antes_de_2020': e0, 'perguntas_na_avaliacao': N, 'com_duplicata_marcada_anterior': len(lab),
            'teto_marcada': round(len(lab) / max(N, 1), 4), 'duplicatas_validas': n_links, 'ligacoes_na_memoria': len(mem_pairs),
            'primeira_data': dates[0] if dates else None, 'ultima_data': dates[-1] if dates else None,
            'sem_historico_usou_versao_atual': meta.get('sem_historico_usou_versao_atual')}
    data_sha = G.sha(f'{i}|{d}|{t}' for i, d, t in zip(ids, dates, texts))
    print(f'  {json.dumps(info, ensure_ascii=False)}', flush=True)
    if len(lab) < 500 or len(mem_pairs) < 1000: sys.exit('Dados pequenos demais para a etapa A; envie a linha acima.')
    tag = a.embed.replace(':', '_').replace('/', '_'); qrows = sorted(set(lab) | set(unl)); qidx = {i: j for j, i in enumerate(qrows)}
    pre_q, pre_d = ('search_query: ', 'search_document: ') if 'nomic' in a.embed else ('', '')
    print('3. embeddings das perguntas novas', flush=True)
    Q = np.asarray(G.embed_matrix(a.host, a.embed, emb_digest, [texts[i] for i in qrows], f'gc_cache/{PFX}_q_{tag}.npy', pre_q), dtype=np.float32)
    print('3. embeddings de todas as perguntas (memória) — a parte longa', flush=True)
    D = np.asarray(G.embed_matrix(a.host, a.embed, emb_digest, texts, f'gc_cache/{PFX}_d_{tag}.npy', pre_d), dtype=np.float32)
    print('4. avaliação', flush=True)
    P = sorted(mem_pairs)
    A = csr_matrix((np.ones(2 * len(P), dtype=np.float32), ([x for x, y in P] + [y for x, y in P], [y for x, y in P] + [x for x, y in P])), shape=(n, n))
    A.sum_duplicates(); A.data[:] = 1
    deg = np.diff(A.indptr).astype(np.float32); H = np.where(deg > 0)[0]; starts = A.indptr[H]
    C = G.normalize(D[H] + np.asarray(A[H] @ D)); logdeg = np.log1p(deg)
    rec = {}; rows_eval = lab + unl
    for b0 in range(0, len(rows_eval), 128):
        R = rows_eval[b0:b0 + 128]; QV = Q[[qidx[i] for i in R]]; SB = QV @ D.T
        for j, i in enumerate(R):
            s = SB[j]; s[i:] = -np.inf
            m1 = s.copy(); m1[H] = np.maximum(np.maximum(m1[H], np.maximum.reduceat(s[A.indices], starts)), C @ QV[j])
            m1[H] = np.where(np.isfinite(s[H]), m1[H], -np.inf)
            r = {'M0': G.top5(s), 'M1': G.top5(m1), 'M2': G.top5(m1 + G.BETA * logdeg)}; r['H'] = G.inter(r['M0'], r['M2']); r['H1'] = G.inter(r['M0'], r['M1'])
            g = earlier(i)
            if g:
                fs = set(g)
                for x in g: fs |= set(A.indices[A.indptr[x]:A.indptr[x + 1]].tolist())
                r['gold'], r['fam'] = g, fs
            rec[i] = r
        if (b0 // 128) % 20 == 0: print(f'  {min(b0 + 128, len(rows_eval))}/{len(rows_eval)}', flush=True)
    MS = ['M0', 'M1', 'M2', 'H', 'H1']
    hit = {(m, key, k): np.array([bool(set(rec[i][m][:k]) & rec[i][key]) for i in lab], dtype=np.float64) for m in MS for key in ('fam', 'gold') for k in (1, 5)}
    bt = np.random.default_rng(3); idx = [bt.integers(0, len(lab), len(lab)) for _ in range(G.NBOOT)]
    def rel(m, ref='M0', key='fam', k=5):
        x, y = hit[(m, key, k)], hit[(ref, key, k)]
        f = lambda ix: x[ix].sum() / y[ix].sum() - 1 if y[ix].sum() > 0 else float('nan')
        return dict(valor=round(float(f(slice(None))), 4), ic95=G.ci([f(ix) for ix in idx]))
    acerto = {m: {f'{"familia" if key == "fam" else "marcada"}_top{k}': round(float(hit[(m, key, k)].sum() / N), 4) for key in ('fam', 'gold') for k in (1, 5)} for m in MS}
    fam_rel = {m: rel(m) for m in ('M1', 'M2', 'H', 'H1')}
    A1 = bool(fam_rel['M1']['ic95'] and fam_rel['M1']['ic95'][0] > P_MIN_REL); A2 = bool(fam_rel['H1']['ic95'] and fam_rel['H1']['ic95'][0] > P_MIN_REL)
    # contagens para planejar a próxima rodada (só recuperação, sem qualidade de resposta)
    diff = lambda i, a_, b_: set(rec[i][a_]) != set(rec[i][b_])
    cont = {}
    for gname, G_ in (('marcadas', lab), ('sem_marcacao_amostra', unl)):
        ac = [i for i in G_ if ids[i] in acc]
        cont[gname] = {'total': len(G_), 'com_resposta_aceita': len(ac), 'aceitas_H1_diferente_de_M0': sum(diff(i, 'H1', 'M0') for i in ac),
                       'aceitas_H_diferente_de_M0': sum(diff(i, 'H', 'M0') for i in ac), 'aceitas_H_diferente_de_H1': sum(diff(i, 'H', 'H1') for i in ac)}
    out = {'versao': VERSAO, 'dados': info, 'acerto_sem_llm': acerto,
           'familia_top5_ganho_relativo_sobre_M0': fam_rel,
           'marcada_top5_ganho_relativo_sobre_M0': {m: rel(m, key='gold') for m in ('M1', 'M2', 'H', 'H1')},
           'criterios': {'A1_M1_familia_top5_ganho_relativo_IC_inferior_>_10%': A1, 'A2_H1_familia_top5_ganho_relativo_IC_inferior_>_10%': A2},
           'contagens_para_planejamento': {**cont, 'escala_sem_marcacao': round((N - len(lab)) / max(len(unl), 1), 4),
                                           'nota': 'resposta aceita = AcceptedAnswerId presente no Posts.xml'},
           'reproducao': {'dados_sha256': data_sha, 'preprocessamento': G.PREPROC, 'embeddings': {'modelo': a.embed, 'digest': emb_digest},
                          'ollama': ollama_version, 'script_sha256': file_sha(os.path.abspath(__file__))},
           'minutos_nesta_execucao': round((time.time() - t_start) / 60, 1)}
    json.dump(out, open(OUT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(json.dumps({k: out[k] for k in ('dados', 'criterios')}, ensure_ascii=False, indent=1))
    print(f'\nPronto. Envie {OUT} (só números).')

if __name__ == '__main__':
    main()
