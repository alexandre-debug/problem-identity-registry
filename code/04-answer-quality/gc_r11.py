"""Grande Cérebro, Rodada 11: busca simples (M0), H1 e H nas mesmas perguntas novas do Super User.

Rode na mesma pasta do gc_conf.py, gc_r9.py e gc_r10_A.py, depois da etapa A (usa gc_data/su24_*, gc_cache/su24_*
e r10A_resultado.json). Precisa também do Votes.xml do Super User; se não estiver extraído, o script o tira do
superuser.com.7z desta pasta.

Passo 1  python3 gc_r11.py preparar
         cria r11_amostra.json (só contagens e números de pergunta)          -> ENVIE
Passo 2  (pré-registro já congelado em 30/09/2026, 14h20)
         python3 gc_r11.py gerar --modelo gemma4:latest --pre-registro-congelado
         gera todas as respostas; pode parar e rodar de novo: continua de onde parou.
Passo 3  python3 gc_r11.py controles
         na 1a vez cria r11_k4_base.txt (versões fiéis para o K4)            -> ENVIE ao Claude
         salve na pasta o r11_k4_erros.json que voltar e rode de novo:
         python3 gc_r11.py controles
         cria r11_controles_revisao.txt                                    -> ENVIE ao Claude
         salve na pasta o r11_controles_aprovados.json que voltar
         (desvio 2, 01/10/2026: se existir r11_k5_versoes.json, a versão 2 desses pares do K5 vem dele)
         (errata 1, 01/10/2026: P1 calculado como Δ(CH1 − CH), como no pré-registro)
Passo 4  python3 gc_r11.py itens
         cria r11_itens.txt                                                -> ENVIE ao Claude
         cria r11_chave_NAO_ENVIAR.json                                    -> NUNCA envie
Passo 5  salve na pasta o r11_rotulos.json que o Claude devolver e rode:
         python3 gc_r11.py comparar r11_rotulos.json
         cria r11_resultado.json (só números agregados)                    -> ENVIE
"""
import argparse, collections, gzip, hashlib, json, os, random, shutil, subprocess, sys, time, urllib.error
import numpy as np
from scipy.sparse import csr_matrix
import gc_conf as G
import gc_r9 as R9

VERSAO = 'r11-v1'
SITE, DUMP, XDIR, PFX, RESA = 'superuser.com', 'superuser.com.7z', 'gc_data/superuser2024', 'su24', 'r10A_resultado.json'
N_P_MAX, N_HM0, N_K1, N_K2, N_K4, N_K5 = 1000, 300, 60, 40, 60, 40
SEED_P, SEED_HM0, SEED_K1, SEED_K4, SEED_K5, SEED_ITEMS = 1111, 1112, 1113, 1114, 1115, 41338
Q_WORDS, DOCQ_WORDS, DOCA_WORDS, REF_WORDS, CAND_WORDS = R9.Q_WORDS, R9.DOCQ_WORDS, R9.DOCA_WORDS, R9.REF_WORDS, R9.CAND_WORDS
NUM_PREDICT, GEN_SEED, NBOOT = R9.NUM_PREDICT, R9.GEN_SEED, R9.NBOOT
MARGIN_P2, K1_MIN, K2_MIN, K4_MIN, K5_MIN_TIE, K4_MIN_APROV, K5_MIN_APROV = -0.03, R9.K1_MIN, R9.K2_MIN, R9.K4_MIN, R9.K5_MIN_TIE, R9.K4_MIN_APROV, R9.K5_MIN_APROV
su = lambda t: t.replace('Ask Ubuntu', 'Super User')           # mesmos textos da rodada 9, com o nome do site trocado
GEN_PROMPT, CTX_HEAD, DOC_FMT, RUBRIC = su(R9.GEN_PROMPT), su(R9.CTX_HEAD), su(R9.DOC_FMT), su(R9.RUBRIC)
CTRL_PROMPTS = {k: su(R9.CTRL_PROMPTS[k]) for k in ('PARA1', 'PARA2')}
REVIEW_HEAD = su(R9.REVIEW_HEAD)
K4_HEAD = ('ERROR INSERTION. For each case, check that VERSION 1 is a clean, technically correct answer equivalent to the reference; '
           'if so, write VERSION 2, identical to VERSION 1 except for ONE minimal edit that introduces one decisive technical error.\n')
AMOSTRA, TEXTOS, REC = 'r11_amostra.json', 'gc_data/r11_textos.json.gz', 'gc_cache/r11_rec.json'
ITEMS, KEY, OUT = 'r11_itens.txt', 'r11_chave_NAO_ENVIAR.json', 'r11_resultado.json'
K4_BASE, K4_EXT, REVIEW, APPROVED = 'r11_k4_base.txt', 'r11_k4_erros.json', 'r11_controles_revisao.txt', 'r11_controles_aprovados.json'
K5_EXT = 'r11_k5_versoes.json'   # desvio 2 (01/10/2026): versão 2 do K5 escrita por um agente separado; chave = id da pergunta no Stack Exchange
words, html_text, file_sha = R9.words, R9.html_text, R9.file_sha
PAIRS = {'H1xM0': ('CH1', 'CM0'), 'HxH1': ('CH', 'CH1'), 'HxM0': ('CH', 'CM0')}
LIST = {'CM0': 'M0', 'CH1': 'H1', 'CH': 'H'}

