import json, glob, collections, re, sys
root=__import__('os').environ.get('SGD_ROOT', 'dstc8-schema-guided-dialogue')
def norm(t): return re.sub(r'\s+',' ',re.sub(r'[^\w\s]','',t.lower())).strip()
schemas={}
for sp in ['train','dev','test']:
    for s in json.load(open(f'{root}/{sp}/schema.json')): schemas.setdefault(s['service_name'],s)
for svc in sys.argv[1:]:
    cat={x['name']:x['is_categorical'] for x in schemas[svc]['slots']}
    T=[]
    for sp in ['train','dev','test']:
        for f in sorted(glob.glob(f'{root}/{sp}/dialogues_*.json')):
            for d in json.load(open(f)):
                if d['services']!=[svc]: continue
                prev='START'; pst={}
                for t in d['turns']:
                    if t['speaker']=='SYSTEM':
                        prev='|'.join(sorted(f"{a['act']}:{a['slot']}" for fr in t['frames'] for a in fr['actions'])); continue
                    st=t['frames'][0]['state']; new={k for k,v in st['slot_values'].items() if pst.get(k)!=v}
                    kind='entidade' if any(not cat[k] for k in new) else ('categorico' if new else 'sem_valor')
                    T.append((kind,norm(t['utterance'])+'##'+prev)); pst=st['slot_values']
    n=len(T); out=[]
    for k in ['entidade','categorico','sem_valor']:
        L=[x[1] for x in T if x[0]==k]; seen=set(); r=0
        for x in L:
            r+= x in seen; seen.add(x)
        out.append(f"{k}: {len(L)/n:.0%} dos turnos, repetição exata {r/len(L):.1%}")
    print(svc, '|', ' ; '.join(out))
