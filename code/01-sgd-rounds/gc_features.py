"""Atributos compartilhados pelo treino e pela inferência da V0."""
import re
from gc_common import intent_slots

def shape(w): return re.sub(r'(.)\1+', r'\1', re.sub('[A-Z]', 'X', re.sub('[a-z]', 'x', re.sub(r'\d', 'd', w))))

def token_feats(toks, i, req):
    w = toks[i][0]; lw = w.lower()
    f = {'b': 1, 'w=' + lw: 1, 'suf3=' + lw[-3:]: 1, 'shape=' + shape(w): 1,
         'title': int(w.istitle()), 'digit': int(w.isdigit()), 'upper': int(w.isupper())}
    for k in (-2, -1, 1, 2):
        j = i + k; f[f'w{k}=' + (toks[j][0].lower() if 0 <= j < len(toks) else '<pad>')] = 1
    f['bg=' + (toks[i - 1][0].lower() if i > 0 else '<s>') + '_' + lw] = 1
    for c in req:
        f['req=' + c] = 1; f['req=' + c + '&title'] = int(w.istitle())
    return f

def decision_features(svc, intent, state, new, intent_changed, prev_acts, act):
    name, req, opt = intent_slots(svc, intent)
    f = {'bias': 1, 'intent=' + intent: 1, 'act=' + act: 1, 'supported': int(bool(name)),
         'req_complete': int(bool(name) and all(c in state for c in req)),
         'any_new': int(bool(new)), 'n_new': len(new), 'intent_changed': int(intent_changed),
         'new_in_method': int(bool(name) and any(c in req + opt for c in new))}
    for c in new: f['new=' + c] = 1
    for a in prev_acts: f['pa=' + a] = 1; f['pact=' + a.split(':')[0]] = 1
    f['req_complete&' + intent] = f['req_complete']
    f['act=' + act + '&prevCONFIRM'] = int(any(a.startswith('CONFIRM') for a in prev_acts))
    f['act=' + act + '&prevOFFER_INTENT'] = int(any(a.startswith('OFFER_INTENT') for a in prev_acts))
    return f

def requested_in(prev_acts): return [a.split(':', 1)[1] for a in prev_acts if a.startswith('REQUEST:')]
