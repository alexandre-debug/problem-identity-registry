"""Grande Cérebro: rodada 5 repetida com busca semântica, rodando na SUA máquina (Ollama).

Mesma simulação e mesmo critério da rodada 5 (AskUbuntu, 167 mil perguntas):
  - perguntas ordenadas por ID; 20% mais recentes = avaliação; 10% anteriores = calibração
  - duas centrais sorteadas (3 sorteios); V2 = memória da própria central; V3 = das duas
  - sugestão útil = uma duplicata marcada e anterior aparece entre as 5 primeiras sugestões
  - critério: V3 >= 5% de todas as perguntas novas E V3 - V2 >= 2 pontos com IC 95% acima de zero
Única mudança: o buscador passa a ser embeddings (mesma configuração do piloto).

Uso (na pasta onde está o script, com o ambiente gc-env ativo e o Ollama aberto):
  python3 gc_local_support.py --embed nomic-embed-text
O cálculo dos embeddings das 167 mil perguntas leva algumas horas e é retomável:
se parar, rode o mesmo comando de novo. No fim, envie gc_local_support_result.json.
"""
import argparse, gzip, json, os, platform, random, sys, time, urllib.request, collections
import numpy as np

BASE = 'https://raw.githubusercontent.com/taolei87/askubuntu/master/'
EVAL_FRAC, CALIB_FRAC, SEEDS, TOPK = 0.20, 0.10, [0, 1, 2], 5
UNLAB_EVAL, UNLAB_CALIB, MIN_PREC, BATCH_Q = 5000, 3000, 0.5, 512

def fetch(name):
    os.makedirs('gc_data', exist_ok=True); path = os.path.join('gc_data', name)
    if not os.path.exists(path):
        print('baixando', name, flush=True); urllib.request.urlretrieve(BASE + name, path)
    return path

def post(host, route, payload, timeout=600):
    req = urllib.request.Request(host + route, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read())

def embed_batch(host, model, texts):
    try: return post(host, '/api/embed', {'model': model, 'input': texts})['embeddings']
    except Exception: return [post(host, '/api/embeddings', {'model': model, 'prompt': t})['embedding'] for t in texts]

