"""Grande Cérebro, Rodada 9: a discussão recuperada melhora a resposta final?

Rode na mesma pasta do gc_conf.py, depois da confirmação (usa gc_data, gc_cache e gc_conf_result.json).
Precisa também do Votes.xml; se ele não estiver extraído, o script o tira do askubuntu.com.7z da mesma pasta.

Passo 1  python3 gc_r9.py preparar
         lê respostas, votos e histórico; monta os estratos e as amostras.
         cria r9_amostra.json (só contagens e números de pergunta)   -> ENVIE
Passo 2  python3 gc_r9.py piloto --modelo gemma4:latest
         10 perguntas fora da amostra; mede o tempo e mostra o formato.
         cria r9_piloto.txt e r9_piloto.json                          -> ENVIE os dois
Passo 3  (só depois que o pré-registro estiver congelado no protocolo)
         python3 gc_r9.py gerar --modelo gemma4:latest --pre-registro-congelado
         gera todas as respostas; pode parar e rodar de novo: continua de onde parou.
Passo 4  python3 gc_r9.py controles
         cria r9_controles_revisao.txt (pares de controle para revisão prévia)  -> ENVIE ao Claude
         salve na pasta o r9_controles_aprovados.json que voltar da revisão
Passo 5  python3 gc_r9.py itens
         cria r9_itens.txt                                           -> ENVIE ao Claude
         cria r9_chave_NAO_ENVIAR.json                               -> NUNCA envie
Passo 6  salve na pasta o r9_rotulos.json que o Claude devolver e rode:
         python3 gc_r9.py comparar r9_rotulos.json
         cria r9_resultado.json (só números agregados)               -> ENVIE
"""
import argparse, collections, gzip, hashlib, html, json, os, random, re, shutil, subprocess, sys, time, urllib.error
import numpy as np
from scipy.sparse import csr_matrix
import gc_conf as G

VERSAO = 'r9-v1'                                # dados e amostras (preparar)
VERSAO_ANALISE = 'r9-v2'                        # geração, controles, itens e comparação (após a revisão do Astra)
N_E1, N_E2, N_E3, N_C0_E1, N_C0_E2, E1_MIN = 250, 400, 80, 75, 75, 80
N_PILOT, N_K1, N_K2, N_K3, N_K4, N_K5 = 10, 60, 40, 60, 60, 40
SEED_SAMPLE, SEED_PILOT, SEED_K3, SEED_K1, SEED_K5, SEED_ITEMS = 909, 910, 911, 912, 913, 31338
Q_WORDS, DOCQ_WORDS, DOCA_WORDS, REF_WORDS, CAND_WORDS = 150, 80, 150, 200, 260
NUM_PREDICT, GEN_SEED, NBOOT = 350, 42, 2000
MARGIN_P2, K1_MIN, K2_MIN, K4_MIN, K5_MIN_TIE = -0.10, 0.85, 0.75, 0.80, 0.50
K4_MIN_APROV, K5_MIN_APROV = 30, 20

GEN_PROMPT = ('You are answering a question posted on Ask Ubuntu.\n\n{context}Question:\n{question}\n\n'
              'Write a helpful answer in English, at most 200 words, with concrete steps or commands where appropriate.')
CTX_HEAD = ('Earlier discussions from the same site are listed below. They may or may not be relevant to this question; '
            'use them only if they apply, and do not refer to them explicitly.\n\n')
DOC_FMT = '[{k}] Earlier question: {q}\nAnswer given there: {a}'
RUBRIC = ('Each item shows a question posted on Ask Ubuntu, a REFERENCE answer and two candidate answers, A and B. '
          'The reference was accepted by the asker; use it as evidence, while also considering the requirements of the question '
          'and the technical validity of each candidate. A different approach can be equally correct. Decide which candidate is '
          'more likely to solve the asker\'s problem; a candidate with wrong, risky or irrelevant steps is worse. Ignore length, '
          'style and formatting. Answer A, B or TIE (TIE when neither is clearly more likely to solve the problem).')
_REWRITE = ('Rewrite the following answer to a question posted on Ask Ubuntu in your own words{extra}. {rule}\n\n'
            'Question:\n{{q}}\n\nAnswer:\n{{ref}}\n\nRewritten answer:')
_KEEP = 'Keep every technical step, command, package name, option and path exactly correct, and do not add or remove steps.'
CTRL_PROMPTS = {
    'PARA1': _REWRITE.format(extra='', rule=_KEEP),
    'PARA2': _REWRITE.format(extra=', using a different structure (numbered steps if the original is a paragraph, a paragraph if it is a list)', rule=_KEEP),
    'ERRO': _REWRITE.format(extra=', but introduce exactly one decisive technical error that would make the solution fail (for example a wrong '
                                  'command, package name, file path, option or order of steps)',
                            rule='Keep everything else correct and do not mention or hint at the error.')}
REVIEW_HEAD = ('CONTROL PAIRS FOR REVIEW. These pairs will later be mixed, without labels, into the items of a blind judge, to check it. '
               'For each pair answer APPROVED or REJECTED.\n'
               '- Type ERROR: Version 1 should be a correct answer, equivalent in substance to the reference; Version 2 should contain at '
               'least one decisive technical error that would make the solution fail. APPROVE only if both hold.\n'
               '- Type EQUIVALENT: both versions should be correct and equivalent in substance to the reference (same steps; wording and '
               'structure may differ), so that a careful judge should call them a TIE. APPROVE only if this holds.\n'
               'Reply as JSON, for example {"C001": "APPROVED", "C002": "REJECTED"}.\n')

AMOSTRA, TEXTOS, REC = 'r9_amostra.json', 'gc_data/r9_textos.json.gz', 'gc_cache/r9_rec.json'
PILOTO_TXT, PILOTO_JSON = 'r9_piloto.txt', 'r9_piloto.json'
ITEMS, KEY, OUT = 'r9_itens.txt', 'r9_chave_NAO_ENVIAR.json', 'r9_resultado.json'
REVIEW, APPROVED = 'r9_controles_revisao.txt', 'r9_controles_aprovados.json'
K4_EXT = 'r9_k4_erros.json'   # desvio 1 (29/09/2026): erros do K4 inseridos por um agente separado; chave = id da pergunta no Stack Exchange

