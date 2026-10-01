# Grande Cérebro — Protocolo do Experimento 1 (continuação)

**Notas de publicação (01/10/2026).**

- Este arquivo é a continuação de [protocolo-original.pt-BR.md](protocolo-original.pt-BR.md), que foi exportado na revisão 75. O texto abaixo foi exportado do mesmo documento vivo na revisão 116, a partir da seção "Versão pública preparada", sem edição de conteúdo.
- Ele cobre a publicação da v0.1.x, as rodadas 9, 10 e 11 (pré-registros, desvios, resultados, erratas e revisões) e o rascunho da rodada 12, ainda não congelado.
- "Astra" é o nome dado às revisões críticas do ChatGPT (OpenAI), repassadas pelo autor.
- Por causa da ordem de inserção no documento vivo, dois blocos do pré-registro da rodada 9 ("Custo estimado da rodada 9" e "Pontos pedidos à revisão da rodada 9") aparecem no fim do arquivo.
- Nenhum trecho de pergunta ou resposta do askubuntu.com ou do superuser.com aparece neste arquivo. Os arquivos que continham esse texto estão listados, com SHA-256, em `results/README.md`.

---

## Versão pública preparada (29/09/2026)

Foi preparado o repositório público "Problem Identity Registry" (v0.1.0), com autoria de Alexandre Cardoso Rego. Contém:

- READMEs em inglês e em português;
- o framework;
- um resumo em inglês de todas as rodadas;
- este protocolo exportado (revisão 75), com notas de publicação;
- o código e os resultados.

**Formulação pública:** a da errata 4. O desenho H é descrito como "M0 em primeiro, alternando com o M2". O M2 inclui o termo de popularidade, que tem dois gumes: prejudica a 1ª sugestão quando usado sozinho e aumenta a recuperação nas posições seguintes. Sem ele (H1), o ganho é de +31%.

**Revisão separada.** Antes da publicação, um agente Claude separado, que não escreveu a documentação, fez duas passadas de conferência. Ele não encontrou números errados, mas apontou problemas de enquadramento, todos corrigidos:

- o H descrito como se não usasse o bônus;
- generalizações sobre o pré-registro;
- o local de execução de cada etapa;
- licenças de trechos de terceiros.

**Texto de terceiros:** os arquivos e campos com trechos de perguntas do askubuntu.com foram retirados da versão pública e substituídos pelos SHA-256 dos originais, para que tudo possa sair sob CC BY 4.0.

**Publicação no GitHub:** https://github.com/alexandre-debug/problem-identity-registry, commit 29e7196, de 29/09/2026 às 11:37 (+02:00). Os 70 arquivos foram conferidos byte a byte contra o pacote preparado. O DOI do Zenodo será registrado aqui quando for gerado.

**DOI no Zenodo (29/09/2026):** a release v0.1.0 foi arquivada com o DOI 10.5281/zenodo.23037100. O DOI que representa todas as versões é 10.5281/zenodo.23037099, usado no selo e na seção "Como citar" do repositório. O arquivamento levou cerca de uma hora; enquanto isso, a importação ficou no estado "Received".

Nesse intervalo foram publicadas duas releases:

- **v0.1.1:** esclarecimentos após a revisão externa (definição de identidade, teto da avaliação, ambiente fixado).
- **Tag v0.1.3:** criada por engano com esse nome; os arquivos dizem 0.1.2. Ela trocou o identificador de licença no `.zenodo.json` de "MIT" para "mit".

A hipótese de que a licença causava o atraso estava errada, pois a v0.1.0 foi arquivada com "MIT". O CHANGELOG do repositório registra essa correção. Na data deste registro, v0.1.1 e v0.1.3 ainda aguardavam processamento no Zenodo.

Depois disso veio a versão 0.1.4, só com informação de citação: selo do DOI, seção "Como citar" e as correções acima no CHANGELOG. Ela foi publicada por engano com a tag v0.1.5 e criada antes de subirem os números de versão. Por isso, os arquivos arquivados com ela dizem 0.1.2 no README, enquanto o `.zenodo.json` diz 0.1.4. O CHANGELOG registra isso. Daqui em diante, cada release sai com a tag exatamente igual à versão do `.zenodo.json`.

## Rodada 9: a discussão recuperada melhora a resposta? (pré-registro congelado em 29/09/2026)

**Situação:** pré-registro congelado em 29/09/2026 às 16h55 (+02:00), depois da revisão do Astra (ver a seção "Revisão do Astra e congelamento" no fim desta rodada). Antes do congelamento rodaram só a preparação e o piloto; nenhuma resposta da amostra foi gerada nem julgada.

**Pergunta.** Um modelo de linguagem responde a uma pergunta nova tendo discussões antigas como contexto. A resposta melhora quando essas discussões vêm do método com relações confirmadas (H) em vez da busca simples (M0)? E ter contexto ajuda em relação a não ter nenhum?

**Por que agora.** A confirmação mediu só a recuperação: se a família marcada aparece entre as cinco sugestões. Esta rodada mede o passo seguinte, que é se isso muda a resposta final. É também o teste mais direto da ideia de usar o registro como contexto para LLMs.

### Dados

- **Base:** a mesma da confirmação. São o dump de 02/04/2024, a mesma SHA-256 dos dados (951a20e2…), os mesmos embeddings em cache, as mesmas sugestões de M0 e H e as mesmas versões de época das perguntas. Acrescentam-se as respostas (Posts.xml, PostTypeId 2), o histórico de edições delas (PostHistory.xml) e o Votes.xml, que diz quando cada resposta foi aceita e quando recebeu votos positivos.
- **Discussão no contexto:** a pergunta da discussão, até 80 palavras e na mesma versão usada na confirmação, mais uma resposta de até 150 palavras, como estava quando a pergunta nova foi publicada. A resposta é a aceita antes dessa data; na falta dela, a mais votada até essa data; se não houver resposta, entra só a pergunta. O texto da resposta é a versão vigente nessa data. Nenhum texto criado ou editado depois da pergunta nova entra no contexto dela.
  - *Mudança em relação ao primeiro rascunho, que cortava tudo em 01/01/2020:* a busca simples (M0) recupera muitas perguntas de 2020 em diante, anteriores à pergunta nova. Com o corte em 2020, elas entrariam sem resposta, e o contexto de M0 ficaria artificialmente mais pobre que o de H. Isso favoreceria H.
- **Referência, que só o juiz vê:** a resposta aceita da própria pergunta nova, na versão atual do dump, até 200 palavras. Só entram perguntas novas com resposta aceita. A resposta da duplicata marcada nunca é usada como referência, porque isso seria circular e favoreceria o método que a recupera.

### Estratos

Os estratos são definidos antes de gerar qualquer resposta, apenas pelo que cada método recupera; nem o modelo nem o juiz veem essa informação. O universo são as perguntas novas avaliadas na confirmação que têm resposta aceita e em que o conjunto top-5 de H é diferente do de M0.

- **E1, a rede traz a família:** entre as 5.982 perguntas com duplicata marcada anterior, aquelas em que a família está no top-5 de H e não no de M0. Até 250 perguntas, ou todas, se houver menos.
- **E2, contextos diferentes sem família nova:** perguntas da amostra de 5.000 sem marcação. São 400 perguntas.
- **E3, a rede perde a família:** família no top-5 de M0 e não no de H. Até 80 perguntas.

O sorteio usa Random(909). Antes de gerar, o script informa os tamanhos disponíveis. Se E1 tiver menos de 80 perguntas, P1 é declarado sem poder estatístico, e isso fica registrado antes da geração.

### Condições e geração

- **CH:** as 5 discussões de H, na ordem de H.
- **CM0:** as 5 discussões de M0, na ordem de M0.
- **C0:** sem contexto, só em uma subamostra de 75 perguntas de E1 e 75 de E2.
- **Modelo gerador:** gemma4 local, com o digest registrado, temperatura 0, até 350 tokens de saída e think desligado. O prompt é o mesmo nas três condições, exceto pelo bloco de contexto, que avisa que as discussões podem ser irrelevantes e só devem ser usadas se se aplicarem. A resposta é pedida em inglês, com passos concretos.
- **Piloto:** 10 perguntas fora da amostra, para medir o tempo e conferir o formato. O piloto não entra em nenhuma análise.

### Julgamento cego

- **Item:** a pergunta (até 150 palavras), a resposta de referência e duas respostas candidatas, A e B, em ordem sorteada.
- **Rubrica, revisada depois do Astra:**
  - A referência foi aceita pelo autor da pergunta. O juiz a usa como evidência, mas considera também os requisitos da pergunta e a validade técnica de cada candidata; uma abordagem diferente pode ser igualmente correta.
  - O juiz escolhe a candidata com mais chance de resolver o problema: A, B ou EMPATE. Tamanho e estilo não contam.
  - O texto exato, em inglês, está nos detalhes de execução.
- **Juiz principal:** subagentes do Claude que recebem só a rubrica e os itens, como no juiz complementar da confirmação. A chave, que diz qual resposta veio de qual condição, fica só no Mac do autor, e um script local compara e devolve apenas agregados.
- **Segundo validador, opcional:** uma subamostra de 100 itens julgada também pelo ChatGPT, com a mesma rubrica.
- **Controles misturados aos itens, sem marcação:**
  - K1, discriminação fácil: A é outra resposta à mesma pergunta, com pontuação positiva e não aceita; B é a resposta aceita de uma pergunta aleatória. O juiz deve escolher A em pelo menos 85% de 60 controles.
  - K2, ordem: 40 itens principais repetidos com A e B trocados. O veredito deve se manter em pelo menos 75% deles.
  - K4, erro decisivo: o gemma reescreve a resposta aceita de uma pergunta fora da amostra duas vezes, uma fielmente e outra com um erro técnico decisivo. O juiz deve escolher a versão correta em pelo menos 80% dos pares aprovados, e precisa haver pelo menos 30 pares aprovados (são gerados 60).
  - K5, equivalentes: duas reescritas fiéis da mesma resposta, com estruturas diferentes. O juiz deve dar EMPATE em pelo menos 50% dos pares aprovados, e precisa haver pelo menos 20 pares aprovados (são gerados 40).
  - **Revisão prévia dos pares de K4 e K5:** antes do julgamento, cada par passa por uma revisão independente. Um agente separado, que não participa do julgamento, confirma que a versão com erro tem mesmo um erro decisivo, que a versão fiel está correta e que as versões equivalentes são de fato equivalentes. O autor pode mandar o mesmo arquivo ao Astra; se qualquer revisor reprovar um par, ele sai.
  - K3, oráculo, virou diagnóstico: mede quanto ajuda dar a referência ao gerador. Ele não reprova o juiz, porque a resposta sem contexto pode estar certa e as duas podem ser equivalentes.
  - Se K1, K2, K4 ou K5 falhar, ou se houver menos pares aprovados que o mínimo, o resultado da rodada é INCONCLUSIVO.

