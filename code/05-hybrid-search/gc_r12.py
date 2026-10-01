"""Grande Cérebro, Rodada 12: as ligações confirmadas ainda ajudam sobre uma busca forte?

Rode na mesma pasta do gc_conf.py, depois da confirmação (usa gc_data/au24_*, gc_cache/au24_*_nomic-embed-text.npy
e gc_conf_result.json). Só recuperação: sem LLM gerando respostas e sem juiz.

Passo 1  baixe os modelos candidatos (uma vez):
           ollama pull mxbai-embed-large
           ollama pull bge-m3
           ollama pull embeddinggemma
           ollama pull qwen3-embedding:0.6b
           ollama pull qwen3-embedding:4b
Passo 2  python3 gc_r12.py piloto
         escolhe o modelo pela regra congelada: maior MAP no dev do AskUbuntu de Lei et al. (dados exploratórios),
         entre os que cabem em uma noite no Mac. Baixa dev.txt e text_tokenized.txt.gz se faltarem.
         cria r12_piloto.json (só números)                               -> ENVIE
Passo 3  python3 gc_r12.py rodar
         usa o modelo escolhido no piloto; calcula os embeddings de todo o acervo (a parte longa, uma noite),
         a busca por palavras (BM25), a busca híbrida e as ligações sobre cada uma.
         pode parar e rodar de novo: os embeddings feitos ficam salvos e ele continua de onde parou.
         cria r12_resultado.json (só números)                            -> ENVIE

Comparação principal, fixada antes: HIB_E, a fusão de postos (RRF, k = 60) das 100 primeiras do BM25 e das 100
primeiras do M0_E (embeddings do modelo selecionado pelo piloto). L(HIB_E) é a mesma fusão com o M1_E (o M1
congelado no espaço do modelo selecionado) no lugar do M0_E. H1(HIB_E) = B1, L1, B2, L2, ... pulando repetidos,
até 5 sugestões; a 1ª sugestão nunca muda.
  F1: ganho relativo de H1(HIB_E) sobre HIB_E na família marcada no top-5, limite inferior do IC 95% > 10%
  F2: o mesmo com limite inferior > 0
  leitura: IC acima de 10%; acima de 0; contendo 0 (inconclusivo); inteiro abaixo de 0 (piora)
"""
import argparse, array, collections, gzip, hashlib, json, os, random, re, sys, time, urllib.request, urllib.error
import numpy as np
from scipy.sparse import csr_matrix
import gc_conf as G

VERSAO = 'r12-v1'
PFX = 'au24'
NOMIC = 'nomic-embed-text'
CANDIDATOS = ['mxbai-embed-large', 'bge-m3', 'embeddinggemma', 'qwen3-embedding:0.6b', 'qwen3-embedding:4b']
QWEN_TASK = 'Given a question posted on Ask Ubuntu, retrieve earlier questions that describe the same problem'
PREFIXOS = {   # (pergunta nova, pergunta da memória), como nos cartões dos modelos
    'nomic-embed-text': ('search_query: ', 'search_document: '),
    'mxbai-embed-large': ('Represent this sentence for searching relevant passages: ', ''),
    'bge-m3': ('', ''),
    'embeddinggemma': ('task: search result | query: ', 'title: none | text: '),
    'qwen3-embedding:0.6b': (f'Instruct: {QWEN_TASK}\nQuery:', ''),
    'qwen3-embedding:4b': (f'Instruct: {QWEN_TASK}\nQuery:', ''),
}
LEI = 'https://raw.githubusercontent.com/taolei87/askubuntu/master/'
MAX_HORAS, MAX_HORAS_2 = 10.0, 24.0   # uma noite no Mac; se nenhum couber, o mais rápido que caiba em 24 h (retomável)
N_TEMPO, SEED_TEMPO = 1000, 1212      # textos da confirmação usados só para medir o tempo
BM25_K1, BM25_B, RRF_K, RRF_TOP = 1.2, 0.75, 60, 100
P_MIN_REL = 0.10
KS = (5, 10, 20, 50)
PILOTO, OUT = 'r12_piloto.json', 'r12_resultado.json'
TOKEN = re.compile(r'\w+')