# ---------------------------------------------------------------- dados da etapa A
def rebuild(embed):
    qpath, lpath, mpath = f'gc_data/{PFX}_perguntas.jsonl.gz', f'gc_data/{PFX}_duplicatas.tsv', f'gc_data/{PFX}_meta.json'
    for p in (qpath, lpath, mpath, RESA):
        if not os.path.exists(p): sys.exit(f'Falta {p}. Rode na mesma pasta, depois da etapa A (gc_r10_A.py).')
    meta = json.load(open(mpath)); res = json.load(open(RESA))
    if meta.get('preproc') != G.PREPROC or meta.get('T0') != G.T0 or meta.get('site') != SITE: sys.exit('Os dados lidos não correspondem à etapa A.')
    ids, dates, texts = [], [], []
    for line in gzip.open(qpath, 'rt', encoding='utf-8'): i, d, t = json.loads(line); ids.append(i); dates.append(d); texts.append(t)
    data_sha = G.sha(f'{i}|{d}|{t}' for i, d, t in zip(ids, dates, texts))
    if data_sha != res['reproducao']['dados_sha256']: sys.exit('Os dados não são os mesmos da etapa A (SHA-256 diferente).')
    pos = {q: k for k, q in enumerate(ids)}; n = len(ids)
    dups = collections.defaultdict(set); mem_pairs = set()
    for line in open(lpath):
        p, q, d = line.rstrip('\n').split('\t'); p, q = int(p), int(q)
        if p in pos and q in pos and p != q:
            dups[p].add(q); dups[q].add(p); x, y = sorted((pos[p], pos[q]))
            if d < G.T0 and dates[y] < G.T0: mem_pairs.add((x, y))
    e0 = next((k for k, d in enumerate(dates) if d >= G.T0), n)
    earlier = lambda i: {pos[s] for s in dups.get(ids[i], ()) if pos[s] < i}
    lab = [i for i in range(e0, n) if earlier(i)]; unl_all = [i for i in range(e0, n) if not earlier(i)]
    N = n - e0; unl = random.Random(2024).sample(unl_all, min(G.N_UNL, len(unl_all)))
    tag = embed.replace(':', '_').replace('/', '_'); qrows = sorted(set(lab) | set(unl)); qidx = {i: j for j, i in enumerate(qrows)}
    pre_q, pre_d = ('search_query: ', 'search_document: ') if 'nomic' in embed else ('', '')
    emb_meta = {}
    for name, rows_, pre in (('q', qrows, pre_q), ('d', range(n), pre_d)):
        path = f'gc_cache/{PFX}_{name}_{tag}.npy'
        if not os.path.exists(path + '.meta.json'): sys.exit(f'Faltam os embeddings {path}.')
        mm = json.load(open(path + '.meta.json'))
        if mm['linhas'] != len(rows_) or mm['textos_sha256'] != G.sha(pre + texts[i] for i in rows_) or int(open(path + '.done').read()) != len(rows_):
            sys.exit(f'Os embeddings {path} não correspondem aos dados da etapa A.')
        emb_meta[name] = mm
    rec_key = G.sha([VERSAO, data_sha, json.dumps(emb_meta, sort_keys=True), G.BETA])[:16]; rec = None
    if os.path.exists(REC):
        c = json.load(open(REC))
        if c.get('chave') == rec_key: rec = {int(k): v for k, v in c['rec'].items()}
    if rec is None:
        print('  recalculando as sugestões de M0, H1 e H (alguns minutos)', flush=True)
        Q = np.asarray(np.load(f'gc_cache/{PFX}_q_{tag}.npy', mmap_mode='r'), dtype=np.float32)
        D = np.asarray(np.load(f'gc_cache/{PFX}_d_{tag}.npy', mmap_mode='r'), dtype=np.float32)
        P = sorted(mem_pairs)
        A = csr_matrix((np.ones(2 * len(P), dtype=np.float32), ([x for x, y in P] + [y for x, y in P], [y for x, y in P] + [x for x, y in P])), shape=(n, n))
        A.sum_duplicates(); A.data[:] = 1
        deg = np.diff(A.indptr).astype(np.float32); H = np.where(deg > 0)[0]; starts = A.indptr[H]
        C = G.normalize(D[H] + np.asarray(A[H] @ D)); logdeg = np.log1p(deg)
        rec = {}; rows_eval = lab + unl
        for b0 in range(0, len(rows_eval), 128):
            R = rows_eval[b0:b0 + 128]; QV = Q[[qidx[i] for i in R]]; SB = QV @ D.T
            for j, i in enumerate(R):
                s = SB[j]; s[i:] = -np.inf
                m1 = s.copy(); m1[H] = np.maximum(np.maximum(m1[H], np.maximum.reduceat(s[A.indices], starts)), C @ QV[j])
                m1[H] = np.where(np.isfinite(s[H]), m1[H], -np.inf)
                M0, M1, M2 = G.top5(s), G.top5(m1), G.top5(m1 + G.BETA * logdeg)
                r = {'M0': M0, 'H1': G.inter(M0, M1), 'H': G.inter(M0, M2)}
                g_ = earlier(i)
                if g_:
                    fs = set(g_)
                    for x in g_: fs |= set(A.indices[A.indptr[x]:A.indptr[x + 1]].tolist())
                    r['fam'] = sorted(fs)
                rec[i] = r
            if (b0 // 128) % 20 == 0: print(f'  {min(b0 + 128, len(rows_eval))}/{len(rows_eval)}', flush=True)
        json.dump({'chave': rec_key, 'rec': rec}, open(REC, 'w'))
    return dict(ids=ids, dates=dates, texts=texts, pos=pos, n=n, e0=e0, N=N, lab=lab, unl=unl, rec=rec, data_sha=data_sha)

def find_xml(names):
    found = {}
    for d, _, fs in os.walk(XDIR) if os.path.isdir(XDIR) else []:
        for f in fs:
            if f in names: found[f] = os.path.join(d, f)
    missing = [f for f in names if f not in found]
    if missing:
        if not os.path.exists(DUMP): sys.exit(f'Falta {missing} em {XDIR} e não achei {DUMP} nesta pasta para extrair.')
        print(f'  extraindo {missing} de {DUMP}', flush=True)
        binary = next((shutil.which(b) for b in ('7zz', '7z', '7za') if shutil.which(b)), None)
        manual = f'Alternativa manual: abra {DUMP} com o Keka ou The Unarchiver e coloque {missing} na pasta {XDIR}/.'
        try:
            if binary: subprocess.run([binary, 'x', DUMP, f'-o{XDIR}', *missing, '-y'], check=True, stdout=subprocess.DEVNULL)
            else:
                try: import py7zr
                except ImportError: sys.exit('Falta o py7zr. Rode: pip install py7zr   (' + manual + ')')
                with py7zr.SevenZipFile(DUMP, 'r') as z: z.extract(path=XDIR, targets=[nm for nm in z.getnames() if os.path.basename(nm) in missing])
        except SystemExit: raise
        except Exception as e: sys.exit(f'Não consegui extrair ({e}). ' + manual)
        for d, _, fs in os.walk(XDIR):
            for f in fs:
                if f in names: found[f] = os.path.join(d, f)
        if any(f not in found for f in names): sys.exit(f'O arquivo {DUMP} não tem {[f for f in names if f not in found]}.')
    return found

# ---------------------------------------------------------------- passo 1: preparar
def preparar(a):
    S = rebuild(a.embed); ids, texts, rec, dates, T0 = S['ids'], S['texts'], S['rec'], S['dates'], G.T0
    found = find_xml(('Posts.xml', 'PostHistory.xml', 'Votes.xml'))
    U = S['lab'] + S['unl']; Uid = {ids[i]: i for i in U}; lab_set = set(S['lab'])
    print('1. lendo respostas (Posts.xml)', flush=True)
    acc, wans, all_ans = {}, collections.defaultdict(list), collections.defaultdict(list)
    for r in G.rows(found['Posts.xml']):
        t = r.get('PostTypeId')
        if t == '1':
            q = int(r['Id'])
            if q in Uid and r.get('AcceptedAnswerId'): acc[q] = int(r['AcceptedAnswerId'])
        elif t == '2':
            p = int(r.get('ParentId', -1)); aid = int(r['Id'])
            if p in Uid: wans[p].append((aid, int(r.get('Score', 0) or 0), html_text(r.get('Body'), REF_WORDS)))
            if p in S['pos']: all_ans[p].append((aid, r.get('CreationDate', '')))
    def ref_text(q):
        for aid, sc_, txt in wans.get(q, ()):
            if aid == acc.get(q) and len(txt.split()) >= 3: return txt
        return None
    elig = [i for i in U if ref_text(ids[i]) is not None]
    fl = {i: {'H1xM0': rec[i]['H1'] != rec[i]['M0'], 'HxM0': rec[i]['H'] != rec[i]['M0'], 'HxH1': rec[i]['H'] != rec[i]['H1']} for i in elig}
    cnt = {}
    for gname, G_ in (('marcadas', [i for i in elig if i in lab_set]), ('sem_marcacao', [i for i in elig if i not in lab_set])):
        cnt[gname] = {'elegiveis': len(G_), **{f'{k}_contexto_diferente': sum(fl[i][k] for i in G_) for k in PAIRS},
                      'algum_diferente_de_M0': sum(fl[i]['H1xM0'] or fl[i]['HxM0'] for i in G_)}
    cnt['marcadas']['total'] = len(S['lab']); cnt['sem_marcacao']['total'] = len(S['unl'])
    poolP = sorted(i for i in elig if i not in lab_set and (fl[i]['H1xM0'] or fl[i]['HxM0']))
    Pq = sorted(random.Random(SEED_P).sample(poolP, N_P_MAX)) if len(poolP) > N_P_MAX else poolP
    Fq = sorted(i for i in elig if i in lab_set and (fl[i]['H1xM0'] or fl[i]['HxM0']))
    hm0_pool = [i for i in Pq + Fq if fl[i]['HxM0']]
    HM0 = sorted(random.Random(SEED_HM0).sample(hm0_pool, min(N_HM0, len(hm0_pool))))
    used = set(Pq) | set(Fq) | set(poolP)
    rest = [i for i in elig if i not in used]
    k1_cand = [i for i in rest if any(aid != acc.get(ids[i]) and sc_ > 0 and len(txt.split()) >= 3 for aid, sc_, txt in wans.get(ids[i], ()))]
    rk = random.Random(SEED_K1); K1q = sorted(rk.sample(k1_cand, min(N_K1, len(k1_cand)))); K1 = []
    for i in K1q:
        good = max((x for x in wans[ids[i]] if x[0] != acc.get(ids[i]) and x[1] > 0 and len(x[2].split()) >= 3), key=lambda x: (x[1], -x[0]))
        j = rk.choice([x for x in rest if x != i]); K1.append({'i': i, 'bom': good[2], 'ruim': ref_text(ids[j]), 'j': j})
    rest2 = [i for i in rest if i not in set(K1q)]
    K4q = sorted(random.Random(SEED_K4).sample(rest2, min(N_K4, len(rest2)))); rest3 = [i for i in rest2 if i not in set(K4q)]
    K5q = sorted(random.Random(SEED_K5).sample(rest3, min(N_K5, len(rest3))))
    # ---- resposta de cada discussão, como estava quando a pergunta nova foi publicada (regra da rodada 9)
    Qs = Pq + Fq
    pairs = sorted({(i, d) for i in Qs for m in ('M0', 'H1', 'H') for d in rec[i][m]}); need = sorted({d for _, d in pairs})
    cand = {aid for d in need for aid, _ in all_ans.get(ids[d], ())}
    print(f'2. votos (Votes.xml) de {len(cand)} respostas de {len(need)} discussões', flush=True)
    acc_days, up_days = collections.defaultdict(list), collections.defaultdict(list)
    for v in G.rows(found['Votes.xml']):
        pid = int(v.get('PostId', -1))
        if pid not in cand: continue
        t = v.get('VoteTypeId'); day_ = (v.get('CreationDate') or '')[:10]
        if t == '1': acc_days[pid].append(day_)
        elif t == '2': up_days[pid].append(day_)
    chosen, rule = {}, {}
    for i, d in pairs:
        qd = dates[i]; qday = qd[:10]
        answers = [(aid, ad) for aid, ad in all_ans.get(ids[d], ()) if ad < qd]
        accepted = [(max(x for x in acc_days[aid] if x < qday), aid) for aid, _ in answers if any(x < qday for x in acc_days.get(aid, ()))]
        if accepted: chosen[(i, d)] = max(accepted)[1]; rule[(i, d)] = 'aceita_antes_da_pergunta'
        elif answers:
            chosen[(i, d)] = min(answers, key=lambda x: (-sum(y < qday for y in up_days.get(x[0], ())), x[1], x[0]))[0]; rule[(i, d)] = 'mais_votada_antes_da_pergunta'
        else: rule[(i, d)] = 'sem_resposta'
    want = set(chosen.values())
    print('3. texto dessas respostas na data de cada pergunta (PostHistory.xml, 10 a 40 minutos)', flush=True)
    versions = collections.defaultdict(list)
    for h in G.rows(found['PostHistory.xml']):
        if h.get('PostHistoryTypeId') not in ('2', '5', '8'): continue
        pid = int(h.get('PostId', -1))
        if pid in want: versions[pid].append((h.get('CreationDate', ''), (h.get('Text') or '')[:20000]))
    doca = {}
    for (i, d) in pairs:
        aid = chosen.get((i, d)); txt = None
        if aid is not None:
            vs = [v for v in versions.get(aid, ()) if v[0] < dates[i]]
            if vs: txt = words(G.clean_md(max(vs)[1]), DOCA_WORDS) or None
            else: rule[(i, d)] = 'sem_historico'
        doca[f'{i}|{d}'] = {'a': txt, 'regra': rule[(i, d)]}
    nans = lambda m, i: sum(doca[f'{i}|{d}']['a'] is not None for d in rec[i][m])
    bal = {s_: {c: round(float(np.mean([nans(LIST[c], i) for i in G_])), 3) if G_ else None for c in LIST} for s_, G_ in (('P', Pq), ('F', Fq))}
    allq = Qs + K1q + K4q + K5q
    T = {'docq': {str(d): words(texts[d], DOCQ_WORDS) for d in need}, 'doca': doca,
         'q': {str(i): words(texts[i], Q_WORDS) for i in allq}, 'ref': {str(i): ref_text(ids[i]) for i in allq}, 'k1': K1}
    with gzip.open(TEXTOS, 'wt', encoding='utf-8') as f: json.dump(T, f, ensure_ascii=False, sort_keys=True)
    sc = (S['N'] - len(S['lab'])) / max(len(S['unl']), 1)
    am = {'versao': VERSAO, 'site': SITE, 'dados_sha256': S['data_sha'], 'textos_sha256': file_sha(TEXTOS),
          'contagens': cnt, 'escala_sem_marcacao': sc,
          'estratos': {'P_pool': len(poolP), 'P': len(Pq), 'P_sorteado': len(poolP) > N_P_MAX, 'F': len(Fq), 'HxM0_subamostra': len(HM0),
                       'K1': len(K1), 'K4': len(K4q), 'K5': len(K5q)},
          'regra_da_resposta_nas_discussoes': dict(collections.Counter(rule.values())),
          'discussoes_com_resposta_por_contexto (media de 5)': bal,
          'ids': {'P': [ids[i] for i in Pq], 'F': [ids[i] for i in Fq], 'HxM0': [ids[i] for i in HM0], 'K1': [[ids[k['i']], ids[k['j']]] for k in K1],
                  'K4': [ids[i] for i in K4q], 'K5': [ids[i] for i in K5q]},
          '_idx': {'P': Pq, 'F': Fq, 'HxM0': HM0, 'K4': K4q, 'K5': K5q, 'P_pool_tamanho': len(poolP)},
          '_flags': {str(i): fl[i] for i in Qs}}
    json.dump(am, open(AMOSTRA, 'w'), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in am.items() if not k.startswith('_') and k != 'ids'}, ensure_ascii=False, indent=1))
    print(f'\nPronto. Envie {AMOSTRA} (só contagens e números de pergunta).')