### Métrica e critérios (fixados antes de rodar)

**Métrica.** A preferência líquida é Δ = fração em que o juiz prefere a primeira condição − fração em que prefere a segunda. Empates contam zero. O IC de 95% vem de bootstrap com 2.000 reamostragens.

- **P1 (principal, efeito no subconjunto):** em E1, o limite inferior do IC de Δ(CH − CM0) fica acima de 0. Leitura: quando a rede traz a família que a busca simples perdeu, a resposta final melhora. Com 124 perguntas, só efeitos grandes são detectados com segurança: há cerca de 90% de chance para +0,20 e cerca de dois terços para +0,15.
- **P2 (sem piora grande):** em E2, o limite inferior do IC de Δ(CH − CM0) fica acima de −0,10. Leitura: as discussões extras da rede não pioram muito a resposta quando não trazem família nova.
  - **P2 não sustenta benefício geral.** E1 pesa cerca de 0,6% das perguntas com resposta aceita, e E2 cerca de 92%. Um ganho de 15 pontos em E1 soma cerca de 0,09 ponto à média geral, e uma piora de 0,1 ponto em E2 já o anularia.
  - A margem continua em −0,10 porque 400 perguntas não têm precisão para uma margem menor.
- **Veredito:**
  - P1 e P2: "H melhora a resposta final no subconjunto em que traz a família que a busca simples perdeu (E1), sem piora grande no restante (E2, margem −0,10). O efeito médio sobre todas as perguntas é exploratório."
  - Só P2: "Melhora em E1 não demonstrada; sem piora grande em E2."
  - P2 falha: "Em E2, H pode piorar a resposta."
  - Controles falham ou são insuficientes: INCONCLUSIVO.
  - Nenhum veredito afirma benefício geral nem resolução real. O que se mede é qualidade estimada por um avaliador, guiado por uma referência imperfeita.
- **Secundários (descritivos, sem critério):**
  - Δ em E3.
  - Efeito médio sobre todas as perguntas, **exploratório**, com IC e com o valor de Δ em E2 que anularia o ganho de E1. Perguntas com top-5 iguais contam Δ = 0, e perguntas marcadas sem mudança de família recebem o Δ de E2.
  - Δ(CM0 − C0) e Δ(CH − C0) na subamostra.
  - Δ(CH − CM0) conforme o equilíbrio de discussões com resposta entre os dois contextos.
  - Tamanho médio das respostas por condição.
  - K3.

### Limites já conhecidos

- O gemma4 pode ter visto parte do AskUbuntu no treino, inclusive respostas de 2020 a 2024. Isso afeta as três condições igualmente e tende a reduzir as diferenças.
- A resposta aceita é uma referência imperfeita: nem sempre é a melhor, e às vezes só aponta para outra pergunta.
- Só entram perguntas com resposta aceita, que tendem a ser as mais fáceis de responder.
- Um juiz guiado pela referência mede "chegou a uma solução equivalente", não "resolveu de fato".
- E1 é um subconjunto selecionado, então P1 é um efeito condicional. O efeito para a população depende da frequência de E1.

### Detalhes de execução (definidos ao escrever o script gc\_r9.py, 29/09/2026)

- **Exclusões:** as 720 perguntas já mostradas a juízes em etapas anteriores ficam fora de todas as amostras.
- **Empate automático:** quando as duas respostas comparadas são idênticas, o item conta como empate e não vai ao juiz.
- **Diagnóstico de equilíbrio:** o script informa, por estrato, quantas das 5 discussões de cada contexto têm resposta, em CH e em CM0.
- **Perguntas dos controles:** K4 usa as 60 perguntas do K1 e K5 usa 40 das 60 perguntas do K3, sorteadas com Random(913). Todas estão fora das amostras principais.
- **Rubrica do juiz (texto exato):** "Each item shows a question posted on Ask Ubuntu, a REFERENCE answer and two candidate answers, A and B. The reference was accepted by the asker; use it as evidence, while also considering the requirements of the question and the technical validity of each candidate. A different approach can be equally correct. Decide which candidate is more likely to solve the asker's problem; a candidate with wrong, risky or irrelevant steps is worse. Ignore length, style and formatting. Answer A, B or TIE (TIE when neither is clearly more likely to solve the problem)."
- **Prompts dos controles (texto exato do início de cada um):**
  - Reescrita fiel: "Rewrite the following answer to a question posted on Ask Ubuntu in your own words. Keep every technical step, command, package name, option and path exactly correct, and do not add or remove steps."
  - Segunda reescrita fiel: o mesmo, com "using a different structure (numbered steps if the original is a paragraph, a paragraph if it is a list)".
  - Reescrita com erro: "… but introduce exactly one decisive technical error that would make the solution fail (for example a wrong command, package name, file path, option or order of steps). Keep everything else correct and do not mention or hint at the error."
- **Sequência no Mac:**
  1. `preparar` monta estratos e amostras.
  2. `piloto` roda 10 perguntas fora da amostra.
  3. `gerar` faz a geração completa, só com a opção de pré-registro congelado.
  4. `controles` cria o arquivo de revisão prévia dos pares K4 e K5.
  5. `itens` cria os itens cegos com os pares aprovados; a chave fica no Mac.
  6. `comparar` devolve só agregados.
- **Teste:** o script foi testado com dados sintéticos e um Ollama simulado, incluindo os caminhos de reprovação: controles insuficientes, rótulos faltando e arquivo de itens alterado. Uma checagem independente refez a escolha da resposta e da versão do texto em 4.633 pares pergunta-discussão, sem nenhuma divergência.

### Amostra real e piloto (29/09/2026, antes do congelamento)

As etapas `preparar` e `piloto` rodaram no Mac do autor. Nenhuma resposta da amostra principal foi gerada.

- **Dados conferidos:** a SHA-256 dos dados é a mesma da confirmação (951a20e2…). O modelo gerador é o gemma4 (digest c6eb396d…) no Ollama 0.30.10, e ele aceitou o think desligado.
- **Perguntas novas com resposta aceita:** só 877 das 5.982 marcadas (14,7%) e 1.109 da amostra de 5.000 sem marcação (22,2%). Perguntas fechadas como duplicata raramente têm resposta aceita.
- **Amostra real:**
  - E1 tem 124 perguntas, todas as disponíveis depois das exclusões (128 no universo), contra até 250 previstas no rascunho. Continua acima do mínimo de 80.
  - E2 tem 400 perguntas, sorteadas de 931.
  - E3 tem 11 perguntas, só descritivo.
  - O resto: C0 com 150, K1 com 60 e K3 com 60.
- **Poder de P1 com 124 perguntas:** supondo cerca de metade de empates, a chance de detectar um efeito real é de uns dois terços para Δ = +0,15, uns 90% para +0,20 e cerca de um terço para +0,10. Ou seja, P1 só detecta com segurança efeitos grandes. P2, com 400 perguntas, mantém cerca de 80% de chance de passar se o efeito real for zero.
- **Peso na população:** E1 corresponde a cerca de 0,6% das perguntas novas com resposta aceita, e E2, somado às marcadas sem mudança de família, a cerca de 92%. Mesmo que P1 dê positivo, o efeito médio sobre todas as perguntas depende quase só do que acontece em E2.
- **Desequilíbrio de contexto:** das 5 discussões de cada contexto, CH tem em média mais discussões com resposta que CM0. Em E1 são 4,52 contra 4,07; em E2, 4,26 contra 3,87. H traz mais perguntas antigas, que já foram respondidas, e M0 traz mais perguntas recentes, ainda sem resposta. Isso faz parte do que a rede faz, que é apontar para problemas já resolvidos, mas é uma explicação alternativa para um efeito "da família".
- **Secundário proposto** para separar esse desequilíbrio (descritivo, sem critério): Δ(CH − CM0) nas perguntas em que os dois contextos têm o mesmo número de discussões com resposta, e Δ conforme a diferença nesse número.
- **Piloto:** 10 perguntas fora da amostra, 30 respostas, nenhuma vazia.
  - Cada resposta levou 18,4 s em média; a rodada completa, com 1.340 respostas, deve levar cerca de 6,8 horas.
  - As respostas têm em média 155 a 161 palavras nas três condições.
  - O formato está correto.
  - 5 das 50 discussões mostradas entraram sem resposta. Um exemplo é uma pergunta de 2020 que ainda não tinha resposta quando a pergunta nova foi publicada, como a regra prevê.
  - As respostas CH e CM0 costumam ser parecidas entre si. Deve haver bastantes empates.

### Revisão do Astra e congelamento (29/09/2026)

O Astra revisou o rascunho com a amostra real e o piloto. As três correções foram aceitas e já estão no texto acima.

1. **O critério permitia comemorar um ganho pequeno aceitando uma perda maior.**
   - O veredito agora fala só do subconjunto E1, e o efeito médio geral virou exploratório.
   - P2 passou a se chamar "sem piora grande". A margem ficou em −0,10, porque 400 perguntas não têm precisão para uma margem menor, e o Astra concordou.
2. **K3 não é um controle confiável de acerto do juiz.**
   - K3 virou diagnóstico.
   - Entraram dois controles difíceis com revisão prévia independente: K4, com erro decisivo, e K5, com respostas equivalentes em que o empate é o certo.
