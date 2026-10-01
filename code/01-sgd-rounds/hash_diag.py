"""Diagnóstico de chaves de hash com memória e desenvolvimento. Os arquivos do SGD são lidos
inteiros e filtrados: os diálogos de teste não entram no diagnóstico, mas são desserializados.

Compara quatro chaves, com cobertura (fração de turnos de desenvolvimento cuja chave
já existe na memória) e precisão (fração desses acertos cuja interpretação registrada
é igual à do turno):
  K1 texto_estrito        frase exatamente como escrita (só espaços das pontas removidos)
  K2 parcial_normalizada  frase normalizada + atos do sistema anterior sem valores (chave antiga)
  K3 parcial_estrita      frase estrita + atos do sistema anterior sem valores
  K4 valores_e_estado_anotado  frase estrita + atos do sistema anterior COM valores + estado anterior
     ANOTADO (gabarito). Diagnóstico com estado ideal: um middleware real teria de construir esse estado.
Interpretação = intenção + parâmetros alterados (com valores) + parâmetros solicitados,
em conceitos comuns. A variante 'relativa' troca valores vindos do sistema por FROM_SYSTEM
usando o gabarito; é análise exploratória, não algo que o middleware saberia fazer sozinho.
"""
import json, glob, re, collections, subprocess, datetime

ROOT = __import__('os').environ.get('SGD_ROOT', 'dstc8-schema-guided-dialogue')
M = json.load(open('manifest.json')); MAP = json.load(open('mapping.json'))
A, B = 'Events_1', 'Events_2'
S = {}
for sp in ['train', 'dev', 'test']:
    for s in json.load(open(f'{ROOT}/{sp}/schema.json')): S.setdefault(s['service_name'], s)
slot2c = {svc: {v[svc]: c for c, v in MAP['slots'].items() if v.get(svc)} for svc in (A, B)}
int2c = {svc: {v[svc]: c for c, v in MAP['intents'].items() if v.get(svc)} for svc in (A, B)}

# carrega apenas diálogos de memória e desenvolvimento
allowed = set()
for svc in (A, B): allowed |= set(M['splits'][svc]['memory']) | set(M['splits'][svc]['dev'])
test_ids = set(M['splits'][A]['test']) | set(M['splits'][B]['test'])
assert not (allowed & test_ids)
D = {}
for f in glob.glob(f'{ROOT}/*/dialogues_*.json'):
    for d in json.load(open(f)):
        k = f.split('/')[-2] + '/' + d['dialogue_id']
        if k in allowed: D[k] = d
assert not (set(D) & test_ids)

def norm(t): return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', '', t.lower())).strip()

def turns(svc, did):
    sc = lambda x: slot2c[svc].get(x, x)
    ic = lambda x: int2c[svc].get(x, x)
    cat = {x['name']: x['is_categorical'] for x in S[svc]['slots']}
    acts, acts_v, pvals, pst, pint, out = 'START', 'START', {}, {}, 'NONE', []
    for t in D[did]['turns']:
        if t['speaker'] == 'SYSTEM':
            A_ = [a for fr in t['frames'] for a in fr['actions']]
            acts = '|'.join(sorted(f"{a['act']}:{sc(a['slot'])}" for a in A_))
            acts_v = '|'.join(sorted(f"{a['act']}:{sc(a['slot'])}={'/'.join(a.get('values', []))}" for a in A_))
            pvals = {a['slot']: set(a.get('values', [])) for a in A_}
            continue
        st = t['frames'][0]['state']
        new = {k: v for k, v in st['slot_values'].items() if pst.get(k) != v}
        kind = 'entidade' if any(not cat[k] for k in new) else ('categorico' if new else 'sem_valor')
        req = tuple(sorted(sc(x) for x in st['requested_slots']))
        lit = (ic(st['active_intent']), tuple(sorted((sc(k), tuple(v)) for k, v in new.items())), req)
        rel = (lit[0], tuple(sorted((sc(k), 'FROM_SYSTEM' if set(v) & pvals.get(k, set()) else tuple(v))
                                   for k, v in new.items())), req)
        prev_state = ic(pint) + ';' + '|'.join(sorted(f"{sc(k)}={'/'.join(v)}" for k, v in pst.items()))
        u = t['utterance'].strip()
        out.append(dict(kind=kind, lit=lit, rel=rel, keys={
            'K1_texto_estrito': u,
            'K2_parcial_normalizada': norm(u) + '##' + acts,
            'K3_parcial_estrita': u + '##' + acts,
            'K4_valores_e_estado_anotado': u + '##' + acts_v + '##' + prev_state,
        }))
        pst, pint = st['slot_values'], st['active_intent']
    return out

KEYS = ['K1_texto_estrito', 'K2_parcial_normalizada', 'K3_parcial_estrita', 'K4_valores_e_estado_anotado']
mem = {svc: {k: collections.defaultdict(collections.Counter) for k in KEYS} for svc in (A, B)}
for item in M['memory_stream_order']:
    svc, did = item.split(':', 1)
    for x in turns(svc, did):
        for k in KEYS:
            mem[svc][k][x['keys'][k]][(x['lit'], x['rel'])] += 1

def lookup(mems, key):
    c = collections.Counter()
    for m in mems: c.update(m.get(key, {}))
    return c.most_common(1)[0][0] if c else None

rows = []
for svc, other in ((A, B), (B, A)):
    T = [x for did in M['splits'][svc]['dev'] for x in turns(svc, did)]
    for cond, mems_of in (('V2', [svc]), ('V3', [svc, other])):
        for k in KEYS:
            for kind in ['todos', 'entidade', 'categorico', 'sem_valor']:
                sub = [x for x in T if kind == 'todos' or x['kind'] == kind]
                hits = lit_ok = rel_ok = 0
                for x in sub:
                    h = lookup([mem[s][k] for s in mems_of], x['keys'][k])
                    if h is None: continue
                    hits += 1; lit_ok += h[0] == x['lit']; rel_ok += h[1] == x['rel']
                rows.append(dict(app=svc, cond=cond, key=k, kind=kind, turns=len(sub), hits=hits,
                                 prec_literal=lit_ok, prec_relativa_com_gabarito=rel_ok))

commit = subprocess.run(['git', '-C', ROOT, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
json.dump(dict(dataset_commit=commit, split='dev', run_at=datetime.datetime.utcnow().isoformat() + 'Z',
               manifest_seed=M['seed'], rows=rows), open('hash_diag_raw.json', 'w'), indent=1)

pct = lambda a, b: f"{a / b:6.1%}" if b else '     -'
print(f"dataset {commit[:12]} | avaliação no desenvolvimento; diálogos de teste filtrados antes do diagnóstico")
for r in rows:
    if r['kind'] != 'todos': continue
    print(f"{r['app']} {r['cond']} {r['key']:24s} turnos={r['turns']:4d} cobertura={pct(r['hits'], r['turns'])}"
          f" precisão_literal={pct(r['prec_literal'], r['hits'])} precisão_relativa*={pct(r['prec_relativa_com_gabarito'], r['hits'])}")