# ---------------------------------------------------------------- geração (cache por prompt: prompts idênticos são gerados uma vez)
def load_state():
    for p in (AMOSTRA, TEXTOS):
        if not os.path.exists(p): sys.exit(f'Falta {p}. Rode primeiro: python3 gc_r11.py preparar')
    am = json.load(open(AMOSTRA))
    if file_sha(TEXTOS) != am['textos_sha256']: sys.exit(f'{TEXTOS} mudou desde o preparar. Rode o preparar de novo.')
    T = json.load(gzip.open(TEXTOS, 'rt', encoding='utf-8')); rec = {int(k): v for k, v in json.load(open(REC))['rec'].items()}
    return am, T, rec

def prompt_for(cond, i, T, rec):
    q = T['q'][str(i)]
    if cond in CTRL_PROMPTS: return CTRL_PROMPTS[cond].format(q=q, ref=T['ref'][str(i)])
    docs = rec[i][LIST[cond]]
    ctx = CTX_HEAD + '\n\n'.join(DOC_FMT.format(k=k, q=T['docq'][str(d)], a=T['doca'][f'{i}|{d}']['a'] or '(no answer)') for k, d in enumerate(docs, 1)) + '\n\n'
    return GEN_PROMPT.format(context=ctx, question=q)

def phash(p): return hashlib.sha256(p.encode('utf-8')).hexdigest()[:24]

