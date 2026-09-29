"""Verificação do buscador da rodada 5 (exploratória, não altera o critério).

1) Benchmark padrão do conjunto: ranquear os 20 candidatos anotados de test.txt (P@1, MAP).
2) Posição da duplicata marcada quando a busca é sobre todo o corpo anterior (amostra de 400).
"""
import gzip, collections
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = __import__('os').environ.get('ASKUBUNTU_ROOT', 'askubuntu')
ids, texts = [], []
for line in gzip.open(f'{ROOT}/text_tokenized.txt.gz', 'rt', encoding='utf-8'):
    p = line.rstrip('\n').split('\t'); ids.append(int(p[0]))
    texts.append((p[1] if len(p) > 1 else '') + ' ' + (p[2] if len(p) > 2 else ''))
pos = {q: i for i, q in enumerate(ids)}; ida = np.array(ids)
X = TfidfVectorizer(sublinear_tf=True, min_df=2, token_pattern=r'\S+').fit_transform(texts)

P1, AP = [], []
for line in open(f'{ROOT}/test.txt'):
    p = line.rstrip('\n').split('\t'); q = int(p[0])
    sim = set(map(int, p[1].split())) if p[1].strip() else set(); cand = list(map(int, p[2].split()))
    if not sim: continue
    s = (X[[pos[c] for c in cand]] @ X[pos[q]].T).toarray().ravel(); order = [cand[j] for j in np.argsort(-s)]
    P1.append(order[0] in sim); hits, prec = 0, []
    for r, c in enumerate(order, 1):
        if c in sim: hits += 1; prec.append(hits / r)
    AP.append(np.mean(prec))
print(f'benchmark (20 candidatos): P@1={np.mean(P1):.3f} MAP={np.mean(AP):.3f}')

dups = collections.defaultdict(set)
for line in open(f'{ROOT}/train_random.txt'):
    p = line.rstrip('\n').split('\t'); q = int(p[0])
    for s in map(int, p[1].split()):
        if q in pos and s in pos: dups[q].add(s); dups[s].add(q)
qs = [q for q in dups if any(s < q for s in dups[q])]
qs = list(np.random.default_rng(0).choice(qs, 400, replace=False)); ranks = []
for q in qs:
    s = (X @ X[pos[q]].T).toarray().ravel(); s[ida >= q] = -np.inf
    ranks.append(min(int((s > s[pos[d]]).sum()) + 1 for d in dups[q] if d < q))
ranks = np.array(ranks)
print(f'posição da duplicata no corpo anterior: mediana {int(np.median(ranks))}, top-1 {(ranks <= 1).mean():.1%}, '
      f'top-5 {(ranks <= 5).mean():.1%}, top-100 {(ranks <= 100).mean():.1%}')
