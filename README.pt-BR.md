# Problem Identity Registry

*Registro de pesquisa sobre dar a problemas recorrentes uma identidade compartilhada e verificável, para que pessoas e sistemas de IA reaproveitem soluções conhecidas em vez de resolver de novo os mesmos problemas.*

**Situação:** pesquisa em andamento · versão 0.1.0 · 29 de setembro de 2026
**Autor:** Alexandre Cardoso Rego (o projeto nasceu com o nome *Grande Cérebro*)
**English:** [README.md](README.md)

---

## A ideia

Todos os dias, pessoas e sistemas de IA resolvem problemas que já foram resolvidos em outro lugar. As soluções ficam espalhadas em fóruns, chamados de suporte e conversas privadas, e cada caso novo começa quase do zero.

A proposta é que problemas recorrentes tenham uma **identidade própria**, construída a partir de confirmações do tipo "este problema é o mesmo que aquele". Essa identidade ficaria num **registro compartilhado e auditável**, usado por várias aplicações. É o que o CID faz para doenças ou o CVE para falhas de segurança, aplicado a problemas técnicos do dia a dia. O registro guarda quem confirmou cada ligação, com que evidência, e permite contestá-la.

A proposta completa, com o que é hipótese e o que é evidência, está em [docs/framework.pt-BR.md](docs/framework.pt-BR.md).

## O que foi demonstrado até aqui

Esta é a única afirmação que este repositório apresenta como confirmada, na forma que consideramos defensável:

> Em perguntas novas do AskUbuntu (janeiro de 2020 a março de 2024, nunca usadas na fase exploratória), aproveitar relações de duplicata registradas anteriormente aumentou a recuperação de discussões da família marcada entre cinco sugestões. A combinação intercalada passou de 1,61% para 2,57% de todas as perguntas novas (+59% relativo; IC 95% do ganho relativo de +54% a +65%), mantendo a primeira sugestão idêntica à da busca semântica comum. **Não** medimos se os problemas foram de fato resolvidos, nem economia de trabalho.

| Método (dados da confirmação, 96.333 perguntas novas) | Família marcada entre as 5 | Ganho relativo sobre a busca comum (IC 95%) |
|---|---|---|
| M0: busca semântica comum (nomic-embed-text) | 1,61% | — |
| M1: busca comum + relações confirmadas, sem termo de popularidade | 2,28% | +41,4% (+36,7% a +45,9%) |
| H1: M0 em primeiro, alternando com o M1 | 2,12% | +31,3% (+27,6% a +35,0%) |
| **H: M0 em primeiro, alternando com o M2** | **2,57%** | **+59,3% (+54,2% a +65,0%)** |
| M2: relações confirmadas + termo global de popularidade | 2,84% | +76,0% (+69,0% a +83,5%) |

- **Teto.** Só 6,21% das perguntas novas tinham uma duplicata marcada anterior, e nenhum método pode passar disso. As duplicatas marcadas pelos usuários são incompletas, então todos os números são limites inferiores de "existe uma discussão anterior relevante".
- **O que é o H.**
  - O H tira a primeira sugestão da busca comum e depois alterna o M2 e o M0 nas posições restantes.
  - O M2 acrescenta às relações confirmadas um termo global de popularidade (o número de ligações confirmadas de uma pergunta).
  - Esse termo tem dois gumes:
    - Depois da primeira posição, ele aumenta a recuperação: sem ele (H1, reportado de forma descritiva), o ganho é de +31% em vez de +59%. A nossa leitura do diagnóstico exploratório é que ele ajuda a trazer para a lista os guias de referência da família.
    - Usado sozinho, o M2 teve a primeira sugestão pior que a da busca comum em todas as comparações julgadas. A diferença foi estatisticamente clara na rodada exploratória 8; o intervalo do primeiro juiz comparativo encostou no zero.
  - O H mantém a primeira sugestão da busca comum por construção.
- **Métodos congelados antes de rodar.** Dados, versões dos textos, critérios e métodos foram registrados antes da confirmação. Os textos foram usados nas versões de época: as perguntas novas como foram escritas originalmente, e as anteriores como estavam em 1º de janeiro de 2020. Nenhuma edição posterior, como uma solução acrescentada ou um aviso de duplicata, pôde vazar para o teste.

## O que não funcionou, ou ainda não está resolvido

Resultados negativos e inconclusivos fazem parte do registro:

- **Guardar frases idênticas não ajudou.** Nas primeiras rodadas, com o Schema-Guided Dialogue, uma memória de interpretações validadas não acrescentou nada a um modelo pequeno já treinado no domínio: concordou com ele em 98% das vezes. Uma memória compartilhada de valores validados ajudou pouco e não atingiu o limite pré-registrado.
- **A busca comum raramente encontra a duplicata marcada anterior.** No AskUbuntu, TF-IDF e embeddings a encontraram em só 0,8% e 1,2% das perguntas novas, contra um teto de 7,2%.
- **Um "ganho de 4×" exploratório era mais ou menos metade artefato da medida.** Os moderadores tendem a marcar o guia de referência como duplicata, e a busca comum muitas vezes achava perguntas irmãs igualmente próximas, só que sem marcação. Contando a família confirmada inteira, o ganho aparente caiu mais ou menos à metade. A comparação da tabela acima usa essa medida por família.
- **Um peso global de popularidade prejudica a primeira sugestão.** No diagnóstico exploratório, a maior parte das primeiras sugestões pioradas (56 de 67) veio desse termo, que puxa guias famosos para perguntas de outros assuntos. O mesmo termo respondeu por 44% do ganho de família. O peso de uma ligação deveria depender do contexto, e não da fama global; isso é uma proposta, ainda não testada.
- **A rede pode escolher sozinha a primeira sugestão? Não resolvido.**
  - Na confirmação, o juiz pré-registrado (um modelo local gemma4 com prompt fixo) foi reprovado nos controles: reconheceu só 27% das duplicatas verdadeiras. Por isso, o resultado oficial da confirmação é **INCONCLUSIVO**.
  - Numa etapa complementar pré-registrada, um segundo juiz às cegas (Claude, com a chave guardada na máquina do autor) passou no mesmo tipo de controle. Ele encontrou M1 − M0 = −1,9 ponto (IC 95% de −4,8 a +0,7) na primeira sugestão.
  - Esse intervalo é compatível tanto com uma perda relevante quanto com uma diferença desprezível. Ainda não há evidência suficiente para deixar a rede escolher a primeira sugestão, então manter a busca comum em primeiro é a escolha prudente.
- **Efeito de rede: só um sinal moderado.**
  - Numa simulação que dividiu uma comunidade em dez "aplicações", as confirmações valeram proporcionalmente mais com mais participantes: o ganho relativo subiu de +3% com uma aplicação para +31% com dez.
  - Parte disso é esperada pela própria construção, porque uma ligação só existe quando as duas perguntas estão na memória.
  - O ganho absoluto de cada participante novo diminuiu.

## O que continua em aberto

- Se as discussões encontradas **resolvem** de fato o problema novo, e quanto **trabalho ou computação** o reaproveitamento economizaria.
- Se o efeito se mantém **entre aplicações e domínios diferentes**, além de uma única comunidade dividida ao acaso.
- Se uma **IA curadora** consegue criar ligações confiáveis. Um juiz que passa em controles fáceis, que rejeitam pares aleatórios, ainda não está validado para os casos difíceis: problemas muito parecidos que pedem soluções diferentes. É a hipótese do autor *"gerar uma vez, validar muitas, reaproveitar sempre"*, descrita no framework.
- Se **pesos que dependem do contexto** conseguem manter o benefício do termo de popularidade sem o prejuízo.
- **Governança:** confirmações falsas ou maliciosas, privacidade dos problemas relatados e incentivo para contribuir.

## Como a pesquisa foi conduzida

- **Protocolo datado.** Antes de cada rodada, a pergunta, os dados e os métodos foram escritos num protocolo datado. As rodadas que decidiam algo tiveram os critérios de sucesso fixados antes, e eles nunca mudaram depois de ver resultados. Quando um resultado ficou abaixo do limite, como por 0,16 ponto na rodada 7, ele foi registrado como não atingido. Algumas etapas foram declaradamente exploratórias e não tinham critério; o registro dos experimentos diz quais.
  - O protocolo é um documento vivo, com datas no nível do dia. Ele não teve carimbo de tempo externo antes desta publicação, que é o seu primeiro registro público datado.
- **Exploração e confirmação separadas.** Todo ajuste foi feito nos dados exploratórios (AskUbuntu de Lei et al., uma cópia mais antiga do site). A confirmação usou perguntas de 2020 a 2024 do dump do Stack Exchange de abril de 2024, nunca tocadas, com tudo congelado.
- **Julgamento às cegas, inclusive as falhas.**
  - Dois testes cegos foram comprometidos porque a chave chegou ao avaliador antes da rotulagem. Os dois estão registrados como comprometidos e não foram usados.
  - O procedimento mudou: a chave nunca sai da máquina do autor, e um script local devolve só números agregados.
  - Na etapa complementar, os rótulos vieram de subagentes do Claude que receberam só a rubrica e os itens. O assistente que coordenava, e que conhecia as hipóteses e o resultado agregado do primeiro juiz, apenas juntou os lotes.
- **Correções como errata.** Depois de revisão externa, interpretações que foram além dos dados foram corrigidas em erratas datadas no fim do protocolo, sem apagar o texto anterior. Isso vale tanto para frases do protocolo quanto para frases da conversa que acompanhou o trabalho.