def jobs(am):
    ix, fl = am['_idx'], am['_flags']; out = []
    for i in ix['P'] + ix['F']:
        f = fl[str(i)]; out.append(('CM0', i))
        if f['H1xM0'] or f['HxH1']: out.append(('CH1', i))
        if f['HxM0'] or f['HxH1']: out.append(('CH', i))
    out += [('PARA1', i) for i in ix['K4'] + ix['K5']] + [('PARA2', i) for i in ix['K5']]
    return list(dict.fromkeys(out))

class Gen:
    def __init__(self, a, am):
        self.host, self.model = a.host, a.modelo
        self.digest, self.ollama_version = G.ollama(a.host, a.modelo)
        self.fp = G.sha([VERSAO, a.modelo, self.digest, NUM_PREDICT, GEN_SEED, am['dados_sha256'], am['textos_sha256']])[:16]
        self.path = f'gc_cache/r11_geracoes_{self.fp}.jsonl'; self.cache = {}
        if os.path.exists(self.path):
            for line in open(self.path, encoding='utf-8'):
                try: d = json.loads(line); self.cache[d['h']] = d
                except Exception: pass
        self.f = open(self.path, 'a', encoding='utf-8'); self.think = True
    def __call__(self, prompt):
        h = phash(prompt)
        if h in self.cache: return self.cache[h]
        payload = {'model': self.model, 'stream': False, 'prompt': prompt, 'options': {'temperature': 0, 'num_predict': NUM_PREDICT, 'seed': GEN_SEED}}
        if self.think: payload['think'] = False
        t0 = time.time()
        try:
            try: r = G.post(self.host, '/api/generate', payload, timeout=900)
            except urllib.error.HTTPError:
                if not self.think: raise
                self.think = False; payload.pop('think'); r = G.post(self.host, '/api/generate', payload, timeout=900)
        except urllib.error.URLError as e:
            sys.exit(f'O Ollama não respondeu ({e}). Abra o Ollama e rode o mesmo comando: o que já foi gerado fica salvo.')
        d = {'h': h, 't': (r.get('response') or '').strip(), 's': round(time.time() - t0, 2),
             'tok_entrada': r.get('prompt_eval_count'), 'tok_saida': r.get('eval_count')}
        self.cache[h] = d; self.f.write(json.dumps(d, ensure_ascii=False) + '\n'); self.f.flush()
        return d