def embed_matrix(host, model, texts, path, prefix, batch=64):
    """Embeddings normalizados, gravados em disco aos poucos (retomável)."""
    n = len(texts); done_path = path + '.done'
    done = int(open(done_path).read()) if os.path.exists(done_path) and os.path.exists(path) else 0
    M = None
    if done:
        M = np.load(path, mmap_mode='r+')
    t0, start = time.time(), done
    for b in range(done, n, batch):
        vecs = np.array(embed_batch(host, model, [prefix + t for t in texts[b:b + batch]]), dtype=np.float32)
        vecs /= np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9
        if M is None: M = np.lib.format.open_memmap(path, mode='w+', dtype=np.float32, shape=(n, vecs.shape[1]))
        M[b:b + len(vecs)] = vecs; M.flush()
        open(done_path, 'w').write(str(b + len(vecs)))
        k = b + len(vecs)
        if (k // batch) % 20 == 0 or k == n:
            rate = (k - start) / max(time.time() - t0, 1e-9)
            print(f'  embeddings {k}/{n}  (~{(n - k) / max(rate, 1e-9) / 60:.0f} min restantes)', flush=True)
    return np.load(path, mmap_mode='r')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--embed', default='nomic-embed-text'); ap.add_argument('--host', default='http://localhost:11434')
    a = ap.parse_args(); t0 = time.time()
    try: version = json.loads(urllib.request.urlopen(a.host + '/api/version', timeout=30).read()).get('version')
    except Exception as e: sys.exit(f'Não consegui falar com o Ollama em {a.host}: {e}')

    ids, texts = [], []
    for line in gzip.open(fetch('text_tokenized.txt.gz'), 'rt', encoding='utf-8'):
        p = line.rstrip('\n').split('\t'); ids.append(int(p[0]))
        texts.append((p[1] if len(p) > 1 else '') + ' ' + (p[2] if len(p) > 2 else ''))
    order = np.argsort(ids); ids = np.array(ids)[order]; texts = [texts[i] for i in order]
    pos = {q: i for i, q in enumerate(ids)}; n = len(ids)
    dups = collections.defaultdict(set)
    for line in open(fetch('train_random.txt'), encoding='utf-8'):
        p = line.rstrip('\n').split('\t'); q = int(p[0])
        for s in map(int, p[1].split()):
            if q in pos and s in pos: dups[q].add(s); dups[s].add(q)
    e0, c0 = int((1 - EVAL_FRAC) * n), int((1 - EVAL_FRAC - CALIB_FRAC) * n)
    windows = {'calibracao': range(c0, e0), 'avaliacao': range(e0, n)}
    earlier = lambda i: {pos[s] for s in dups.get(ids[i], ()) if pos[s] < i}
    desks = {s: np.random.default_rng(100 + s).integers(0, 2, n) for s in SEEDS}
    rng = random.Random(20260928); proc = {}
    for w, rg in windows.items():
        lab = [i for i in rg if earlier(i)]; unl = [i for i in rg if not earlier(i)]
        k = UNLAB_EVAL if w == 'avaliacao' else UNLAB_CALIB
        proc[w] = dict(lab=lab, unl=rng.sample(unl, min(k, len(unl))), n_total=len(rg), n_unl=len(unl))
    print(f'{n} perguntas; avaliação {proc["avaliacao"]["n_total"]} ({len(proc["avaliacao"]["lab"])} com duplicata marcada anterior)', flush=True)

    os.makedirs('gc_cache', exist_ok=True); tag = a.embed.replace(':', '_').replace('/', '_')
    pre_q, pre_d = ('search_query: ', 'search_document: ') if 'nomic' in a.embed else ('', '')
    print('embeddings das perguntas-consulta', flush=True)
    qrows = sorted({i for w in proc for i in proc[w]['lab'] + proc[w]['unl']})
    Q = embed_matrix(a.host, a.embed, [texts[i] for i in qrows], f'gc_cache/support_q_{tag}.npy', pre_q)
    qidx = {i: j for j, i in enumerate(qrows)}
    print('embeddings de todas as perguntas (memória)', flush=True)
    Dm = np.asarray(embed_matrix(a.host, a.embed, texts, f'gc_cache/support_d_{tag}.npy', pre_d))

    def run(w):
        rows = proc[w]['lab'] + proc[w]['unl']; res = {}
        for b in range(0, len(rows), BATCH_Q):
            R = rows[b:b + BATCH_Q]; S = np.asarray(Q[[qidx[i] for i in R]]) @ Dm.T
            for j, i in enumerate(R):
                s = S[j].astype(np.float64); s[i:] = -np.inf; gold = earlier(i)
                top = np.argpartition(-s, TOPK)[:TOPK]; top = top[np.argsort(-s[top])]
                out = {'V3': (bool(any(t in gold for t in top)), float(s[top[0]]), bool(top[0] in gold))}
                for sd in SEEDS:
                    s2 = s.copy(); s2[desks[sd] != desks[sd][i]] = -np.inf
                    t2 = np.argpartition(-s2, TOPK)[:TOPK]; t2 = t2[np.argsort(-s2[t2])]
                    out[f'V2_s{sd}'] = (bool(any(t in gold for t in t2)), float(s2[t2[0]]), bool(t2[0] in gold))
                res[i] = out
            print(f'  busca {w}: {min(b + BATCH_Q, len(rows))}/{len(rows)}', flush=True)
        return res

    def suggestion_rate(res, w, cond): return sum(res[i][cond][0] for i in proc[w]['lab']) / proc[w]['n_total']
    def threshold(res, cond):
        w = 'calibracao'; scale = proc[w]['n_unl'] / len(proc[w]['unl'])
        pts = [(res[i][cond][1], 1.0 if res[i][cond][2] else 0.0, 1.0) for i in proc[w]['lab']] + \
              [(res[i][cond][1], 0.0, scale) for i in proc[w]['unl']]
        pts.sort(key=lambda x: -x[0]); ok = tot = 0.0; best = float('inf')
        for sim, c, wgt in pts:
            ok += c; tot += wgt
            if tot > 0 and ok / tot >= MIN_PREC: best = sim
        return best
    def auto_rate(res, w, cond, tau):
        lab = sum(1 for i in proc[w]['lab'] if res[i][cond][1] >= tau and res[i][cond][2])
        conf_unl = sum(1 for i in proc[w]['unl'] if res[i][cond][1] >= tau) * proc[w]['n_unl'] / len(proc[w]['unl'])
        conf_lab = sum(1 for i in proc[w]['lab'] if res[i][cond][1] >= tau)
        return lab / proc[w]['n_total'], (lab / (conf_lab + conf_unl) if conf_lab + conf_unl else None)
    def boot(res, w, B=2000):
        N = proc[w]['n_total']; lab = proc[w]['lab']
        va = np.zeros((len(SEEDS), N)); vb = np.zeros((len(SEEDS), N))
        for k, sd in enumerate(SEEDS):
            for j, i in enumerate(lab): va[k, j] = res[i][f'V2_s{sd}'][0]; vb[k, j] = res[i]['V3'][0]
        point = (vb.mean(1) - va.mean(1)).mean(); g = np.random.default_rng(0); diffs = []
        for _ in range(B):
            idx = g.integers(0, N, N); diffs.append((vb[:, idx].mean(1) - va[:, idx].mean(1)).mean())
        return round(float(point), 4), [round(float(np.percentile(diffs, 2.5)), 4), round(float(np.percentile(diffs, 97.5)), 4)]

    cal, ev = run('calibracao'), run('avaliacao')
    w = 'avaliacao'
    v2 = float(np.mean([suggestion_rate(ev, w, f'V2_s{s}') for s in SEEDS])); v3 = suggestion_rate(ev, w, 'V3')
    tau3 = threshold(cal, 'V3'); a3 = auto_rate(ev, w, 'V3', tau3)
    a2 = [auto_rate(ev, w, f'V2_s{s}', threshold(cal, f'V2_s{s}')) for s in SEEDS]
    teto3 = len(proc[w]['lab']) / proc[w]['n_total']
    teto2 = float(np.mean([sum(1 for i in proc[w]['lab'] if any(desks[s][j] == desks[s][i] for j in earlier(i))) / proc[w]['n_total'] for s in SEEDS]))
    d = boot(ev, w)
    out = {'modelo_embeddings': a.embed, 'ollama': version, 'maquina': platform.platform(),
           'janelas': {k: {'total': proc[k]['n_total'], 'com_duplicata_anterior_marcada': len(proc[k]['lab'])} for k in proc},
           'avaliacao': {'teto_V2': round(teto2, 4), 'teto_V3': round(teto3, 4),
                         'sugestao_util_V2': round(v2, 4), 'sugestao_util_V3': round(v3, 4), 'V3_menos_V2': d,
                         'reuso_automatico_V2': round(float(np.mean([x[0] for x in a2])), 4),
                         'reuso_automatico_V3': round(a3[0], 4), 'precisao_conservadora_V3': a3[1] and round(a3[1], 4), 'limiar_V3': tau3},
           'criterio_atingido': bool(v3 >= 0.05 and d[0] >= 0.02 and d[1][0] > 0),
           'referencia_rodada5_tfidf': {'teto_V2': 0.0375, 'teto_V3': 0.0719, 'sugestao_util_V2': 0.005, 'sugestao_util_V3': 0.008},
           'minutos_totais': round((time.time() - t0) / 60, 1)}
    json.dump(out, open('gc_local_support_result.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(json.dumps(out['avaliacao'], ensure_ascii=False), '\ncritério atingido:', out['criterio_atingido'])
    print('\nPronto. Envie o arquivo gc_local_support_result.json.')

if __name__ == '__main__':
    main()
