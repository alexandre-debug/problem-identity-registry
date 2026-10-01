# Problem Identity Registry

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23037099.svg)](https://doi.org/10.5281/zenodo.23037099)

*Registro de pesquisa sobre dar a problemas recorrentes uma identidade compartilhada e verificável, para que pessoas e sistemas de IA reaproveitem soluções conhecidas em vez de resolver de novo os mesmos problemas.*

**Situação:** pesquisa em andamento · versão 0.2.2 · 1º de outubro de 2026 · [mudanças](CHANGELOG.md)
**Autor:** Alexandre Cardoso Rego (o projeto nasceu com o nome *Grande Cérebro*)
**English:** [README.md](README.md)

---

## A ideia

Todos os dias, pessoas e sistemas de IA resolvem problemas que já foram resolvidos em outro lugar. As soluções ficam espalhadas em fóruns, chamados de suporte e conversas privadas, e cada caso novo começa quase do zero.

A proposta é que problemas recorrentes tenham uma **identidade própria**, construída a partir de confirmações do tipo "este problema é o mesmo que aquele". Essa identidade ficaria num **registro compartilhado e auditável**, usado por várias aplicações. É o que o CID faz para doenças ou o CVE para falhas de segurança, aplicado a problemas técnicos do dia a dia. O registro guarda quem confirmou cada ligação, com que evidência, e permite contestá-la.

A proposta completa, com o que é hipótese e o que é evidência, está em [docs/framework.pt-BR.md](docs/framework.pt-BR.md).

## O que foi demonstrado até aqui

Este é o principal resultado confirmado de recuperação, na forma que consideramos defensável:

> Em perguntas novas do AskUbuntu (janeiro de 2020 a março de 2024, nunca usadas na fase exploratória), aproveitar relações de duplicata registradas anteriormente aumentou a recuperação de discussões da família marcada entre cinco sugestões. A combinação intercalada passou de 1,61% para 2,57% de todas as perguntas novas (+59% relativo; IC 95% do ganho relativo de +54% a +65%), mantendo a primeira sugestão idêntica à da busca semântica comum. **Não** medimos se os problemas foram de fato resolvidos, nem economia de trabalho.

| Método (dados da confirmação, 96.333 perguntas novas) | Família marcada entre as 5 | Ganho relativo sobre a busca comum (IC 95%) |
|---|---|---|
| M0: busca semântica comum (nomic-embed-text) | 1,61% | — |
| M1: busca comum + relações confirmadas, sem termo de popularidade | 2,28% | +41,4% (+36,7% a +45,9%) |
| H1: M0 em primeiro, alternando com o M1 | 2,12% | +31,3% (+27,6% a +35,0%) |
| **H: M0 em primeiro, alternando com o M2** | **2,57%** | **+59,3% (+54,2% a +65,0%)** |
| M2: relações confirmadas + termo global de popularidade | 2,84% | +76,0% (+69,0% a +83,5%) |

- **Teto desta avaliação.** Só 6,21% das perguntas novas tinham uma duplicata marcada anterior, então, nesta avaliação baseada nas marcações disponíveis, nenhum método pode passar de 6,21%. É um limite da medida, não da utilidade real do sistema. As duplicatas marcadas pelos usuários são incompletas, então todos os números são limites inferiores de "existe uma discussão anterior relevante".
- **Discussão não é solução.** Uma discussão da família marcada não é automaticamente uma solução que se aplica à pergunta nova; isso não foi medido.
- **O que é o H.**
  - O H tira a primeira sugestão da busca comum e depois alterna o M2 e o M0 nas posições restantes.
  - O M2 acrescenta às relações confirmadas um termo global de popularidade (o número de ligações confirmadas de uma pergunta).
  - Esse termo tem dois gumes:
    - Depois da primeira posição, ele aumenta a recuperação: sem ele (H1, reportado de forma descritiva), o ganho é de +31% em vez de +59%. A nossa leitura do diagnóstico exploratório é que ele ajuda a trazer para a lista os guias de referência da família.
    - Usado sozinho, o M2 teve a primeira sugestão pior que a da busca comum em todas as comparações julgadas. A diferença foi estatisticamente clara na rodada exploratória 8; o intervalo do primeiro juiz comparativo encostou no zero.
  - O H mantém a primeira sugestão da busca comum por construção.
- **Métodos congelados antes de rodar.** Dados, versões dos textos, critérios e métodos foram registrados antes da confirmação. Os textos foram usados nas versões de época: as perguntas novas como foram escritas originalmente, e as anteriores como estavam em 1º de janeiro de 2020. Nenhuma edição posterior, como uma solução acrescentada ou um aviso de duplicata, pôde vazar para o teste.

### Melhora a resposta final? (rodadas 9 a 11)

A recuperação é um meio; o que importa é a resposta. Em duas rodadas pré-registradas, a 9 e a 11, um modelo de linguagem local (gemma4) respondeu a perguntas novas usando cinco discussões recuperadas como contexto. Juízes às cegas compararam as respostas com a ajuda da resposta aceita pelo autor da pergunta. A rodada 10, entre elas, testou um portão e a recuperação no Super User, sem gerar respostas. Os juízes eram subagentes novos do Claude, que viram só uma rubrica e os itens, e a chave ficou na máquina do autor. Os juízes passaram em todos os controles nas duas rodadas julgadas. São preferências de um juiz, não problemas verificados como resolvidos.

| Rodada, site | Comparação | Preferência líquida Δ [IC 95%] | Resultado pré-registrado |
|---|---|---|---|
| 9, AskUbuntu | H contra a busca comum, quando o H traz a família marcada que a busca comum perdeu (124 perguntas) | +0,153 [+0,024; +0,282] | passou |
| 9, AskUbuntu | H contra a busca comum, perguntas sem duplicata marcada, contextos diferentes (400) | −0,070 [−0,138; 0,000] | não passou (margem −0,10) |
| 11, Super User | H1 contra H, perguntas sem duplicata marcada em que os dois diferem (838) | +0,060 [+0,013; +0,109] | passou |
| 11, Super User | H1 contra a busca comum, população das perguntas elegíveis | +0,006 [−0,016; +0,029] | sem perda além de 3 pontos: passou; superioridade: não demonstrada |

- **O que isso significa.**
  - Na rodada 9 (AskUbuntu), quando a rede trouxe a família marcada que a busca comum perdeu, os juízes preferiram as respostas dela.
  - Na rodada 11 (Super User), nas perguntas sem duplicata marcada, retirar o termo de popularidade (H1) melhorou as respostas em relação ao H, o mesmo desenho com o termo. É o primeiro teste direto do termo nas respostas.
  - Sem o termo, a rede manteve a qualidade das respostas a até 3 pontos da busca comum nas perguntas elegíveis do Super User.
  - Um benefício sobre a busca comum, em qualidade, trabalho economizado ou custo total, **não** foi demonstrado.
- **Errata.** O script da rodada 11 calculava o primeiro critério como H − H1, com o rótulo H1 − H. Depois do resultado, o sinal foi corrigido conforme o texto pré-registrado, e uma revisão externa recalculou os agregados. As duas saídas estão publicadas.
- **Desvios.** Na rodada 9, o modelo local não conseguiu inserir erros aproveitáveis nos pares de controle de erro decisivo (K4); na rodada 11, não conseguiu escrever pares equivalentes aproveitáveis em número suficiente (K5). Antes de qualquer julgamento, agentes Claude separados cobriram essas faltas (desvios 1 e 2), e outros agentes revisaram os pares. Na rodada 11, os erros do K4 foram escritos por um agente, conforme o desenho congelado. Os juízes são da mesma família de modelos.

## O que não funcionou, ou ainda não está resolvido

Resultados negativos e inconclusivos fazem parte do registro:

- **Guardar frases idênticas não ajudou.** Nas primeiras rodadas, com o Schema-Guided Dialogue, uma memória de interpretações validadas não acrescentou nada a um modelo pequeno já treinado no domínio: concordou com ele em 98% das vezes. Uma memória compartilhada de valores validados ajudou pouco e não atingiu o limite pré-registrado.
- **A busca comum raramente encontra a duplicata marcada anterior.** No AskUbuntu, TF-IDF e embeddings a encontraram em só 0,8% e 1,2% das perguntas novas, contra um teto de 7,2%.
- **Um "ganho de 4×" exploratório era mais ou menos metade artefato da medida.** Os moderadores tendem a marcar o guia de referência como duplicata, e a busca comum muitas vezes achava perguntas irmãs igualmente próximas, só que sem marcação. Contando a família confirmada inteira, o ganho aparente caiu mais ou menos à metade. A comparação da tabela acima usa essa medida por família.
- **Um peso global de popularidade prejudica a primeira sugestão.** No diagnóstico exploratório, a maior parte das primeiras sugestões pioradas (56 de 67) veio desse termo, que puxa guias famosos para perguntas de outros assuntos. O mesmo termo respondeu por 44% do ganho de família. Depois, a rodada 11 encontrou o mesmo nas respostas finais, no Super User: nas perguntas sem duplicata marcada, as respostas foram preferidas sem o termo. Um peso que dependa do contexto, e não da fama global, continua sendo uma proposta, ainda não testada.
- **A rede pode escolher sozinha a primeira sugestão? Não resolvido.**
  - Na confirmação, o juiz pré-registrado (um modelo local gemma4 com prompt fixo) foi reprovado nos controles: reconheceu só 27% das duplicatas verdadeiras. Por isso, o resultado oficial da confirmação é **INCONCLUSIVO**.
  - Numa etapa complementar pré-registrada, um segundo juiz às cegas (Claude, com a chave guardada na máquina do autor) passou no mesmo tipo de controle. Ele encontrou M1 − M0 = −1,9 ponto (IC 95% de −4,8 a +0,7) na primeira sugestão.
  - Esse intervalo é compatível tanto com uma perda relevante quanto com uma diferença desprezível. Ainda não há evidência suficiente para deixar a rede escolher a primeira sugestão, então manter a busca comum em primeiro é a escolha prudente.
- **Saber de antemão quando usar a rede: não atingido.**
  - Na rodada 9, a rede ajudou quando trouxe a família marcada e pode ter piorado um pouco a resposta nas perguntas sem duplicata marcada. Uma aplicação real não enxerga a família marcada de antemão.
  - Na rodada 10, um portão baseado em quanto o candidato da rede superava a busca comum chegou no máximo a 17,6% de ganhos entre as suas aberturas nas perguntas com duplicata marcada (metade de desenvolvimento, cobertura ≥ 2%), contra 12,5% do H1 sem portão. A exigência pré-registrada era pelo menos o dobro, 25,1%. O portão é "não calibrável" para esse sinal, essa grade e essas exigências.
- **Ganhos menores numa rede mais esparsa.** No Super User, só 1,89% das perguntas novas têm uma duplicata marcada anterior. Lá, as relações melhoraram muito menos a recuperação: M1 +15,5%, contra +41,4% no AskUbuntu. O H1 ganhou +11,6%, mas o limite inferior do IC dele (+7,9%) ficou abaixo do mínimo pré-registrado de 10%.
- **Efeito de rede: só um sinal moderado.**
  - Numa simulação que dividiu uma comunidade em dez "aplicações", as confirmações valeram proporcionalmente mais com mais participantes: o ganho relativo subiu de +3% com uma aplicação para +31% com dez.
  - Parte disso é esperada pela própria construção, porque uma ligação só existe quando as duas perguntas estão na memória.
  - O ganho absoluto de cada participante novo diminuiu.

## O que continua em aberto

- Se as ligações ainda acrescentam algo sobre uma **busca híbrida**. A rodada 12 as compara com uma fusão da busca por palavras (BM25) com um modelo de embeddings selecionado por um piloto em dados exploratórios. Ela foi congelada e publicada na versão 0.2.2 antes de rodar.
- Se a rede traz um **benefício sobre a busca comum**, e não só ausência de perda: respostas melhores, trabalho economizado ou custo total menor.
- Se o resultado da rodada 11 **se mantém no AskUbuntu** e em outros sites.
- Se as discussões encontradas **resolvem** de fato o problema novo, e quanto **trabalho ou computação** o reaproveitamento economizaria.
- Se o efeito se mantém **entre aplicações e domínios diferentes**, além de uma única comunidade dividida ao acaso.
- Se uma **IA curadora** consegue criar ligações confiáveis. Um juiz que passa em controles fáceis, que rejeitam pares aleatórios, ainda não está validado para os casos difíceis: problemas muito parecidos que pedem soluções diferentes. É a hipótese do autor *"gerar uma vez, validar muitas, reaproveitar sempre"*, descrita no framework. Um rascunho da rodada 13, já revisado externamente, a testaria com modelos locais pequenos.
- Se **pesos que dependem do contexto** conseguem manter o benefício do termo de popularidade sem o prejuízo.
- **Governança:** confirmações falsas ou maliciosas, privacidade dos problemas relatados e incentivo para contribuir.

## Como a pesquisa foi conduzida

- **Protocolo datado.** Antes de cada rodada, a pergunta, os dados e os métodos foram escritos num protocolo datado. As rodadas que decidiam algo tiveram os critérios de sucesso fixados antes, e eles nunca mudaram depois de ver resultados. Quando um resultado ficou abaixo do limite, como por 0,16 ponto na rodada 7, ele foi registrado como não atingido. Algumas etapas foram declaradamente exploratórias e não tinham critério; o registro dos experimentos diz quais.
  - O protocolo é um documento vivo, datado no nível do dia e, da rodada 9 em diante, muitas vezes no nível da hora. Ele não teve carimbo de tempo externo antes da v0.1.0 (29 de setembro de 2026), o seu primeiro registro público datado; cada versão publicada arquiva o estado dele naquela data. A continuação, com os pré-registros das rodadas 9 a 11, só é publicada na v0.2.0, depois dos resultados delas; as datas dela são o registro do próprio autor.
- **Exploração e confirmação separadas.** Todo ajuste foi feito nos dados exploratórios (AskUbuntu de Lei et al., uma cópia mais antiga do site). A confirmação usou perguntas de 2020 a 2024 do dump do Stack Exchange de abril de 2024, nunca tocadas, com tudo congelado.
- **Julgamento às cegas, inclusive as falhas.**
  - Dois testes cegos foram comprometidos porque a chave chegou ao avaliador antes da rotulagem. Os dois estão registrados como comprometidos e não foram usados.
  - O procedimento mudou: a chave nunca sai da máquina do autor, e um script local devolve só números agregados.
  - Na etapa complementar, os rótulos vieram de subagentes do Claude que receberam só a rubrica e os itens. O assistente que coordenava, e que conhecia as hipóteses e o resultado agregado do primeiro juiz, apenas juntou os lotes.
- **Correções como errata.** Depois de revisão externa, interpretações que foram além dos dados foram corrigidas em erratas datadas no fim do protocolo, sem apagar o texto anterior. Isso vale tanto para frases do protocolo quanto para frases da conversa que acompanhou o trabalho.
- **Desvios registrados, não escondidos.** Algumas mudanças foram necessárias depois que um desenho foi congelado, mas antes de qualquer resultado, como a forma de produzir os pares de controle do juiz. Cada uma foi registrada como um desvio numerado, com a decisão do autor. Cada mudança de script recebeu um novo SHA-256 e foi testada para reproduzir a saída congelada onde não deveria mudar nada.

O resumo em inglês de todas as rodadas está em [docs/experiment-log.md](docs/experiment-log.md). O protocolo original datado, em português, está em [docs/protocolo-original.pt-BR.md](docs/protocolo-original.pt-BR.md); a última seção dele lista as poucas mudanças feitas para a publicação. As rodadas 9 a 13 continuam em [docs/protocolo-continuacao.pt-BR.md](docs/protocolo-continuacao.pt-BR.md).

## Organização do repositório

```
README.md, README.pt-BR.md       esta visão geral
docs/framework.md (+ .pt-BR)     a proposta: identidade de problemas, confirmações, IA curadora, riscos
docs/experiment-log.md           resumo em inglês de cada rodada, com critérios e resultados
docs/protocolo-original.pt-BR.md protocolo original datado (fonte de referência), até a confirmação
docs/protocolo-continuacao.pt-BR.md  a continuação dele: rodadas 9 a 13
code/01-sgd-rounds/              rodadas 1 a 4 (Schema-Guided Dialogue)
code/02-askubuntu-exploratory/   rodadas 5 a 8, diagnósticos e curvas de rede (AskUbuntu, Lei et al.)
code/03-confirmation/            confirmação independente (AskUbuntu 2020–2024) e segundo juiz às cegas
code/04-answer-quality/          rodadas 9 a 11: respostas com contexto recuperado, julgamento às cegas, portão, Super User
code/05-hybrid-search/           rodada 12 (congelada, ainda não rodada): ligações sobre uma busca híbrida
results/                         arquivos de resultado de cada etapa
```

## Como reproduzir

- **Requisitos:** Python 3.10+ com `numpy`, `scipy`, `scikit-learn` e, opcionalmente, `py7zr`. As versões exatas usadas, os arquivos de requisitos fixados e o passo a passo para uma execução do zero estão em [code/ENVIRONMENT.md](code/ENVIRONMENT.md).
- **Onde cada etapa rodou:**
  - As rodadas 1 a 5 (modelos scikit-learn pequenos, TF-IDF e os vetores de palavras pré-treinados do conjunto) rodaram no ambiente de nuvem do assistente.
  - Da rodada 6 em diante, os embeddings e os juízes LLM via [Ollama](https://ollama.com) (`nomic-embed-text` para os embeddings, `gemma4` como juiz) rodaram no Mac do autor. O arquivo de resultado da confirmação registra os digests exatos dos modelos e a versão do Ollama.
  - A rotulagem do segundo juiz, na etapa complementar, foi feita por subagentes do Claude no ambiente do assistente, com a chave guardada na máquina do autor.
- **Tempo:** a confirmação levou cerca de 94 minutos no total para 414.451 perguntas. A estimativa do próprio terminal para a etapa de embeddings foi de cerca de uma hora desse total.
- **Dados da confirmação:** `askubuntu.com.7z`, do dump do Stack Exchange de 2 de abril de 2024, no [Internet Archive](https://archive.org/details/stackexchange).
- **Comandos:** `python3 gc_conf.py --judge gemma4:latest`, depois `python3 gc_conf_juiz2.py gerar` / `comparar juiz2_rotulos.json`.
- **Rodadas 9 a 11:** veja [code/04-answer-quality/README.md](code/04-answer-quality/README.md). As respostas foram geradas pelo gemma4 no Mac do autor (cerca de 4,5 horas para as 1.540 respostas da rodada 9; 2.846 prompts distintos na rodada 11), e o julgamento foi feito por subagentes do Claude, com a chave guardada na máquina do autor. Dados do Super User: `superuser.com.7z`, do mesmo dump.
- **Rodada 12:** veja [code/05-hybrid-search/README.md](code/05-hybrid-search/README.md). Congelada em 1º de outubro de 2026 e publicada antes de rodar; ainda sem resultados.
- **Arquivos com texto de terceiros omitidos:** os arquivos de itens do julgamento às cegas, as respostas do piloto, os arquivos de revisão dos pares de controle, as edições de controle escritas por agentes, o arquivo de exemplos e os campos de exemplos de quatro arquivos de resultado não estão incluídos, porque contêm trechos de posts do askubuntu.com ou do superuser.com, ou reescritas deles feitas por modelos. Com exceção dos arquivos escritos por agentes, os scripts os produzem a partir dos dados públicos, desde que com os mesmos digests de modelo e os caches salvos localmente. Não há garantia de regeneração idêntica bit a bit em outra máquina. Os SHA-256 deles estão em [results/README.md](results/README.md), e o autor guarda os originais para conferência sob pedido.

## Dados e licenças

- **Código:** licença MIT ([LICENSE](LICENSE)).
- **Documentação e arquivos de resultado:** CC BY 4.0 ([LICENSE-docs.md](LICENSE-docs.md)). O texto de terceiros do askubuntu.com e do superuser.com foi removido dos arquivos publicados.
- **Conjuntos de dados:** nenhum é redistribuído aqui.
  - Schema-Guided Dialogue (Rastogi et al., 2020).
  - Conjunto de perguntas duplicadas do AskUbuntu (Lei et al., NAACL 2016).
  - Dump do Stack Exchange de 02/04/2024 (AskUbuntu e Super User).

## Autoria e assistência de IA

- **Autor:** a ideia, a direção e as decisões deste projeto são de Alexandre Cardoso Rego.
- **Claude (Anthropic):** o desenho dos experimentos, o código, as análises e a documentação foram desenvolvidos com o Claude, que atuou como assistente de pesquisa.
- **ChatGPT (OpenAI):** o autor trouxe revisões críticas do ChatGPT. Várias mudaram o protocolo antes das execuções e corrigiram interpretações depois delas.
- **Juízes:** o modelo local gemma4 (na máquina do autor) e, na etapa complementar e nas rodadas 9 e 11, subagentes do Claude que receberam apenas a rubrica de julgamento e os itens. Quando isto foi registrado (1º de outubro de 2026), a sessão de trabalho estava configurada como `claude-opus-5-5`; a versão que serviu cada chamada de julgamento não foi exposta e não está registrada. Subagentes separados ajudam a preservar o cegamento, mas não são modelos independentes. Detalhes em [code/ENVIRONMENT.md](code/ENVIRONMENT.md).
- **Rodadas 9 a 11:** as respostas foram geradas pelo gemma4. Alguns pares de controle do juiz foram escritos e revisados por agentes Claude separados (desvios 1 e 2).
- **Revisão separada:** antes da publicação, um agente Claude separado (da mesma família de modelos), que não escreveu a documentação, conferiu a documentação contra os arquivos de resultado e o protocolo. Ele revisou a documentação, não o código. Para a versão 0.2.0, uma revisão externa (ChatGPT) recalculou os agregados da rodada 11 e conferiu a errata dela.

## Como citar

Cite o registro arquivado no Zenodo:

> Rego, A. C. (2026). *Problem Identity Registry: a research record on shared, verifiable identities for recurring problems*. Zenodo. https://doi.org/10.5281/zenodo.23037099

- O DOI acima representa todas as versões e sempre leva à mais recente.
- Para citar uma versão específica, use o DOI próprio dela, listado na página do Zenodo. Versão 0.1.0: [10.5281/zenodo.23037100](https://doi.org/10.5281/zenodo.23037100).
- As mesmas informações estão no [CITATION.cff](CITATION.cff), que o GitHub mostra em "Cite this repository".
