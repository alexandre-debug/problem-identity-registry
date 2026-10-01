import json, glob, collections, re
root=__import__('os').environ.get('SGD_ROOT', 'dstc8-schema-guided-dialogue')
schemas={}
for sp in ['train','dev','test']:
    for s in json.load(open(f'{root}/{sp}/schema.json')): schemas.setdefault(s['service_name'],s)
def norm(t): return re.sub(r'\s+',' ',re.sub(r'[^\w\s]','',t.lower())).strip()
turns=collections.defaultdict(list)  # service -> list of (utt_key, ctx_key)
for sp in ['train','dev','test']:
    for f in sorted(glob.glob(f'{root}/{sp}/dialogues_*.json')):
        for d in json.load(open(f)):
            if len(d['services'])!=1: continue
            s=d['services'][0]; prev='START'
            for t in d['turns']:
                if t['speaker']=='SYSTEM':
                    prev='|'.join(sorted(f"{a['act']}:{a['slot']}" for fr in t['frames'] for a in fr['actions']))
                else:
                    u=norm(t['utterance']); turns[s].append((u,u+'##'+prev))
def rep(lst,i):
    c=collections.Counter(x[i] for x in lst); n=len(lst)
    return 1-len(c)/n  # fração de turnos que repetem uma chave já vista
def cross(a,b,i):
    ka={x[i] for x in turns[a]}; return sum(1 for x in turns[b] if x[i] in ka)/len(turns[b])
pairs=[('Events_1','Events_2'),('Flights_1','Flights_2'),('Restaurants_1','Restaurants_2'),('Services_1','Services_2'),('Hotels_1','Hotels_3'),('Buses_1','Buses_2'),('RentalCars_1','RentalCars_2'),('Homes_1','Homes_2'),('Music_2','Music_1'),('Media_1','Media_3')]
for a,b in pairs:
    sa={x['name'] for x in schemas[a]['slots']}; sb={x['name'] for x in schemas[b]['slots']}
    ia={x['name'] for x in schemas[a]['intents']}; ib={x['name'] for x in schemas[b]['intents']}
    print(f"{a}/{b}: intents comuns={sorted(ia&ib)} so_A={sorted(ia-ib)} so_B={sorted(ib-ia)}")
    print(f"   slots A={len(sa)} B={len(sb)} mesmo_nome={len(sa&sb)}")
    for s in (a,b): print(f"   {s}: turnos={len(turns[s])} repet_frase={rep(turns[s],0):.1%} repet_frase+ctx={rep(turns[s],1):.1%}")
    print(f"   B com chave vista em A: frase={cross(a,b,0):.1%} frase+ctx={cross(a,b,1):.1%}")
