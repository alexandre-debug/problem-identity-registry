"""Grande Cérebro: CONFIRMAÇÃO em dados nunca usados (AskUbuntu, perguntas de 2020 a abril de 2024).

Métodos congelados das rodadas 7, 8 e 8b (nada é recalibrado aqui):
  M0 busca plana; M1 relações sem bônus; M2 relações + bônus de popularidade (beta = 0,02);
  H  = M0 e M2 intercalados (desenho da rodada 8); H1 = M0 e M1 intercalados (secundário).
Memória: todas as perguntas anteriores a cada pergunta nova; ligações = duplicatas marcadas ANTES de
01/01/2020 entre perguntas anteriores a essa data. Avaliação: perguntas criadas a partir de 01/01/2020.
Textos de época (histórico de edições, PostHistory.xml): a pergunta nova e as perguntas da janela entram
na versão inicial, como foram escritas; as perguntas anteriores a 2020 entram na versão vigente em
01/01/2020. Assim nenhuma edição posterior (solução descoberta, aviso de duplicata) vaza para o teste.
Mede recuperação e correspondência entre perguntas; não lê respostas, então não mede resolução nem economia.
Critérios fixados no protocolo antes de rodar.

Etapas (retomáveis: se parar, rode o MESMO comando de novo):
  1. extrai Posts.xml, PostLinks.xml e PostHistory.xml de askubuntu.com.7z (precisa ~10 GB livres)
  2. lê perguntas, versões de época e duplicatas marcadas (LinkTypeId = 3)
  3. embeddings (a etapa longa: algumas horas)
  4. avaliação sem LLM + juiz local (gemma) + conjunto cego para um segundo juiz
Tudo o que é reaproveitado (dados lidos, embeddings, julgamentos) é conferido por impressão digital
(dados, processamento, prompt e versão exata dos modelos); se algo mudou, o script para e avisa.

Uso: python3 gc_conf.py --judge gemma4:latest
Saídas: gc_conf_result.json e gc_conf_cegos.txt -> envie estes dois.
        gc_conf_chave.json -> NÃO envie ainda; só depois que eu devolver os rótulos do arquivo cego.
"""
import argparse, gzip, hashlib, html, json, os, random, re, shutil, subprocess, sys, time, collections, urllib.request, urllib.error
import xml.etree.ElementTree as ET
import numpy as np
from scipy.sparse import csr_matrix

DUMP, XDIR, T0 = 'askubuntu.com.7z', 'gc_data/askubuntu2024', '2020-01-01'
MAX_WORDS, PRE_WORDS, JUDGE_WORDS, BLIND_WORDS = 200, 30, 70, 90
BETA, N_UNL, N_JL, N_JU, N_CTRL, N_BLIND_CTRL, N_BLIND_SUG, NBOOT = 0.02, 5000, 200, 400, 60, 20, 60, 2000
P_MIN_REL, P_MIN_JUDGE = 0.10, -0.03
J_MIN_TPR, J_MAX_FPR, J_MIN_GAP = 0.30, 0.15, 0.25          # o juiz precisa passar nos controles
PREPROC = 'v2: historico de edicoes; markdown limpo; pre/code ate 30 palavras; minusculas; 200 palavras'
FILES = ('Posts.xml', 'PostLinks.xml', 'PostHistory.xml')
PROMPT = ('Question A: {a}\n\nQuestion B: {b}\n\nAre A and B about the same technical problem, so that a correct '
          'answer to B would also solve A? Reply with exactly one word: YES or NO.')
PRE, TAG = re.compile(r'<pre[^>]*>(.*?)</pre>', re.S | re.I), re.compile(r'<[^>]+>')

FENCE = re.compile(r'```.*?```|~~~.*?~~~', re.S)
def short(txt): return ' ' + ' '.join(TAG.sub(' ', txt).replace('`', ' ').replace('~', ' ').split()[:PRE_WORDS]) + ' '
def clean_html(title, body):                      # reserva: perguntas sem histórico (versão atual, HTML)
    body = PRE.sub(lambda m: short(m.group(1)), body or '')
    return ' '.join(html.unescape(TAG.sub(' ', (title or '') + ' . ' + body)).lower().split()[:MAX_WORDS])