3. **A resposta aceita não prova resolução.** A rubrica passou a tratá-la como evidência, com o texto proposto pelo Astra.

O Astra também considerou adequados E1 com 124 perguntas, para efeitos grandes, e C0 com 150, como comparação exploratória. Sobre o desequilíbrio de discussões com resposta, ele observou que, se H ajuda por encontrar discussões já respondidas, isso pode ser um benefício real do sistema, embora não isole o papel das relações.

**Congelado em 29/09/2026 às 16h55 (+02:00).** O script da rodada é o `gc_r9.py` com SHA-256 08963d0a10333741a0d71850e2756a2bf9af8d6bcab1ca4c43e20dd732b5947e. As etapas `preparar` e `piloto` rodaram com uma versão anterior do mesmo script. A amostra e os textos não mudam: continuam os da SHA-256 1fb76609… A partir daqui, nada do desenho muda depois de ver resultados; qualquer desvio será registrado como desvio.

### Desvio 1: origem dos erros do K4 (29/09/2026, antes de qualquer julgamento)

**Geração.** Rodou no Mac do autor com o script congelado: 1.540 respostas, nenhuma vazia, em cerca de 4 horas e meia. O cache das respostas é o `r9_geracoes_e25567e4cc702dff.jsonl`.

**O que falhou.** Os pares de controle passaram pela revisão prévia, feita por 4 agentes separados com 25 pares cada.

- **K5, respostas equivalentes:** 21 de 40 aprovados, acima do mínimo de 20.
- **K4, erro decisivo:** só 4 de 60 aprovados. Na maioria dos casos o gemma apenas reescreveu a resposta, sem inserir o erro pedido; em outros, a versão fiel tinha texto meta, estava truncada ou distorcia a referência.

Com menos de 30 pares no K4, o juiz ficaria sem validação, e a rodada seria INCONCLUSIVO antes de qualquer julgamento.

**Decisão do autor, antes de ver qualquer resultado.** Os erros do K4 passam a ser inseridos por um agente Claude separado. Ele faz uma edição mínima sobre a reescrita fiel do gemma, que fica inalterada como versão 1.

- O agente descartou 21 casos em que a versão fiel não servia (texto meta, truncamento, distorção ou falta de conteúdo técnico) e escreveu 39 versões com erro. Um exemplo: `.bashrc` trocado por `.bash_logout`.
- Dois outros agentes, que não inseriram erros e não serão juízes, revisaram os 39 pares com os mesmos critérios e aprovaram 35.
- Os controles ficaram com 35 pares no K4 (mínimo de 30) e 21 no K5 (mínimo de 20). Nenhum critério ou limiar mudou.

**Limitações.**

- Os erros foram escritos por um agente da mesma família de modelos do juiz. O autor pode mandar os pares ao Astra como revisão independente.
- O assistente que coordena a rodada viu os pares de controle, mas não os itens principais. Os juízes serão agentes novos, que recebem só a rubrica e os itens.

**Arquivos e registro.**

- `r9_k4_erros.json` (SHA-256 17bd985a…) tem os textos com erro, indexados pelo número da pergunta no Stack Exchange.
- `r9_controles_aprovados.json` (SHA-256 2d1091ee…) reúne as decisões da revisão: K4 da segunda revisão e K5 da primeira.
- A descrição de cada erro inserido fica guardada para auditoria.
- O `gc_r9.py` passou para a SHA-256 e1dbbe2cd3b04dce163a842c085b190c18b77d4e03cdcc3d7228c154f491e997. A única mudança é ler `r9_k4_erros.json`. No teste, sem esse arquivo, o arquivo de revisão saiu idêntico, byte a byte, ao da versão congelada.
- O novo arquivo de revisão deve ter a SHA-256 1bbf38211918c1b36dd6a6334dc9ee0a75270e3ee9d502c2433e0b46a4125ecf, que é exatamente o que os revisores aprovaram.

**Conferência no Mac (29/09/2026, 22h47).** O arquivo de revisão saiu com a SHA-256 bf804039…, e não 1bbf3821…, porque o script descartou o par C032. A regra, que já estava no script congelado, trata como idênticos dois textos que só diferem em maiúsculas e minúsculas, e no C032 o erro inserido era justamente trocar `-F` por `-f` no awk. Refazendo o cálculo aqui sem o C032, a SHA-256 dá exatamente bf804039…: o arquivo do Mac é o conjunto revisado, só sem esse par. Os itens foram gerados com 34 pares no K4 (mínimo de 30) e 21 no K5 (mínimo de 20), 1.050 itens no total, sem nenhum empate automático. A SHA-256 dos itens é d1fb1aa08ccabc1ab686b71681a52afe6a9fea9fec8819db1849dca6621a0086.

### Resultado da Rodada 9 (30/09/2026, 02h55)

O julgamento cego foi feito por 30 agentes novos, um por lote de 35 itens, que receberam só a rubrica e os itens. Os 1.050 rótulos têm SHA-256 ed24c20f… A comparação rodou no Mac do autor, e a chave não saiu de lá.

**O juiz passou em todos os controles:**

- K1, discriminação fácil: 60 de 60.
- K2, ordem: 87,5% de consistência.
- K4, erro decisivo: 34 de 34.
- K5, equivalentes: 21 de 21 empates.
- Não houve viés de posição nos itens principais: A em 24,9%, B em 26,5% e empate em 48,6%.
- O tamanho médio das respostas foi parecido nas condições: 166,6 palavras em CH, 165,6 em CM0 e 169,1 em C0.

**Critérios pré-registrados:**

| Estrato | n | Δ(CH − CM0) | IC 95% | CH preferida / CM0 preferida / empate |
| --- | --- | --- | --- | --- |
| E1: a rede traz a família | 124 | **+0,153** | +0,024 a +0,282 | 44 / 25 / 55 |
| E2: sem família nova | 400 | **−0,070** | −0,138 a 0,000 | 87 / 115 / 198 |
| E3: a rede perde a família (descritivo) | 11 | −0,182 | −0,545 a +0,182 | 1 / 3 / 7 |

- **P1 passou:** o limite inferior em E1 ficou acima de 0.
- **P2 falhou:** o limite inferior em E2 foi −0,138, abaixo da margem de −0,10.
- **Veredito oficial, pelo texto pré-registrado:** "Em E2, H pode piorar a resposta." O P1 também está registrado: quando a rede traz a família que a busca simples perdeu, a resposta final melhorou.

**Secundários (descritivos, sem critério):**

- **Efeito médio sobre todas as perguntas, exploratório:** −0,064, IC 95% de −0,124 a −0,001. Um Δ de apenas −0,001 em E2 já anularia o ganho de E1.
- **Equilíbrio de discussões com resposta:**
  - Em E1, o ganho aparece justamente quando os dois contextos têm o mesmo número de discussões com resposta: +0,237 (IC de +0,079 a +0,395; n = 76). Quando CH tem mais discussões respondidas, o ganho é de +0,021 (n = 48).
  - Em E2, a piora aparece com o mesmo número: −0,089 (IC de −0,177 a +0,004; n = 248).
  - Portanto, nem o ganho de E1 nem a piora de E2 são explicados por H trazer mais discussões respondidas.
- **Comparação com responder sem contexto (C0, 75 perguntas por estrato, todos os IC cruzam zero):**
  - Em E1: CH − C0 = +0,080 e CM0 − C0 = −0,107.
  - Em E2: CH − C0 = −0,067 e CM0 − C0 = +0,133.
- **K3, diagnóstico:** com a solução verdadeira no contexto, a resposta foi preferida em 70% das vezes, contra 8% para a resposta sem contexto e 22% de empates. O contexto certo muda muito a resposta.

**Leitura \[Interpretação, não medida diretamente\]:**

- A rede ajuda quando traz o que falta, que é a família do problema, e atrapalha um pouco quando não traz.
- Em E2, H troca parte das discussões de M0 por sugestões de M2, que inclui o termo de popularidade global. Esse termo já aparecia nas rodadas 8 e 8b puxando guias famosos para perguntas não relacionadas. A explicação mais provável da piora em E2 é esse contexto menos pertinente, e não as relações em si.
- Isso aponta para um uso seletivo: acrescentar as discussões da rede só quando elas são pertinentes. Pode ser sem o termo de popularidade (H1), com pesos contextuais ou com um portão. Essa é uma hipótese para uma próxima rodada pré-registrada, testada em perguntas novas e não nesta amostra.

**Limites:**

- Mede-se qualidade estimada por um juiz guiado pela resposta aceita, não resolução real.
- O gerador é um modelo pequeno, o gemma4, e o efeito pode ser diferente com modelos maiores.
- O juiz e o agente que inseriu os erros do K4 são da mesma família de modelos (Desvio 1).
- E1 tem 124 perguntas.
- O coordenador viu os pares de controle, mas não os itens principais nem a chave.

### Revisão do Astra sobre o resultado e errata (30/09/2026, 03h)

A avaliação do Astra foi esta: o resultado é positivo como evidência de benefício condicional e negativo para adotar H de forma geral. Com base nele, não se recomenda trocar a busca comum por H para todas as perguntas. As correções abaixo valem para a seção de resultado acima e para o que foi dito na conversa; o texto anterior não foi apagado.

1. **E2 não significa "a rede não trouxe família".** Significa que a pergunta não tem marcação disponível. As relações reais dessas perguntas são desconhecidas. O nome correto é "perguntas sem duplicata marcada, com contextos diferentes".
2. **A rodada não isolou o termo de popularidade.** Ele é um suspeito plausível pela piora em E2, por causa das rodadas 8 e 8b, mas não foi testado aqui. Para atribuir a piora a ele, seria preciso comparar H com H1 nas mesmas perguntas. A frase "a explicação mais provável" fica corrigida para "um suspeito plausível, não testado".
3. **Igualar o número de discussões respondidas não elimina todas as explicações alternativas.** O ganho de E1 nesse recorte enfraquece a explicação de "apenas mais respostas disponíveis", mas não identifica sozinho a causa do ganho. A frase "nem o ganho nem a piora são explicados por…" fica corrigida para "o recorte enfraquece essa explicação".
4. **O efeito médio negativo é exploratório.** Ele depende dos pesos e das suposições usados para os grupos não avaliados, e não é perda comprovada sobre todas as perguntas.

