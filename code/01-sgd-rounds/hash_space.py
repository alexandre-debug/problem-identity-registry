"""Quanto espaço existe para ganho por hash: acertos exatos no teste, por tipo de turno e por condição."""
import json, glob, re, collections
ROOT=__import__('os').environ.get('SGD_ROOT', 'dstc8-schema-guided-dialogue'); M=json.load(open('manifest.json')); MAP=json.load(open('mapping.json'))
A,B='Events_1','Events_2'
import sys
RELATIVE=int(sys.argv[1]) if len(sys.argv)>1 else 0
S={}
for sp in ['train','dev','test']:
    for s in json.load(open(f'{ROOT}/{sp}/schema.json')): S.setdefault(s['service_name'],s)
slot2c={svc:{v[svc]:c for c,v in MAP['slots'].items() if v.get(svc)} for svc in (A,B)}
int2c={svc:{v[svc]:c for c,v in MAP['intents'].items() if v.get(svc)} for svc in (A,B)}
D={}
for f in glob.glob(f'{ROOT}/*/dialogues_*.json'):
    for d in json.load(open(f)): D[f.split('/')[-2]+'/'+d['dialogue_id']]=d
def norm(t): return re.sub(r'\s+',' ',re.sub(r'[^\w\s]','',t.lower())).strip()
def turns(svc,did):
    d=D[did]; prev='START'; pst={}; pint='NONE'; out=[]; pvals={}
    sc=lambda x: slot2c[svc].get(x,x)
    for t in d['turns']:
        if t['speaker']=='SYSTEM':
            prev='|'.join(sorted(f"{a['act']}:{sc(a['slot'])}" for fr in t['frames'] for a in fr['actions']))
            pvals={a['slot']:set(a.get('values',[])) for fr in t['frames'] for a in fr['actions']}; continue
        st=t['frames'][0]['state']
        new={k:v for k,v in st['slot_values'].items() if pst.get(k)!=v}
        cat={x['name']:x['is_categorical'] for x in S[svc]['slots']}
        kind='entidade' if any(not cat[k] for k in new) else ('categorico' if new else 'sem_valor')
        interp=(int2c[svc].get(st['active_intent'],st['active_intent']),
                tuple(sorted((sc(k),tuple(v)) for k,v in new.items())),
                tuple(sorted(sc(x) for x in st['requested_slots'])))
        # interpretação relativa: valor que veio de uma oferta/confirmação do sistema vira referência ao contexto
        rel=tuple(sorted((sc(k),'FROM_SYSTEM' if set(v)&pvals.get(k,set()) else tuple(v)) for k,v in new.items()))
        out.append(dict(key=norm(t['utterance'])+'##'+prev,kind=kind,interp=(interp,(interp[0],rel,interp[2]))[RELATIVE],intent=st['active_intent']))
        pst=st['slot_values']; pint=st['active_intent']
    return out
mem={A:collections.defaultdict(collections.Counter),B:collections.defaultdict(collections.Counter)}
for item in M['memory_stream_order']:
    svc,did=item.split(':',1)
    for x in turns(svc,did): mem[svc][x['key']][x['interp']]+=1
def lookup(memories,key):
    c=collections.Counter()
    for m in memories: c.update(m.get(key,{}))
    return c.most_common(1)[0][0] if c else None
res={}
for svc,other in ((A,B),(B,A)):
    T=[x for did in M['splits'][svc]['test'] for x in turns(svc,did)]
    for cond,mems in (('V2',[mem[svc]]),('V3',[mem[svc],mem[other]])):
        by=collections.defaultdict(lambda:[0,0,0])
        for x in T:
            h=lookup(mems,x['key']); r=by[x['kind']]; r[0]+=1
            if h is not None: r[1]+=1; r[2]+= h==x['interp']
        tot=[sum(v[i] for v in by.values()) for i in range(3)]
        res[(svc,cond)]=(tot,dict(by))
for (svc,cond),(tot,by) in res.items():
    print(f"{svc} {cond}: turnos={tot[0]} acertos_hash={tot[1]/tot[0]:.1%} interpretação_correta_no_hit={tot[2]/max(tot[1],1):.1%}")
    for k in ['entidade','categorico','sem_valor']:
        n,h,c=by.get(k,[0,0,0])
        if n: print(f"     {k:10s} turnos={n:4d} hit={h/n:5.1%} correta_no_hit={c/max(h,1):5.1%}")
gd=[did for did in M['splits'][B]['test'] if any(x['intent']=='GetEventDates' for x in turns(B,did))]
print('dialogos de teste de B com GetEventDates (sonda de "não suportada" em A):',len(gd))