def file_sha(path): return hashlib.sha256(open(path, 'rb').read()).hexdigest()
def tagof(model): return model.replace(':', '_').replace('/', '_')
def prefixos(model):
    if model not in PREFIXOS: sys.exit(f'Modelo {model} fora da lista pré-registrada.')
    return PREFIXOS[model]

def fetch(name):
    os.makedirs('gc_data', exist_ok=True); path = os.path.join('gc_data', name)
    if not os.path.exists(path):
        print('  baixando', name, flush=True)
        try: urllib.request.urlretrieve(LEI + name, path + '.tmp'); os.replace(path + '.tmp', path)
        except Exception as e: sys.exit(f'Não consegui baixar {name} ({e}). Baixe em {LEI}{name} e coloque em gc_data/.')
    return path

def embed(host, model, texts, batch=32):
    out = []
    for b in range(0, len(texts), batch):
        try: vecs = G.post(host, '/api/embed', {'model': model, 'input': texts[b:b + batch]})['embeddings']
        except urllib.error.HTTPError as e: raise RuntimeError(f'erro HTTP {e.code} do Ollama')
        except urllib.error.URLError as e: sys.exit(f'O Ollama não respondeu ({e}). Abra o Ollama e rode o mesmo comando.')
        except (KeyError, ValueError, TypeError) as e: raise RuntimeError(f'resposta inesperada do Ollama: {e}')
        out.extend(vecs)
    M = np.array(out, dtype=np.float32)
    return M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)

def show(host, model):
    """Configuração do modelo no Ollama: quantização, parâmetros, dimensão e limite de entrada."""
    try: r = G.post(host, '/api/show', {'model': model}, timeout=60)
    except Exception as e: return {'erro': str(e)}
    d, mi = r.get('details', {}) or {}, r.get('model_info', {}) or {}
    pick = lambda suf: next((v for k, v in mi.items() if k.endswith(suf)), None)
    return {'formato': d.get('format'), 'familia': d.get('family'), 'parametros': d.get('parameter_size'), 'quantizacao': d.get('quantization_level'),
            'dimensao': pick('.embedding_length'), 'limite_de_entrada_tokens': pick('.context_length'),
            'truncamento': 'padrão do /api/embed (truncate = true): texto acima do limite é cortado'}

def load_conf():
    qpath, lpath, mpath = f'gc_data/{PFX}_perguntas.jsonl.gz', f'gc_data/{PFX}_duplicatas.tsv', f'gc_data/{PFX}_meta.json'
    for p in (qpath, lpath, mpath):
        if not os.path.exists(p): sys.exit(f'Não achei {p}. Rode na pasta da confirmação (a do gc_conf.py).')
    meta = json.load(open(mpath))
    if meta.get('preproc') != G.PREPROC or meta.get('T0') != G.T0: sys.exit('Os dados salvos não são os da confirmação (pré-processamento ou T0 diferentes).')
    ids, dates, texts = [], [], []
    for line in gzip.open(qpath, 'rt', encoding='utf-8'): i, d, t = json.loads(line); ids.append(i); dates.append(d); texts.append(t)
    return lpath, ids, dates, texts