**Resumo, na formulação do Astra:** o sistema consegue trazer contexto que melhora a resposta, mas ainda não sabe reconhecer com segurança quando deve fazê-lo. Além disso, E1 foi identificado pelas marcações do dataset, e uma aplicação real não conhece esse grupo de antemão. Qualquer filtro que decida quando usar a rede precisa funcionar só com a pergunta e o que está disponível naquele momento.

## Rodada 10: usar a rede só quando ela ajuda (desenho congelado em 30/09/2026)

**Situação:** a regra da etapa B e o desenho da etapa C foram congelados em 30/09/2026, depois de duas revisões do Astra (03h08 e 03h15). Nada foi rodado. A sequência é esta:

1. Congelar agora a regra da etapa B e todo o desenho da etapa C, incluindo a regra de tamanho da amostra, que depende só de contagens.
2. Rodar a etapa B no AskUbuntu e registrar o τ e o resultado da verificação.
3. Baixar o Super User, rodar a etapa A e contar as perguntas elegíveis. Não há nenhuma comparação de qualidade de resposta nessa etapa.
4. Sortear a amostra da etapa C pela regra congelada, gerar as respostas e julgar.

Nenhum dado do Super User é consultado antes de o τ estar registrado.

**Primeira revisão do Astra, incorporada abaixo:**

1. O portão deve prever ganho de recuperação, sem tratar a falta de marcação como erro.
2. Os grupos devem ser recalculados para o método que o portão usa, H1.
3. A regra tem de ser concreta: sinal, candidatos, grade, escolha do τ e cobertura mínima. A calibração separa desenvolvimento e verificação.
4. A conta do efeito médio vale só para a população avaliada. Com o portão fechado, reutiliza-se a saída de CM0, e o custo é medido.
5. A comparação H × H1 fica como secundária, pareada e com o mesmo orçamento de contexto.
6. O Super User testa transferência, não compartilhamento entre sites.
7. A etapa A precisa de critérios de recuperação com nome próprio, e os custos são recalculados depois.

**Segunda revisão do Astra, incorporada abaixo:**

1. Registrar uma propriedade do sinal: só a semelhança com o centro da família pode tornar S positivo. O sinal é um só nesta rodada.
2. Exigir mais ganhos que perdas entre as aberturas com marcação, e renomear a métrica para "fração de ganhos entre as aberturas com marcação".
3. Dar consequência à metade de verificação.
4. Fixar tamanho desejado, mínimo e procedimento para amostra insuficiente, e resolver a sequência.
5. Atualizar o bloco de custo.

**Pergunta.** Um portão que decide, só com informação disponível na hora da pergunta, quando acrescentar discussões da rede ao contexto consegue manter o ganho visto em E1 sem a piora vista em E2, em perguntas novas de outro site?

**Ideia central.** Com um portão, as perguntas em que ele não abre recebem exatamente o contexto da busca simples, e nelas se reutiliza a mesma resposta de CM0, sem gerar de novo. A diferença de qualidade ali é zero por construção. Dentro da população avaliada, o efeito médio é a fração em que o portão abre vezes o efeito nessas perguntas. A população são as perguntas novas com resposta aceita, e a conclusão fica restrita a ela, não a todas as perguntas do site. O custo não é zero quando o portão fecha, porque o sinal também precisa ser calculado, e isso é medido. Diferente de E1, o grupo "portão aberto" é identificável na aplicação real.

**Desenho proposto.**

- **Dados:** o site Super User, do mesmo dump de 02/04/2024, com as mesmas regras da confirmação:
  - corte em 01/01/2020;
  - versões de época dos textos;
  - memória com as relações anteriores a 2020;
  - o mesmo modelo de embeddings;
  - respostas do contexto como estavam quando a pergunta nova foi publicada.
  - Para a etapa C, o portão é calculado para todas as perguntas novas com resposta aceita, e não só para uma amostra.
- **Etapa A, transferência da recuperação para o Super User, sem LLM e sem juiz.** Os critérios têm nome próprio:
  - A1: o ganho relativo de M1 sobre M0 na família marcada no top-5 tem limite inferior do IC acima de 10%.
  - A2: o mesmo para H1.
  - Descritivos: H, M2, a duplicata marcada no top-5 e o teto.
- **Etapa B, calibração do portão.** É desenvolvimento, feito só com os dados de recuperação do AskUbuntu, que já foram muito explorados; o Super User é a avaliação de transferência.
  - **Método que o portão libera:** H1, isto é, M0 intercalado com M1, sem popularidade.
  - **Grupos, recalculados para H1:**
    - ganho: a família marcada está no top-5 de H1 e não no de M0;
    - perda: está no top-5 de M0 e não no de H1;
    - neutro: a mesma situação nos dois;
    - sem marcação: não há evidência para dizer ganho ou perda. Esse grupo é registrado à parte e nunca contado como erro.
  - **Sinal (único nesta rodada):** S(q) = maxₓ m1(d) − s(primeira sugestão de M0), com o máximo tomado sobre as discussões d que entrariam no contexto por H1 e não estão no top-5 de M0.
    - m1(d) é a pontuação de M1, sem popularidade: a maior entre a semelhança direta, a semelhança com as duplicatas confirmadas de d e a semelhança com o centro da família.
    - Se não houver discussão nova, o portão fica fechado.
    - **Propriedade do sinal:** a primeira sugestão de M0 já tem a maior semelhança direta da base, e as duplicatas confirmadas também fazem parte da base. Por isso nem a semelhança direta nem a semelhança com uma duplicata superam s(primeira sugestão de M0), e só a semelhança com o centro da família pode tornar S positivo.
    - Limiares positivos selecionam, portanto, evidência de centro de família; limiares negativos admitem outras evidências da rede. Se o portão funcionar com τ positivo, o sinal útil será especificamente a proximidade com o centro da família.
    - Nenhum sinal alternativo será procurado depois de ver resultados.
  - **Grade:** τ de −0,10 a +0,10, de 0,02 em 0,02 (11 valores). O portão abre quando S(q) ≥ τ.
  - **Divisão:** as perguntas do AskUbuntu (marcadas e amostra sem marcação) são sorteadas com Random(1010) em duas metades. A de desenvolvimento escolhe o τ; a de verificação confere.
  - **Medidas por τ, com as contagens absolutas:**
    - aberturas em ganho, perda e neutro;
    - fração de ganhos entre as aberturas com marcação, que é o número de ganhos dividido pelo total de aberturas entre as perguntas marcadas;
    - cobertura, que é a fração das perguntas novas com resposta aceita em que o portão abre, com marcadas e sem marcação ponderadas como na rodada 9;
    - abertura nas perguntas sem marcação, à parte.
  - **Regra de escolha (limiares pragmáticos, congelados):** um τ é admissível se cumprir três condições:
    1. a fração de ganhos é pelo menos o dobro da de H1 sem portão, na mesma metade;
    2. há mais ganhos que perdas entre as aberturas com marcação;
    3. a cobertura é de pelo menos 2%.
  - **Escolha:** entre os τ admissíveis na metade de desenvolvimento, escolhe-se o de maior cobertura. Se nenhum for admissível, o portão é declarado não calibrável, a etapa C não roda, e isso fica registrado como resultado.
  - **Verificação com consequência:** as três condições são aplicadas à metade de verificação com o mesmo τ, sem reajuste. Se alguma falhar, registra-se que a calibração não se mostrou estável, e a etapa C, se rodar, será explicitamente exploratória.
  - Prever ganho de recuperação não garante prever melhora da resposta. É justamente essa passagem que a etapa C testa.
- **Etapa C, qualidade da resposta no Super User (avaliação de transferência).**
  - **População:** perguntas novas com resposta aceita, e as conclusões ficam restritas a ela.
  - **Tamanho da amostra, só por contagens:** conta-se N, o número de perguntas elegíveis com o portão aberto.
    - N ≥ 250: sorteiam-se 250 com Random(2020).
    - 150 ≤ N < 250: usam-se todas.
    - 60 ≤ N < 150: usam-se todas, mas a etapa C é só exploratória.
    - N < 60: a etapa C não roda.
    - Com 2% de abertura, 250 perguntas abertas exigem cerca de 12.500 perguntas elegíveis. 250 perguntas são um alvo razoável para efeitos moderados, mas não garantem detectar ganhos pequenos.
  - **Condições:** CM0 e CG. Com o portão fechado, CG é CM0 por definição, e reutiliza-se a mesma saída. Com o portão aberto, CG usa o contexto de H1.
  - **Principal:** Δ(CG − CM0) nas perguntas com o portão aberto, com limite inferior do IC acima de 0. O efeito médio na população avaliada é a cobertura no Super User vezes Δ.
  - **Secundário, para isolar a popularidade:** Δ(CH − CH1) em 150 perguntas sorteadas com Random(2021) entre as elegíveis em que H e H1 diferem, com ou sem portão aberto (restrição declarada). O orçamento de contexto é o mesmo (5 discussões), o julgamento é pareado, e gerações com contexto idêntico são reutilizadas.
  - **Custo:** registram-se o tempo de cálculo do sinal do portão e os tokens de entrada e de saída de cada condição.
- **Julgamento:** como na rodada 9, com os mesmos limiares de validade. Os controles são K1 (60), K2 (40), K4 (60 gerados, com erros inseridos desde o início por um agente separado e revisão prévia) e K5 (40).
- **O que esta rodada não testa:** compartilhamento entre aplicações. Repetir o método com a memória própria do Super User responde se o mecanismo funciona em outra comunidade. Comparar a memória local com uma memória acrescida de contribuições externas fica para outra rodada.

**Riscos já visíveis:**

- Pode não existir um τ admissível. A etapa B mostra isso antes de baixar o Super User ou gastar geração.
- O Super User pode ter poucas perguntas elegíveis com o portão aberto. A regra de tamanho de amostra já define o que fazer.