def gerar(a):
    if not a.pre_registro_congelado: sys.exit('Use --pre-registro-congelado (o pré-registro da rodada 11 foi congelado em 30/09/2026, 14h20).')
    am, T, rec = load_state(); g = Gen(a, am); todo = jobs(am)
    prompts = {}
    for c, i in todo: prompts.setdefault(phash(prompt_for(c, i, T, rec)), (c, i))
    left = [(h, ci) for h, ci in prompts.items() if h not in g.cache]
    print(f'Gerando {len(left)} de {len(prompts)} prompts distintos ({len(todo)} pares condição-pergunta; os repetidos são reaproveitados)', flush=True)
    t0 = time.time()
    for k, (h, (c, i)) in enumerate(left, 1):
        g(prompt_for(c, i, T, rec))
        if k % 20 == 0 or k == len(left):
            rate = k / max(time.time() - t0, 1e-9); print(f'  {k}/{len(left)}  (~{(len(left) - k) / rate / 60:.0f} min restantes)', flush=True)
    print(json.dumps({'prompts_distintos': len(prompts), 'vazias': sum(1 for h in prompts if not g.cache[h]['t']), 'cache': os.path.basename(g.path)}, ensure_ascii=False))
    print('\nPronto. Agora rode: python3 gc_r11.py controles')

# ---------------------------------------------------------------- controles
def ctrl(am, T, rec, g):
    ix = am['_idx']; txt = lambda c, i: words(g(prompt_for(c, i, T, rec))['t'], CAND_WORDS)
    pid = {i: str(am['ids']['K4'][n]) for n, i in enumerate(ix['K4'])}
    return ix, txt, pid

def controles(a):
    am, T, rec = load_state(); g = Gen(a, am)
    miss = [x for x in jobs(am) if phash(prompt_for(x[0], x[1], T, rec)) not in g.cache]
    if miss: sys.exit(f'Faltam {len(miss)} gerações. Rode: python3 gc_r11.py gerar --modelo {a.modelo} --pre-registro-congelado')
    ix, txt, pid = ctrl(am, T, rec, g)
    if not os.path.exists(K4_EXT):
        with open(K4_BASE, 'w', encoding='utf-8') as f:
            f.write(K4_HEAD)
            for n, i in enumerate(ix['K4'], 1):
                f.write(f'\n#C{n:03d}  QUESTION_ID: {pid[i]}\nQUESTION: {T["q"][str(i)]}\nREFERENCE (accepted by the asker): {T["ref"][str(i)]}\nVERSION 1: {txt("PARA1", i)}\n')
        print(f'Criado {K4_BASE}. Envie ao Claude. Quando voltar o {K4_EXT}, salve na pasta e rode de novo: python3 gc_r11.py controles'); return
    pairs = ctrl_pairs(am, T, rec, g)
    open(REVIEW, 'w', encoding='utf-8').write(review_text(pairs, T))
    print(json.dumps({'pares_para_revisao': dict(collections.Counter(p['rotulo'] for p in pairs)), 'arquivo_sha256': file_sha(REVIEW)}, ensure_ascii=False, indent=1))
    print(f'\nEnvie {REVIEW} ao Claude para a revisão prévia. Salve a resposta como {APPROVED} e rode: python3 gc_r11.py itens')

def ctrl_pairs(am, T, rec, g):
    ix, txt, pid = ctrl(am, T, rec, g); norm = lambda t: ' '.join(t.split()).lower(); out = []
    raw = json.load(open(K4_EXT, encoding='utf-8')); extra = set(raw) - set(pid.values())
    if extra: sys.exit(f'{K4_EXT} tem perguntas fora do K4: {sorted(extra)[:5]}')
    ok = lambda t1, t2: t1.strip() and t2.strip() and norm(t1) != norm(t2)
    for n, i in enumerate(ix['K4'], 1):
        if pid[i] not in raw or not raw[pid[i]]: continue
        t1, t2 = txt('PARA1', i), words(raw[pid[i]], CAND_WORDS)
        if ok(t1, t2): out.append({'tipo': 'K4', 'rotulo': 'ERROR', 'i': i, 'c1': 'PARA1', 'c2': 'ERRO_EXTERNO', 't1': t1, 't2': t2, 'id': f'C{n:03d}'})
    pid5 = {i: str(am['ids']['K5'][n]) for n, i in enumerate(ix['K5'])}
    ext5 = json.load(open(K5_EXT, encoding='utf-8')) if os.path.exists(K5_EXT) else {}
    extra5 = set(ext5) - set(pid5.values())
    if extra5: sys.exit(f'{K5_EXT} tem perguntas fora do K5: {sorted(extra5)[:5]}')
    for n, i in enumerate(ix['K5'], len(ix['K4']) + 1):
        if ext5.get(pid5[i]): c2, t1, t2 = 'PARA_EXTERNO', txt('PARA1', i), words(ext5[pid5[i]], CAND_WORDS)
        else: c2, t1, t2 = 'PARA2', txt('PARA1', i), txt('PARA2', i)
        if ok(t1, t2): out.append({'tipo': 'K5', 'rotulo': 'EQUIVALENT', 'i': i, 'c1': 'PARA1', 'c2': c2, 't1': t1, 't2': t2, 'id': f'C{n:03d}'})
    return out

def review_text(pairs, T):
    return REVIEW_HEAD + ''.join(f'\n#{p["id"]}  TYPE: {p["rotulo"]}\nQUESTION: {T["q"][str(p["i"])]}\nREFERENCE (accepted by the asker): {T["ref"][str(p["i"])]}\n'
                                 f'VERSION 1: {p["t1"]}\nVERSION 2: {p["t2"]}\n' for p in pairs)