# ---------------------------------------------------------------- piloto
def piloto(a):
    t_start = time.time()
    try: version = json.loads(urllib.request.urlopen(a.host + '/api/version', timeout=30).read()).get('version')
    except Exception as e: sys.exit(f'Não consegui falar com o Ollama em {a.host}: {e}')
    tags = json.loads(urllib.request.urlopen(a.host + '/api/tags', timeout=30).read()).get('models', [])
    have = {m.get('name') for m in tags} | {m.get('model') for m in tags}
    falta = [m for m in [NOMIC] + CANDIDATOS if m not in have and m + ':latest' not in have]
    if falta: sys.exit('Faltam modelos no Ollama. Rode:\n' + '\n'.join(f'  ollama pull {m}' for m in falta))
    # dev do AskUbuntu de Lei et al. (dados exploratórios; o teste desse conjunto já foi usado na rodada 6)
    texts = {}
    for line in gzip.open(fetch('text_tokenized.txt.gz'), 'rt', encoding='utf-8'):
        p = line.rstrip('\n').split('\t')
        texts[int(p[0])] = ' '.join(((p[1] if len(p) > 1 else '') + ' . ' + (p[2] if len(p) > 2 else '')).split()[:G.MAX_WORDS])
    queries = []
    for line in open(fetch('dev.txt'), encoding='utf-8'):
        p = line.rstrip('\n').split('\t'); sim = set(map(int, p[1].split())) if p[1].strip() else set()
        cand = list(map(int, p[2].split()))
        if sim & set(cand): queries.append((int(p[0]), sim, cand))
    need = sorted({x for _, _, c in queries for x in c})
    print(f'  dev de Lei et al.: {len(queries)} perguntas com duplicata entre as 20 candidatas, {len(need)} candidatas', flush=True)
    _, _, _, ctexts = load_conf(); n_total = len(ctexts)
    tsample = [ctexts[k] for k in random.Random(SEED_TEMPO).sample(range(n_total), min(N_TEMPO, n_total))]
    parc_path = 'r12_piloto_parcial.json'
    parc = json.load(open(parc_path)) if os.path.exists(parc_path) else {}
    digests = {m.get('name'): m.get('digest') for m in tags}
    for model in [NOMIC] + CANDIDATOS:
        dg = digests.get(model) or digests.get(model + ':latest')
        if model in parc and parc[model].get('digest') == dg: print(f'  {model}: já medido', flush=True); continue
        pq, pd = prefixos(model); print(f'  {model}: medindo', flush=True)
        try:
            Qv = embed(a.host, model, [pq + texts[q] for q, _, _ in queries]); Dv = embed(a.host, model, [pd + texts[x] for x in need])
            col = {x: k for k, x in enumerate(need)}; aps, rrs, p1s = [], [], []
            for qi, (q, sim, cand) in enumerate(queries):
                sc = Dv[[col[x] for x in cand]] @ Qv[qi]; order = [cand[k] for k in np.argsort(-sc, kind='stable')]
                hits = [x in sim for x in order]; prec = [sum(hits[:r + 1]) / (r + 1) for r, h in enumerate(hits) if h]
                aps.append(float(np.mean(prec))); rrs.append(1.0 / (hits.index(True) + 1)); p1s.append(float(hits[0]))
            embed(a.host, model, [pd + t for t in tsample[:32]])                   # aquecimento (carrega o modelo)
            t0 = time.time(); embed(a.host, model, [pd + t for t in tsample], batch=64); sec = (time.time() - t0) / len(tsample)
            parc[model] = {'digest': dg, 'MAP': round(float(np.mean(aps)), 4), 'MRR': round(float(np.mean(rrs)), 4), 'P1': round(float(np.mean(p1s)), 4),
                           'dimensao': int(Dv.shape[1]), 'segundos_por_1000_textos': round(sec * 1000, 1),
                           'horas_estimadas_acervo': round(sec * (n_total + 11000) / 3600, 2), 'configuracao': show(a.host, model)}
        except RuntimeError as e:
            parc[model] = {'digest': dg, 'erro': str(e)}
        print(f'    {json.dumps(parc[model], ensure_ascii=False)}', flush=True)
        json.dump(parc, open(parc_path, 'w'), indent=1)
    ok = [m for m in CANDIDATOS if 'MAP' in parc[m]]
    elig = [m for m in ok if parc[m]['horas_estimadas_acervo'] <= MAX_HORAS]
    if elig: best = max(elig, key=lambda m: (parc[m]['MAP'], -parc[m]['horas_estimadas_acervo']))
    else:
        elig2 = [m for m in ok if parc[m]['horas_estimadas_acervo'] <= MAX_HORAS_2]
        if not elig2: sys.exit(f'Nenhum candidato cabe em {MAX_HORAS_2} horas: pela regra, a rodada não roda com estes candidatos. Envie {parc_path}.')
        best = min(elig2, key=lambda m: parc[m]['horas_estimadas_acervo'])
    out = {'versao': VERSAO, 'regra': (f'maior MAP no dev de Lei et al. entre os candidatos com tempo estimado <= {MAX_HORAS} h (empate: o mais rápido); '
                                       f'se nenhum couber, o mais rápido com tempo <= {MAX_HORAS_2} h; se nem isso, a rodada não roda'),
           'dev_perguntas': len(queries), 'dev_candidatas': len(need), 'acervo_textos': n_total, 'modelos': {m: parc[m] for m in [NOMIC] + CANDIDATOS},
           'elegiveis': elig, 'modelo_escolhido': best, 'prefixos': {m: PREFIXOS[m] for m in [NOMIC] + CANDIDATOS},
           'ollama': version, 'script_sha256': file_sha(os.path.abspath(__file__)), 'minutos': round((time.time() - t_start) / 60, 1)}
    json.dump(out, open(PILOTO, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(json.dumps({k: out[k] for k in ('modelos', 'elegiveis', 'modelo_escolhido')}, ensure_ascii=False, indent=1))
    print(f'\nPronto. Envie {PILOTO}. Depois rode: python3 gc_r12.py rodar')

# ---------------------------------------------------------------- BM25
def bm25_index(texts, e0):
    """Pesos BM25 por documento (k1=1,2; b=0,75), sem stopwords do scikit-learn; IDF e tamanho médio só das perguntas anteriores a T0."""
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    vocab, rows_, cols, vals, dl = {}, array.array('i'), array.array('i'), array.array('f'), np.zeros(len(texts), np.float32)
    for d, t in enumerate(texts):
        c = collections.Counter(w for w in TOKEN.findall(t) if w not in ENGLISH_STOP_WORDS)
        dl[d] = sum(c.values())
        for w, f in c.items(): rows_.append(d); cols.append(vocab.setdefault(w, len(vocab))); vals.append(f)
        if d % 100000 == 0: print(f'    BM25: {d}/{len(texts)}', flush=True)
    TF = csr_matrix((np.frombuffer(vals, np.float32), (np.frombuffer(rows_, np.int32), np.frombuffer(cols, np.int32))), shape=(len(texts), len(vocab)))
    del rows_, cols, vals
    df0 = np.bincount(TF[:e0].indices, minlength=len(vocab)).astype(np.float64)
    idf = np.log(1 + (e0 - df0 + 0.5) / (df0 + 0.5)).astype(np.float32); avgdl = float(dl[:e0].mean())
    W = TF.tocoo(); norm = BM25_K1 * (1 - BM25_B + BM25_B * dl[W.row] / avgdl)
    W = csr_matrix((idf[W.col] * W.data * (BM25_K1 + 1) / (W.data + norm), (W.row, W.col)), shape=TF.shape).tocsc()
    return vocab, W

def bm25_scores(vocab, W, text, n):
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    terms = sorted({vocab[w] for w in TOKEN.findall(text) if w not in ENGLISH_STOP_WORDS and w in vocab})
    if not terms: return np.zeros(n, np.float32)
    idx = np.concatenate([W.indices[W.indptr[t]:W.indptr[t + 1]] for t in terms])
    val = np.concatenate([W.data[W.indptr[t]:W.indptr[t + 1]] for t in terms])
    return np.bincount(idx, weights=val, minlength=n).astype(np.float32)

def topk(v, k):
    k = min(k, int(np.isfinite(v).sum()))
    if k <= 0: return []
    t = np.argpartition(-v, k - 1)[:k]; return [int(x) for x in t[np.lexsort((t, -v[t]))]]

def rrf_scores(a, b):
    sc = collections.defaultdict(float)
    for lst in (a, b):
        for r, x in enumerate(lst): sc[x] += 1.0 / (RRF_K + r + 1)
    return dict(sc)
def ranked(sc): return [x for x, _ in sorted(sc.items(), key=lambda kv: (-kv[1], kv[0]))]

# ---------------------------------------------------------------- rodar
def rodar(a):
    t_start = time.time()
    if not os.path.exists(PILOTO): sys.exit(f'Falta {PILOTO}. Rode primeiro: python3 gc_r12.py piloto')
    tm = collections.defaultdict(float)
    pil = json.load(open(PILOTO, encoding='utf-8')); E = pil['modelo_escolhido']
    if E not in CANDIDATOS: sys.exit(f'O modelo escolhido ({E}) não está na lista pré-registrada.')
    if not os.path.exists('gc_conf_result.json'): sys.exit('Falta gc_conf_result.json (resultado da confirmação) nesta pasta.')
    conf = json.load(open('gc_conf_result.json', encoding='utf-8'))
    nomic_digest, ollama_version = G.ollama(a.host, NOMIC); e_digest, _ = G.ollama(a.host, E)
    if pil['modelos'][E].get('digest') not in (None, e_digest): sys.exit(f'O {E} mudou desde o piloto (digest diferente).')
    lpath, ids, dates, texts = load_conf(); T0 = G.T0
    pos = {q: k for k, q in enumerate(ids)}; n = len(ids)
    dups = collections.defaultdict(set); mem_pairs = set()
    for line in open(lpath):
        p, q, d = line.rstrip('\n').split('\t'); p, q = int(p), int(q)
        if p in pos and q in pos and p != q:
            dups[p].add(q); dups[q].add(p); x, y = sorted((pos[p], pos[q]))
            if d < T0 and dates[y] < T0: mem_pairs.add((x, y))
    e0 = next((k for k, d in enumerate(dates) if d >= T0), n)
    earlier = lambda i: {pos[s] for s in dups.get(ids[i], ()) if pos[s] < i}
    lab = [i for i in range(e0, n) if earlier(i)]; unl_all = [i for i in range(e0, n) if not earlier(i)]
    N = n - e0; unl = random.Random(2024).sample(unl_all, min(G.N_UNL, len(unl_all)))   # mesma amostra da confirmação (reaproveita o cache)
    data_sha = G.sha(f'{i}|{d}|{t}' for i, d, t in zip(ids, dates, texts))
    if data_sha != conf['reproducao']['dados_sha256']: sys.exit('Os dados não são os mesmos da confirmação (SHA-256 diferente).')
    qrows = sorted(set(lab) | set(unl)); qidx = {i: j for j, i in enumerate(qrows)}
    print(f'  {n} perguntas, {N} novas, {len(lab)} com duplicata marcada anterior, {len(mem_pairs)} ligações na memória', flush=True)

    print('1. embeddings do nomic-embed-text (do cache da confirmação)', flush=True)
    pq, pd = prefixos(NOMIC)
    Qn = np.asarray(G.embed_matrix(a.host, NOMIC, nomic_digest, [texts[i] for i in qrows], f'gc_cache/{PFX}_q_{tagof(NOMIC)}.npy', pq), dtype=np.float32)
    Dn = np.asarray(G.embed_matrix(a.host, NOMIC, nomic_digest, texts, f'gc_cache/{PFX}_d_{tagof(NOMIC)}.npy', pd), dtype=np.float32)
    print(f'2. embeddings do {E}: perguntas novas e depois todo o acervo (a parte longa)', flush=True)
    pq, pd = prefixos(E); t_emb = time.time()
    Qe = np.asarray(G.embed_matrix(a.host, E, e_digest, [texts[i] for i in qrows], f'gc_cache/{PFX}_q_{tagof(E)}.npy', pq), dtype=np.float32)
    De = np.asarray(G.embed_matrix(a.host, E, e_digest, texts, f'gc_cache/{PFX}_d_{tagof(E)}.npy', pd), dtype=np.float32)
    min_emb = round((time.time() - t_emb) / 60, 1)

    print('3. índice BM25 (alguns minutos)', flush=True)
    t0 = time.time(); vocab, W = bm25_index(texts, e0); tm['construir_bm25_s'] = time.time() - t0

    print('4. avaliação', flush=True)
    P = sorted(mem_pairs)
    A = csr_matrix((np.ones(2 * len(P), dtype=np.float32), ([x for x, y in P] + [y for x, y in P], [y for x, y in P] + [x for x, y in P])), shape=(n, n))
    A.sum_duplicates(); A.data[:] = 1
    deg = np.diff(A.indptr).astype(np.float32); Hn = np.where(deg > 0)[0]; starts = A.indptr[Hn]; logdeg = np.log1p(deg)
    t0 = time.time(); Cn = G.normalize(Dn[Hn] + np.asarray(A[Hn] @ Dn)); tm['construir_rede_nomic_s'] = time.time() - t0
    t0 = time.time(); Ce = G.normalize(De[Hn] + np.asarray(A[Hn] @ De)); tm['construir_rede_E_s'] = time.time() - t0
    def m1(s, C, qv):
        m = s.copy(); m[Hn] = np.maximum(np.maximum(m[Hn], np.maximum.reduceat(s[A.indices], starts)), C @ qv)
        m[Hn] = np.where(np.isfinite(s[Hn]), m[Hn], -np.inf); return m
    rec = {}; KMAX = max(KS + (RRF_TOP,)); labset = set(lab); rows_eval = lab + unl   # mesmos lotes da confirmação
    for b0 in range(0, len(rows_eval), 128):
        R = rows_eval[b0:b0 + 128]; QN = Qn[[qidx[i] for i in R]]; QE = Qe[[qidx[i] for i in R]]; frac = sum(i in labset for i in R) / len(R)
        t0 = time.time(); SN = QN @ Dn.T; tm['busca_nomic_s'] += (time.time() - t0) * frac
        t0 = time.time(); SE = QE @ De.T; tm['busca_E_s'] += (time.time() - t0) * frac
        for j, i in enumerate(R):
            if i not in labset: continue
            sn, se = SN[j], SE[j]; sn[i:] = -np.inf; se[i:] = -np.inf
            t0 = time.time(); sb = bm25_scores(vocab, W, texts[i], n); sb[i:] = -np.inf; tm['busca_BM25_s'] += time.time() - t0
            t0 = time.time(); m1n = m1(sn, Cn, QN[j]); tm['ligacoes_nomic_s'] += time.time() - t0; t0 = time.time(); m1e = m1(se, Ce, QE[j]); tm['ligacoes_E_s'] += time.time() - t0
            r = {'M0_nomic': G.top5(sn), 'M1_nomic': G.top5(m1n), 'M2_nomic': G.top5(m1n + G.BETA * logdeg),
                 'M0_E': G.top5(se), 'M1_E': G.top5(m1e), 'M2_E': G.top5(m1e + G.BETA * logdeg)}
            tb, te, tn = topk(sb, RRF_TOP), topk(se, KMAX), topk(sn, RRF_TOP)
            t0 = time.time(); he = rrf_scores(tb, te[:RRF_TOP]); hel = ranked(he); tm['fusao_s'] += time.time() - t0; hn = rrf_scores(tb, tn)
            r['BM25'] = tb[:5]; r['HIB_E'] = hel[:5]; r['HIB_nomic'] = ranked(hn)[:5]
            t0 = time.time(); r['L_HIB_E'] = ranked(rrf_scores(tb, topk(m1e, RRF_TOP)))[:5]; tm['fusao_com_ligacoes_s'] += time.time() - t0; r['L_HIB_nomic'] = ranked(rrf_scores(tb, topk(m1n, RRF_TOP)))[:5]
            r['H1_nomic'] = G.inter(r['M0_nomic'], r['M1_nomic']); r['H_nomic'] = G.inter(r['M0_nomic'], r['M2_nomic'])
            r['H1_E'] = G.inter(r['M0_E'], r['M1_E']); r['H_E'] = G.inter(r['M0_E'], r['M2_E'])
            r['H1_HIB_E'] = G.inter(r['HIB_E'], r['L_HIB_E']); r['H1_HIB_nomic'] = G.inter(r['HIB_nomic'], r['L_HIB_nomic'])
            g = earlier(i); fs = set(g)
            for x in g: fs |= set(A.indices[A.indptr[x]:A.indptr[x + 1]].tolist())
            r['gold'], r['fam'] = g, fs
            r['cand_E'] = te; r['cand_BM25'] = tb[:KMAX]; r['cand_HIB_E'] = hel[:KMAX]
            rec[i] = r
        if (b0 // 128) % 5 == 0: print(f'  {min(b0 + 128, len(rows_eval))}/{len(rows_eval)}', flush=True)

    MS = ['M0_nomic', 'M1_nomic', 'M2_nomic', 'H_nomic', 'H1_nomic', 'BM25', 'HIB_nomic', 'L_HIB_nomic', 'H1_HIB_nomic',
          'M0_E', 'M1_E', 'M2_E', 'H_E', 'H1_E', 'HIB_E', 'L_HIB_E', 'H1_HIB_E']
    hit = {(m, key, k): np.array([bool(set(rec[i][m][:k]) & rec[i][key]) for i in lab], dtype=np.float64) for m in MS for key in ('fam', 'gold') for k in (1, 5)}
    # reprodução: os métodos com nomic precisam dar os números da confirmação (tolerância de 0,0001, cerca de 10 perguntas)
    repro = {}
    for m_conf, m_here in (('M0', 'M0_nomic'), ('M1', 'M1_nomic'), ('M2', 'M2_nomic'), ('H', 'H_nomic'), ('H1', 'H1_nomic')):
        v, c = round(float(hit[(m_here, 'fam', 5)].sum() / N), 4), conf['acerto_sem_llm'][m_conf]['familia_top5']; repro[m_conf] = [v, c]
        if abs(v - c) > 0.0001: sys.exit(f'Reprodução falhou: {m_conf} deu {v}, a confirmação deu {c}. Envie esta linha.')
    for i in lab:   # a 1ª sugestão de H1(B) é sempre a de B
        for b, h in (('M0_E', 'H1_E'), ('HIB_E', 'H1_HIB_E'), ('HIB_nomic', 'H1_HIB_nomic')):
            if rec[i][b] and rec[i][h][0] != rec[i][b][0]: sys.exit('Erro interno: H1 mudou a 1ª sugestão.')
    bt = np.random.default_rng(3); idx = [bt.integers(0, len(lab), len(lab)) for _ in range(G.NBOOT)]; bt2 = np.random.default_rng(7)
    def rel(m, ref, key='fam', k=5, sub=None):
        x, y = hit[(m, key, k)], hit[(ref, key, k)]
        if sub is not None: x, y = x[sub], y[sub]
        f = lambda ix: x[ix].sum() / y[ix].sum() - 1 if y[ix].sum() > 0 else float('nan')
        ixs = idx if sub is None else [bt2.integers(0, len(x), len(x)) for _ in range(G.NBOOT)]
        return dict(valor=round(float(f(slice(None))), 4), ic95=G.ci([f(ix) for ix in ixs]), acertos=[int(x.sum()), int(y.sum())])
    acerto = {m: {f'{"familia" if key == "fam" else "marcada"}_top{k}': round(float(hit[(m, key, k)].sum() / N), 4) for key in ('fam', 'gold') for k in (1, 5)} for m in MS}
    h1_of = {'M0_E': 'H1_E', 'HIB_E': 'H1_HIB_E', 'HIB_nomic': 'H1_HIB_nomic'}; B = 'HIB_E'   # comparação principal fixada antes
    f1 = rel(h1_of[B], B); lo, hi = f1['ic95'] if f1['ic95'] else (float('nan'), float('nan'))
    F1 = bool(lo > P_MIN_REL); F2 = bool(lo > 0)
    leitura = ('ganho acima de 10% sustentado pelo critério' if F1 else
               'ganho positivo demonstrado; ganho acima de 10% não demonstrado' if F2 else
               'evidência de piora' if hi < 0 else
               'ganho não demonstrado; resultado inconclusivo quanto à direção')
    yr = np.array([dates[i][:4] in ('2020', '2021') for i in lab])
    por_ano = {'2020-2021': rel(h1_of[B], B, sub=np.where(yr)[0]), '2022-2024': rel(h1_of[B], B, sub=np.where(~yr)[0]),
               'perguntas': {'2020-2021': int(yr.sum()), '2022-2024': int((~yr).sum())}}
    cand = {f'cand_{b}': {f'top{k}': round(float(np.mean([bool(set(rec[i][f'cand_{b}'][:k]) & rec[i]['fam']) for i in lab])), 4) for k in KS}
            for b in ('E', 'BM25', 'HIB_E')}
    out = {'versao': VERSAO, 'modelo_E': E,
           'dados': {'perguntas': n, 'perguntas_na_avaliacao': N, 'com_duplicata_marcada_anterior': len(lab), 'teto_marcada': round(len(lab) / max(N, 1), 4),
                     'ligacoes_na_memoria': len(mem_pairs)},
           'acerto_sem_llm': acerto,
           'comparacao_principal': 'H1(HIB_E) sobre HIB_E',
           'criterios': {'F1_H1(HIB_E)_sobre_HIB_E_familia_top5_ganho_relativo_IC_inferior_>_10%': F1,
                         'F2_H1(HIB_E)_sobre_HIB_E_IC_inferior_>_0': F2, 'leitura_pre_registrada': leitura},
           'F1_ganho_H1_sobre_HIB_E': f1,
           'qual_busca_sem_ligacoes_acertou_mais (descritivo)': {b: int(hit[(b, 'fam', 5)].sum()) for b in ('M0_nomic', 'BM25', 'HIB_nomic', 'M0_E', 'HIB_E')},
           'ganho_das_ligacoes_sobre_cada_busca (H1 sobre a busca)': {b: rel(h1_of[b], b) for b in ('M0_E', 'HIB_E', 'HIB_nomic')}
                                                                     | {'M0_nomic (confirmação)': rel('H1_nomic', 'M0_nomic')},
           'ligacoes_sozinhas_sobre_cada_busca (L sobre a busca)': {'M0_E': rel('M1_E', 'M0_E'), 'HIB_E': rel('L_HIB_E', 'HIB_E'), 'HIB_nomic': rel('L_HIB_nomic', 'HIB_nomic')},
           'comparacoes_entre_buscas': {'M0_E_sobre_M0_nomic': rel('M0_E', 'M0_nomic'), 'BM25_sobre_M0_nomic': rel('BM25', 'M0_nomic'),
                                        'HIB_E_sobre_M0_nomic': rel('HIB_E', 'M0_nomic'), 'HIB_nomic_sobre_M0_nomic': rel('HIB_nomic', 'M0_nomic'),
                                        'H1_nomic_sobre_HIB_E (busca barata com ligações x busca híbrida sem ligações)': rel('H1_nomic', 'HIB_E'),
                                        'H_E_sobre_M0_E (com bônus)': rel('H_E', 'M0_E')},
           'F1_por_periodo (descritivo; não confirma nem exclui contaminação)': por_ano,
           'familia_entre_as_k_candidatas (para a rodada 13)': cand,
           'parametros': {'bm25': {'k1': BM25_K1, 'b': BM25_B, 'stopwords': 'scikit-learn ENGLISH_STOP_WORDS', 'token': TOKEN.pattern,
                                   'idf_e_tamanho_medio': 'perguntas anteriores a T0'}, 'rrf': {'k': RRF_K, 'top': RRF_TOP}, 'prefixos_E': PREFIXOS[E]},
           'custo': {'minutos_embeddings_E_nesta_execucao': min_emb, 'piloto': pil['modelos'][E],
                     'construcao_s': {k: round(v, 1) for k, v in tm.items() if k.startswith('construir')},
                     'latencia_ms_por_pergunta (Mac, busca exaustiva, sem índice aproximado)': {k[:-2]: round(1000 * v / len(lab), 2) for k, v in tm.items() if not k.startswith('construir')},
                     'embedding_da_pergunta_ms (do piloto)': {'E': pil['modelos'][E].get('segundos_por_1000_textos'), 'nomic': pil['modelos'][NOMIC].get('segundos_por_1000_textos')},
                     'configuracao_E': show(a.host, E), 'configuracao_nomic': show(a.host, NOMIC)},
           'reproducao': {'confirmacao_familia_top5 [aqui, confirmação]': repro, 'dados_sha256': data_sha, 'embeddings': {'nomic': nomic_digest, 'E': {'modelo': E, 'digest': e_digest}}, 'ollama': ollama_version,
                          'piloto_sha256': file_sha(PILOTO), 'script_sha256': file_sha(os.path.abspath(__file__))},
           'minutos_nesta_execucao': round((time.time() - t_start) / 60, 1)}
    json.dump(out, open(OUT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(json.dumps({k: out[k] for k in ('modelo_E', 'criterios', 'F1_ganho_H1_sobre_HIB_E')}, ensure_ascii=False, indent=1))
    print(f'\nPronto. Envie {OUT} (só números).')

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('acao', choices=['piloto', 'rodar']); ap.add_argument('--host', default='http://localhost:11434')
    a = ap.parse_args(); os.makedirs('gc_data', exist_ok=True); os.makedirs('gc_cache', exist_ok=True)
    piloto(a) if a.acao == 'piloto' else rodar(a)

if __name__ == '__main__':
    main()