def clean_md(body):                               # corpo em markdown (histórico de edições)
    t = (body or '').replace('\r\n', '\n')
    t = FENCE.sub(lambda m: short(m.group(0)), t); t = PRE.sub(lambda m: short(m.group(1)), t)
    out, block = [], []
    for ln in t.split('\n'):                        # blocos de código indentados
        if ln.startswith('    ') or ln.startswith('\t'): block.append(ln); continue
        if block: out.append(short(' '.join(block))); block = []
        out.append(ln)
    if block: out.append(short(' '.join(block)))
    t = '\n'.join(out)
    t = re.sub(r'!\[([^\]]*)\]\([^)]*\)', r'\1', t); t = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', t)
    t = re.sub(r'\[([^\]]*)\]\[[^\]]*\]', r'\1', t); t = re.sub(r'(?m)^\s*\[[^\]]+\]:\s*\S+.*$', ' ', t)
    t = TAG.sub(' ', t).replace('`', ' '); t = re.sub(r'[*#>]+', ' ', t)
    return ' '.join(html.unescape(t).split()[:MAX_WORDS])
def final_text(title, body): return ' '.join((html.unescape(title or '') + ' . ' + (body or '')).lower().split()[:MAX_WORDS])
def sha(parts):
    h = hashlib.sha256()
    for p in parts: h.update(str(p).encode('utf-8')); h.update(b'\0')
    return h.hexdigest()
def ollama(host, name):
    try:
        tags = json.loads(urllib.request.urlopen(host + '/api/tags', timeout=30).read()).get('models', [])
        version = json.loads(urllib.request.urlopen(host + '/api/version', timeout=30).read()).get('version')
    except Exception as e: sys.exit(f'Não consegui falar com o Ollama em {host}: {e}')
    for m in tags:
        if name in (m.get('name'), m.get('model')) or name + ':latest' in (m.get('name'), m.get('model')): return m.get('digest', ''), version
    sys.exit(f'O modelo {name} não está no Ollama. Rode: ollama pull {name}')

def rows(path):
    ctx = ET.iterparse(path, events=('start', 'end')); _, root = next(ctx); k = 0
    for ev, el in ctx:
        if ev == 'end' and el.tag == 'row':
            yield el.attrib; k += 1
            if k % 5000 == 0: root.clear()
    root.clear()

def normalize(M): return (M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)).astype(np.float32)
def top5(v): t = np.argpartition(-v, 5)[:5]; return [int(x) for x in t[np.argsort(-v[t])]]
def inter(a, b):
    out = []
    for x in [v for pair in zip(a, b) for v in pair]:
        if x not in out: out.append(x)
    return out[:5]
def ci(x): x = [v for v in x if np.isfinite(v)]; return [round(float(np.percentile(x, 2.5)), 4), round(float(np.percentile(x, 97.5)), 4)] if x else None

def post(host, route, payload, timeout=600):
    req = urllib.request.Request(host + route, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read())