# ---------------------------------------------------------------- itens cegos
def itens(a):
    if os.path.exists(KEY) and not a.refazer: sys.exit(f'{KEY} já existe. Para gerar de novo (invalida rótulos anteriores), use --refazer.')
    am, T, rec = load_state(); g = Gen(a, am)
    miss = [x for x in jobs(am) if phash(prompt_for(x[0], x[1], T, rec)) not in g.cache]
    if miss: sys.exit(f'Faltam {len(miss)} gerações. Rode: python3 gc_r11.py gerar --modelo {a.modelo} --pre-registro-congelado')
    if not os.path.exists(K4_EXT): sys.exit(f'Falta {K4_EXT}. Rode primeiro: python3 gc_r11.py controles')
    pairs = ctrl_pairs(am, T, rec, g)
    if not os.path.exists(REVIEW) or open(REVIEW, encoding='utf-8').read() != review_text(pairs, T): sys.exit('Rode primeiro: python3 gc_r11.py controles')
    if not os.path.exists(APPROVED): sys.exit(f'Falta {APPROVED} (a revisão prévia dos pares de controle).')
    raw = json.load(open(APPROVED)); raw = raw.get('aprovacoes', raw) if isinstance(raw, dict) else raw
    okp = {str(k).lstrip('#'): str(v).strip().upper() in ('APPROVED', 'APROVADO', 'SIM', 'YES', 'TRUE') for k, v in raw.items()}
    if [p['id'] for p in pairs if p['id'] not in okp]: sys.exit(f'{APPROVED} não tem decisão para todos os pares.')
    ix, fl = am['_idx'], am['_flags']; lab_q = set(ix['F']); hm0 = set(ix['HxM0'])
    gen = lambda c, i: g(prompt_for(c, i, T, rec)); norm = lambda t: ' '.join(t.split()).lower()
    nans = lambda m, i: sum(T['doca'][f'{i}|{d}']['a'] is not None for d in rec[i][m])
    base, auto = [], []
    for i in ix['P'] + ix['F']:
        estr = 'F' if i in lab_q else 'P'
        for pk, (c1, c2) in PAIRS.items():
            if pk == 'HxM0' and i not in hm0: continue
            it = {'tipo': pk, 'estrato': estr, 'i': i, 'c1': c1, 'c2': c2, 'r1': nans(LIST[c1], i), 'r2': nans(LIST[c2], i)}
            if not fl[str(i)][pk]: auto.append({**it, 'empate': 'prompt_identico'}); continue
            t1, t2 = words(gen(c1, i)['t'], CAND_WORDS), words(gen(c2, i)['t'], CAND_WORDS)
            if norm(t1) == norm(t2): auto.append({**it, 'empate': 'resposta_identica'}); continue
            base.append({**it, 't1': t1, 't2': t2})
    for k in T['k1']: base.append({'tipo': 'K1', 'i': k['i'], 'c1': 'MESMA_PERGUNTA', 'c2': 'OUTRA_PERGUNTA', 'certo': 'MESMA_PERGUNTA', 't1': k['bom'], 't2': k['ruim']})
    for p in pairs:
        if okp[p['id']]: base.append({'tipo': p['tipo'], 'i': p['i'], 'c1': p['c1'], 'c2': p['c2'], 't1': p['t1'], 't2': p['t2'], 'certo': 'PARA1' if p['tipo'] == 'K4' else None})
    r = random.Random(SEED_ITEMS); principal = [it for it in base if it['tipo'] in PAIRS]
    k2src = r.sample(principal, min(N_K2, len(principal)))
    for it in base: it['A'] = r.choice(('c1', 'c2'))
    sent = list(base)
    for o in k2src: sent.append({**{k: v for k, v in o.items() if k != 'A'}, 'tipo': 'K2', 'origem': id(o), 'A': 'c2' if o['A'] == 'c1' else 'c1'})
    for it in sent: it['_id'] = id(it)
    r.shuffle(sent); num = {it['_id']: n for n, it in enumerate(sent, 1)}
    with open(ITEMS, 'w', encoding='utf-8') as f:
        f.write('ROUND 11: BLIND ITEMS\n' + RUBRIC + '\n')
        for n, it in enumerate(sent, 1):
            A, B = (it['t1'], it['t2']) if it['A'] == 'c1' else (it['t2'], it['t1'])
            f.write(f'\n#{n}\nQUESTION: {T["q"][str(it["i"])]}\nREFERENCE (accepted by the asker): {T["ref"][str(it["i"])]}\nANSWER A: {A}\nANSWER B: {B}\n')
    rows = []
    for it in sent:
        cA, cB = (it['c1'], it['c2']) if it['A'] == 'c1' else (it['c2'], it['c1'])
        rows.append({'n': num[it['_id']], 'tipo': it['tipo'], 'estrato': it.get('estrato'), 'i': it['i'], 'A': cA, 'B': cB, 'certo': it.get('certo'),
                     'origem': num.get(it.get('origem')), 'c1': it['c1'], 'c2': it['c2'], 'r1': it.get('r1'), 'r2': it.get('r2')})
    # família no top-5 de cada método (só para o estrato F, descritivo)
    famg = {}
    for i in ix['F']:
        fs = set(rec[i].get('fam', [])); famg[str(i)] = {m: bool(fs & set(rec[i][m])) for m in ('M0', 'H1', 'H')}
    stats = collections.defaultdict(list)
    for c, i in jobs(am):
        if c in LIST:
            d = gen(c, i); stats[c].append((len(d['t'].split()), d.get('tok_entrada') or 0, d.get('tok_saida') or 0))
    custo = {c: {'palavras_media': round(float(np.mean([x[0] for x in v])), 1), 'tokens_entrada_media': round(float(np.mean([x[1] for x in v])), 1),
                 'tokens_saida_media': round(float(np.mean([x[2] for x in v])), 1)} for c, v in stats.items()}
    key = {'versao': VERSAO, 'itens_sha256': file_sha(ITEMS), 'rubrica': RUBRIC, 'amostra_textos_sha256': am['textos_sha256'],
           'geracoes_cache': os.path.basename(g.path), 'modelo': a.modelo, 'digest': g.digest, 'ollama': g.ollama_version,
           'script_sha256': file_sha(os.path.abspath(__file__)), 'itens': sorted(rows, key=lambda x: x['n']), 'empates_automaticos': auto,
           'contagens': am['contagens'], 'escala_sem_marcacao': am['escala_sem_marcacao'], 'P_pool_tamanho': ix['P_pool_tamanho'],
           'P_n': len(ix['P']), 'F_n': len(ix['F']), 'familia_no_top5_F': famg, 'custo_por_condicao': custo,
           'controles': {'pares_revisados': dict(collections.Counter(p['tipo'] for p in pairs)),
                         'pares_aprovados': dict(collections.Counter(p['tipo'] for p in pairs if okp[p['id']])),
                         'revisao_sha256': file_sha(REVIEW), 'aprovacoes_sha256': file_sha(APPROVED), 'erros_do_K4_sha256': file_sha(K4_EXT),
                         'versoes_do_K5_sha256': file_sha(K5_EXT) if os.path.exists(K5_EXT) else None}}
    json.dump(key, open(KEY, 'w'), ensure_ascii=False)
    print(json.dumps({'itens': len(sent), 'empates_automaticos': dict(collections.Counter(f"{x['tipo']}:{x['empate']}" for x in auto)),
                      'por_tipo': dict(collections.Counter(it['tipo'] for it in sent)), 'controles': key['controles'], 'itens_sha256': key['itens_sha256']},
                     ensure_ascii=False, indent=1, default=str))
    print(f'\nEnvie SÓ o arquivo {ITEMS} ao Claude. NÃO envie {KEY}.')