**Custo estimado da rodada 10** (a confirmar pelas contagens):

- **Etapa B:** minutos no Mac, sem Ollama.
- **Etapa A:** embeddings do Super User inteiro, como documentos e como perguntas novas, na ordem de 1 a 2 horas.
- **Etapa C:** cerca de 1.000 gerações, somando 250 × 2, 150 × 2 e os controles, menos as reutilizadas. São umas 5 horas de gemma, mais cerca de 800 itens para o juiz.

**Congelado em 30/09/2026 às 03h20 (+02:00):** a regra da etapa B e o desenho das etapas A e C. O script da etapa B será registrado com SHA-256 antes de rodar. A partir daqui, qualquer mudança é desvio registrado.

**Script da etapa B:** `gc_r10_portao.py`, com SHA-256 790fd9c56498435d4f891bb7fe50de844fca82042d2278aeb38da65876332b55, registrado antes de rodar.

- Ele implementa exatamente a regra acima e devolve só números: as contagens absolutas por τ nas duas metades, o τ escolhido e o resultado da verificação.
- Informa também, para cada abertura, de onde veio o sinal (semelhança direta, com duplicata ou com o centro da família). Isso permite conferir a propriedade registrada.
- Foi testado com dados sintéticos: acima de τ = 0 todas as aberturas vieram do centro da família, como a propriedade prevê.

### Resultado da etapa B: o portão não é calibrável (30/09/2026, 03h30)

O script congelado (SHA-256 790fd9c5…) rodou no Mac do autor em 2,8 minutos, com a mesma SHA-256 dos dados da confirmação. Cada metade tem 5.491 perguntas: 3.044 marcadas na de desenvolvimento e 2.938 na de verificação.

**Resultado oficial: nenhum τ foi admissível, e o portão é declarado não calibrável.** Pela regra congelada, a etapa C não roda. Nenhum sinal alternativo será procurado dentro desta rodada.

| Metade de desenvolvimento | aberturas marcadas | ganho | perda | neutro | fração de ganhos | cobertura |
| --- | --- | --- | --- | --- | --- | --- |
| H1 sem portão | 2.306 | 289 | 38 | 1.979 | 12,5% | 56,7% |
| τ = 0,00 | 1.222 | 155 | 20 | 1.047 | 12,7% | 26,2% |
| τ = +0,02 | 272 | 48 | 3 | 221 | 17,6% | 4,9% |
| τ = +0,04 | 27 | 5 | 0 | 22 | 18,5% | 0,6% |

- **O que faltou:** a exigência era uma fração de ganhos de pelo menos 25,1%, o dobro de 12,5%, com cobertura de pelo menos 2%. O melhor que o sinal alcançou com cobertura útil foi 17,6%, em τ = +0,02, ou 1,4 vez a fração de H1 sem portão.
- **Na verificação, o quadro é o mesmo:**
  - H1 sem portão: 12,7%.
  - τ = +0,02: 16,0%, com 41 ganhos e 9 perdas.
  - τ = +0,04: 5%, isto é, 1 ganho em 20 aberturas.
- **A propriedade registrada se confirmou:** acima de τ = 0, todas as aberturas vieram da semelhança com o centro da família.
- **Leitura (descritiva):**
  - A proximidade com o centro da família carrega um sinal fraco. Ela enriquece um pouco as aberturas que trazem a família marcada, mas nem de longe o suficiente para reconhecer de antemão quando a rede vale a pena.
  - H1 sem portão raramente perde a família marcada: 289 ganhos contra 38 perdas. A maior parte das aberturas, porém, é neutra, porque o contexto muda sem trazer nem tirar a família marcada.
  - Pela errata da rodada 9, "neutro" não significa inútil. Significa apenas que não há evidência marcada.
- **O que continua válido:** a etapa A, transferência da recuperação para o Super User, não depende do portão. Ela pode rodar como congelada, como teste de generalização do resultado confirmado.
- **O que fica em aberto para uma nova rodada, com novo pré-registro:**
  - se H1 sem portão, isto é, sem o termo de popularidade, evita a piora vista em E2 e mantém o ganho;
  - ou se é preciso outro tipo de portão, por exemplo um avaliador que confirme a pertinência das discussões antes de usá-las.

**Revisão do Astra sobre a etapa B e errata (30/09/2026, 10h53).** Parar antes da geração, como estava registrado, foi considerado correto. A etapa não testou nem rejeitou o benefício de H1 sobre a resposta final. O texto acima não foi apagado; valem estas correções:

1. **"Não calibrável" vale só para este sinal, esta grade e estes requisitos.**
   - A exigência de dobrar a fração de ganhos foi uma escolha pragmática nossa, não uma fronteira natural entre útil e inútil.
   - O resultado mostra que o critério não foi atingido. Não mostra que 17,6% seria insuficiente para melhorar respostas, porque isso não foi testado.
   - Baixar o limite agora para declarar sucesso não cabe.
2. **"Neutro" não significa ausência de evidência marcada.**
   - O grupo tem perguntas marcadas em que os dois métodos encontraram a família, ou em que nenhum dos dois encontrou.
   - O significado correto é "sem mudança no acerto da métrica".
   - Ainda pode haver diferença na utilidade dos textos dados ao LLM.

**Próximos passos recomendados pelo Astra:**

- Executar a etapa A no Super User, como congelada.
- Numa próxima avaliação de respostas, comparar M0, H1 e H nas mesmas perguntas novas, para ver se a dificuldade vem principalmente da popularidade ou persiste sem ela.

A regra de seleção descartada não descarta o uso das relações sem popularidade. H1 teve 289 ganhos de recuperação contra 38 perdas na metade de desenvolvimento, o que mantém aberta a hipótese mais simples: talvez retirar a popularidade já baste.

**Script da etapa A:** `gc_r10_A.py`, com SHA-256 6b744b417a36b5b32e3facdca0392910bd1b06f6dbe87262a41ee9633cca933e, registrado antes de rodar.

- Aplica ao Super User o mesmo método da confirmação e avalia os critérios A1 e A2.
- Devolve também contagens de recuperação para planejar a próxima rodada: quantas perguntas têm resposta aceita e em quantas H1, H e M0 diferem. Essas contagens não dizem nada sobre qualidade de resposta.
- Foi testado com os dados sintéticos da confirmação. Com os mesmos dados, reproduziu exatamente os números do `gc_conf.py`, inclusive a SHA-256 dos textos e os ganhos de M1, H e H1 com seus IC.

### Resultado da etapa A: transferência para o Super User (30/09/2026, 14h)

O script congelado (SHA-256 6b744b41…) rodou no Mac do autor em 140 minutos. A SHA-256 dos dados do Super User é 4f7c78f1…, e os embeddings foram gerados com o mesmo digest do nomic-embed-text da confirmação (0a109f42…).

**Os dados:**

- 505.136 perguntas, das quais 93.515 são novas (2020 a 2024).
- Só 1.766 perguntas novas têm duplicata marcada anterior, ou seja, o teto é 1,89%. No AskUbuntu era 6,21%.
- A memória tem 12.377 ligações confirmadas, contra 32.864 no AskUbuntu.
- A rede é, portanto, bem mais rala.

| Família marcada no top-5 | Super User | Ganho relativo sobre M0 (IC 95%) | AskUbuntu (confirmação) |
| --- | --- | --- | --- |
| M0, busca simples | 0,68% | — | 1,61% |
| M1, relações sem popularidade | 0,79% | **+15,5%** (+11,4% a +20,0%) | +41,4% |
| H1, M0 intercalado com M1 | 0,76% | **+11,6%** (+7,9% a +15,4%) | +31,3% |
| H, M0 intercalado com M2 | 0,85% | +25,3% (+19,9% a +30,7%) | +59,3% |
| M2, relações mais popularidade | 0,87% | +27,3% (+21,4% a +33,6%) | +76,0% |

**Critérios congelados:**

- **A1 passou:** o limite inferior do ganho de M1 foi +11,4%, acima de 10%.
- **A2 falhou:** o limite inferior do ganho de H1 foi +7,9%, abaixo de 10%. O ganho de H1 é positivo, com IC que exclui zero, mas não alcançou o limiar registrado.

**Descritivos:**

- Na duplicata marcada no top-5, os ganhos foram M1 +33,5%, H1 +28,5%, H +49,0% e M2 +53,5%.
- Em pontos absolutos o efeito é pequeno: a família marcada no top-5 passa de 0,68% para 0,79% das perguntas novas com M1.

**Leitura \[Interpretação\]:**

- As relações confirmadas continuam ajudando a recuperação em outra comunidade, mas bem menos: o ganho de M1 caiu de +41% para +16%.
- Isso é compatível com a ideia de que o valor depende da densidade de confirmações. O Super User tem cerca de um terço da taxa de marcação do AskUbuntu.
- São só dois sites, que diferem em muitas outras coisas, então isso não demonstra a relação entre densidade e ganho.
- O termo de popularidade continua aumentando a recuperação: H +25% contra H1 +12%. Na rodada 9, H coincidiu com piora das respostas em E2. Recuperação e qualidade da resposta podem, portanto, apontar em direções diferentes. Essa é a pergunta da próxima rodada.

**Contagens para planejamento (perguntas com resposta aceita, só recuperação):**

- **Marcadas:** 267 de 1.766. H1 difere de M0 em 136, H difere de M0 em 210, e H difere de H1 em 164.
- **Amostra sem marcação:** 1.350 de 5.000, com peso de 18,35 cada. H1 difere de M0 em 413, H difere de M0 em 880, e H difere de H1 em 727.

## Rodada 11: busca simples, H1 e H nas mesmas perguntas (desenho congelado em 30/09/2026)

**Situação:** o desenho foi congelado depois da revisão do Astra (30/09/2026, 14h06). Nada foi rodado. As correções dele estão incorporadas abaixo:

1. P2 pode ficar inconclusivo por falta de precisão. Não passar em P2 não demonstra piora.
2. O efeito sobre a população usa denominadores explícitos e pesos reais, com a incerteza deles, e não transfere o efeito para grupos não avaliados.
3. "Contexto idêntico" significa o mesmo conteúdo na mesma ordem.
4. As três perguntas têm resposta separada: se retirar a popularidade melhora em relação a H, se H1 fica dentro da perda tolerada frente a M0 e se H1 supera M0.
5. O estrato F é secundário e passa a se chamar "perguntas com duplicata marcada".
6. Não há repetição no AskUbuntu por enquanto.

**Objetivo.** Isolar o efeito do termo de popularidade na resposta final e estimar a qualidade de H1 frente à busca simples (M0), nas mesmas perguntas novas do Super User.

**Dados.**

- Super User, com as mesmas regras da rodada 9, aproveitando os embeddings da etapa A.
- As respostas das discussões entram como estavam quando a pergunta nova foi publicada.
- A população são as perguntas novas com resposta aceita, e as conclusões ficam restritas a ela.

**Amostra (só por contagens).**

- **Elegíveis:** perguntas novas com resposta aceita, com pelo menos 3 palavras na resposta aceita. Elas vêm das 1.766 perguntas marcadas e da amostra aleatória de 5.000 sem marcação, a mesma da etapa A, em que cada pergunta vale 18,35.
- **Contagens registradas antes de gerar,** separadas entre marcadas e sem marcação: total de elegíveis e, para cada par de métodos (H1 e M0, H e M0, H e H1), quantas têm contexto idêntico e quantas têm contexto diferente.
- **Estrato P:** todas as perguntas elegíveis sem marcação em que H ou H1 difere de M0, cerca de 880. Por precisão, usa-se o conjunto inteiro, e não 400 perguntas. Acima de 1.000, sorteiam-se 1.000 com Random(1111).
- **Estrato F, perguntas com duplicata marcada:** todas as elegíveis marcadas em que H ou H1 difere de M0, cerca de 210. É secundário.
- **Perguntas elegíveis com os três contextos idênticos:** contam Δ = 0 no efeito sobre a população e entram no denominador. Nenhum efeito é transferido para grupos não avaliados, porque os estratos são completos dentro das perguntas elegíveis.

**Condições.** CM0, CH1 e CH, com o mesmo orçamento de 5 discussões e o mesmo prompt da rodada 9. Quando dois prompts são idênticos (mesmo conteúdo na mesma ordem), a geração é reutilizada e a comparação conta como empate automático. Quando os prompts diferem mas as respostas geradas saem iguais, também há empate automático, registrado à parte. Registram-se os tokens de entrada e de saída de cada geração.

**Julgamento.** O juiz é cego e compara pares, com a mesma rubrica, os mesmos controles e os mesmos limiares da rodada 9.

- **Comparações:**
  - H1 × M0 em todas as perguntas dos estratos em que os prompts diferem;
  - H × H1 em todas as perguntas em que os prompts diferem;
  - H × M0 numa subamostra de 300 perguntas sorteadas com Random(1112) entre as dos estratos em que H difere de M0 (secundário).
- **Controles:**
  - K1: 60 pares.
  - K2: 40 itens principais repetidos com a ordem trocada.
  - K4: 60 perguntas, reescrita fiel pelo gemma, erro inserido desde o início por um agente separado e revisão prévia.
  - K5: 40 perguntas, com revisão prévia.
  - Mínimos: 30 pares aprovados no K4 e 20 no K5.
- **K3:** fica de fora nesta rodada.

**Critérios (congelados), com resposta separada para cada pergunta:**

- **P1, retirar a popularidade melhora em relação a H?** Δ(CH1 − CH) no estrato P, entre as perguntas em que os prompts de H e H1 diferem. Passa se o limite inferior do IC ficar acima de 0.
- **P2, H1 fica dentro da perda tolerada frente a M0?** O Δ(CH1 − CM0) estimado para a população de perguntas elegíveis passa se o limite inferior do IC ficar acima de −0,03.
  - A margem de 3 pontos é a perda máxima aceitável e não será ampliada.
  - P2 pode ficar inconclusivo, e não passar em P2 não demonstra piora.
- **P3, H1 supera M0?** Passa se o IC inteiro do mesmo Δ populacional ficar acima de 0. É uma afirmação separada, e P1 junto com P2 não a implicam.
- **Efeito sobre a população:** média ponderada dos escores por pergunta sobre todas as elegíveis, com as marcadas com peso 1 e as sem marcação com peso 18,35. As perguntas com prompts idênticos entram com 0. O IC vem de bootstrap que reamostra perguntas dentro de cada grupo, capturando também a incerteza das frações.
- **Secundários:**
  - Δ(CH − CM0) na subamostra;
  - no estrato F, os três Δ separados por ganho, perda ou nenhuma mudança de família em cada método;
  - o equilíbrio de discussões com resposta;
  - o tamanho das respostas;
  - os tokens.

**Poder aproximado,** supondo cerca de metade de empates:

- **P1:** H e H1 diferem em cerca de 730 perguntas do estrato P, o que dá cerca de 80% de chance de detectar uma diferença líquida de 7 a 8 pontos.
- **P2:** H1 difere de M0 em cerca de 31% das perguntas sem marcação, e o estrato P inteiro fornece cerca de 410 comparações. Se H1 e M0 forem de fato equivalentes, a chance de passar na margem de −3 pontos fica perto de 80%. Com 400 perguntas amostradas, como no rascunho, seria perto de 50%. Na conta do Astra, que não separa as perguntas de contexto idêntico, era cerca de 13%.
- Esses números mudam com a proporção de empates.

**Custo estimado:** cerca de 2.900 gerações, considerando as reutilizações e os controles, o que dá umas 8 a 9 horas de gemma no ritmo real da rodada 9. São cerca de 1.900 itens para o juiz. O custo será recalculado pelas contagens antes de gerar.

**Congelado em 30/09/2026 às 14h20 (+02:00).** O script será registrado com SHA-256 antes de rodar, e qualquer mudança posterior é desvio registrado.

Uma mudança em relação ao rascunho revisado pelo Astra foi decidida antes de qualquer dado de resposta: o estrato P passou de 400 perguntas sorteadas para o conjunto inteiro, cerca de 880, para dar precisão a P2. Os critérios e a margem não mudaram.

**Script da rodada 11:** `gc_r11.py`, com SHA-256 ab436f92b8ec48db0384604a656cef7fec6df7bf12558c7fcbb1086c76b3d477, registrado antes de rodar. Ele importa do `gc_r9.py` (SHA-256 e1dbbe2c…) o prompt, a rubrica e os prompts de controle, trocando apenas "Ask Ubuntu" por "Super User".

- **Reaproveitamento:** a geração é guardada por prompt. Prompts idênticos são gerados uma vez só, e o par vira empate automático registrado como "prompt idêntico".
- **K4:** o script entrega as versões fiéis. Um agente separado insere os erros, e outro agente faz a revisão prévia antes dos itens.
- **Teste:** o script foi testado com dados sintéticos e um Ollama simulado. O efeito sobre a população e P1 conferiram com um cálculo independente.

**Amostra da rodada 11 (`preparar`, 30/09/2026).** O `r11_amostra.json` traz só contagens e ids de pergunta. O dado de base confere com a etapa A (SHA-256 4f7c78f1…); o arquivo de textos tem SHA-256 afb2c708….

- **P:** as 886 perguntas sem marcação em que algum contexto difere do M0. Entraram todas, sem sorteio, porque o total ficou abaixo do teto de 1.000.
- **F:** as 214 perguntas marcadas (com família) em que algum contexto difere do M0.
- **H×M0:** subamostra de 300 das 1.100 perguntas de P e F (246 de P e 54 de F, perto da proporção esperada).
- **Controles:** K1 com 60, K4 com 60 e K5 com 40. Nenhuma pergunta de controle está em P ou F.
- **Elegíveis:** 267 das 1.766 marcadas e 1.350 das 5.000 sem marcação. O peso das sem marcação na estimativa da população é 18,3498.
- **Respostas nas discussões, pela regra do tempo:** 3.589 aceitas antes da pergunta nova, 2.668 mais votadas antes dela e 1.063 sem resposta.
- **Discussões com resposta (de 5):** em P, M0 4,09, H1 4,12 e H 4,29; em F, 4,26, 4,35 e 4,44. A diferença é pequena e entra só como análise secundária de equilíbrio.
- **Observação:** em 7 casos, a resposta "de outra pergunta" usada no K1 vem de uma pergunta que também está no K4 (1) ou no K5 (6). Isso segue o script congelado e não toca P, F nem H×M0; fica só registrado.

Próximo passo: a geração com o gemma4 local, estimada em cerca de 2.800 prompts distintos.

**Geração e erros do K4 da rodada 11 (01/10/2026).** A geração terminou no Mac do autor: 2.846 prompts distintos para 3.440 pares condição-pergunta. O `controles` produziu o `r11_k4_base.txt` (SHA-256 6855ce43…), com as 60 versões fiéis do K4.

- **Inserção dos erros:** foi feita por um agente Claude separado, que não será juiz, como previsto no desenho congelado e com as regras do desvio 1 da rodada 9.
- **Lição do C032 da rodada 9:** o agente recebeu a regra de que o erro precisa sobreviver à comparação sem maiúsculas e sem espaços extras. Cada versão 2 foi montada por script, com uma única substituição sobre a versão 1.
- **Resultado:** 41 versões com erro e 19 casos descartados. Os descartes foram por texto meta (6), distorção da referência ou detalhe errado na versão fiel (7), corte antes do passo principal (4) e falta de conteúdo técnico concreto (2).
- **Conferência independente, feita aqui:** as 41 chaves são perguntas do K4, e todas as versões 2 diferem da versão 1 depois da normalização. Nenhuma passa de 260 palavras.
- **Arquivos:** `r11_k4_erros.json` (SHA-256 39f83b88…). A descrição de cada erro está em `r11_k4_erros_descricao.json` (SHA-256 c19afa53…), guardada para auditoria.
- **Próximo passo:** o autor roda o `controles` de novo, e o arquivo de revisão, com K4 e K5, vai para revisores separados, que não inseriram erros e não serão juízes.

