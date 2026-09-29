"""Entrega 2: divisões por diálogo, conjuntos fora do catálogo e manifesto reproduzível."""
import json, glob, hashlib, random, collections
ROOT=__import__('os').environ.get('SGD_ROOT', 'dstc8-schema-guided-dialogue'); SEED=20260928
A,B='Events_1','Events_2'; OOC_DEV,OOC_TEST='Hotels_1','RentalCars_1'
FRAC={'dev':0.15,'memory':0.55,'test':0.30}
files=sorted(glob.glob(f'{ROOT}/*/dialogues_*.json'))+sorted(glob.glob(f'{ROOT}/*/schema.json'))
dlg={}
for f in files:
    if 'dialogues_' in f:
        for d in json.load(open(f)):
            if len(d['services'])==1: dlg.setdefault(d['services'][0],[]).append(f.split('/')[-2]+'/'+d['dialogue_id'])  # ids só são únicos dentro de cada split original
def split(ids,rng):
    ids=sorted(ids); rng.shuffle(ids); n=len(ids); a=round(n*FRAC['dev']); b=a+round(n*FRAC['memory'])
    return {'dev':ids[:a],'memory':ids[a:b],'test':ids[b:]}
rng=random.Random(SEED)
out={'seed':SEED,'fractions':FRAC,'services':{A:'A',B:'B'},'splits':{}}
for s in (A,B): out['splits'][s]=split(dlg[s],rng)
ooc_d=sorted(dlg[OOC_DEV]); ooc_t=sorted(dlg[OOC_TEST]); rng.shuffle(ooc_d); rng.shuffle(ooc_t)
out['out_of_catalog']={'dev':{'service':OOC_DEV,'dialogues':ooc_d[:30]},'test':{'service':OOC_TEST,'dialogues':ooc_t[:30]}}
# ordem do fluxo de memória: intercala A e B por diálogos inteiros, mesma ordem em V2 e V3
ma=[(A,x) for x in out['splits'][A]['memory']]; mb=[(B,x) for x in out['splits'][B]['memory']]
stream=[]; ia=ib=0
while ia<len(ma) or ib<len(mb):
    # proporcional ao tamanho de cada lista, para intercalar sem esgotar uma antes
    if ib>=len(mb) or (ia<len(ma) and ia/len(ma)<=ib/len(mb)): stream.append(ma[ia]); ia+=1
    else: stream.append(mb[ib]); ib+=1
out['memory_stream_order']=[f'{s}:{x}' for s,x in stream]
out['source_sha256']={f.replace(ROOT+'/',''):hashlib.sha256(open(f,'rb').read()).hexdigest() for f in files}
out['mapping_sha256']=hashlib.sha256(open('mapping.json','rb').read()).hexdigest()
json.dump(out,open('manifest.json','w'),indent=1)
for s in (A,B): print(s,{k:len(v) for k,v in out['splits'][s].items()})
print('OOC', {k:(v['service'],len(v['dialogues'])) for k,v in out['out_of_catalog'].items()}, 'stream', len(stream))
