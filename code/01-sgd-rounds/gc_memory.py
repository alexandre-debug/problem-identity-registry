"""Memória de episódios de V2/V3: interpretações validadas do fluxo de memória.

Guarda, por turno, a interpretação validada (aqui, o gabarito: validação idealizada):
intenção, ato do usuário e decisão de chamar. Não guarda valores literais.
"""
import re, collections
import numpy as np
from gc_common import *

HASH_MIN, HASH_AGREE, HASH_W = 2, 0.8, 0.8
K, SIM_MIN, RET_W = 5, 0.8, 0.5

def norm(t): return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', '', t.lower())).strip()
def key_of(utt, prev_acts): return norm(utt) + '##' + '|'.join(prev_acts)

class Memory:
    def __init__(self, N, D, stream):
        self.app, self.lab, texts, self.keys = [], [], [], collections.defaultdict(list)
        for item in stream:
            svc, did = item.split(':', 1); d = D[did]
            prev_acts, pint = ['START'], 'NONE'
            for i, t in enumerate(d['turns']):
                fr = t['frames'][0]
                if t['speaker'] == 'SYSTEM': prev_acts = sys_acts(svc, fr); continue
                intent = int2c[svc].get(fr['state']['active_intent'], 'NONE')
                nxt = d['turns'][i + 1]['frames'][0] if i + 1 < len(d['turns']) else {}
                self.keys[key_of(t['utterance'], prev_acts)].append(len(self.app))
                self.app.append(svc); self.lab.append((intent, user_act_class(fr), int('service_call' in nxt)))
                texts.append(text_features(t['utterance'], prev_acts, pint)); pint = intent
        self.X = self._embed(N, texts)              # linhas já normalizadas (TF-IDF l2)
        self.app = np.array(self.app); self._sub = {}

    def _embed(self, N, texts): return N['vec'].transform(texts)

    def _scope(self, scope):
        s = tuple(sorted(scope))
        if s not in self._sub:
            rows = np.where(np.isin(self.app, s))[0]; self._sub[s] = (rows, self.X[rows])
        return self._sub[s]

    @staticmethod
    def _dists(labs, weights):
        wi, wa, wc, tot = collections.Counter(), collections.Counter(), 0.0, float(sum(weights))
        for (i, a, c), w in zip(labs, weights): wi[i] += w; wa[a] += w; wc += w * c
        return {k: v / tot for k, v in wi.items()}, {k: v / tot for k, v in wa.items()}, wc / tot

    def consult(self, scope, utt, prev_acts, X, text=None):
        idx = [i for i in self.keys.get(key_of(utt, prev_acts), []) if self.app[i] in scope]
        if len(idx) >= HASH_MIN:
            labs = [self.lab[i] for i in idx]
            if collections.Counter(labs).most_common(1)[0][1] / len(labs) >= HASH_AGREE:
                di, da, dc = self._dists(labs, [1.0] * len(labs))
                return {'source': 'hash', 'weight': HASH_W, 'intent': di, 'act': da, 'call': dc, 'n': len(labs)}
        rows, sub = self._scope(scope)
        sims = (sub @ X.T).toarray().ravel()
        if not len(sims): return None
        top = np.argsort(-sims)[:K]; top = [j for j in top if sims[j] >= SIM_MIN]
        if not top: return None
        di, da, dc = self._dists([self.lab[rows[j]] for j in top], [sims[j] for j in top])
        return {'source': 'retrieval', 'weight': RET_W, 'intent': di, 'act': da, 'call': dc, 'n': len(top)}

class MemoryOwnVec(Memory):
    """Rodada 3: a recuperação usa TF-IDF ajustado aos próprios registros da memória,
    em vez do vocabulário do normalizador (que pode ter sido treinado com pouco dado)."""
    def __init__(self, D, stream):
        super().__init__(None, D, stream)

    def _embed(self, N, texts):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, token_pattern=r'(?u)\b\w+\b')
        return self.vec.fit_transform(texts)

    def consult(self, scope, utt, prev_acts, X, text=None):
        return super().consult(scope, utt, prev_acts, self.vec.transform([text]), text)