def file_sha(path): return hashlib.sha256(open(path, 'rb').read()).hexdigest()
def words(t, k): return ' '.join((t or '').split()[:k])
def html_text(body, k):                       # HTML do Posts.xml, sem passar para minúsculas
    body = G.PRE.sub(lambda m: G.short(m.group(1)), body or '')
    return words(html.unescape(G.TAG.sub(' ', body)), k)
def ci(x): return G.ci(list(x))

# ---------------------------------------------------------------- dados da confirmação
def rebuild(embed):
    qpath, lpath, mpath = 'gc_data/au24_perguntas.jsonl.gz', 'gc_data/au24_duplicatas.tsv', 'gc_data/au24_meta.json'
    for p in (qpath, lpath, mpath, 'gc_conf_result.json'):
        if not os.path.exists(p): sys.exit(f'Falta {p}. Rode na mesma pasta do gc_conf.py, depois da confirmação.')
    meta = json.load(open(mpath)); res = json.load(open('gc_conf_result.json'))
    if meta.get('preproc') != G.PREPROC or meta.get('T0') != G.T0: sys.exit('Os dados lidos não correspondem a este gc_conf.py.')
    ids, dates, texts = [], [], []
    for line in gzip.open(qpath, 'rt', encoding='utf-8'): i, d, t = json.loads(line); ids.append(i); dates.append(d); texts.append(t)
    data_sha = G.sha(f'{i}|{d}|{t}' for i, d, t in zip(ids, dates, texts))
    if data_sha != res['reproducao']['dados_sha256']: sys.exit('Os dados não são os mesmos da confirmação (SHA-256 diferente).')
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
    g = random.Random(2025)                   # perguntas já mostradas a juízes em etapas anteriores: excluídas
    JL = g.sample(lab, min(G.N_JL, len(lab))); JU = g.sample(unl, min(G.N_JU, len(unl)))
    POS = g.sample([i for i in lab if i not in set(JL)], G.N_CTRL); NEG = g.sample([i for i in unl if i not in set(JU)], G.N_CTRL)
    excluded = set(JL) | set(JU) | set(POS) | set(NEG)
    tag = embed.replace(':', '_').replace('/', '_'); qrows = sorted(set(lab) | set(unl)); qidx = {i: j for j, i in enumerate(qrows)}
    pre_q, pre_d = ('search_query: ', 'search_document: ') if 'nomic' in embed else ('', '')
    emb_meta = {}
    for name, rows_, pre in (('q', qrows, pre_q), ('d', range(n), pre_d)):
        path = f'gc_cache/au24_{name}_{tag}.npy'
        if not os.path.exists(path + '.meta.json'): sys.exit(f'Faltam os embeddings {path}.')
        mm = json.load(open(path + '.meta.json'))
        if mm['linhas'] != len(rows_) or mm['textos_sha256'] != G.sha(pre + texts[i] for i in rows_) or int(open(path + '.done').read()) != len(rows_):
            sys.exit(f'Os embeddings {path} não correspondem aos dados da confirmação.')
        emb_meta[name] = mm
    rec_key = G.sha([VERSAO, data_sha, json.dumps(emb_meta, sort_keys=True), G.BETA])[:16]
    rec = None
    if os.path.exists(REC):
        c = json.load(open(REC))
        if c.get('chave') == rec_key: rec = {int(k): v for k, v in c['rec'].items()}
    if rec is None:
        print('  recalculando as sugestões de M0 e H (alguns minutos)', flush=True)
        Q = np.asarray(np.load(f'gc_cache/au24_q_{tag}.npy', mmap_mode='r'), dtype=np.float32)
        D = np.asarray(np.load(f'gc_cache/au24_d_{tag}.npy', mmap_mode='r'), dtype=np.float32)
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
                r = {'M0': G.top5(s), 'M2': G.top5(m1 + G.BETA * logdeg)}; r['H'] = G.inter(r['M0'], r['M2'])
                g_ = earlier(i)
                if g_:
                    fs = set(g_)
                    for x in g_: fs |= set(A.indices[A.indptr[x]:A.indptr[x + 1]].tolist())
                    r['fam'] = sorted(fs)
                rec[i] = {k: v for k, v in r.items() if k != 'M2'}
            if (b0 // 128) % 20 == 0: print(f'  {min(b0 + 128, len(rows_eval))}/{len(rows_eval)}', flush=True)
        json.dump({'chave': rec_key, 'rec': rec}, open(REC, 'w'))
    return dict(ids=ids, dates=dates, texts=texts, pos=pos, n=n, e0=e0, N=N, lab=lab, unl=unl, excluded=excluded,
                rec=rec, data_sha=data_sha, res=res, emb_meta=emb_meta)

def find_xml(names):
    found = {}
    for d, _, fs in os.walk(G.XDIR) if os.path.isdir(G.XDIR) else []:
        for f in fs:
            if f in names: found[f] = os.path.join(d, f)
    missing = [f for f in names if f not in found]
    if missing:
        if not os.path.exists(G.DUMP): sys.exit(f'Falta {missing} em {G.XDIR} e não achei {G.DUMP} nesta pasta para extrair.')
        print(f'  extraindo {missing} de {G.DUMP}', flush=True)
        binary = next((shutil.which(b) for b in ('7zz', '7z', '7za') if shutil.which(b)), None)
        manual = f'Alternativa manual: abra {G.DUMP} com o Keka ou The Unarchiver e coloque {missing} na pasta {G.XDIR}/.'
        try:
            if binary: subprocess.run([binary, 'x', G.DUMP, f'-o{G.XDIR}', *missing, '-y'], check=True, stdout=subprocess.DEVNULL)
            else:
                try: import py7zr
                except ImportError: sys.exit('Falta o py7zr. Rode: pip install py7zr   (' + manual + ')')
                with py7zr.SevenZipFile(G.DUMP, 'r') as z: z.extract(path=G.XDIR, targets=[nm for nm in z.getnames() if os.path.basename(nm) in missing])
        except SystemExit: raise
        except Exception as e: sys.exit(f'Não consegui extrair ({e}). ' + manual)
        for d, _, fs in os.walk(G.XDIR):
            for f in fs:
                if f in names: found[f] = os.path.join(d, f)
        if any(f not in found for f in names): sys.exit(f'O arquivo {G.DUMP} não tem {[f for f in names if f not in found]}.')
    return found

# ---------------------------------------------------------------- passo 1: preparar
def preparar(a):
    S = rebuild(a.embed); ids, texts, rec, T0 = S['ids'], S['texts'], S['rec'], G.T0
    found = find_xml(('Posts.xml', 'PostHistory.xml', 'Votes.xml'))
    if len(found) < 3: sys.exit(f'Não achei Posts.xml, PostHistory.xml e Votes.xml em {G.XDIR}.')
    U = S['lab'] + S['unl']; Uid = {ids[i]: i for i in U}; dates = S['dates']
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
        for aid, sc, txt in wans.get(q, ()):
            if aid == acc.get(q) and len(txt.split()) >= 3: return txt
        return None
    # ---- estratos
    lab_set = set(S['lab'])
    def status(i):
        r = rec[i]; ok = ref_text(ids[i]) is not None
        diff = set(r['H']) != set(r['M0'])
        if 'fam' in r:
            fh, fm = bool(set(r['H']) & set(r['fam'])), bool(set(r['M0']) & set(r['fam']))
            kind = 'E1' if fh and not fm else ('E3' if fm and not fh else 'marcada_mesma_familia')
        else: kind = 'E2'
        return ok, diff, kind
    st = {i: status(i) for i in U}
    cnt = collections.Counter()
    for i in U:
        ok, diff, kind = st[i]; grp = 'marcada' if i in lab_set else 'sem_marcacao'
        cnt[(grp, 'total')] += 1; cnt[(grp, 'com_resposta_aceita')] += ok
        if ok: cnt[(grp, kind if diff else 'top5_iguais')] += 1
    pool = lambda kind: sorted(i for i in U if i not in S['excluded'] and st[i][0] and st[i][1] and st[i][2] == kind)
    E1, E2, E3 = pool('E1'), pool('E2'), pool('E3')
    r = random.Random(SEED_SAMPLE)
    E1s = sorted(r.sample(E1, min(N_E1, len(E1)))); E2s = sorted(r.sample(E2, min(N_E2, len(E2)))); E3s = sorted(r.sample(E3, min(N_E3, len(E3))))
    C0s = sorted(r.sample(E1s, min(N_C0_E1, len(E1s)))) + sorted(r.sample(E2s, min(N_C0_E2, len(E2s))))
    used = set(E1s) | set(E2s) | set(E3s)
    rest = [i for i in U if i not in S['excluded'] and i not in used and st[i][0]]
    pil_pool = [i for i in rest if st[i][1]]
    pilot = sorted(random.Random(SEED_PILOT).sample(pil_pool, min(N_PILOT, len(pil_pool))))
    rest = [i for i in rest if i not in set(pilot)]
    K3 = sorted(random.Random(SEED_K3).sample(rest, min(N_K3, len(rest))))
    rest = [i for i in rest if i not in set(K3)]
    k1_cand = [i for i in rest if any(aid != acc.get(ids[i]) and sc > 0 and len(txt.split()) >= 3 for aid, sc, txt in wans.get(ids[i], ()))]
    rk = random.Random(SEED_K1); K1q = sorted(rk.sample(k1_cand, min(N_K1, len(k1_cand)))); K1 = []
    for i in K1q:
        good = max((x for x in wans[ids[i]] if x[0] != acc.get(ids[i]) and x[1] > 0 and len(x[2].split()) >= 3), key=lambda x: (x[1], -x[0]))
        j = rk.choice([x for x in rest if x != i]); K1.append({'i': i, 'bom': good[2], 'ruim': ref_text(ids[j]), 'j': j})
    # ---- resposta de cada discussão, como estava quando a pergunta nova foi publicada
    Qs = E1s + E2s + E3s + pilot
    pairs = sorted({(i, d) for i in Qs for m in ('M0', 'H') for d in rec[i][m]})
    need = sorted({d for _, d in pairs})
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
    print(f'3. texto dessas respostas na data de cada pergunta (PostHistory.xml, 10 a 30 minutos)', flush=True)
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
    with_ans = lambda m, G_: round(float(np.mean([sum(doca[f'{i}|{d}']['a'] is not None for d in rec[i][m]) for i in G_])), 3) if G_ else None
    ctx_balance = {s_: {'CM0': with_ans('M0', G_), 'CH': with_ans('H', G_)} for s_, G_ in (('E1', E1s), ('E2', E2s), ('E3', E3s))}
    T = {'docq': {str(d): words(texts[d], DOCQ_WORDS) for d in need}, 'doca': doca,
         'q': {str(i): words(texts[i], Q_WORDS) for i in Qs + K3 + K1q},
         'ref': {str(i): ref_text(ids[i]) for i in Qs + K3 + K1q}, 'k1': K1}
    with gzip.open(TEXTOS, 'wt', encoding='utf-8') as f: json.dump(T, f, ensure_ascii=False, sort_keys=True)
    textos_sha = file_sha(TEXTOS)
    amostra = {'versao': VERSAO, 'dados_sha256': S['data_sha'], 'textos_sha256': textos_sha,
               'universo': {f'{g}.{k}': v for (g, k), v in sorted(cnt.items())},
               'disponiveis_apos_exclusoes': {'E1': len(E1), 'E2': len(E2), 'E3': len(E3)},
               'amostra': {'E1': len(E1s), 'E2': len(E2s), 'E3': len(E3s), 'C0': len(C0s), 'piloto': len(pilot), 'K1': len(K1), 'K3': len(K3)},
               'P1_com_poder': len(E1s) >= E1_MIN,
               'regra_da_resposta_nas_discussoes': dict(collections.Counter(rule.values())),
               'discussoes_com_resposta_por_contexto (media de 5)': ctx_balance,
               'perguntas_excluidas_por_ja_terem_sido_mostradas': len(S['excluded']),
               'escala_sem_marcacao': (S['N'] - len(S['lab'])) / max(len(S['unl']), 1),
               'ids': {'E1': [ids[i] for i in E1s], 'E2': [ids[i] for i in E2s], 'E3': [ids[i] for i in E3s], 'C0': [ids[i] for i in C0s],
                       'piloto': [ids[i] for i in pilot], 'K3': [ids[i] for i in K3], 'K1': [[ids[k['i']], ids[k['j']]] for k in K1]},
               '_idx': {'E1': E1s, 'E2': E2s, 'E3': E3s, 'C0': C0s, 'piloto': pilot, 'K3': K3}}
    json.dump(amostra, open(AMOSTRA, 'w'), ensure_ascii=False, indent=1)
    show = {k: v for k, v in amostra.items() if k not in ('ids', '_idx')}
    print(json.dumps(show, ensure_ascii=False, indent=1))
    if not amostra['P1_com_poder']: print(f'\nATENÇÃO: E1 tem só {len(E1s)} perguntas (mínimo {E1_MIN}); P1 fica sem poder estatístico.')
    print(f'\nPronto. Envie {AMOSTRA} (só contagens e números de pergunta). Depois rode o piloto.')

# ---------------------------------------------------------------- geração
def load_state(a, need_model=True):
    for p in (AMOSTRA, TEXTOS):
        if not os.path.exists(p): sys.exit(f'Falta {p}. Rode primeiro: python3 gc_r9.py preparar')
    am = json.load(open(AMOSTRA))
    if file_sha(TEXTOS) != am['textos_sha256']: sys.exit(f'{TEXTOS} mudou desde o preparar. Rode o preparar de novo.')
    T = json.load(gzip.open(TEXTOS, 'rt', encoding='utf-8'))
    rec = {int(k): v for k, v in json.load(open(REC))['rec'].items()}
    return am, T, rec

class Gen:
    def __init__(self, a, am):
        self.host, self.model = a.host, a.modelo
        self.digest, self.ollama_version = G.ollama(a.host, a.modelo)
        self.fp = G.sha([VERSAO, VERSAO_ANALISE, a.modelo, self.digest, GEN_PROMPT, CTX_HEAD, DOC_FMT, json.dumps(CTRL_PROMPTS, sort_keys=True),
                         NUM_PREDICT, GEN_SEED, am['dados_sha256'], am['textos_sha256']])[:16]
        self.path = f'gc_cache/r9_geracoes_{self.fp}.jsonl'; self.cache = {}
        if os.path.exists(self.path):
            for line in open(self.path, encoding='utf-8'):
                try: d = json.loads(line); self.cache[(d['c'], d['i'])] = d
                except Exception: pass
        self.f = open(self.path, 'a', encoding='utf-8'); self.think = True; self.empty = 0
    def __call__(self, cond, i, prompt):
        if (cond, i) in self.cache: return self.cache[(cond, i)]['t']
        payload = {'model': self.model, 'stream': False, 'prompt': prompt,
                   'options': {'temperature': 0, 'num_predict': NUM_PREDICT, 'seed': GEN_SEED}}
        if self.think: payload['think'] = False
        t0 = time.time()
        try:
            try: r = G.post(self.host, '/api/generate', payload, timeout=900)
            except urllib.error.HTTPError:
                if not self.think: raise
                self.think = False; payload.pop('think'); r = G.post(self.host, '/api/generate', payload, timeout=900)
        except urllib.error.URLError as e:
            sys.exit(f'O Ollama não respondeu ({e}). Abra o Ollama e rode o mesmo comando: o que já foi gerado fica salvo.')
        txt = (r.get('response') or '').strip(); self.empty += not txt
        d = {'c': cond, 'i': i, 't': txt, 's': round(time.time() - t0, 2)}
        self.cache[(cond, i)] = d; self.f.write(json.dumps(d, ensure_ascii=False) + '\n'); self.f.flush()
        return txt

def prompt_for(cond, i, T, rec):
    q = T['q'][str(i)]
    if cond in CTRL_PROMPTS: return CTRL_PROMPTS[cond].format(q=q, ref=T['ref'][str(i)])
    if cond == 'C0': ctx = ''
    elif cond == 'ORACLE': ctx = CTX_HEAD + DOC_FMT.format(k=1, q=q, a=T['ref'][str(i)]) + '\n\n'
    else:
        docs = rec[i]['H' if cond == 'CH' else 'M0']
        ctx = CTX_HEAD + '\n\n'.join(DOC_FMT.format(k=k, q=T['docq'][str(d)], a=T['doca'][f'{i}|{d}']['a'] or '(no answer)')
                                     for k, d in enumerate(docs, 1)) + '\n\n'
    return GEN_PROMPT.format(context=ctx, question=q)

def ctrl_questions(am, T):
    K4q = sorted(k['i'] for k in T['k1'])[:N_K4]
    K3 = sorted(am['_idx']['K3']); K5q = sorted(random.Random(SEED_K5).sample(K3, min(N_K5, len(K3))))
    return K4q, K5q

def jobs(am, T):
    ix = am['_idx']; out = []
    for s in ('E1', 'E2', 'E3'): out += [(c, i) for i in ix[s] for c in ('CH', 'CM0')]
    out += [('C0', i) for i in ix['C0']] + [(c, i) for i in ix['K3'] for c in ('ORACLE', 'C0')]
    K4q, K5q = ctrl_questions(am, T)
    out += [(c, i) for i in K4q for c in ('PARA1', 'ERRO')] + [(c, i) for i in K5q for c in ('PARA1', 'PARA2')]
    return list(dict.fromkeys(out))

def k4_external(am, T):
    if not os.path.exists(K4_EXT): return None
    K4q, _ = ctrl_questions(am, T); pid = {k['i']: str(am['ids']['K1'][n][0]) for n, k in enumerate(T['k1'])}
    raw = json.load(open(K4_EXT, encoding='utf-8')); extra = set(raw) - {pid[i] for i in K4q}
    if extra: sys.exit(f'{K4_EXT} tem perguntas fora do K4: {sorted(extra)[:5]}')
    return {i: words(raw[pid[i]], CAND_WORDS) for i in K4q if pid[i] in raw}

def ctrl_pairs(am, T, g):
    norm = lambda t: ' '.join(t.split()).lower(); K4q, K5q = ctrl_questions(am, T); out = []; ext = k4_external(am, T)
    ok = lambda t1, t2: t1.strip() and t2.strip() and norm(t1) != norm(t2)
    for n, i in enumerate(K4q, 1):                  # numeração fixa por pergunta (igual à da primeira revisão)
        t1 = words(g.cache[('PARA1', i)]['t'], CAND_WORDS)
        if ext is None: c2, t2 = 'ERRO', words(g.cache[('ERRO', i)]['t'], CAND_WORDS)
        elif i in ext: c2, t2 = 'ERRO_EXTERNO', ext[i]
        else: continue
        if ok(t1, t2): out.append({'tipo': 'K4', 'rotulo': 'ERROR', 'i': i, 'c1': 'PARA1', 'c2': c2, 't1': t1, 't2': t2, 'id': f'C{n:03d}'})
    for n, i in enumerate(K5q, len(K4q) + 1):
        t1, t2 = words(g.cache[('PARA1', i)]['t'], CAND_WORDS), words(g.cache[('PARA2', i)]['t'], CAND_WORDS)
        if ok(t1, t2): out.append({'tipo': 'K5', 'rotulo': 'EQUIVALENT', 'i': i, 'c1': 'PARA1', 'c2': 'PARA2', 't1': t1, 't2': t2, 'id': f'C{n:03d}'})
    return out

def review_text(pairs, T):
    return REVIEW_HEAD + ''.join(f'\n#{p["id"]}  TYPE: {p["rotulo"]}\nQUESTION: {T["q"][str(p["i"])]}\nREFERENCE (accepted by the asker): {T["ref"][str(p["i"])]}\n'
                                 f'VERSION 1: {p["t1"]}\nVERSION 2: {p["t2"]}\n' for p in pairs)

def piloto(a):
    am, T, rec = load_state(a); g = Gen(a, am); pil = am['_idx']['piloto']; secs = []; out = []
    print(f'Piloto: {len(pil)} perguntas x 3 condições (não entra na análise)', flush=True)
    for k, i in enumerate(pil, 1):
        row = {'pergunta': T['q'][str(i)], 'referencia': T['ref'][str(i)], 'respostas': {}}
        for c in ('CH', 'CM0', 'C0'):
            new = (c, i) not in g.cache; txt = g(c, i, prompt_for(c, i, T, rec))
            if new: secs.append(g.cache[(c, i)]['s'])
            row['respostas'][c] = txt
        row['prompt_CH'] = prompt_for('CH', i, T, rec); out.append(row)
        print(f'  {k}/{len(pil)}', flush=True)
    with open(PILOTO_TXT, 'w', encoding='utf-8') as f:
        for k, row in enumerate(out, 1):
            f.write(f'==================== PILOTO {k}\n--- PROMPT (condição CH)\n{row["prompt_CH"]}\n--- REFERÊNCIA\n{row["referencia"]}\n')
            for c, t in row['respostas'].items(): f.write(f'--- RESPOSTA {c} ({len(t.split())} palavras)\n{t}\n')
            f.write('\n')
    per = float(np.mean(secs)) if secs else float(np.mean([g.cache[(c, i)]['s'] for i in pil for c in ('CH', 'CM0', 'C0')]))
    total = len(jobs(am, T))
    info = {'segundos_por_resposta': round(per, 1), 'respostas_na_rodada_completa': total,
            'horas_estimadas': round(per * total / 3600, 1), 'respostas_vazias': sum(1 for i in pil for c in ('CH', 'CM0', 'C0') if not g.cache[(c, i)]['t']),
            'palavras_medias': {c: round(float(np.mean([len(g.cache[(c, i)]['t'].split()) for i in pil])), 1) for c in ('CH', 'CM0', 'C0')},
            'modelo': a.modelo, 'digest': g.digest, 'ollama': g.ollama_version, 'think_desligado_aceito': g.think}
    json.dump(info, open(PILOTO_JSON, 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(info, ensure_ascii=False, indent=1)); print(f'\nPronto. Envie {PILOTO_TXT} e {PILOTO_JSON}.')

def gerar(a):
    if not a.pre_registro_congelado: sys.exit('Só rode a geração completa depois que o pré-registro estiver congelado no protocolo. Aí use --pre-registro-congelado.')
    am, T, rec = load_state(a); g = Gen(a, am); todo = jobs(am, T); left = [(c, i) for c, i in todo if (c, i) not in g.cache]
    print(f'Gerando {len(left)} de {len(todo)} respostas (as outras já estão salvas)', flush=True); t0 = time.time()
    for k, (c, i) in enumerate(left, 1):
        g(c, i, prompt_for(c, i, T, rec))
        if k % 20 == 0 or k == len(left):
            rate = k / max(time.time() - t0, 1e-9); print(f'  {k}/{len(left)}  (~{(len(left) - k) / rate / 60:.0f} min restantes)', flush=True)
    print(json.dumps({'respostas': len(todo), 'vazias': sum(1 for x in todo if not g.cache[x]['t']), 'cache': os.path.basename(g.path)}, ensure_ascii=False))
    print('\nPronto. Agora rode: python3 gc_r9.py controles')

def controles(a):
    am, T, rec = load_state(a); g = Gen(a, am)
    miss = [x for x in jobs(am, T) if x not in g.cache]
    if miss: sys.exit(f'Faltam {len(miss)} respostas. Rode: python3 gc_r9.py gerar --modelo {a.modelo} --pre-registro-congelado')
    pairs = ctrl_pairs(am, T, g)
    open(REVIEW, 'w', encoding='utf-8').write(review_text(pairs, T))
    print(json.dumps({'pares_para_revisao': dict(collections.Counter(p['rotulo'] for p in pairs)), 'arquivo_sha256': file_sha(REVIEW)}, ensure_ascii=False, indent=1))
    print(f'\nEnvie {REVIEW} ao Claude para a revisão prévia (pode mandar também ao Astra). Salve a resposta como {APPROVED} e rode: python3 gc_r9.py itens')

# ---------------------------------------------------------------- itens cegos e comparação
def itens(a):
    if os.path.exists(KEY) and not a.refazer: sys.exit(f'{KEY} já existe. Para gerar de novo (invalida rótulos anteriores), use --refazer.')
    am, T, rec = load_state(a); g = Gen(a, am); ix = am['_idx']
    miss = [x for x in jobs(am, T) if x not in g.cache]
    if miss: sys.exit(f'Faltam {len(miss)} respostas. Rode: python3 gc_r9.py gerar --modelo {a.modelo} --pre-registro-congelado')
    pairs = ctrl_pairs(am, T, g)
    if not os.path.exists(REVIEW) or open(REVIEW, encoding='utf-8').read() != review_text(pairs, T): sys.exit(f'Rode primeiro: python3 gc_r9.py controles')
    if not os.path.exists(APPROVED): sys.exit(f'Falta {APPROVED} (a revisão prévia dos pares de controle).')
    raw = json.load(open(APPROVED)); raw = raw.get('aprovacoes', raw) if isinstance(raw, dict) else raw
    ok = {str(k).lstrip('#'): str(v).strip().upper() in ('APPROVED', 'APROVADO', 'SIM', 'YES', 'TRUE') for k, v in raw.items()}
    missing = [p['id'] for p in pairs if p['id'] not in ok]
    if missing: sys.exit(f'{APPROVED} não tem decisão para {len(missing)} pares (ex.: {missing[:5]}).')
    ans = lambda c, i: words(g.cache[(c, i)]['t'], CAND_WORDS)
    base = []
    nans = lambda m, i: sum(T['doca'][f'{i}|{d}']['a'] is not None for d in rec[i][m])
    for s in ('E1', 'E2', 'E3'): base += [{'tipo': 'principal', 'estrato': s, 'i': i, 'c1': 'CH', 'c2': 'CM0', 'rCH': nans('H', i), 'rCM0': nans('M0', i)} for i in ix[s]]
    e1set = set(ix['E1'])
    for i in ix['C0']:
        s = 'E1' if i in e1set else 'E2'
        base += [{'tipo': 'c0', 'estrato': s, 'i': i, 'c1': 'CH', 'c2': 'C0'}, {'tipo': 'c0', 'estrato': s, 'i': i, 'c1': 'CM0', 'c2': 'C0'}]
    base += [{'tipo': 'K3', 'i': i, 'c1': 'ORACLE', 'c2': 'C0', 'certo': 'ORACLE'} for i in ix['K3']]
    for it in base: it['t1'], it['t2'] = ans(it['c1'], it['i']), ans(it['c2'], it['i'])
    for k in T['k1']: base.append({'tipo': 'K1', 'i': k['i'], 'c1': 'MESMA_PERGUNTA', 'c2': 'OUTRA_PERGUNTA', 'certo': 'MESMA_PERGUNTA', 't1': k['bom'], 't2': k['ruim']})
    norm = lambda t: ' '.join(t.split()).lower()
    auto = [it for it in base if norm(it['t1']) == norm(it['t2'])]; sent = [it for it in base if norm(it['t1']) != norm(it['t2'])]
    for p in pairs:
        if ok[p['id']]: sent.append({'tipo': p['tipo'], 'i': p['i'], 'c1': p['c1'], 'c2': p['c2'], 't1': p['t1'], 't2': p['t2'], 'certo': 'PARA1' if p['tipo'] == 'K4' else None})
    ctrl_info = {'pares_revisados': dict(collections.Counter(p['tipo'] for p in pairs)),
                 'pares_aprovados': dict(collections.Counter(p['tipo'] for p in pairs if ok[p['id']])),
                 'revisao_sha256': file_sha(REVIEW), 'aprovacoes_sha256': file_sha(APPROVED),
                 'erros_do_K4': ('externos, desvio 1: ' + file_sha(K4_EXT)) if os.path.exists(K4_EXT) else 'gemma'}
    r = random.Random(SEED_ITEMS)
    k2src = r.sample([it for it in sent if it['tipo'] == 'principal'], min(N_K2, sum(it['tipo'] == 'principal' for it in sent)))
    for it in sent: it['A'] = r.choice(('c1', 'c2'))
    for o in k2src: sent.append({**{k: v for k, v in o.items() if k != 'A'}, 'tipo': 'K2', 'origem': id(o), 'A': 'c2' if o['A'] == 'c1' else 'c1'})
    for it in sent: it['_id'] = id(it)
    r.shuffle(sent)
    num = {it['_id']: n for n, it in enumerate(sent, 1)}
    with open(ITEMS, 'w', encoding='utf-8') as f:
        f.write('ROUND 9: BLIND ITEMS\n' + RUBRIC + '\n')
        for n, it in enumerate(sent, 1):
            A, B = (it['t1'], it['t2']) if it['A'] == 'c1' else (it['t2'], it['t1'])
            f.write(f'\n#{n}\nQUESTION: {T["q"][str(it["i"])]}\nREFERENCE (accepted by the asker): {T["ref"][str(it["i"])]}\nANSWER A: {A}\nANSWER B: {B}\n')
    rows = []
    for it in sent:
        cA, cB = (it['c1'], it['c2']) if it['A'] == 'c1' else (it['c2'], it['c1'])
        rows.append({'n': num[it['_id']], 'tipo': it['tipo'], 'estrato': it.get('estrato'), 'i': it['i'], 'A': cA, 'B': cB, 'certo': it.get('certo'),
                     'origem': num.get(it.get('origem')), 'rCH': it.get('rCH'), 'rCM0': it.get('rCM0')})
    lens = {c: round(float(np.mean([len(g.cache[(c, i)]['t'].split()) for (cc, i) in jobs(am, T) if cc == c])), 1) for c in ('CH', 'CM0', 'C0', 'ORACLE')}
    key = {'versao': VERSAO_ANALISE, 'controles': ctrl_info, 'itens_sha256': file_sha(ITEMS), 'rubrica': RUBRIC, 'amostra_textos_sha256': am['textos_sha256'],
           'geracoes_cache': os.path.basename(g.path), 'modelo': a.modelo, 'digest': g.digest, 'ollama': g.ollama_version,
           'itens': sorted(rows, key=lambda x: x['n']),
           'empates_automaticos': [{'tipo': it['tipo'], 'estrato': it.get('estrato'), 'i': it['i'], 'c1': it['c1'], 'c2': it['c2'], 'rCH': it.get('rCH'), 'rCM0': it.get('rCM0')} for it in auto],
           'script_sha256': file_sha(os.path.abspath(__file__)),
           'palavras_medias': lens, 'universo': am['universo'], 'escala_sem_marcacao': am['escala_sem_marcacao'], 'P1_com_poder': am['P1_com_poder']}
    json.dump(key, open(KEY, 'w'), ensure_ascii=False)
    print(json.dumps({'itens': len(sent), 'empates_automaticos (respostas idênticas, não enviados)': len(auto), 'controles': ctrl_info,
                      'por_tipo': dict(collections.Counter(it['tipo'] for it in sent)), 'itens_sha256': key['itens_sha256']}, ensure_ascii=False, indent=1))
    print(f'\nEnvie SÓ o arquivo {ITEMS} ao Claude. NÃO envie {KEY}.')

def parse_labels(path, n):
    raw = json.load(open(path)); raw = raw.get('rotulos', raw) if isinstance(raw, dict) else raw
    if isinstance(raw, list): raw = {str(k): v for k, v in enumerate(raw, 1)}
    norm = {'A': 'A', 'B': 'B', 'TIE': 'TIE', 'EMPATE': 'TIE', 'E': 'TIE'}
    lab = {int(k): norm.get(str(v).strip().upper()) for k, v in raw.items()}
    missing = [k for k in range(1, n + 1) if lab.get(k) is None]
    if missing: sys.exit(f'Faltam rótulos válidos (A, B ou TIE) para {len(missing)} itens (ex.: {missing[:10]}).')
    return lab

def comparar(a):
    if not os.path.exists(KEY): sys.exit(f'Falta {KEY}. Rode primeiro: python3 gc_r9.py itens')
    key = json.load(open(KEY))
    if file_sha(ITEMS) != key['itens_sha256']: sys.exit(f'{ITEMS} foi alterado ou gerado de novo; os rótulos não correspondem.')
    its = key['itens']; lab = parse_labels(a.rotulos, len(its))
    for it in its: it['vence'] = None if lab[it['n']] == 'TIE' else it[lab[it['n']]]
    acc = lambda t: [it['vence'] == it['certo'] for it in its if it['tipo'] == t]
    by_n = {it['n']: it for it in its}
    k2 = [it['vence'] == by_n[it['origem']]['vence'] for it in its if it['tipo'] == 'K2']
    k5 = [it['vence'] is None for it in its if it['tipo'] == 'K5']
    mean = lambda x: round(float(np.mean(x)), 3) if x else None
    K = {'K1_discriminacao_facil': {'n': len(acc('K1')), 'acerto': mean(acc('K1')), 'minimo': K1_MIN},
         'K2_ordem': {'n': len(k2), 'consistencia': mean(k2), 'minimo': K2_MIN},
         'K4_erro_decisivo': {'n': len(acc('K4')), 'acerto': mean(acc('K4')), 'minimo': K4_MIN, 'minimo_de_pares': K4_MIN_APROV},
         'K5_equivalentes': {'n': len(k5), 'empates': mean(k5), 'minimo': K5_MIN_TIE, 'minimo_de_pares': K5_MIN_APROV}}
    valid = (all(v[m] is not None and v[m] >= v['minimo'] for v, m in ((K['K1_discriminacao_facil'], 'acerto'), (K['K2_ordem'], 'consistencia'),
                                                                     (K['K4_erro_decisivo'], 'acerto'), (K['K5_equivalentes'], 'empates')))
             and len(acc('K4')) >= K4_MIN_APROV and len(k5) >= K5_MIN_APROV)
    k3 = [it['vence'] for it in its if it['tipo'] == 'K3']
    K3diag = {'n': len(k3), 'prefere_oraculo': mean([v == 'ORACLE' for v in k3]), 'prefere_C0': mean([v == 'C0' for v in k3]),
              'empates': mean([v is None for v in k3]), 'nota': 'diagnostico do beneficio de dar a referencia ao gerador; nao reprova o juiz'}
    def scores(tipo, c1, c2, estrato):
        s = [(+1 if it['vence'] == c1 else (-1 if it['vence'] == c2 else 0)) for it in its
             if it['tipo'] == tipo and it['estrato'] == estrato and {it['A'], it['B']} == {c1, c2}]
        s += [0 for x in key['empates_automaticos'] if x['tipo'] == tipo and x['estrato'] == estrato and {x['c1'], x['c2']} == {c1, c2}]
        return np.array(s, dtype=float)
    rng = np.random.default_rng(9)
    def delta(x):
        if not len(x): return {'n': 0, 'delta': None, 'ic95': None}
        boots = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(NBOOT)]
        return {'n': int(len(x)), 'delta': round(float(x.mean()), 4), 'ic95': ci(boots),
                'prefere_primeira': int((x > 0).sum()), 'prefere_segunda': int((x < 0).sum()), 'empates': int((x == 0).sum())}
    D = {s: scores('principal', 'CH', 'CM0', s) for s in ('E1', 'E2', 'E3')}
    def bal(s):                                 # desequilíbrio: nº de discussões com resposta em CH menos em CM0
        rows = [((+1 if it['vence'] == 'CH' else (-1 if it['vence'] == 'CM0' else 0)), it['rCH'] - it['rCM0']) for it in its if it['tipo'] == 'principal' and it['estrato'] == s]
        rows += [(0, x['rCH'] - x['rCM0']) for x in key['empates_automaticos'] if x['tipo'] == 'principal' and x['estrato'] == s]
        pick = lambda f: np.array([v for v, dd in rows if f(dd)], dtype=float)
        return {'mesmo_numero': delta(pick(lambda dd: dd == 0)), 'CH_com_mais': delta(pick(lambda dd: dd > 0)), 'CM0_com_mais': delta(pick(lambda dd: dd < 0))}
    R = {s: delta(D[s]) for s in D}
    P1 = (bool(R['E1']['ic95'] and R['E1']['ic95'][0] > 0) if key['P1_com_poder'] else 'sem poder estatistico (E1 pequeno)') if valid else 'inconclusivo (juiz reprovado nos controles)'
    P2 = bool(R['E2']['ic95'] and R['E2']['ic95'][0] > MARGIN_P2) if valid else 'inconclusivo (juiz reprovado nos controles)'
    if not valid: verdict = 'INCONCLUSIVO (juiz reprovado nos controles ou controles insuficientes)'
    elif P2 is not True: verdict = 'Em E2, H pode piorar a resposta (limite inferior abaixo da margem de -0,10)'
    elif P1 is True: verdict = ('H melhora a resposta final no subconjunto em que traz a familia que a busca simples perdeu (E1), sem piora grande '
                                'no restante (E2, margem -0,10). O efeito medio sobre todas as perguntas e exploratorio.')
    else: verdict = 'Melhora em E1 nao demonstrada; sem piora grande em E2 (margem -0,10). O efeito medio e exploratorio.'
    u = key['universo']; sc = key['escala_sem_marcacao']
    w = {'E1': u.get('marcada.E1', 0), 'E3': u.get('marcada.E3', 0), 'E2_marcada': u.get('marcada.marcada_mesma_familia', 0),
         'E2': sc * u.get('sem_marcacao.E2', 0)}
    tot = u.get('marcada.com_resposta_aceita', 0) + sc * u.get('sem_marcacao.com_resposta_aceita', 0)
    def pop(ix=None):
        m = {s: (D[s][ix[s]] if ix else D[s]).mean() if len(D[s]) else 0.0 for s in D}
        return (w['E1'] * m['E1'] + w['E3'] * m['E3'] + (w['E2_marcada'] + w['E2']) * m['E2']) / max(tot, 1e-9)
    pb = [pop({s: rng.integers(0, len(D[s]), len(D[s])) for s in D}) for _ in range(NBOOT)] if all(len(D[s]) for s in D) else []
    wE2 = (w['E2_marcada'] + w['E2']) / max(tot, 1e-9); wE1 = w['E1'] / max(tot, 1e-9)
    eq = round(float(-wE1 * D['E1'].mean() / wE2), 4) if len(D['E1']) and wE2 > 0 else None
    out = {'versao': key['versao'], 'itens': len(its), 'empates_automaticos': len(key['empates_automaticos']),
           'controles_do_juiz': K, 'juiz_valido': valid, 'controles_revisados': key['controles'], 'K3_diagnostico_oraculo': K3diag,
           'CH_menos_CM0_por_estrato': R,
           'criterios': {'P1_E1_IC_inferior_>_0': P1, f'P2_E2_IC_inferior_>_{MARGIN_P2}': P2, 'VEREDITO': verdict},
           'secundarios': {
               'efeito_populacional_estimado_EXPLORATORIO': {'delta': round(float(pop()), 4), 'ic95': ci(pb) if pb else None,
                                                'delta_em_E2_que_anularia_o_ganho_de_E1': eq,
                                                'pesos': {k: round(v / max(tot, 1e-9), 4) for k, v in w.items()},
                                                'nota': 'top-5 iguais contam 0; marcadas sem mudanca de familia recebem o delta de E2'},
               'CH_menos_C0': {s: delta(scores('c0', 'CH', 'C0', s)) for s in ('E1', 'E2')},
               'CM0_menos_C0': {s: delta(scores('c0', 'CM0', 'C0', s)) for s in ('E1', 'E2')},
               'CH_menos_CM0_por_equilibrio_de_discussoes_com_resposta': {s: bal(s) for s in ('E1', 'E2')},
               'palavras_medias_por_condicao': key['palavras_medias'],
               'juiz_escolheu_A_nos_principais': round(float(np.mean([lab[it['n']] == 'A' for it in its if it['tipo'] == 'principal'])), 3),
               'juiz_empates_nos_principais': round(float(np.mean([lab[it['n']] == 'TIE' for it in its if it['tipo'] == 'principal'])), 3)},
           'reproducao': {'itens_sha256': key['itens_sha256'], 'modelo': key['modelo'], 'digest': key['digest'], 'ollama': key['ollama'],
                          'geracoes_cache': key['geracoes_cache'], 'script_sha256': key['script_sha256']}}
    json.dump(out, open(OUT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(json.dumps(out, ensure_ascii=False, indent=1)); print(f'\nPronto. Envie {OUT} (só números agregados). NÃO envie {KEY}.')

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('acao', choices=['preparar', 'piloto', 'gerar', 'controles', 'itens', 'comparar']); ap.add_argument('rotulos', nargs='?')
    ap.add_argument('--embed', default='nomic-embed-text'); ap.add_argument('--modelo', default='gemma4:latest'); ap.add_argument('--host', default='http://localhost:11434')
    ap.add_argument('--pre-registro-congelado', action='store_true'); ap.add_argument('--refazer', action='store_true'); a = ap.parse_args()
    os.makedirs('gc_cache', exist_ok=True)
    if a.acao == 'preparar': preparar(a)
    elif a.acao == 'piloto': piloto(a)
    elif a.acao == 'gerar': gerar(a)
    elif a.acao == 'controles': controles(a)
    elif a.acao == 'itens': itens(a)
    else:
        if not a.rotulos: sys.exit('Informe o arquivo de rótulos: python3 gc_r9.py comparar r9_rotulos.json')
        comparar(a)

if __name__ == '__main__':
    main()
