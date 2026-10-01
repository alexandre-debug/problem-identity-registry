"""Grande Cérebro: piloto local com Ollama (roda na SUA máquina).

Mede se busca semântica e a forma padrão do problema reconhecem duplicatas de suporte
técnico melhor que o TF-IDF, no teste padrão do AskUbuntu (perguntas com 20 candidatos
anotados manualmente). O TF-IDF deu P@1 = 0,543 e MAP = 0,557 nesse teste.

Métodos comparados:
  tfidf        linha de base (texto original)
  embed        embeddings do texto original (modelo de embeddings do Ollama)
  canon_embed  o LLM reescreve cada pergunta como forma padrão do problema; embeddings dessa forma
  canon_tfidf  TF-IDF sobre as formas padrão

Requisitos: Python 3.9+, numpy, scikit-learn, Ollama rodando (ollama serve).
  ollama pull nomic-embed-text        # modelo de embeddings (~270 MB)
  ollama pull llama3.1:8b             # ou o modelo que você já tiver

Uso:
  python3 gc_local_pilot.py --llm llama3.1:8b --embed nomic-embed-text --limit 60
  (--limit = número de perguntas de teste; 60 perguntas ~ 1.200 textos. Sem --limit, usa todas.)

O resultado vai para gc_local_pilot_result.json. Envie esse arquivo de volta.
O progresso fica salvo em gc_cache/, então dá para interromper e continuar depois.
"""
import argparse, gzip, json, os, platform, sys, time, urllib.request
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

BASE = 'https://raw.githubusercontent.com/taolei87/askubuntu/master/'
PROMPT = ("Rewrite the Ubuntu support question below as ONE short canonical problem statement "
          "(at most 25 words): the core problem, the component or software involved, and any key "
          "condition (version, hardware, when it happens). No greeting, no solution, no explanation. "
          "Output only the statement.\n\nQuestion title: {title}\nQuestion body: {body}\n\nCanonical problem:")

def fetch(name):
    os.makedirs('gc_data', exist_ok=True); path = os.path.join('gc_data', name)
    if not os.path.exists(path):
        print('baixando', name, flush=True); urllib.request.urlretrieve(BASE + name, path)
    return path

def post(host, route, payload, timeout=600):
    req = urllib.request.Request(host + route, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read())

def get(host, route):
    with urllib.request.urlopen(host + route, timeout=30) as r: return json.loads(r.read())

class Cache:
    def __init__(self, path):
        self.path = path; self.d = {}
        if os.path.exists(path):
            for line in open(path, encoding='utf-8'):
                k, v = json.loads(line); self.d[k] = v
        self.f = open(path, 'a', encoding='utf-8')
    def get(self, k): return self.d.get(k)
    def put(self, k, v): self.d[k] = v; self.f.write(json.dumps([k, v]) + '\n'); self.f.flush()

def embed_all(host, model, keys, texts, cache, prefix):
    todo = [(k, t) for k, t in zip(keys, texts) if cache.get(k) is None]
    t0 = time.time()
    for b in range(0, len(todo), 32):
        chunk = todo[b:b + 32]
        try:
            vecs = post(host, '/api/embed', {'model': model, 'input': [prefix + t for _, t in chunk]})['embeddings']
        except Exception:
            vecs = [post(host, '/api/embeddings', {'model': model, 'prompt': prefix + t})['embedding'] for _, t in chunk]
        for (k, _), v in zip(chunk, vecs): cache.put(k, v)
        print(f'  embeddings {min(b + 32, len(todo))}/{len(todo)}', flush=True)
    return (time.time() - t0) / max(len(todo), 1)

def normalize_all(host, model, qids, title, body, cache):
    todo = [q for q in qids if cache.get(str(q)) is None]; t0 = time.time()
    for n, q in enumerate(todo, 1):
        r = post(host, '/api/generate', {'model': model, 'stream': False, 'options': {'temperature': 0, 'num_predict': 60},
                                         'prompt': PROMPT.format(title=title[q], body=' '.join(body[q].split()[:100]))})
        cache.put(str(q), r['response'].strip().split('\n')[0])
        if n % 20 == 0 or n == len(todo):
            el = time.time() - t0; print(f'  formas padrão {n}/{len(todo)}  ({el / n:.1f}s cada, faltam ~{el / n * (len(todo) - n) / 60:.0f} min)', flush=True)
    return (time.time() - t0) / max(len(todo), 1)