# ---------------------------------------------------------------- comparação
def comparar(a):
    if not os.path.exists(KEY): sys.exit(f'Falta {KEY}. Rode primeiro: python3 gc_r11.py itens')
    key = json.load(open(KEY))
    if file_sha(ITEMS) != key['itens_sha256']: sys.exit(f'{ITEMS} foi alterado ou gerado de novo; os rótulos não correspondem.')
    its = key['itens']; lab = R9.parse_labels(a.rotulos, len(its))
    for it in its: it['vence'] = None if lab[it['n']] == 'TIE' else it[lab[it['n']]]
    mean = lambda x: round(float(np.mean(x)), 3) if len(x) else None
    acc = lambda t: [it['vence'] == it['certo'] for it in its if it['tipo'] == t]
    by_n = {it['n']: it for it in its}
    k2 = [it['vence'] == by_n[it['origem']]['vence'] for it in its if it['tipo'] == 'K2']; k5 = [it['vence'] is None for it in its if it['tipo'] == 'K5']
    K = {'K1_discriminacao_facil': {'n': len(acc('K1')), 'acerto': mean(acc('K1')), 'minimo': K1_MIN},
         'K2_ordem': {'n': len(k2), 'consistencia': mean(k2), 'minimo': K2_MIN},
         'K4_erro_decisivo': {'n': len(acc('K4')), 'acerto': mean(acc('K4')), 'minimo': K4_MIN, 'minimo_de_pares': K4_MIN_APROV},
         'K5_equivalentes': {'n': len(k5), 'empates': mean(k5), 'minimo': K5_MIN_TIE, 'minimo_de_pares': K5_MIN_APROV}}
    valid = (all(v[m] is not None and v[m] >= v['minimo'] for v, m in ((K['K1_discriminacao_facil'], 'acerto'), (K['K2_ordem'], 'consistencia'),
                                                                     (K['K4_erro_decisivo'], 'acerto'), (K['K5_equivalentes'], 'empates')))
             and len(acc('K4')) >= K4_MIN_APROV and len(k5) >= K5_MIN_APROV)
    # escore por pergunta e comparação: +1 primeira condição (c1), -1 segunda (c2), 0 empate
    score = collections.defaultdict(dict)
    for it in its:
        if it['tipo'] in PAIRS: score[it['tipo']][it['i']] = (+1 if it['vence'] == it['c1'] else (-1 if it['vence'] == it['c2'] else 0), it['estrato'], it['r1'] - it['r2'], 'julgado')
    for x in key['empates_automaticos']: score[x['tipo']][x['i']] = (0, x['estrato'], x['r1'] - x['r2'], x['empate'])
    rng = np.random.default_rng(11)
    def delta(x):
        x = np.array(x, dtype=float)
        if not len(x): return {'n': 0, 'delta': None, 'ic95': None}
        boots = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(NBOOT)]
        return {'n': int(len(x)), 'delta': round(float(x.mean()), 4), 'ic95': R9.ci(boots),
                'prefere_primeira': int((x > 0).sum()), 'prefere_segunda': int((x < 0).sum()), 'empates': int((x == 0).sum())}
    cond = lambda pk, estr, pred=lambda v: True: [v[0] for i, v in score[pk].items() if v[1] == estr and pred(v)]
    # efeito sobre a população de perguntas elegíveis (marcadas peso 1, sem marcação peso escala), com zeros das que não entraram nos estratos
    cm, cu, sc = key['contagens']['marcadas'], key['contagens']['sem_marcacao'], key['escala_sem_marcacao']
    NL, NU, Np, nP = cm['elegiveis'], cu['elegiveis'], key['P_pool_tamanho'], key['P_n']
    def pop(pk, n_boot=NBOOT):
        sF = np.array([v[0] for v in score[pk].values() if v[1] == 'F'], float); sP = np.array([v[0] for v in score[pk].values() if v[1] == 'P'], float)
        labs = np.concatenate([sF, np.zeros(max(NL - len(sF), 0))])
        est = lambda L, npool, sp: (L.sum() + sc * npool * (sp.mean() if len(sp) else 0.0)) / (NL + sc * NU)
        point = est(labs, Np, sP); boots = []
        for _ in range(n_boot):
            Lb = labs[rng.integers(0, len(labs), len(labs))] if len(labs) else labs
            npb = rng.binomial(NU, Np / NU) if NU else 0
            spb = sP[rng.integers(0, len(sP), len(sP))] if len(sP) else sP
            boots.append(est(Lb, npb, spb))
        return {'delta': round(float(point), 4), 'ic95': R9.ci(boots)}
    # errata 1 (01/10/2026): o par HxH1 tem CH como primeira condição; o P1 pré-registrado é Δ(CH1 − CH), então o escore entra com sinal trocado
    P1 = delta([-s for s in cond('HxH1', 'P', lambda v: v[3] != 'prompt_identico')])
    popH1 = pop('H1xM0')
    p1 = (bool(P1['ic95'] and P1['ic95'][0] > 0)) if valid else 'inconclusivo (juiz reprovado nos controles)'
    p2 = (bool(popH1['ic95'] and popH1['ic95'][0] > MARGIN_P2)) if valid else 'inconclusivo (juiz reprovado nos controles)'
    p3 = (bool(popH1['ic95'] and popH1['ic95'][0] > 0)) if valid else 'inconclusivo (juiz reprovado nos controles)'
    if not valid: resumo = ['INCONCLUSIVO (juiz reprovado nos controles ou controles insuficientes)']
    else:
        resumo = [('P1: retirar a popularidade melhorou a resposta em relacao a H' if p1 else 'P1: melhora de H1 sobre H nao demonstrada'),
                  ('P2: H1 ficou dentro da perda tolerada (-0,03) frente a M0' if p2 else 'P2: nao foi possivel demonstrar que H1 fica dentro da perda tolerada (isso sozinho nao demonstra piora)'),
                  ('P3: H1 superou M0' if p3 else 'P3: superioridade de H1 sobre M0 nao demonstrada')]
    groups = lambda i: key['familia_no_top5_F'].get(str(i), {})
    def fam_split(pk, a_, b_):
        out = collections.defaultdict(list)
        for i, v in score[pk].items():
            if v[1] != 'F': continue
            g_ = groups(i); ka = 'ganho' if g_.get(a_) and not g_.get(b_) else ('perda' if g_.get(b_) and not g_.get(a_) else 'sem_mudanca')
            out[ka].append(v[0])
        return {k: delta(v) for k, v in out.items()}
    def balance(pk, estr):
        out = collections.defaultdict(list)
        for i, v in score[pk].items():
            if v[1] == estr and v[3] != 'prompt_identico': out['mesmo_numero' if v[2] == 0 else ('primeira_com_mais' if v[2] > 0 else 'segunda_com_mais')].append(v[0])
        return {k: delta(v) for k, v in out.items()}
    out = {'versao': key['versao'], 'itens': len(its), 'controles_do_juiz': K, 'juiz_valido': valid, 'controles_revisados': key['controles'],
           'errata_1': 'P1 = Δ(CH1 − CH) como no pré-registro; a versão 6e6ec634 calculava CH − CH1 com o rótulo trocado. Em P1, prefere_primeira = H1 e prefere_segunda = H.',
           'criterios': {'P1_HxH1_no_estrato_P_IC_inferior_>_0': p1, 'P2_populacao_H1_menos_M0_IC_inferior_>_-0.03': p2,
                         'P3_populacao_H1_menos_M0_IC_inteiro_>_0': p3, 'RESUMO': resumo},
           'P1_H1_menos_H_no_estrato_P': P1, 'populacao_H1_menos_M0': popH1,
           'secundarios': {
               'populacao_H_menos_H1': pop('HxH1'),
               'condicionais_contexto_diferente': {pk: {e: delta(cond(pk, e, lambda v: v[3] != 'prompt_identico')) for e in ('P', 'F')} for pk in PAIRS},
               'H_menos_M0_subamostra': {e: delta(cond('HxM0', e)) for e in ('P', 'F')},
               'F_por_familia': {'H1_menos_M0': fam_split('H1xM0', 'H1', 'M0'), 'H_menos_H1': fam_split('HxH1', 'H', 'H1'), 'H_menos_M0': fam_split('HxM0', 'H', 'M0')},
               'equilibrio_de_discussoes_com_resposta_P': {pk: balance(pk, 'P') for pk in PAIRS},
               'empates_automaticos': dict(collections.Counter(f"{x['tipo']}:{x['empate']}" for x in key['empates_automaticos'])),
               'custo_por_condicao': key['custo_por_condicao'],
               'juiz_escolheu_A_nos_principais': round(float(np.mean([lab[it['n']] == 'A' for it in its if it['tipo'] in PAIRS])), 3),
               'juiz_empates_nos_principais': round(float(np.mean([lab[it['n']] == 'TIE' for it in its if it['tipo'] in PAIRS])), 3)},
           'pesos': {'marcadas_elegiveis': NL, 'sem_marcacao_elegiveis_na_amostra': NU, 'escala_sem_marcacao': sc, 'P_pool': Np, 'P_julgado': nP},
           'reproducao': {'itens_sha256': key['itens_sha256'], 'modelo': key['modelo'], 'digest': key['digest'], 'ollama': key['ollama'],
                          'geracoes_cache': key['geracoes_cache'], 'script_sha256': key['script_sha256'],
                          'script_comparar_sha256': file_sha(os.path.abspath(__file__))}}
    json.dump(out, open(OUT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(json.dumps(out, ensure_ascii=False, indent=1)); print(f'\nPronto. Envie {OUT} (só números agregados). NÃO envie {KEY}.')

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('acao', choices=['preparar', 'gerar', 'controles', 'itens', 'comparar']); ap.add_argument('rotulos', nargs='?')
    ap.add_argument('--embed', default='nomic-embed-text'); ap.add_argument('--modelo', default='gemma4:latest'); ap.add_argument('--host', default='http://localhost:11434')
    ap.add_argument('--pre-registro-congelado', action='store_true'); ap.add_argument('--refazer', action='store_true'); a = ap.parse_args()
    os.makedirs('gc_cache', exist_ok=True)
    if a.acao == 'preparar': preparar(a)
    elif a.acao == 'gerar': gerar(a)
    elif a.acao == 'controles': controles(a)
    elif a.acao == 'itens': itens(a)
    else:
        if not a.rotulos: sys.exit('Informe o arquivo de rótulos: python3 gc_r11.py comparar r11_rotulos.json')
        comparar(a)

if __name__ == '__main__':
    main()