### Desvio 2 da rodada 11: versão 2 do K5 (01/10/2026, antes de qualquer julgamento)

**Revisão prévia.** Quatro agentes separados revisaram os 81 pares do `r11_controles_revisao.txt` (SHA-256 a948756b…), cerca de 20 cada. Nenhum deles inseriu erros, e nenhum será juiz.

- K4, erro decisivo: 37 de 41 aprovados. O mínimo é 30.
- K5, respostas equivalentes: 16 de 40 aprovados, abaixo do mínimo de 20. Na maioria dos casos, o gemma escreveu texto de bastidor ("Here's a rewritten version…", "Here are a few options…") ou uma das versões mudou o conteúdo.

Com menos de 20 pares no K5, o juiz ficaria sem validação, e a rodada seria INCONCLUSIVO antes de qualquer julgamento.

**Decisão do autor, antes de ver qualquer resultado.** Segue o mesmo caminho do desvio 1 da rodada 9. Nos pares rejeitados em que a versão 1 do gemma está limpa, um agente Claude separado escreve uma nova versão 2, equivalente em substância e com outras palavras. A versão 1 fica inalterada. Nenhum critério ou limiar muda.

- **Escrita:** o agente recebeu os 24 pares rejeitados. Descartou 14 em que a própria versão 1 tinha texto de bastidor, erro, passo a mais ou corte antes do passo principal, e escreveu 10 novas versões 2.
- **Segunda revisão:** dois outros agentes, que não escreveram versões e não serão juízes, revisaram os 10 pares novos com os mesmos critérios, 5 cada. Aprovaram os 10.
- **Controles finais:** 37 pares no K4 (mínimo de 30) e 26 no K5 (mínimo de 20). A aprovação do K4 e dos 16 pares originais do K5 vem da primeira revisão; a dos 10 pares novos, da segunda.

**Script.** O `gc_r11.py` passou para a SHA-256 6e6ec634e00c1dcc029965e98e77c43d90f5984706f16535af10f7c9044cf96e. A única mudança é ler o `r11_k5_versoes.json`, indexado pelo número da pergunta no Stack Exchange, e registrar a SHA desse arquivo na chave.

- No teste com dados sintéticos e sem esse arquivo, o arquivo de revisão e os itens saíram idênticos, byte a byte, aos da versão congelada (ab436f92…).
- Com o arquivo, só os pares indicados mudam, e uma pergunta fora do K5 é recusada.

**Arquivos:**

- `r11_k5_versoes.json`: SHA-256 a60cf273…
- `r11_k5_versoes_descricao.json` (auditoria): SHA-256 df5a12d7…
- `r11_controles_aprovados.json`: SHA-256 921547d5…
- O novo arquivo de revisão, gerado no Mac, deve ter a SHA-256 5c54da1bbdac0653353e6f248b2d0596ec3093899ead5c885d2df4ab10212c32. É exatamente o conjunto que os revisores viram.

**Limitações.** Nos 10 pares novos, a versão 2 foi escrita por um agente da mesma família de modelos do juiz, e o estilo das duas versões pode diferir. Isso torna o K5 um teste um pouco mais exigente: o juiz precisa ignorar o estilo para declarar empate. O coordenador da rodada viu os pares de controle, mas não os itens principais.

**Itens e julgamento cego da rodada 11 (01/10/2026).**

- **Conferência no Mac:** o arquivo de revisão saiu com a SHA-256 5c54da1b…, exatamente a esperada.
- **Itens:** o `itens` gerou 2.070 itens (SHA-256 3f13b88d…). A chave ficou no Mac.
- **Julgamento:** 60 agentes novos, um por lote de 35 itens (o último com 5), receberam só a rubrica e os itens, com o mesmo texto de instrução da rodada 9.
- **Rótulos:** todos os 2.070 itens receberam rótulo válido: A em 607, B em 568 e empate em 895. A distribuição entre A e B não mostra viés de posição. O arquivo `r11_rotulos.json` tem SHA-256 36742e39…
- **Próximo passo:** a comparação roda no Mac do autor e devolve só os agregados.

### Resultado da rodada 11 (01/10/2026, 01h35)

A comparação rodou no Mac do autor com o `gc_r11.py` SHA-256 6e6ec634…, e a chave não saiu de lá. Os itens têm SHA-256 3f13b88d…, e a geração usou gemma4 (digest c6eb396d…, Ollama 0.30.10).

**O juiz passou em todos os controles:**

- K1, discriminação fácil: 60 de 60.
- K2, ordem: 0,80 de consistência em 40 pares (mínimo 0,75).
- K4, erro decisivo: 37 de 37.
- K5, equivalentes: 26 de 26 empates.

Nos itens principais, o juiz escolheu A em 29% e empate em 44,6%.

**Errata 1 do script da rodada 11 (encontrada depois do resultado).** O pré-registro define P1 como Δ(CH1 − CH) no estrato P, e P1 passa se o limite inferior do IC ficar acima de 0.

- **O erro:** o script calculou P1 a partir do par "HxH1", em que a primeira condição é CH. O número saído é, portanto, H − H1, mas foi rotulado "H1 − H" e testado como se fosse Δ(CH1 − CH). A frase automática "P1: melhora de H1 sobre H não demonstrada" decorre desse sinal invertido.
- **Por que é um erro de implementação, e não de critério:** a intenção está escrita no pré-registro e na própria mensagem do script para P1 aprovado ("retirar a popularidade melhorou a resposta em relação a H"). O teste com dados sintéticos não pegou o erro, porque a conferência independente usou a mesma orientação.
- **Como foi encontrado:** as contagens do próprio resultado contradiziam o rótulo. H1 foi preferida em 246 perguntas e H em 196, mas o Δ rotulado "H1 − H" saiu negativo.
- **Correção, sem mudar critério nem limiar:** inverter o sinal. Com os mesmos sorteios de bootstrap, Δ(CH1 − CH) = +0,0597, IC 95% de +0,0131 a +0,1086.
- **Recálculo independente a partir das contagens:** +0,0597, IC 95% de +0,0107 a +0,1086; teste de sinal nos pares decididos, p = 0,02.
- **Confirmação pelo secundário:** o efeito sobre a população H − H1, que está rotulado corretamente, vai na mesma direção.
- **Revisão:** esta errata deve ser revisada pelo Astra antes de qualquer divulgação.

**Critérios pré-registrados, com a errata aplicada ao P1:**

| Critério | Δ | IC 95% | Resultado |
| --- | --- | --- | --- |
| P1: Δ(CH1 − CH), estrato P, n = 838 (H1 preferida 246, H 196, empate 396) | +0,060 | +0,013 a +0,109 | passa |
| P2: Δ(CH1 − CM0) na população, limite inferior > −0,03 | +0,006 | −0,016 a +0,029 | passa |
| P3: mesmo Δ, IC inteiro acima de 0 | +0,006 | −0,016 a +0,029 | não passa |

**Veredito, pelos textos pré-registrados:**

- "P1: retirar a popularidade melhorou a resposta em relação a H."
- "P2: H1 ficou dentro da perda tolerada (−0,03) frente a M0."
- "P3: superioridade de H1 sobre M0 não demonstrada."

**Secundários (descritivos, sem critério):**

- **Efeito de H − H1 sobre a população:** −0,037, IC de −0,067 a −0,007.
- **Equilíbrio de discussões com resposta:** no estrato P, quando os dois contextos têm o mesmo número de discussões respondidas, H − H1 = −0,079, IC de −0,133 a −0,025 (n = 648). A vantagem do H1 não vem de ter mais discussões respondidas.
- **H − M0 na subamostra:** −0,024 no estrato P, IC de −0,122 a +0,073 (n = 246); −0,037 no estrato F (n = 54). Inconclusivo.
- **H1 − M0 onde os contextos diferem:** +0,019 no estrato P, IC de −0,055 a +0,093 (n = 420); +0,075 no estrato F, IC de −0,048 a +0,184 (n = 147).
- **Estrato F, perguntas com duplicata marcada:** H − H1 = −0,005 (n = 202), sem diferença. Quando H traz a família e H1 não, H − H1 = +0,278 (n = 18, IC inclui 0). Quando H1 traz a família e M0 não, H1 − M0 = +0,5 (n = 6). As amostras são pequenas.
- **Custo:** tokens de entrada em média de 1.360 no CM0, 1.368 no CH1 e 1.406 no CH; saída de cerca de 255 nas três. Os tokens de geração foram semelhantes. O custo total da rede (construção, manutenção e consulta) não foi medido.
- **Empates automáticos por prompt idêntico:** 533 em H1×M0 e 60 em H×H1.

**Limites da leitura:**

- Vale para o Super User. Não foi repetido no AskUbuntu.
- P2 é não inferioridade dentro de 3 pontos, e não equivalência nem ganho.
- Na recuperação, o H1 acha menos família do que o H (+11,6% contra +25,3% no Super User). Tirar a popularidade troca parte do ganho de recuperação por melhor qualidade relativa a H. A não inferioridade na população não garante segurança em cada pergunta.
- Os pares de controle K4 e parte do K5 foram escritos por agentes da mesma família de modelos do juiz (desvio 2).

### Revisão do Astra do resultado da rodada 11 (01/10/2026)

- **Errata 1 confirmada:** refazendo as contas a partir do JSON, Δ(H1 − H) = (246 − 196)/838 = +5,97 pontos, com IC invertido corretamente de +1,31 a +10,86 pontos. Isso atende ao critério registrado. Corrigir a orientação respeita o protocolo e não é mudar a regra depois do resultado.
- **P2 reproduzido:** H1 − M0 = +0,63 ponto, IC de −1,58 a +2,86, reproduzido a partir das contagens e dos pesos.
- **Escopo da revisão:** o Astra validou a aritmética dos agregados, e não o código nem os julgamentos individuais.
- **Natureza do resultado:** são preferências do juiz pelas respostas, e não problemas efetivamente resolvidos.
- **Leitura:** neste teste, o bônus de popularidade prejudicou a qualidade em comparação com a mesma arquitetura sem ele. A rede sem bônus manteve a qualidade dentro da margem aceita. Ainda não foi demonstrado benefício adicional sobre a busca simples, seja em qualidade, em trabalho poupado ou em custo total.
- **Duas frases do relatório foram ajustadas a pedido dele:** "tokens de geração semelhantes", no lugar de "custa praticamente o mesmo", e "melhor qualidade relativa a H", no lugar de "segurança".