O resumo em inglês de todas as rodadas está em [docs/experiment-log.md](docs/experiment-log.md). O protocolo original datado, em português, está em [docs/protocolo-original.pt-BR.md](docs/protocolo-original.pt-BR.md); a última seção dele lista as poucas mudanças feitas para a publicação.

## Organização do repositório

```
README.md, README.pt-BR.md       esta visão geral
docs/framework.md (+ .pt-BR)     a proposta: identidade de problemas, confirmações, IA curadora, riscos
docs/experiment-log.md           resumo em inglês de cada rodada, com critérios e resultados
docs/protocolo-original.pt-BR.md protocolo original datado (fonte de referência)
code/01-sgd-rounds/              rodadas 1 a 4 (Schema-Guided Dialogue)
code/02-askubuntu-exploratory/   rodadas 5 a 8, diagnósticos e curvas de rede (AskUbuntu, Lei et al.)
code/03-confirmation/            confirmação independente (AskUbuntu 2020–2024) e segundo juiz às cegas
results/                         arquivos de resultado de cada etapa
```

## Como reproduzir

- **Requisitos:** Python 3.10+ com `numpy`, `scipy`, `scikit-learn` e, opcionalmente, `py7zr`; veja [code/README.md](code/README.md).
- **Onde cada etapa rodou:**
  - As rodadas 1 a 5 (modelos scikit-learn pequenos, TF-IDF e os vetores de palavras pré-treinados do conjunto) rodaram no ambiente de nuvem do assistente.
  - Da rodada 6 em diante, os embeddings e os juízes LLM via [Ollama](https://ollama.com) (`nomic-embed-text` para os embeddings, `gemma4` como juiz) rodaram no Mac do autor. O arquivo de resultado da confirmação registra os digests exatos dos modelos e a versão do Ollama.
  - A rotulagem do segundo juiz, na etapa complementar, foi feita por subagentes do Claude no ambiente do assistente, com a chave guardada na máquina do autor.
- **Tempo:** a confirmação levou cerca de 94 minutos no total para 414.451 perguntas. A estimativa do próprio terminal para a etapa de embeddings foi de cerca de uma hora desse total.
- **Dados da confirmação:** `askubuntu.com.7z`, do dump do Stack Exchange de 2 de abril de 2024, no [Internet Archive](https://archive.org/details/stackexchange).
- **Comandos:** `python3 gc_conf.py --judge gemma4:latest`, depois `python3 gc_conf_juiz2.py gerar` / `comparar juiz2_rotulos.json`.
- **Arquivos com texto de terceiros omitidos:** os arquivos de itens do julgamento às cegas, o arquivo de exemplos e os campos de exemplos de quatro arquivos de resultado não estão incluídos, porque contêm trechos de posts do askubuntu.com. Os scripts os produzem a partir dos dados públicos, desde que com os mesmos digests de modelo e os caches salvos localmente. Não há garantia de regeneração idêntica bit a bit em outra máquina. Os SHA-256 deles estão em [results/README.md](results/README.md), e o autor guarda os originais para conferência sob pedido.

## Dados e licenças

- **Código:** licença MIT ([LICENSE](LICENSE)).
- **Documentação e arquivos de resultado:** CC BY 4.0 ([LICENSE-docs.md](LICENSE-docs.md)). O texto de terceiros do askubuntu.com foi removido dos arquivos publicados.
- **Conjuntos de dados:** nenhum é redistribuído aqui.
  - Schema-Guided Dialogue (Rastogi et al., 2020).
  - Conjunto de perguntas duplicadas do AskUbuntu (Lei et al., NAACL 2016).
  - Dump do Stack Exchange de 02/04/2024.

## Autoria e assistência de IA

- **Autor:** a ideia, a direção e as decisões deste projeto são de Alexandre Cardoso Rego.
- **Claude (Anthropic):** o desenho dos experimentos, o código, as análises e a documentação foram desenvolvidos com o Claude, que atuou como assistente de pesquisa.
- **ChatGPT (OpenAI):** o autor trouxe revisões críticas do ChatGPT. Várias mudaram o protocolo antes das execuções e corrigiram interpretações depois delas.
- **Juízes:** o modelo local gemma4 (na máquina do autor) e, na etapa complementar, subagentes do Claude que receberam apenas a rubrica de julgamento e os itens.
- **Revisão separada:** antes da publicação, um agente Claude separado (da mesma família de modelos), que não escreveu a documentação, conferiu a documentação contra os arquivos de resultado e o protocolo. Ele revisou a documentação, não o código.

## Como citar

Veja [CITATION.cff](CITATION.cff). Um DOI será acrescentado depois da primeira versão arquivada no Zenodo.
