"""Rodada 4: memória de valores validados (argumentos ditos pelos usuários e confirmados).

Guarda, por fonte, contagens de (conceito, valor em minúsculas). Na consulta, varre a
frase do trecho mais longo para o mais curto e devolve, por conceito, o trecho encontrado.
"""
import re, collections
from gc_common import *

MIN_VALIDATIONS, MIN_CHARS, VAL_CONF, MAX_TOKENS = 2, 3, 0.85, 8

def other_domain_concept(sl):
    """Regra registrada para mapear parâmetros de outros domínios em conceitos comuns."""
    if sl['is_categorical']: return None
    n, d = sl['name'], sl['description'].lower()
    if re.search(r'\bcity\b', d): return 'place.city'
    if n == 'date' or n.endswith('_date'): return 'event.date'
    if n == 'time' or n.endswith('_time'): return 'event.time'
    return None

def other_services():
    return sorted(s for s in SCHEMA if s not in RESERVED and s not in SERVICES and not s.startswith('Events'))

class ValueMemory:
    def __init__(self):
        self.counts = collections.defaultdict(collections.Counter)   # fonte -> (conceito, valor) -> n

    def add_dialogue(self, source, svc, d):
        if svc in SERVICES: cmap = lambda slot: slot2c[svc].get(slot)
        else:
            rule = {sl['name']: other_domain_concept(sl) for sl in SCHEMA[svc]['slots']}
            cmap = lambda slot: rule.get(slot)
        for t in d['turns']:
            if t['speaker'] != 'USER': continue
            for fr in t['frames']:
                if fr['service'] != svc: continue
                for sl in fr['slots']:
                    c = cmap(sl['slot'])
                    if c and c in SPAN_CONCEPTS:
                        self.counts[source][(c, t['utterance'][sl['start']:sl['exclusive_end']].lower())] += 1

    def index(self, sources):
        """Índice valor -> (conceito, validações) combinando as fontes pedidas."""
        tot = collections.Counter()
        for s in sources: tot.update(self.counts[s])
        best = {}
        for (c, v), n in tot.items():
            if n < MIN_VALIDATIONS or len(v) < MIN_CHARS or (v.isdigit() and len(v) < 3): continue
            if v not in best or n > best[v][1]: best[v] = (c, n)
        return best

def match(index, utt, toks, allowed):
    """Trechos da frase que são valores validados, sem sobreposição, do mais longo ao mais curto."""
    found, used = {}, set()
    for size in range(min(MAX_TOKENS, len(toks)), 0, -1):
        for i in range(len(toks) - size + 1):
            if any(j in used for j in range(i, i + size)): continue
            s, e = toks[i][1], toks[i + size - 1][2]
            hit = index.get(utt[s:e].lower())
            if hit and hit[0] in allowed and hit[0] not in found:
                found[hit[0]] = utt[s:e]; used.update(range(i, i + size))
    return found
