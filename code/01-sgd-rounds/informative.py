import json, glob, collections, re, sys
root=__import__('os').environ.get('SGD_ROOT', 'dstc8-schema-guided-dialogue')
def norm(t): return re.sub(r'\s+',' ',re.sub(r'[^\w\s]','',t.lower())).strip()
def load(svc):
    out=[]
    for sp in ['train','dev','test']:
        for f in sorted(glob.glob(f'{root}/{sp}/dialogues_*.json')):
            for d in json.load(open(f)):
                if d['services']!=[svc]: continue
                prev='START'; pst={}; pint='NONE'
                for t in d['turns']:
                    if t['speaker']=='SYSTEM':
                        prev='|'.join(sorted(f"{a['act']}:{a['slot']}" for fr in t['frames'] for a in fr['actions'])); continue
                    fr=t['frames'][0]; st=fr['state']
                    new={k:v for k,v in st['slot_values'].items() if pst.get(k)!=v}
                    info=bool(new) or st['active_intent']!=pint
                    u=norm(t['utterance']); out.append(dict(u=u,ctx=u+'##'+prev,info=info))
                    pst=st['slot_values']; pint=st['active_intent']
    return out
for svc in sys.argv[1:]:
    T=load(svc); I=[x for x in T if x['info']]
    c=collections.Counter(x['u'] for x in T)
    ci=collections.Counter(x['ctx'] for x in I)
    print(f"{svc}: turnos={len(T)} informativos={len(I)} ({len(I)/len(T):.0%}) repet_ctx_informativos={1-len(ci)/len(I):.1%}")
    print('   top repetidas (todas):',[f"{k} ×{v}" for k,v in c.most_common(6)])
    print('   top repetidas (informativas):',[f"{k.split('##')[0]} ×{v}" for k,v in ci.most_common(4)])