**Resultado corrigido.** O JSON original, com o sinal errado, fica guardado sem alteração como `r11_resultado_original.json` (SHA-256 16847f74…).

- O `gc_r11.py` passou para a SHA-256 0783fb6b1dd8392b34c45b2717829568410ee047d5a0b2951cd02dc1de0c6e21. As únicas mudanças são três:
  - o P1 passa a ser calculado como Δ(CH1 − CH);
  - a saída ganha o campo `errata_1`;
  - a saída registra também a SHA do script da comparação.
- No teste com dados sintéticos, a saída corrigida só difere da anterior no bloco do P1, que fica com sinal trocado, IC espelhado e contagens trocadas, e no campo da errata. Os sorteios de bootstrap são os mesmos.
- O autor roda de novo o `comparar` no Mac. O novo `r11_resultado.json` deve ter P1 = +0,0597, IC de +0,0131 a +0,1086, e ser igual ao original em todo o resto.

**Resultado corrigido gerado no Mac (01/10/2026, 01h51).** O autor guardou o original como `r11_resultado_original.json` (SHA-256 16847f74…) e rodou o `comparar` com o script 0783fb6b… O novo `r11_resultado.json` tem SHA-256 42d676dc19ad5569731604457ed8937c32908bf27a7248a17217534ab2302510.

- **Conferência campo a campo contra o original:** só mudaram o bloco do P1 (+0,0597, IC de +0,0131 a +0,1086, H1 preferida 246 e H 196), o critério P1 (agora verdadeiro), a primeira frase do resumo, o campo `errata_1` e a SHA do script da comparação.
- **Conferência contra a previsão feita aqui:** tudo o mais é idêntico ao que foi previsto antes da nova execução.
- **Veredito oficial da rodada 11:** "P1: retirar a popularidade melhorou a resposta em relação a H." "P2: H1 ficou dentro da perda tolerada (−0,03) frente a M0." "P3: superioridade de H1 sobre M0 não demonstrada."

## Rodada 12: a IA consegue criar as ligações? (rascunho, 30/09/2026, não congelado)

**Status:** rascunho para revisão do Astra. Não será congelado antes do resultado da rodada 11, porque ele decide se a etapa de busca usa H1 ou só M1.

**Revisão do Astra (01/10/2026).** Quatro correções foram incorporadas abaixo, antes do congelamento: a relação que a IA cria, a precisão medida na distribuição real, a separação entre calibração e avaliação e o braço de treino (M3, e não M4). A rodada 11 definiu a base da busca: H1.

**Pergunta:** modelos locais de baixo custo conseguem criar ligações "mesmo problema" que ajudem a busca como as ligações humanas? Se conseguirem, o registro cresce sem depender de moderadores, e a cobertura de famílias deixa de ser o gargalo. No Super User, só 1,89% das perguntas novas têm uma duplicata anterior.

**O que já sabemos:**

- Como validador, o gemma4 é rígido: no teste cego S3 aceitou cerca de 20% das duplicatas verdadeiras, e o kappa com o juiz Claude foi 0,33. Nenhum dos dois aceitou pares aleatórios.
- Pela errata do Astra, passar nos controles não valida um curador. O teste decisivo precisa de casos difíceis e de avaliação independente, antes que as ligações da IA influenciem respostas.

**Desenho proposto:**

- **Site e tempo:** AskUbuntu, com o mesmo corte T0 = 01/01/2020 das rodadas 9 e 10. A IA só liga perguntas anteriores a T0 e não vê nada posterior. O AskUbuntu tem mais ligações humanas para servir de gabarito, mas já foi explorado nas rodadas anteriores. Aqui ele serve para desenvolver a curadoria, e não como confirmação independente; a confirmação fica para outro site ou para uma janela de tempo ainda não usada.
- **Relação criada:** aplicabilidade direcional, "as respostas de B resolvem A", que é o que a duplicata marcada significa no site. O prompt do curador e o gabarito usam a mesma relação e a mesma direção. "Mesmo problema" (identidade) fica como rótulo secundário, registrado à parte, porque uma duplicata pode apontar para um guia que ajuda problemas diferentes.
- **Curadores:** dois modelos locais com o mesmo prompt, o gemma4 e um modelo menor, de 1 a 4 bilhões de parâmetros. O prompt pede para comparar causa e solução, não palavras, e responder YES ou NO com uma nota de confiança. O Claude pode entrar numa amostra, como referência forte.
- **Onde a IA procura:** só entre vizinhos próximos, ou seja, cada pergunta antiga contra as k mais parecidas pelo M0. É ali que estão os casos difíceis e é ali que uma ligação muda a busca. O valor de k e o número de perguntas saem de um piloto de tempo no Mac.
- **Circularidade:** um curador que aprova quase tudo que é parecido só repete o M0. Por isso a etapa 1 mede a precisão em pares muito parecidos, não em pares aleatórios.

**Etapa 1, qualidade das ligações em casos difíceis (antes de qualquer uso):**

- Um conjunto fixo e sorteado de pares vizinhos:
  - positivos: pares com ligação humana;
  - negativos difíceis: pares muito parecidos de famílias confirmadas distintas, com alvos diferentes e não ligados.
- "Não ligados" não prova "diferentes". Um juiz cego (Claude, em lotes, com a chave fora do Claude) revisa os negativos e retira os que forem o mesmo problema.
- **Medidas:** precisão e cobertura de cada curador, por limiar de confiança, e o custo por ligação em segundos e tokens no Mac.
- **Critério E1, a IA pode entrar no registro:** precisão de pelo menos 0,80 (limite inferior do IC) numa amostra aleatória das ligações que o curador realmente aprovaria entre as candidatas, julgada por um avaliador cego independente, com cobertura de pelo menos 0,30. O conjunto de casos difíceis serve de diagnóstico. Os valores estão abertos à discussão.
- **Calibração separada da avaliação:** o limiar de confiança é escolhido num conjunto de calibração. A precisão e a cobertura são medidas num conjunto de avaliação separado, sorteado antes.

**Etapa 2, utilidade na busca (só se E1 passar para algum curador):**

- Quatro braços, nas mesmas perguntas novas:
  - MH: só ligações humanas;
  - MH+IA: humanas e da IA;
  - MIA: só da IA.
  - ET: espaço treinado com os mesmos pares humanos de MH, sem ligações na busca. A versão mínima usa o aprendizado de métrica da rodada 7 sem a rede (M3, já implementado). O M4 inclui a rede e não isola o treino. Se couber no Mac, entra também um ajuste do próprio nomic-embed-text com os pares. É o braço que compara "conectar com modelo barato" contra "treinar".
- **Medida:** família marcada entre as 5 sugestões, com H1 (a base definida pela rodada 11) e com M1, contra M0.
- **Critérios propostos:**
  - Q1: MIA melhora sobre M0, com o IC do ganho relativo acima de 0.
  - Q2: MIA recupera pelo menos metade do ganho de MH (limite inferior de pelo menos 50%).
  - Q3: MH+IA não fica pior que MH, com margem a definir. A IA não pode estragar a memória humana.
  - Q4: MH+IA não fica pior que ET, com margem a definir. Se também custar menos para manter, a curadoria barata passa a ser o caminho preferido do projeto.
- **Limite conhecido:** o gabarito é a família humana. Ligações da IA que tragam discussões úteis fora da família marcada não contam aqui; só a etapa 3 mede isso.

**Custo de cada caminho, medido no Mac:**

- **Curadoria:** segundos e tokens por pergunta nova (as k chamadas) e por ligação criada.
- **Treino:** tempo para ajustar o espaço e para recalcular os vetores de todo o acervo, e com que frequência isso precisaria ser refeito conforme o registro cresce.
- **Comparação no relatório:** custo para manter cada caminho atualizado a cada 1.000 perguntas novas.
- **Limite conhecido:** a curadoria só julga as candidatas que a busca por vetores traz. Se a família certa não estiver entre as k mais próximas, a ligação não nasce. O treino ataca justamente essa parte, e por isso os dois podem se somar em vez de competir. O relatório mostra também em quantas perguntas a família certa estava fora das k candidatas.

**Etapa 3, resposta final (futura):** se a etapa 2 passar, repetir o desenho das rodadas 9 e 11, com o gemma4 gerando e juízes cegos avaliando, usando a memória MIA ou MH+IA.

**Pontos para o Astra:**

1. AskUbuntu, que tem mais ligações humanas para gabarito, ou Super User, onde a cobertura é o gargalo?
2. Os limiares de E1 e a margem de Q3.
3. Como tratar o viés do guia canônico nas ligações da IA.
4. O tamanho do teste, que depende do custo no Mac. A proposta é um piloto de tempo com 200 pares antes de fixar k e o número de pares.
5. O sinal de resultado ("resolveu") como fonte de ligações fica para depois. Os dados públicos não trazem esse sinal entre perguntas diferentes; a resposta aceita é o mais próximo.
6. O braço ET: se basta o M3 da rodada 7 ou se vale ajustar o nomic-embed-text no Mac, e com quantos pares.

**Custo estimado da rodada 9 (antes do congelamento):** cerca de 1.540 gerações no Mac, incluindo as 200 dos controles K4 e K5. Pelo tempo do piloto (18,4 s por resposta), são cerca de 8 horas, uma noite. O juiz recebe cerca de 1.100 itens. A geração real levou cerca de 4 horas e meia.

**Pontos pedidos à revisão da rodada 9** (respondidos na seção "Revisão do Astra e congelamento"):

1. Tamanhos das amostras e margem de −0,10 em P2.
2. Uso da resposta aceita como referência.
3. Escolha do juiz e dos controles, em especial se o K3 basta para mostrar que o juiz enxerga qualidade de solução.
4. Se a subamostra C0 deve ser maior.
