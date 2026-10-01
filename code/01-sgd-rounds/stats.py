import json, glob, collections
root=__import__('os').environ.get('SGD_ROOT', 'dstc8-schema-guided-dialogue')
schemas={}
for sp in ['train','dev','test']:
    for s in json.load(open(f'{root}/{sp}/schema.json')):
        schemas.setdefault(s['service_name'],s)
dlg=collections.Counter(); uturns=collections.Counter(); calls=collections.Counter(); splits=collections.defaultdict(collections.Counter)
for sp in ['train','dev','test']:
    for f in sorted(glob.glob(f'{root}/{sp}/dialogues_*.json')):
        for d in json.load(open(f)):
            if len(d['services'])!=1: continue   # só diálogos de um serviço
            s=d['services'][0]; dlg[s]+=1; splits[s][sp]+=1
            for t in d['turns']:
                if t['speaker']=='USER': uturns[s]+=1
                else:
                    for fr in t['frames']:
                        if 'service_call' in fr: calls[s]+=1
dom=collections.defaultdict(list)
for s in schemas: dom[s.rsplit('_',1)[0]].append(s)
for d,ss in sorted(dom.items()):
    if len(ss)<2: continue
    print(f'== {d}')
    for s in sorted(ss):
        it=sorted(i['name'] for i in schemas[s]['intents'])
        print(f'  {s}: dialogos={dlg[s]} {dict(splits[s])} turnos_usuario={uturns[s]} chamadas={calls[s]} intents={it}')
