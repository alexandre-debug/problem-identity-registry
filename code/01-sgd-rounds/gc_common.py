"""Utilidades comuns do experimento Grande Cérebro (V0): dados, mapeamento, tokenização."""
import json, glob, os, pickle, re

ROOT = __import__('os').environ.get('SGD_ROOT', 'dstc8-schema-guided-dialogue')
HERE = os.path.dirname(os.path.abspath(__file__))
MAP = json.load(open(os.path.join(HERE, 'mapping.json')))
SERVICES = ('Events_1', 'Events_2')
# serviços que não podem entrar no treino: pares de avaliação, fora do catálogo e o Events_3 reservado
RESERVED = {'Events_3', 'Flights_1', 'Flights_2', 'Flights_3', 'Flights_4',
            'Hotels_1', 'RentalCars_1', 'Services_3', 'Movies_1'}

slot2c = {s: {v[s]: c for c, v in MAP['slots'].items() if v.get(s)} for s in SERVICES}
c2slot = {s: {c: v[s] for c, v in MAP['slots'].items() if v.get(s)} for s in SERVICES}
int2c = {s: {v[s]: c for c, v in MAP['intents'].items() if v.get(s)} for s in SERVICES}
c2int = {s: {c: v[s] for c, v in MAP['intents'].items() if v.get(s)} for s in SERVICES}
CATEGORICAL = ['event.type', 'tickets.count']
SPAN_CONCEPTS = [c for c in MAP['slots'] if c not in CATEGORICAL]
INTENTS = list(MAP['intents']) + ['NONE', 'OUT']

SCHEMA = {}
for sp in ['train', 'dev', 'test']:
    for s in json.load(open(f'{ROOT}/{sp}/schema.json')): SCHEMA.setdefault(s['service_name'], s)

def intent_slots(svc, concept):
    """Conceitos exigidos e opcionais do método que realiza a intenção no serviço."""
    name = c2int[svc].get(concept)
    if not name: return None, [], []
    it = next(i for i in SCHEMA[svc]['intents'] if i['name'] == name)
    return name, [slot2c[svc][x] for x in it['required_slots']], [slot2c[svc][x] for x in it['optional_slots']]

def load_all():
    cache = os.path.join(HERE, '.sgd_cache.pkl')
    if os.path.exists(cache): return pickle.load(open(cache, 'rb'))
    D = {}
    for f in sorted(glob.glob(f'{ROOT}/*/dialogues_*.json')):
        sp = f.split('/')[-2]
        for d in json.load(open(f)): D[sp + '/' + d['dialogue_id']] = d
    pickle.dump(D, open(cache, 'wb'))
    return D

TOK = re.compile(r"\w+|[^\w\s]")
def tokenize(text): return [(m.group(), m.start(), m.end()) for m in TOK.finditer(text)]

def map_slot(svc, slot): return slot2c.get(svc, {}).get(slot, slot)

def sys_acts(svc, frame):
    """Atos do turno do sistema, em conceitos comuns. O sistema conhece os próprios atos."""
    if frame is None: return ['START']
    return sorted({f"{a['act']}:{map_slot(svc, a['slot'])}" if a['slot'] else a['act'] for a in frame['actions']}) or ['NOACT']

def offered_values(svc, frame):
    out = {}
    if frame is None: return out
    for a in frame['actions']:
        if a['act'] in ('OFFER', 'CONFIRM') and a['values']:
            out[map_slot(svc, a['slot'])] = a['values'][0]
    return out

def user_act_class(frame):
    acts = {a['act'] for a in frame['actions']}
    if acts & {'NEGATE', 'NEGATE_INTENT'}: return 'negate'
    if acts & {'AFFIRM', 'SELECT', 'AFFIRM_INTENT'}: return 'accept'
    return 'other'

def text_features(utt, prev_acts, prev_intent):
    """Texto + marcadores de contexto para os classificadores de frase."""
    ctx = ' '.join('__pa_' + re.sub(r'\W', '_', a) for a in prev_acts)
    return f"{utt.lower()} {ctx} __pi_{prev_intent.replace('.', '_')}"