def embed_matrix(host, model, digest, texts, path, prefix, batch=64):
    n = len(texts); done_path, meta_path = path + '.done', path + '.meta.json'
    meta = {'modelo': model, 'digest': digest, 'prefixo': prefix, 'linhas': n, 'textos_sha256': sha(prefix + t for t in texts)}
    done = int(open(done_path).read()) if os.path.exists(done_path) and os.path.exists(path) else 0
    if done:
        old = json.load(open(meta_path)) if os.path.exists(meta_path) else None
        if old != meta: sys.exit(f'Os embeddings salvos em {path} não correspondem aos dados/modelo atuais. Apague {path}, {done_path} e {meta_path} e rode de novo.')
    else: json.dump(meta, open(meta_path, 'w'))
    M = np.load(path, mmap_mode='r+') if done else None; t0, start = time.time(), done
    for b in range(done, n, batch):
        try: vecs = post(host, '/api/embed', {'model': model, 'input': [prefix + t for t in texts[b:b + batch]]})['embeddings']
        except urllib.error.URLError as e: sys.exit(f'O Ollama não respondeu ({e}). Abra o Ollama e rode o mesmo comando: continua de onde parou.')
        vecs = np.array(vecs, dtype=np.float32); vecs /= np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9
        if M is None: M = np.lib.format.open_memmap(path, mode='w+', dtype=np.float32, shape=(n, vecs.shape[1]))
        M[b:b + len(vecs)] = vecs; M.flush(); open(done_path, 'w').write(str(b + len(vecs))); k = b + len(vecs)
        if (k // batch) % 50 == 0 or k == n:
            rate = (k - start) / max(time.time() - t0, 1e-9)
            print(f'  embeddings {k}/{n}  (~{(n - k) / max(rate, 1e-9) / 60:.0f} min restantes)', flush=True)
    return np.load(path, mmap_mode='r')

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--judge', required=True); ap.add_argument('--host', default='http://localhost:11434')
    ap.add_argument('--embed', default='nomic-embed-text'); a = ap.parse_args(); t_start = time.time()
    os.makedirs('gc_data', exist_ok=True); os.makedirs('gc_cache', exist_ok=True)
    emb_digest, ollama_version = ollama(a.host, a.embed); judge_digest, _ = ollama(a.host, a.judge)   # falha cedo se faltar modelo

    # ---------- 1. extração ----------
    found = {}
    for d, _, fs in os.walk(XDIR) if os.path.isdir(XDIR) else []:
        for f in fs:
            if f in FILES: found[f] = os.path.join(d, f)
    if len(found) < 3:
        if not os.path.exists(DUMP): sys.exit(f'Não achei {DUMP} nesta pasta. Baixe em https://archive.org/download/stackexchange/{DUMP} e coloque aqui.')
        manual = (f'Alternativa manual: abra {DUMP} com o Keka ou The Unarchiver (ou rode: brew install sevenzip), '
                  f'e coloque Posts.xml, PostLinks.xml e PostHistory.xml na pasta {XDIR}/. Depois rode o mesmo comando.')
        print('1. extraindo Posts.xml, PostLinks.xml e PostHistory.xml (alguns minutos; precisa de ~10 GB livres)', flush=True); os.makedirs(XDIR, exist_ok=True)
        binary = next((shutil.which(b) for b in ('7zz', '7z', '7za') if shutil.which(b)), None)
        try:
            if binary: subprocess.run([binary, 'x', DUMP, f'-o{XDIR}', *FILES, '-y'], check=True, stdout=subprocess.DEVNULL)
            else:
                try: import py7zr
                except ImportError: sys.exit('Falta o py7zr. Rode: pip install py7zr   (' + manual + ')')
                with py7zr.SevenZipFile(DUMP, 'r') as z:
                    targets = [nm for nm in z.getnames() if os.path.basename(nm) in FILES]
                    z.extract(path=XDIR, targets=targets)
        except SystemExit: raise
        except Exception as e: sys.exit(f'Não consegui extrair ({e}). ' + manual)
        for d, _, fs in os.walk(XDIR):
            for f in fs:
                if f in FILES: found[f] = os.path.join(d, f)
        if len(found) < 3: sys.exit(f'O arquivo não tem {FILES} (achei: {sorted(found)}).')

    # ---------- 2. leitura (versões de época) ----------
    qpath, lpath, mpath = 'gc_data/au24_perguntas.jsonl.gz', 'gc_data/au24_duplicatas.tsv', 'gc_data/au24_meta.json'
    want = {'preproc': PREPROC, 'T0': T0, 'xml_bytes': {f: os.path.getsize(p) for f, p in sorted(found.items())}}
    have = json.load(open(mpath)) if os.path.exists(mpath) else None
    if not (os.path.exists(qpath) and os.path.exists(lpath) and have and {k: have.get(k) for k in want} == want):
        print('2. lendo perguntas e histórico de edições (10 a 30 minutos)', flush=True)
        qdate = {int(r['Id']): r.get('CreationDate', '') for r in rows(found['Posts.xml']) if r.get('PostTypeId') == '1'}
        TITLE, BODY, ver = ('1', '4', '7'), ('2', '5', '8'), {}
        for r in rows(found['PostHistory.xml']):
            t = r.get('PostHistoryTypeId')
            if t not in TITLE and t not in BODY: continue
            p = int(r.get('PostId', -1)); cd = qdate.get(p)
            if cd is None: continue
            d = r.get('CreationDate', ''); v = ver.setdefault(p, ['', '', '', '']); k = 0 if t in TITLE else 2
            if cd >= T0: ok = t in ('1', '2') and not v[k + 1]            # pergunta de 2020+: versão inicial
            else: ok = d < T0 and d >= v[k + 1]                         # anterior a 2020: vigente em 01/01/2020
            if ok: v[k], v[k + 1] = ((r.get('Text') or '')[:300] if k == 0 else clean_md((r.get('Text') or '')[:20000])), d
        missing = {p for p in qdate if p not in ver or not ver[p][1] or not ver[p][3]}
        fallback = {}
        if missing:
            for r in rows(found['Posts.xml']):
                p = int(r['Id'])
                if p in missing: fallback[p] = clean_html(r.get('Title'), r.get('Body'))
        Qs = sorted((qdate[p], p, fallback[p] if p in missing else final_text(ver[p][0], ver[p][2])) for p in qdate)
        L = [(int(r['PostId']), int(r['RelatedPostId']), r.get('CreationDate', '')) for r in rows(found['PostLinks.xml']) if r.get('LinkTypeId') == '3']
        with gzip.open(qpath + '.tmp', 'wt', encoding='utf-8') as f:
            for d, i, t in Qs: f.write(json.dumps([i, d, t]) + '\n')
        os.replace(qpath + '.tmp', qpath)
        with open(lpath + '.tmp', 'w') as f:
            for p, q, d in L: f.write(f'{p}\t{q}\t{d}\n')
        os.replace(lpath + '.tmp', lpath)
        json.dump({**want, 'sem_historico_usou_versao_atual': len(missing)}, open(mpath, 'w'))
    meta_data = json.load(open(mpath))
    ids, dates, texts = [], [], []
    for line in gzip.open(qpath, 'rt', encoding='utf-8'): i, d, t = json.loads(line); ids.append(i); dates.append(d); texts.append(t)
    pos = {q: k for k, q in enumerate(ids)}; n = len(ids)
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
    N = n - e0; unl = random.Random(2024).sample(unl_all, min(N_UNL, len(unl_all)))
    info = {'perguntas': n, 'perguntas_antes_de_2020': e0, 'perguntas_na_avaliacao': N, 'com_duplicata_marcada_anterior': len(lab),
            'teto_marcada': round(len(lab) / max(N, 1), 4), 'duplicatas_validas': n_links, 'ligacoes_na_memoria': len(mem_pairs),
            'primeira_data': dates[0] if dates else None, 'ultima_data': dates[-1] if dates else None,
            'sem_historico_usou_versao_atual': meta_data.get('sem_historico_usou_versao_atual')}
    data_sha = sha(f'{i}|{d}|{t}' for i, d, t in zip(ids, dates, texts))
    print(f'  {json.dumps(info, ensure_ascii=False)}', flush=True)
    if len(lab) < 500 or len(mem_pairs) < 1000: sys.exit('Dados pequenos demais para a confirmação; envie a linha acima.')

    # ---------- 3. embeddings ----------
    tag = a.embed.replace(':', '_').replace('/', '_'); qrows = sorted(set(lab) | set(unl)); qidx = {i: j for j, i in enumerate(qrows)}
    pre_q, pre_d = ('search_query: ', 'search_document: ') if 'nomic' in a.embed else ('', '')
    print('3. embeddings das perguntas novas', flush=True)
    Q = np.asarray(embed_matrix(a.host, a.embed, emb_digest, [texts[i] for i in qrows], f'gc_cache/au24_q_{tag}.npy', pre_q), dtype=np.float32)
    print('3. embeddings de todas as perguntas (memória) — a parte longa', flush=True)
    D = np.asarray(embed_matrix(a.host, a.embed, emb_digest, texts, f'gc_cache/au24_d_{tag}.npy', pre_d), dtype=np.float32)

    # ---------- 4a. avaliação sem LLM ----------
    print('4. avaliação', flush=True)
    P = sorted(mem_pairs)
    A = csr_matrix((np.ones(2 * len(P), dtype=np.float32), ([x for x, y in P] + [y for x, y in P], [y for x, y in P] + [x for x, y in P])), shape=(n, n))
    A.sum_duplicates(); A.data[:] = 1
    deg = np.diff(A.indptr).astype(np.float32); H = np.where(deg > 0)[0]; starts = A.indptr[H]
    C = normalize(D[H] + np.asarray(A[H] @ D)); logdeg = np.log1p(deg)
    rec = {}; rows_eval = lab + unl
    for b0 in range(0, len(rows_eval), 128):
        R = rows_eval[b0:b0 + 128]; QV = Q[[qidx[i] for i in R]]; SB = QV @ D.T
        for j, i in enumerate(R):
            s = SB[j]; s[i:] = -np.inf
            m1 = s.copy(); m1[H] = np.maximum(np.maximum(m1[H], np.maximum.reduceat(s[A.indices], starts)), C @ QV[j])
            m1[H] = np.where(np.isfinite(s[H]), m1[H], -np.inf)
            r = {'M0': top5(s), 'M1': top5(m1), 'M2': top5(m1 + BETA * logdeg)}; r['H'] = inter(r['M0'], r['M2']); r['H1'] = inter(r['M0'], r['M1'])
            g = earlier(i)
            if g:
                fs = set(g)
                for x in g: fs |= set(A.indices[A.indptr[x]:A.indptr[x + 1]].tolist())
                r['gold'], r['fam'] = g, fs
            rec[i] = r
        if (b0 // 128) % 20 == 0: print(f'  {min(b0 + 128, len(rows_eval))}/{len(rows_eval)}', flush=True)
    MS = ['M0', 'M1', 'M2', 'H', 'H1']
    hit = {(m, key, k): np.array([bool(set(rec[i][m][:k]) & rec[i][key]) for i in lab], dtype=np.float64) for m in MS for key in ('fam', 'gold') for k in (1, 5)}
    bt = np.random.default_rng(3); idx = [bt.integers(0, len(lab), len(lab)) for _ in range(NBOOT)]
    def rel(m, ref='M0', key='fam', k=5):
        x, y = hit[(m, key, k)], hit[(ref, key, k)]
        f = lambda ix: x[ix].sum() / y[ix].sum() - 1 if y[ix].sum() > 0 else float('nan')
        return dict(valor=round(float(f(slice(None))), 4), ic95=ci([f(ix) for ix in idx]))
    acerto = {m: {f'{"familia" if key == "fam" else "marcada"}_top{k}': round(float(hit[(m, key, k)].sum() / N), 4) for key in ('fam', 'gold') for k in (1, 5)} for m in MS}

    # ---------- 4b. juiz ----------
    g = random.Random(2025)
    JL = g.sample(lab, min(N_JL, len(lab))); JU = g.sample(unl, min(N_JU, len(unl)))
    POS = g.sample([i for i in lab if i not in set(JL)], N_CTRL); NEG = g.sample([i for i in unl if i not in set(JU)], N_CTRL)
    NEGj = [g.randrange(0, i) for i in NEG]
    judge_fp = sha([a.judge, judge_digest, PROMPT, JUDGE_WORDS, data_sha])[:16]
    cpath = f"gc_cache/juiz_conf_{judge_fp}.jsonl"; cache = {}
    if os.path.exists(cpath):
        for line in open(cpath, encoding='utf-8'):
            try: d = json.loads(line); cache[(d['a'], d['b'])] = d['v']
            except Exception: pass
    print(f'  juiz: {len(cache)} julgamentos já salvos', flush=True)
    cfile = open(cpath, 'a', encoding='utf-8'); words = lambda i, k: ' '.join(texts[i].split()[:k])
    st = dict(shown=0, new=0, invalid=0, think=True)
    def judge(i, j):
        key = (int(ids[i]), int(ids[j]))
        if key in cache: return cache[key]
        payload = {'model': a.judge, 'stream': False, 'prompt': PROMPT.format(a=words(i, JUDGE_WORDS), b=words(j, JUDGE_WORDS)),
                   'options': {'temperature': 0, 'num_predict': 64}}
        if st['think']: payload['think'] = False
        try:
            try: r = post(a.host, '/api/generate', payload)
            except urllib.error.HTTPError:
                if not st['think']: raise
                st['think'] = False; payload.pop('think'); r = post(a.host, '/api/generate', payload)
        except urllib.error.URLError as e:
            sys.exit(f'O Ollama não respondeu ({e}). Abra o Ollama e rode o mesmo comando: os julgamentos feitos ficam salvos.')
        raw = (r.get('response') or '').strip()
        if st['shown'] < 3: print(f'  resposta crua {st["shown"] + 1}: {raw[:80]!r}', flush=True); st['shown'] += 1
        m = re.search(r'\b(YES|NO)\b', raw.upper()); v = None if m is None else m.group(1) == 'YES'
        st['new'] += 1; st['invalid'] += v is None
        if st['new'] == 20 and st['invalid'] >= 10: sys.exit(f'O juiz não respondeu YES/NO em {st["invalid"]} dos primeiros 20. Veja as respostas cruas acima.')
        cache[key] = v
        if v is not None: cfile.write(json.dumps({'a': key[0], 'b': key[1], 'v': v}) + '\n'); cfile.flush()
        return v
    J = {}
    for k, i in enumerate(JL + JU):
        J[i] = {m: judge(i, rec[i][m][0]) for m in ('M0', 'M1', 'M2')}
        if (k + 1) % 50 == 0: print(f'  juiz: {k + 1}/{len(JL) + len(JU)}', flush=True)
    yP = [judge(i, sorted(earlier(i))[0]) for i in POS]; yN = [judge(i, j) for i, j in zip(NEG, NEGj)]
    if st['new'] and st['invalid'] > 0.2 * st['new']: sys.exit(f'O juiz não respondeu YES/NO em {st["invalid"]} de {st["new"]} julgamentos.')
    wL, wU = len(lab) / N, (N - len(lab)) / N
    def wdiff(m, ref):
        grp = lambda G: np.array([float(J[i][m]) - float(J[i][ref]) for i in G if J[i][m] is not None and J[i][ref] is not None])
        dL, dU = grp(JL), grp(JU); b = np.random.default_rng(5)
        boots = [wL * dL[b.integers(0, len(dL), len(dL))].mean() + wU * dU[b.integers(0, len(dU), len(dU))].mean() for _ in range(NBOOT)]
        return dict(diferenca_ponderada=round(float(wL * dL.mean() + wU * dU.mean()), 4), ic95=ci(boots),
                    discordantes={'marcada': [int((dL < 0).sum()), int((dL > 0).sum())], 'sem_marcacao': [int((dU < 0).sum()), int((dU > 0).sum())]})
    yes = lambda G, m: round(float(np.mean([J[i][m] for i in G if J[i][m] is not None])), 3)

    # ---------- 4c. conjunto cego (chave em arquivo separado) ----------
    gb = random.Random(4242); items = [('controle', 'duplicata_marcada', i, sorted(earlier(i))[0]) for i in POS[:N_BLIND_CTRL]]
    pool = JL + JU
    used_q = set()
    for m in ('M0', 'M1', 'M2'):
        cand = [i for i in gb.sample(pool, len(pool)) if i not in used_q][:N_BLIND_SUG // 3]
        for i in cand: items.append(('sugestao', m, i, rec[i][m][0])); used_q.add(i)
    gb.shuffle(items); key = []; blind_q = {it[2] for it in items}
    with open('gc_conf_cegos.txt', 'w', encoding='utf-8') as f:
        f.write('Para cada item: uma resposta correta a B resolveria o problema de A? (SIM / NÃO)\n')
        for k, (kind, m, i, j) in enumerate(items, 1):
            f.write(f'\n#{k}\n  A: {words(i, BLIND_WORDS)}\n  B: {words(j, BLIND_WORDS)}\n')
            fam_ok = (j in rec[i]['fam']) if i in rec and 'fam' in rec[i] else ((j in earlier(i)) if kind == 'controle' else None)
            key.append({'n': k, 'tipo': kind, 'metodo': m, 'grupo': 'marcada' if earlier(i) else 'sem_marcacao',
                        'gemma': cache.get((int(ids[i]), int(ids[j]))), 'na_familia_marcada': fam_ok})
    json.dump(key, open('gc_conf_chave.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)

    # ---------- resultado ----------
    tpr = float(np.mean([v for v in yP if v is not None])); fpr = float(np.mean([v for v in yN if v is not None]))
    judge_ok = tpr >= J_MIN_TPR and fpr <= J_MAX_FPR and tpr - fpr >= J_MIN_GAP
    p1, p3, p2 = rel('M1'), rel('H'), wdiff('M1', 'M0'); s1 = wdiff('M2', 'M1')
    P1 = bool(p1['ic95'] and p1['ic95'][0] > P_MIN_REL); P3 = bool(p3['ic95'] and p3['ic95'][0] > P_MIN_REL)
    P2 = bool(p2['ic95'] and p2['ic95'][0] >= P_MIN_JUDGE) if judge_ok else 'inconclusivo (juiz reprovado nos controles)'
    S1 = bool(s1['ic95'] and s1['ic95'][1] < 0) if judge_ok else 'inconclusivo (juiz reprovado nos controles)'
    decision = 'NAO' if not (P1 and P3) else ('INCONCLUSIVO (juiz reprovado nos controles)' if not judge_ok else ('SIM' if P2 is True else 'NAO'))
    crit = {'juiz_valido (sens >= 0,30; falsos pos. <= 0,15; diferenca >= 0,25)': judge_ok,
            'P1_familia_M1_ganho_relativo_IC_inferior_>_10%': P1, 'P2_juiz_M1_menos_M0_IC_inferior_>=_-0,03': P2,
            'P3_familia_H_ganho_relativo_IC_inferior_>_10%': P3, 'S1_bonus_piora_M2_menos_M1_IC_superior_<_0': S1, 'CONFIRMA': decision}
    worse = [i for i in JL + JU if i not in blind_q and J[i]['M0'] and J[i]['M2'] is False and rec[i]['M2'][0] != rec[i]['M0'][0]]
    ex = [{'pergunta': texts[i][:110], 'M0': texts[rec[i]['M0'][0]][:110], 'M1': texts[rec[i]['M1'][0]][:110], 'M2': texts[rec[i]['M2'][0]][:110],
           'juiz': J[i], 'ligacoes_M2': int(deg[rec[i]['M2'][0]])} for i in random.Random(9).sample(worse, min(10, len(worse)))]
    out = {'dados': info, 'modelo_juiz': a.judge, 'julgamentos_novos': st['new'], 'respostas_invalidas': st['invalid'],
           'acerto_sem_llm': acerto,
           'familia_top5_ganho_relativo_sobre_M0': {m: rel(m) for m in ('M1', 'M2', 'H', 'H1')},
           'marcada_top5_ganho_relativo_sobre_M0': {m: rel(m, key='gold') for m in ('M1', 'M2', 'H')},
           'juiz_1a_sugestao': {'M1_menos_M0': p2, 'M2_menos_M1 (bonus)': s1, 'M2_menos_M0': wdiff('M2', 'M0'),
                                'sim_bruto': {gname: {m: yes(G, m) for m in ('M0', 'M1', 'M2')} for gname, G in (('marcada', JL), ('sem_marcacao', JU))},
                                'controles': {'sensibilidade': round(tpr, 3), 'falsos_positivos': round(fpr, 3)}},
           'pesos': {'marcada': round(wL, 4), 'sem_marcacao': round(wU, 4)},
           'criterios': crit, 'exemplos_M2_piorou': ex,
           'reproducao': {'dados_sha256': data_sha, 'preprocessamento': PREPROC, 'embeddings': {'modelo': a.embed, 'digest': emb_digest},
                          'juiz': {'modelo': a.judge, 'digest': judge_digest, 'cache': os.path.basename(cpath)}, 'ollama': ollama_version}, 'minutos_nesta_execucao': round((time.time() - t_start) / 60, 1)}
    json.dump(out, open('gc_conf_result.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in out.items() if k != 'exemplos_M2_piorou'}, ensure_ascii=False, indent=1))
    print('\nPronto. Envie gc_conf_result.json e gc_conf_cegos.txt. NÃO envie gc_conf_chave.json ainda.')

if __name__ == '__main__':
    main()