def score(queries, sim_fn):
    P1, AP = [], []
    for q, sim, cand in queries:
        s = sim_fn(q, cand); order = [cand[j] for j in np.argsort(-np.array(s), kind='stable')]
        P1.append(order[0] in sim); hits, prec = 0, []
        for r, c in enumerate(order, 1):
            if c in sim: hits += 1; prec.append(hits / r)
        AP.append(np.mean(prec))
    return {'P@1': round(float(np.mean(P1)), 4), 'MAP': round(float(np.mean(AP)), 4), 'perguntas': len(queries)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--llm', default='llama3.1:8b'); ap.add_argument('--embed', default='nomic-embed-text')
    ap.add_argument('--host', default='http://localhost:11434'); ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--skip-llm', action='store_true', help='só embeddings, sem formas padrão')
    a = ap.parse_args()
    t0 = time.time()
    try: version = get(a.host, '/api/version').get('version')
    except Exception as e: sys.exit(f'Não consegui falar com o Ollama em {a.host}: {e}\nRode "ollama serve" e tente de novo.')

    title, body, texts = {}, {}, {}
    for line in gzip.open(fetch('text_tokenized.txt.gz'), 'rt', encoding='utf-8'):
        p = line.rstrip('\n').split('\t'); q = int(p[0])
        title[q] = p[1] if len(p) > 1 else ''; body[q] = p[2] if len(p) > 2 else ''; texts[q] = title[q] + ' ' + body[q]
    queries = []
    for line in open(fetch('test.txt'), encoding='utf-8'):
        p = line.rstrip('\n').split('\t'); sim = set(map(int, p[1].split())) if p[1].strip() else set()
        if sim: queries.append((int(p[0]), sim, list(map(int, p[2].split()))))
    if a.limit: queries = queries[:a.limit]
    need = sorted({q for q, _, c in queries} | {x for _, _, c in queries for x in c})
    print(f'{len(queries)} perguntas de teste, {len(need)} textos', flush=True)

    ids = sorted(texts); tf = TfidfVectorizer(sublinear_tf=True, min_df=2, token_pattern=r'\S+').fit([texts[i] for i in ids])
    X = {q: v for q, v in zip(need, tf.transform([texts[q] for q in need]))}
    res = {'tfidf': score(queries, lambda q, c: [float((X[q] @ X[x].T).toarray()[0, 0]) for x in c])}
    print('tfidf', res['tfidf'], flush=True)

    os.makedirs('gc_cache', exist_ok=True); tag = a.embed.replace(':', '_').replace('/', '_')
    pre_q, pre_d = ('search_query: ', 'search_document: ') if 'nomic' in a.embed else ('', '')
    ce = Cache(f'gc_cache/embed_{tag}.jsonl')
    t_q = embed_all(a.host, a.embed, [f'q{q}' for q, _, _ in queries], [texts[q] for q, _, _ in queries], ce, pre_q)
    t_d = embed_all(a.host, a.embed, [f'd{x}' for x in need], [texts[x] for x in need], ce, pre_d)
    def cos(u, v): u, v = np.array(u), np.array(v); return float(u @ v / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-9))
    res['embed'] = score(queries, lambda q, c: [cos(ce.get(f'q{q}'), ce.get(f'd{x}')) for x in c])
    print('embed', res['embed'], flush=True)

    t_norm = None
    if not a.skip_llm:
        cn = Cache(f"gc_cache/canon_{a.llm.replace(':', '_').replace('/', '_')}.jsonl")
        t_norm = normalize_all(a.host, a.llm, need, title, body, cn)
        canon = {x: cn.get(str(x)) for x in need}
        cc = Cache(f"gc_cache/embedcanon_{tag}_{a.llm.replace(':', '_').replace('/', '_')}.jsonl")
        embed_all(a.host, a.embed, [f'q{q}' for q, _, _ in queries], [canon[q] for q, _, _ in queries], cc, pre_q)
        embed_all(a.host, a.embed, [f'd{x}' for x in need], [canon[x] for x in need], cc, pre_d)
        res['canon_embed'] = score(queries, lambda q, c: [cos(cc.get(f'q{q}'), cc.get(f'd{x}')) for x in c])
        tc = TfidfVectorizer(sublinear_tf=True, token_pattern=r'\S+').fit([canon[x] for x in need])
        C = {x: v for x, v in zip(need, tc.transform([canon[x].lower() for x in need]))}
        res['canon_tfidf'] = score(queries, lambda q, c: [float((C[q] @ C[x].T).toarray()[0, 0]) for x in c])
        res['exemplos_forma_padrao'] = [{'titulo': title[q], 'forma_padrao': canon[q]} for q, _, _ in queries[:8]]
        print('canon_embed', res['canon_embed'], 'canon_tfidf', res['canon_tfidf'], flush=True)

    out = {'resultados': res, 'modelos': {'llm': None if a.skip_llm else a.llm, 'embed': a.embed, 'ollama': version},
           'segundos_por_texto': {'embedding': round(t_d, 3), 'forma_padrao': t_norm and round(t_norm, 2)},
           'maquina': {'sistema': platform.platform(), 'python': platform.python_version()},
           'minutos_totais': round((time.time() - t0) / 60, 1),
           'referencia_publicada_BM25': {'P@1': 0.53, 'MAP': 0.57}}
    json.dump(out, open('gc_local_pilot_result.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print('\nPronto. Envie o arquivo gc_local_pilot_result.json.')

if __name__ == '__main__':
    main()
