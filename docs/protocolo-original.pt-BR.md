# Grande Cérebro — Protocolo do Experimento 1

> Registro original do experimento, em português, como foi mantido durante a pesquisa (documento vivo, com seções datadas acrescentadas ao longo do trabalho), com as poucas alterações listadas nas Notas de publicação ao final. É a fonte de referência; o resumo em inglês está em [experiment-log.md](experiment-log.md). Correções de interpretação foram registradas como errata ao final, sem apagar o texto anterior.


Autor: Alexandre Cardoso Rego · iniciado em 28/09/2026 · exportado em 29/09/2026 (revisão 75)

## Objetivo e hipóteses

O experimento decide se reaproveitar interpretações validadas entre aplicações reduz o trabalho total sem perder qualidade. É um teste de viabilidade técnica, feito de forma reprodutível para poder virar artigo.

**Pergunta central:** quando a aplicação B recebe um pedido, aproveitar uma interpretação validada na aplicação A preserva os detalhes necessários e reduz o custo total, comparado a B trabalhar sozinha?

| Hipótese | Afirmação testada | Comparação |
| --- | --- | --- |
| H1 Reconhecimento | O middleware interpreta intenções suportadas, sinaliza as não suportadas pelo serviço e recusa as fora do catálogo, sem recusar indevidamente casos conhecidos | V0, V2, V3 |
| H2 Preservação | A representação estruturada mantém os parâmetros e a decisão de agir necessários para concluir a tarefa | V0, V2, V3 contra V1 |
| H3 Processamento menor | Normalizador, mapeamentos e caminho sem LLM final reduzem o custo sem memória | V0 contra V1 |
| H4 Memória | A memória local acrescenta economia ao processamento menor | V2 contra V0 |
| H5 Compartilhamento | A memória compartilhada acrescenta economia à local, nos problemas compartilhados e no fluxo completo | V3 contra V2 |

A economia será separada por origem: repetições exatas (resolvidas por hash) e paráfrases inéditas (resolvidas pelo normalizador). Assim se vê se o ganho vem do banco compartilhado, do normalizador ou dos dois.

## Premissas provisórias

As premissas abaixo permitem escrever o protocolo agora. Modelo, orçamento e prazo precisam estar fechados antes da etapa que depende deles.

| Decisão | Premissa | Quando precisa estar fechada |
| --- | --- | --- |
| Idioma | Inglês; português como teste posterior de transferência | Já fechada |
| Modelo (LLM) | Um único modelo fixo em todas as condições, com versão registrada | Antes da condição V1 |
| Orçamento | Piloto pequeno para medir custo por caso; teto definido antes de ampliar | Depois do piloto |
| Objetivo | Decidir viabilidade técnica, com reprodutibilidade de artigo | Já fechada |
| Prazo | Organizado por entregas verificáveis, ajustado à disponibilidade | Antes da execução |

## Dados

A base é um recorte do Schema-Guided Dialogue (SGD): um domínio com pelo menos dois serviços comparáveis, tratados como aplicação A e aplicação B. O SGD anota intenção, parâmetros (slots) e a chamada de serviço de cada diálogo, o que permite medir reconhecimento, preservação e resultado.

**Unidade de avaliação:** um turno do usuário, com o contexto do diálogo até ali. O alvo é o estado anotado (intenção e parâmetros) e, quando houver, a chamada de serviço seguinte.

**Domínio:** Events, com Events\_1 como aplicação A (289 diálogos) e Events\_2 como aplicação B (572 diálogos). As duas compartilham FindEvents e BuyEventTickets; GetEventDates existe só em B, o que permite testar intenções conhecidas mas não suportadas em A. Os esquemas têm só 4 de 9 parâmetros com o mesmo nome, e `category` significa tipo de evento em A e subcategoria em B, um caso real de nome igual com significado diferente.

O recorte precisa conter quatro tipos de caso, marcados para análise separada:

| Tipo de caso | Por que importa |
| --- | --- |
| Problemas compartilhados, descritos de formas diferentes em A e B | É onde o compartilhamento pode ajudar |
| Problemas exclusivos de cada aplicação | Testa se o sistema recusa o que não conhece |
| Frases parecidas cujo parâmetro ou procedimento muda entre A e B | Testa contraexemplos e separação de padrões |
| Repetições exatas e paráfrases inéditas | Separa o ganho do hash do ganho do normalizador |

**Divisão:** um conjunto de desenvolvimento para ajustar limiares, um fluxo de memória para o aprendizado progressivo e um conjunto de teste final que não participa de nenhum ajuste.

Banking77 e CLINC150 ficam para uma etapa posterior, como avaliações complementares de reconhecimento e rejeição.

## Condições comparadas

As quatro condições resolvem os mesmos casos de teste, com o mesmo LLM, o mesmo normalizador e os mesmos mapeamentos de esquema. Cada comparação isola uma fonte de ganho: V0 contra V1 mede o processamento menor, V2 contra V0 a memória e V3 contra V2 o compartilhamento.

| Condição | Como funciona | O que isola |
| --- | --- | --- |
| V1 Texto original | O turno e o contexto vão direto ao LLM | Linha de base de qualidade e custo |
| V0 Sem memória | Normalizador, mapeamentos, caminho sem LLM final e fallback, sem nenhum vínculo de episódios anteriores | Ganho do processamento menor |
| V2 Memória local | V0 mais vínculos aprendidos só na própria aplicação | Ganho da memória |
| V3 Memória compartilhada | V0 mais vínculos aprendidos em A e em B | Ganho do compartilhamento |

**Como a memória ajuda uma frase inédita.** O normalizador tem pesos fixos nesta fase. A memória atua por dois mecanismos, ambos com custo contabilizado:

| Mecanismo | O que faz | Custo contabilizado |
| --- | --- | --- |
| Consulta exata | Hash do turno normalizado com o contexto relevante; um acerto devolve a interpretação registrada | Consulta à memória |
| Recuperação de exemplos | Os vínculos validados mais parecidos entram como exemplos no normalizador | Comparação vetorial sobre a memória e tokens dos exemplos |

A hipótese, portanto, é reduzir interpretações repetidas, não eliminar toda comparação por similaridade. Atualizar os pesos do normalizador com os vínculos fica para uma fase posterior.

**Caminho sem LLM final.** A chamada de serviço é montada pelo mapeamento, sem o LLM principal, quando quatro condições valem: a intenção é suportada, os parâmetros obrigatórios estão completos, a incerteza está abaixo do limiar e o usuário indicou que quer executar agora, sem confirmação pendente nem restrição explícita ("ainda não reserve"). Nos demais casos, o LLM recebe apenas os campos necessários à tarefa, mais o texto original quando houver dúvida. Se o normalizador for um modelo generativo pequeno, sua inferência continua contada no custo. Todas as chamadas são simuladas; nenhum serviço real é executado.

## Representação de saída

A representação usa conceitos comuns ao domínio, independentes do esquema de cada serviço. Um mapeamento explícito converte esses conceitos para os campos de A ou de B.

Registro de avaliação de um caso:

```json
{
  "intent": "restaurant.reserve",
  "slots": {
    "venue_name": "Sakura",
    "date": "2019-03-08",
    "time": "19:00",
    "party_size": 4
  },
  "service_specific": {},
  "action": {
    "decision": "wait",
    "confirmation_pending": false,
    "execution_blocked": true
  },
  "support": "supported",
  "hypotheses": [],
  "uncertainty": { "identity": 0.04, "applicability": 0.10 },
  "source": "hash",
  "outcome": "confirmed"
}
```

- Os conceitos comuns e os mapeamentos para cada serviço são construídos a partir dos esquemas do SGD e do conjunto de desenvolvimento, nunca do teste.
- Campos que só existem num serviço ficam em `service_specific`.
- `action` registra a decisão de agir: executar ou aguardar, confirmação pendente e bloqueio explícito do usuário ("ainda não reserve"). É inferido só do contexto disponível, sem acesso ao gabarito.
- `support` distingue intenção suportada, conhecida mas não suportada por este serviço, e fora do catálogo.
- `source` registra a origem da interpretação: `hash`, `retrieval` (normalizador com exemplos) ou `llm`.
- `outcome` admite quatro estados: confirmado, falhou, parcial ou desconhecido.
- Ao LLM vão apenas `intent`, `slots`, `service_specific`, `action` e, quando houver dúvida, o texto original. `action` acompanha tanto o caminho sem LLM final quanto o encaminhamento ao LLM. Os demais campos ficam só no registro, para não gastar tokens.
- A incerteza de resultado não é estimada nesta fase, porque o gabarito define o resultado. Por isso ela não entra na calibração.

**Tarefas avaliadas.** Em cada turno elegível, avaliam-se três coisas:

| Decisão | Onde é avaliada | Erro contabilizado |
| --- | --- | --- |
| Intenção e estado | Todos os turnos elegíveis | Intenção ou parâmetros incorretos |
| Chamar ou aguardar | Todos os turnos elegíveis | Chamada indevida ou chamada necessária omitida |
| Qual chamada produzir | Turnos cujo turno seguinte do sistema tem chamada anotada | Método ou argumentos incorretos |

Isso mede correspondência com as chamadas anotadas, não execução nem resolução real do problema.

## Protocolo de memória e divisão dos dados

Nenhum caso é avaliado com uma memória que já contém sua própria resposta.

&#91;embedded content: fluxo de aprendizado progressivo · avaliação antes da memória\]

O resultado de cada pedido é registrado antes de sua interpretação entrar na memória; falhas viram contraexemplos em vez de serem descartadas.

1. Todos os turnos de um diálogo ficam na mesma divisão, na ordem original.
2. Limiares e mapeamentos de esquema são ajustados apenas no conjunto de desenvolvimento.
3. O fluxo de memória é processado em ordem fixa, com semente registrada, intercalando A e B por diálogos inteiros, da mesma forma em V2 e V3.
4. Na simulação, a validação usa a anotação do SGD como gabarito. O custo de uma validação real fica registrado como não demonstrado.
5. Em V2, a memória recebe só vínculos da própria aplicação. Em V3, recebe vínculos de A e de B.
6. Algumas intenções ficam fora da memória e de qualquer ajuste, para testar casos fora do catálogo.
7. O teste final usa a memória congelada ao fim do fluxo e nunca a alimenta.
8. Repetições exatas e paráfrases inéditas são contadas separadamente no fluxo e no teste.

## Métricas

Cada hipótese tem suas próprias métricas; acertar a intenção sozinho não conta como sucesso.

| Etapa | Métrica | Hipótese |
| --- | --- | --- |
| Reconhecimento | Acurácia de intenção nos casos conhecidos e suportados | H1 |
| Reconhecimento | Identificação correta de intenções conhecidas mas não suportadas pelo serviço | H1 |
| Reconhecimento | Recusa correta de intenções fora do catálogo | H1 |
| Reconhecimento | Taxa de recusa indevida de casos conhecidos | H1 |
| Preservação | F1 dos parâmetros e taxa de estado completo correto | H2 |
| Preservação | Chamadas indevidas e chamadas omitidas, em todos os turnos elegíveis | H2 |
| Qualidade final | Acerto da ação por turno (Q), com chamadas indevidas e omitidas sempre reportadas à parte | H2 a H5 |
| Custo | Custo total por caso, em moeda (fórmula abaixo) | H3 a H5 |
| Custo | Tokens e chamadas do LLM e tempo total (mediana e p95), como detalhamento | H3 a H5 |
| Origem da interpretação | Fração de casos por origem e pelo caminho sem LLM final, com a qualidade de cada fração | H3 a H5 |
| Calibração | Erro de calibração das incertezas de identidade e aplicabilidade | H1, H2 |

O custo total por caso soma todos os componentes do percurso:

```latex
C_{\text{total}} = C_{\text{LLM}} + C_{\text{normalizador}} + C_{\text{memória}} + C_{\text{comunicação}} + C_{\text{manutenção alocada}}
```

Os preços unitários de cada termo são fixados no protocolo, com data. O custo de construir a memória e o custo de operar com ela pronta são reportados separadamente.

As diferenças entre condições usam bootstrap pareado por diálogo: os mesmos diálogos são reamostrados nas quatro condições, com intervalo de confiança de 95%. Energia fica fora desta fase.

## Critérios de sucesso e fracasso

Os limites abaixo são uma proposta inicial e precisam ser confirmados antes de rodar o conjunto de teste. Depois disso, não mudam.

Cada regra usa o intervalo de confiança de 95% do bootstrap pareado. Q é o acerto da ação por turno elegível: aguardar quando não há chamada anotada, e produzir método e argumentos corretos quando há. ΔQ é a diferença de Q em pontos percentuais; as razões de custo usam o custo total em moeda.

| Hipótese | Sustentada se | Rejeitada se |
| --- | --- | --- |
| H1 | Acurácia ≥ 90% nos casos suportados, recusa correta ≥ 80% fora do catálogo e recusa indevida ≤ 5% | Algum limite violado com o intervalo inteiro do lado errado |
| H2 | Para V0, V2 e V3, limite inferior de ΔQ contra V1 acima de −2 pontos | Para alguma delas, limite superior de ΔQ contra V1 abaixo de −2 pontos |
| H3 | H2 sustentada para V0 e limite superior da razão de custo V0/V1 abaixo de 70% | H2 rejeitada para V0, ou limite inferior da razão V0/V1 acima de 85% |
| H4 | Limite superior da razão V2/V0 abaixo de 90% e limite inferior de ΔQ (V2 − V0) acima de −1 ponto | Limite inferior da razão V2/V0 acima de 100%, ou limite superior de ΔQ abaixo de −1 ponto |
| H5 | Nos problemas compartilhados, limite superior da razão V3/V2 abaixo de 90%; no fluxo completo, abaixo de 100%; e limite inferior de ΔQ (V3 − V2) acima de −1 ponto nos dois recortes | Limite inferior da razão V3/V2 no fluxo completo acima de 100%, ou limite superior de ΔQ abaixo de −1 ponto em algum recorte |

Quando o intervalo atravessa um limite, o resultado é inconclusivo, não um fracasso. Ausência de diferença significativa não demonstra equivalência e pode indicar dados insuficientes. Um resultado negativo rejeita esta implementação neste cenário, não a ideia de normalização em geral.

## Limitações

Um resultado positivo mostra viabilidade técnica numa simulação controlada, não o valor do Grande Cérebro em produção.

- **Compartilhamento simulado:** serviços diferentes do mesmo dataset não equivalem a duas empresas reais, com usuários e vocabulários próprios.
- **Validação idealizada:** o gabarito do SGD substitui a validação real, que é mais lenta e ruidosa.
- **Um idioma e um modelo:** os resultados podem mudar em português ou com outro LLM.
- **Diálogos construídos:** o SGD foi produzido para pesquisa e tende a ser mais regular que conversas reais.
- **Custo não é energia:** a economia medida é de tokens, chamadas e tempo.

## Entregas e decisões pendentes

O trabalho segue em sete entregas, cada uma verificável antes da próxima.

**Decisões em aberto**

1. **Protocolo:** este documento, com os critérios confirmados.
2. **Dados:** recorte do SGD, marcação dos tipos de caso, divisão por diálogos, conceitos comuns e mapeamentos de esquema.
3. **V1:** linha de base com o LLM escolhido, incluindo o piloto de custo.
4. **V0:** normalizador, mapeamentos, caminho sem LLM final e fallback, sem memória.
5. **V2:** V0 com consulta exata, recuperação de exemplos e memória local.
6. **V3:** memória compartilhada entre A e B.
7. **Relatório:** resultados por hipótese, origem da interpretação, custos de construção e de operação, e limitações.

**Decisões em aberto**

- [ ] Escolher o LLM e registrar a versão
- [ ] Escolher o normalizador e o modelo de embeddings da recuperação de exemplos
- [ ] Domínio definido: Events (Events\_1 e Events\_2), na entrega 2
- [ ] Fixar os preços unitários da fórmula de custo
- [ ] Confirmar os limites dos critérios de sucesso e fracasso
- [ ] Definir o teto do piloto antes de rodá-lo, e o orçamento maior depois dele
- [ ] Definir o calendário das entregas

## Resultados da entrega 2

O hash tem uma troca clara entre cobertura e precisão: chaves parciais alcançam 15% a 25% dos turnos com 61% a 82% de precisão, e a chave com valores e estado anterior anotado alcança cerca de 1% dos turnos. Estes números vêm só do conjunto de desenvolvimento, com o dataset na revisão `e852981` do repositório oficial.

**Divisões.** Semente 20260928; o manifesto registra os hashes SHA-256 dos arquivos de origem e se reproduz byte a byte.

| Conjunto | Desenvolvimento | Memória | Teste |
| --- | --- | --- | --- |
| Events\_1 (A) | 43 diálogos | 159 diálogos | 87 diálogos |
| Events\_2 (B) | 86 diálogos | 315 diálogos | 171 diálogos |
| Fora do catálogo | 30 diálogos de Hotels\_1 | nenhum | 30 diálogos de RentalCars\_1 |

O fluxo de memória tem 474 diálogos, intercalando A e B proporcionalmente. Dos diálogos de teste de B, 98 usam GetEventDates e servem de sonda para intenções não suportadas em A.

**Chaves comparadas.** Todas buscam na memória construída pelo fluxo; a interpretação comparada é intenção, parâmetros alterados com valores e parâmetros solicitados.

| Chave | Composição |
| --- | --- |
| K1 Texto estrito | Frase exatamente como escrita |
| K2 Parcial normalizada | Frase sem pontuação e em minúsculas, mais os atos do sistema anterior sem valores |
| K3 Parcial estrita | Frase exata, mais os atos do sistema anterior sem valores |
| K4 Valores e estado anotado | Frase exata, atos do sistema anterior com valores e estado anterior anotado (gabarito) |

| Aplicação e condição | K1 cobertura / precisão | K2 | K3 | K4 |
| --- | --- | --- | --- | --- |
| A, V2 (303 turnos) | 16,2% / 61,2% | 14,5% / 77,3% | 9,9% / 66,7% | 1,0% / 100% (3 acertos) |
| A, V3 (303 turnos) | 24,8% / 64,0% | 22,1% / 82,1% | 16,8% / 78,4% | 1,0% / 100% (3 acertos) |
| B, V2 (825 turnos) | 22,5% / 61,8% | 16,7% / 76,1% | 13,3% / 76,4% | 1,3% / 90,9% (11 acertos) |
| B, V3 (825 turnos) | 23,8% / 63,3% | 18,3% / 76,8% | 14,3% / 78,0% | 1,3% / 90,9% (11 acertos) |

**O que os dados sustentam**

- A chave antiga (K2) era ambígua: juntava situações diferentes, como "perfeito" respondendo a ofertas de eventos distintos. Os erros medem essa perda de informação na chave, não uma falha do hash em distinguir entradas completas.
- K4 usa o estado anterior anotado, ou seja, o gabarito. É um diagnóstico com estado ideal e inclui só parte do contexto estruturado, não o histórico inteiro. Os atos do sistema também vêm da anotação; num sistema real eles seriam conhecidos, mas o estado do usuário teria de ser inferido.
- Neste recorte e nestas quatro chaves, acrescentar contexto reduziu a cobertura e aumentou a precisão observada. Os poucos acertos de K4 (3 em A, 11 em B) tornam essa precisão pouco confiável.
- Com chaves parciais, os acertos ficam quase todos em confirmações e encerramentos. Em turnos com entidades, K3 cobre cerca de 6% com precisão de 5% a 11%.
- O compartilhamento aumenta a cobertura sobretudo em A, a aplicação menor: com K2, de 14,5% para 22,1%.
- Hipótese a testar, não resultado: separar a operação reutilizável dos seus argumentos, como `aceitar(oferta_atual)`. A chave do procedimento ficaria sem os valores, mas eles continuam necessários para resolver a oferta atual e precisam ser preservados e recuperados do contexto.
- Não está demonstrado que a economia por hash seja pequena, nem que o normalizador será a principal fonte de ganho.

A precisão relativa, que troca valores oferecidos pelo sistema por uma referência, foi calculada com o gabarito e fica como análise exploratória; ela está na saída bruta, mas não é algo que o middleware saberia fazer sozinho.

**Contaminação do teste.** Uma análise anterior desta entrega leu o conjunto de teste de A e B e foi usada para tirar conclusões de projeto. Por isso, esse teste não serve mais como avaliação final e passa a ser tratado como exploratório.

Arquivos: `mapping.json`, `manifest.json`, `split.py`, `hash_diag.py` e a saída bruta `hash_diag_raw.json`.

## Avaliação posterior em Flights

Events passa a ser o conjunto de desenvolvimento e exploração. Flights\_1 (A) e Flights\_2 (B) ficam para uma avaliação posterior, com divisões congeladas antes de qualquer análise adicional, e não são apresentados como inéditos.

**O que já foi visto de Flights**

| Script | Informação vista |
| --- | --- |
| `stats.py` | Contagem de diálogos por divisão original, turnos do usuário, chamadas de serviço e intenções de cada serviço |
| `pairs.py` | Intenções comuns e exclusivas, parâmetros com o mesmo nome e taxas agregadas de repetição exata (frase normalizada, frase com atos do sistema anterior, e de B em A) |
| `informative.py` | Fração de turnos informativos, repetição entre eles e as frases mais repetidas, como "no thank you" (82 vezes em Flights\_1) |
| `entity.py` | Fração de turnos com entidade, categóricos e sem valor, e a repetição exata em cada tipo |

Nenhuma dessas análises comparou interpretações com o gabarito nem ajustou limiares, chaves ou modelos. As taxas de repetição, porém, têm relação direta com H4 e H5, e por isso ficam registradas.

**Divisões congeladas.** Mesma semente (20260928) e mesmas frações de Events. As intenções de reserva existem só em A e servem de sonda para "conhecida mas não suportada" em B.

| Conjunto | Desenvolvimento | Memória | Teste |
| --- | --- | --- | --- |
| Flights\_1 (A) | 120 diálogos | 440 diálogos | 240 diálogos |
| Flights\_2 (B) | 28 diálogos | 102 diálogos | 55 diálogos |
| Fora do catálogo | 30 diálogos de Services\_3 | nenhum | 30 diálogos de Movies\_1 |

Manifesto `manifest_flights.json`, SHA-256 `9cbdf92113af94cc5c5a9388aa3bddc04d44eeddeaf112ebaf0a6c0bfee46c1e`. O mesmo script (`split_pair.py`) reproduz byte a byte o manifesto de Events.

**Dois modos de avaliação, reportados separadamente**

| Modo | O que pode usar de Flights | O que mede |
| --- | --- | --- |
| Método congelado | Só os esquemas, para montar o mapeamento; regras e limiares vêm de Events | Transferência entre domínios |
| Após adaptação | Esquemas e o conjunto de desenvolvimento de Flights | Desempenho com ajuste ao domínio |

- O teste de Flights só é aberto depois que o método e os limiares de cada modo estiverem registrados neste documento.
- Nenhum domínio é trocado ou acrescentado por causa de resultados.

## Ensaio da V0 no desenvolvimento de Events

A V0 interpreta os pedidos e produz ações avaliáveis sem consultar anotações na inferência, a cerca de 2 ms por turno em CPU. Quando se considera confiante (cerca de 15% dos turnos), ela monta a chamada sem LLM e acerta 93% a 98% dessas chamadas; no restante, erra principalmente a intenção.

**Ambiente e normalizador.** O ambiente tem 2 CPUs, 7 GB de memória e nenhuma GPU, e a política de rede bloqueia o Hugging Face; nenhum modelo pré-treinado pôde ser baixado. O normalizador é, portanto, um conjunto de modelos scikit-learn treinados localmente em 25 a 50 segundos: classificador de intenção com classe "fora do catálogo", classificador de ato do usuário (aceitar, negar, outro), extrator de parâmetros por token, classificadores para parâmetros categóricos e classificador de chamar ou aguardar.

**Dados de treino.** Quadros de Events\_1 e Events\_2 em diálogos com mais de um serviço: 2.760 diálogos (17.371 turnos), mais 306 para validação interna. Esses diálogos não estão em nenhuma divisão, o que o script verifica. A classe "fora do catálogo" usa 4.000 pedidos de outros domínios, excluindo Flights, Events\_3 e os serviços dos conjuntos fora do catálogo. A regra de copiar valores oferecidos quando o usuário aceita foi derivada dos dados de treino: só nome e data do evento entram no estado.

**Na inferência**, cada turno recebe a frase do usuário, os atos e valores do turno anterior do sistema e o estado previsto pela própria V0. Os limiares do caminho sem LLM final (incerteza de identidade e de aplicabilidade abaixo de 0,2) foram fixados antes da execução.

| Métrica | A (Events\_1) | B (Events\_2) |
| --- | --- | --- |
| Turnos | 303 | 825 |
| Acurácia de intenção | 91,4% | 79,5% |
| Estado completo correto | 70,0% | 61,3% |
| Parâmetros: precisão / cobertura | 97,5% / 88,0% | 97,0% / 85,9% |
| Chamadas anotadas / previstas | 74 / 63 | 234 / 155 |
| Chamadas indevidas / omitidas | 0 / 11 | 2 / 81 |
| Argumentos corretos quando ambos chamam | 88,9% | 86,9% |
| Q (acerto da ação por turno) | 94,1% | 87,5% |
| Q da linha de base "sempre aguardar" | 75,6% | 71,6% |
| Q só nos turnos com chamada anotada | 75,7% | 56,8% |
| Turnos no caminho sem LLM final | 16,2% | 14,7% |
| Chamada certa no caminho sem LLM final | 98,0% | 93,4% |
| Tempo por turno: mediana / p95 | 2,0 / 4,3 ms | 2,1 / 3,1 ms |

**Recusa e sonda.** Os 43 pedidos fora do catálogo (Hotels\_1) foram todos recusados, e a recusa indevida em turnos de Events foi de 0,8%. Na sonda, 72,9% dos 155 turnos de GetEventDates atendidos por A foram sinalizados como não suportados.

**Principais erros**

- **Buscar eventos versus buscar datas.** A maior fonte de erro: em B, 100 turnos de FindEvents viraram GetEventDates e 31 o contrário. No próprio SGD, frases como "i want to find events on new york" aparecem anotadas como GetEventDates, então a distinção muitas vezes não está na primeira frase. Em A, o mesmo erro marca 23 buscas como não suportadas.
- **Propagação.** Metade dos 195 erros de intenção repete o erro do turno anterior, porque o modelo foi treinado com a intenção anterior anotada e usa a prevista na inferência.
- **Chamadas omitidas.** Em B, 48 das 81 vêm de intenção errada e 33 do classificador de decisão.
- **Argumentos.** A maioria dos erros é parâmetro faltando (17 de 26).

**Limitações deste ensaio**

- O normalizador foi treinado com dados do mesmo domínio. Ele não serve para o modo "método congelado" em Flights, que exige um modelo guiado por esquema.
- A equivalência entre valores como "March 9th" e "2019-03-09" é resolvida com o gabarito, só na avaliação. A V0 não converte datas relativas; numa chamada real, isso ficaria para o LLM ou para um conversor.
- Os pedidos fora do catálogo foram avaliados como início de conversa, sem contexto.
- A validação interna do normalizador (98,5% de intenção) é otimista, porque usa o estado anterior anotado.

**Próximos ajustes possíveis, a registrar antes de fazer:** usar hipóteses em vez de uma intenção única quando buscar eventos e buscar datas empatam; treinar com a intenção anterior prevista, para reduzir a propagação; e informar ao classificador qual aplicação está atendendo.

Arquivos: `gc_common.py`, `gc_features.py`, `train_normalizer.py`, `run_v0.py`, `normalizer_report.json`, `v0_dev_summary.json` e a saída por turno `v0_dev_turns.jsonl`.

## Ajustes da V0 e desenho de V2 e V3

Registrado antes de rodar, em 28/09/2026. Todos os parâmetros abaixo ficam fixos nesta rodada; qualquer mudança posterior será registrada como nova rodada.

**Ajustes da V0**

- **Hipóteses:** quando a diferença de probabilidade entre as duas intenções mais prováveis for menor que 0,3, a segunda vira hipótese. Casos com hipótese não usam o caminho sem LLM final.
- **Desempate pela aplicação:** se a primeira intenção não é suportada pela aplicação e a segunda é, dentro dessa margem, vence a suportada. A aplicação não entra como atributo do modelo, para não apagar a detecção de intenções não suportadas.
- **Propagação de erros:** o normalizador passa a ser treinado em dois estágios, com validação cruzada em duas partes. O segundo estágio aprende com a intenção anterior e o estado previstos pelo primeiro, além dos anotados, e o decisor de chamar ou aguardar aprende com atributos previstos.

**Memória de V2 e V3**

- **Conteúdo:** para cada turno do fluxo de memória, a interpretação validada, que nesta simulação vem do gabarito: intenção, ato do usuário e decisão de chamar. Valores literais não são guardados; eles vêm sempre do contexto atual, como na hipótese `aceitar(oferta_atual)`.
- **Consulta exata:** chave K2 (frase normalizada e atos anteriores sem valores). Só é usada com pelo menos 2 registros e 80% de concordância, com peso 0,8 sobre a previsão do normalizador.
- **Recuperação de exemplos:** similaridade de cosseno em TF-IDF, com os 5 registros mais parecidos que tenham similaridade de pelo menos 0,8, e peso 0,5.
- **Escopo:** V2 consulta só registros da própria aplicação; V3 consulta os de A e de B.

**Avaliação desta rodada:** desenvolvimento de Events, com a memória congelada ao fim do fluxo. Comparações pareadas por diálogo, com 2.000 reamostragens, para Q, Q nos turnos com chamada anotada, fração de turnos no caminho sem LLM final e acerto nesse caminho. Os números são exploratórios: servem para decidir se vale seguir, não para testar as hipóteses.

## Resultados da rodada 2

Os ajustes melhoraram bastante a V0, sobretudo em B. A memória, local ou compartilhada, não acrescentou nada: foi consultada em 24% a 27% dos turnos, mas concordou com o normalizador em 98% das vezes.

| Métrica | A: rodada 1 | A: V0 | A: V2 | A: V3 | B: rodada 1 | B: V0 | B: V2 | B: V3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Acurácia de intenção | 91,4% | 97,4% | 97,4% | 97,4% | 79,5% | 88,6% | 88,8% | 88,5% |
| Estado completo correto | 70,0% | 71,6% | 71,6% | 71,6% | 61,3% | 64,4% | 64,4% | 64,4% |
| Q | 94,1% | 96,0% | 95,7% | 95,7% | 87,5% | 90,9% | 90,8% | 90,7% |
| Chamadas omitidas | 11 | 5 | 5 | 5 | 81 | 52 | 54 | 54 |
| Chamadas indevidas | 0 | 0 | 1 | 1 | 2 | 5 | 5 | 6 |
| Turnos sem LLM final | 16,2% | 18,8% | 18,8% | 18,8% | 14,7% | 18,5% | 18,7% | 18,7% |
| Acerto sem LLM final | 98,0% | 98,2% | 98,2% | 98,2% | 93,4% | 95,4% | 95,5% | 95,5% |

**Comparações pareadas por diálogo**, em pontos percentuais, com intervalo de 95%:

| Comparação | Aplicação | Q | Q nos turnos com chamada | Turnos sem LLM final |
| --- | --- | --- | --- | --- |
| V0 contra a V0 só com desempate | B | +3,4 \[2,0; 4,9\] | +13,2 \[8,3; 18,3\] | +3,9 \[2,5; 5,4\] |
| V2 contra V0 | A | −0,3 \[−1,1; 0,0\] | 0,0 | 0,0 |
| V2 contra V0 | B | −0,1 \[−0,6; 0,3\] | −0,4 \[−2,0; 0,9\] | +0,1 \[−0,5; 0,7\] |
| V3 contra V2 | B | −0,1 \[−0,4; 0,0\] | 0,0 | 0,0 |

**O que cada ajuste fez**

- O desempate pela aplicação sozinho levou a intenção de A de 91,4% para 96,4%, sem mudar B.
- O treino em dois estágios levou a intenção de B de 79,5% para 88,6% e cortou as chamadas omitidas de 81 para 52.
- A recusa de pedidos fora do catálogo continuou em 100%, e a recusa indevida caiu de 0,8% para 0,3%. A sonda de GetEventDates em A passou de 72,9% para 78,1% na V0, e caiu para 74,2% e 72,9% com memória.

**Por que a memória não ajudou aqui.** O normalizador foi treinado com cerca de 17 mil turnos do próprio domínio. A memória tem 3.917 interpretações validadas da mesma distribuição, então traz pouca informação que o modelo já não tenha. Das mudanças que causou, uma melhorou e três ou quatro pioraram o resultado.

Isso responde à pergunta desta rodada só para este cenário: **com um modelo pequeno já bem treinado no domínio, a memória de episódios é redundante.** O cenário em que o Grande Cérebro prometeria valor é outro: uma aplicação nova ou pequena, cujo modelo sabe pouco, aproveitando interpretações validadas por outras. Esse cenário ainda não foi testado.

Arquivos: `gc_v0.py`, `gc_train.py`, `gc_memory.py`, `train_normalizer_r2.py`, `run_round2.py`, `normalizer_r2_report.json`, `r2_dev_summary.json` e a saída por turno `r2_dev_turns.jsonl`. A execução foi repetida e reproduziu as métricas.

## Rodada 3: aplicação com pouco dado

Registrado antes de rodar, em 28/09/2026. A pergunta é se a memória compensa quando o modelo pequeno sabe pouco, que é a situação de uma aplicação nova.

**Hipótese:** o ganho da memória (V2 contra V0 e V3 contra V0) é positivo quando o normalizador tem pouco dado e diminui à medida que ele recebe mais. **Critério principal:** com 2% dos dados, a diferença de Q entre V3 e V0 tem intervalo de 95% inteiro acima de zero em pelo menos uma aplicação. Se isso não acontecer, a memória não compensa nem no cenário mais favorável testado aqui.

**Desenho**

- **Frações de treino do normalizador:** 2%, 10%, 50% e 100% dos diálogos de treino, sorteados por diálogo e aninhados (os 2% estão dentro dos 10%, e assim por diante). Os exemplos da classe "fora do catálogo" são reduzidos na mesma proporção, com mínimo de 50.
- **Sorteios:** três por fração abaixo de 100%. O ponto de 100% é o normalizador da rodada 2.
- **Treino:** o mesmo procedimento em dois estágios da rodada 2, aplicado só aos dados da fração.
- **Memória:** os mesmos 3.917 registros validados. Muda uma coisa em relação à rodada 2: a recuperação usa uma representação TF-IDF ajustada aos próprios registros da memória, para não depender do vocabulário de um normalizador treinado com pouco dado. Todos os pontos da curva, inclusive 100%, usam essa mesma memória.
- **Parâmetros da memória e da V0:** os da rodada 2, sem alteração.
- **Avaliação:** desenvolvimento de Events. As diferenças são a média entre sorteios, com intervalo de 95% por bootstrap que reamostra os mesmos diálogos em todos os sorteios (2.000 reamostragens).

## Resultados da rodada 3

O critério registrado foi atingido em B por margem mínima, mas o efeito prático é desprezível: com 2% dos dados, a V0 perde cerca de 19 pontos de Q em B, e a memória compartilhada recupera menos de 1.

| Fração de treino | A: Q da V0 | A: V3 − V0 | B: Q da V0 | B: V3 − V0 |
| --- | --- | --- | --- | --- |
| 2% (55 diálogos) | 79,1% | +1,0 \[0,0; 2,1\] | 72,0% | +0,9 \[0,1; 1,7\] |
| 10% (276 diálogos) | 90,2% | +0,2 \[−0,2; 0,8\] | 84,7% | +0,5 \[0,0; 1,1\] |
| 50% (1.380 diálogos) | 95,0% | −0,2 \[−0,7; 0,0\] | 88,7% | +0,4 \[−0,1; 1,0\] |
| 100% | 96,0% | −0,3 \[−1,1; 0,0\] | 90,9% | 0,0 \[−0,5; 0,5\] |

Diferenças em pontos percentuais, média de três sorteios, com intervalo de 95%. Para referência, "sempre aguardar" tem Q de 75,6% em A e 71,6% em B.

**O que os dados mostram**

- **Direção prevista, magnitude pequena.** O ganho da memória é maior com menos dados e some com os dados completos, como a hipótese previa. Mas mesmo no ponto mais favorável ele não passa de 1 ponto, enquanto a V0 com 2% fica perto da linha de base.
- **Compartilhamento.** Com 2%, V3 contra V2 dá +0,7 \[−0,1; 1,7\] em A, a aplicação menor, e +0,2 \[0,0; 0,6\] em B.
- **A memória ajuda onde o gargalo não está.** Com 2%, ela melhora a intenção de B em 2,2 pontos \[0,8; 3,7\], mas a intenção já estava em 82%. O que falha é outra coisa:

| Chamadas anotadas | A com 2% | B com 2% | A com 100% | B com 100% |
| --- | --- | --- | --- | --- |
| Chamada certa | 35% | 17% | 84% | 70% |
| Argumentos errados | 43% | 45% | 9% | 8% |
| Chamada omitida | 22% | 35% | 7% | 22% |
| Método errado | 0% | 3% | 0% | 0% |

- **Por que a memória não compensa.** Com pouco dado, o modelo pequeno falha sobretudo em extrair os argumentos (nomes, cidades, datas). A memória, como foi desenhada, guarda a operação (intenção, ato e decisão de chamar), mas não como extrair os argumentos. Ela não carrega o conhecimento que falta.
- **Recusa indevida.** Com pouco dado, a recusa indevida sobe para até 3,9% (2%, V3), contra 0,3% com os dados completos.

**Conclusão desta rodada:** neste desenho, a memória de operações não compensa a falta de dados. A hipótese que sobra, ainda não registrada, é uma memória que compartilhe o conhecimento que o modelo fraco não tem: valores validados de cada conceito (cidades, eventos, locais) e exemplos de extração. A alternativa é o terceiro mecanismo previsto no protocolo: usar os registros validados para atualizar o próprio normalizador.

A avaliação é determinística: o sorteio 0 com 2% reproduziu os valores de um teste feito antes da execução completa. Arquivos: `run_curve.py`, `gc_memory.py` e `r3_curve_summary.json`.

## Rodada 4: memória de valores validados

Registrado antes de rodar, em 28/09/2026. A pergunta é se compartilhar o conhecimento que falta ao modelo fraco, como reconhecer argumentos, compensa a falta de dados, inclusive quando esse conhecimento vem de aplicações de outros domínios.

**Critério de parada.** Com 2% dos dados, a condição "V3 + valores + outros domínios" precisa recuperar pelo menos 25% da lacuna de Q nos turnos com chamada anotada entre a V0 com 2% e a V0 com 100%, com intervalo de 95% inteiro acima de zero, em pelo menos uma aplicação. A lacuna é de cerca de 50 pontos em A e em B, então o mínimo é de cerca de 12,5 pontos. Se o critério não for atingido, a memória compartilhada é abandonada nesta forma, e o projeto segue só com o modelo pequeno com portão de confiança.

**Memória de valores**

- **Conteúdo:** trechos de argumentos ditos pelos usuários e validados (pelo gabarito, como antes), com o conceito e o número de validações.
- **Fontes:** o fluxo de memória de A; o de B; e outros domínios, com os diálogos de um serviço de todos os serviços do SGD que não são Events nem reservados. Nos outros domínios, parâmetros cuja descrição menciona cidade viram `place.city`; os chamados `date` ou terminados em `_date` viram `event.date`; e os chamados `time` ou terminados em `_time` viram `event.time`. São 60 parâmetros em mais de 20 serviços.
- **Uso:** a frase é varrida do trecho mais longo para o mais curto, procurando valores com pelo menos 2 validações e 3 caracteres. Se o mesmo texto aparece em mais de um conceito, vence o de mais validações. O valor só entra para conceitos do método da intenção prevista, quando o extrator não encontrou esse conceito no turno e o valor difere do estado atual, com confiança 0,85.

**Condições**, cada uma com os normalizadores de 2%, 10%, 50% e 100% da rodada 3:

| Condição | Memória |
| --- | --- |
| V0 | Nenhuma |
| V3 | Operações de A e B, como na rodada 3 |
| V2 + valores | Operações e valores só da própria aplicação |
| V3 + valores | Operações e valores de A e B |
| V3 + valores + outros | O mesmo, mais valores de outros domínios |

**Comparações:** "V3 + valores + outros" contra V0 (o critério); "V3 + valores" contra "V2 + valores" (compartilhar entre A e B); e "V3 + valores + outros" contra "V3 + valores" (outros domínios). O bootstrap é o mesmo da rodada 3.

**Fora do alcance desta rodada:** problemas abertos com procedimentos caros de descobrir. O SGD não tem esse tipo de dado.

## Resultados da rodada 4

**O critério de parada não foi atingido.** Com 2% dos dados, a memória de valores com outros domínios recuperou 10,7% da lacuna em A e 2,8% em B, abaixo dos 25% registrados. Pela regra definida antes de rodar, a memória compartilhada nesta forma é abandonada.

| Aplicação | Lacuna (V0 100% − V0 2%) | Ganho de "V3 + valores + outros" | Fração recuperada |
| --- | --- | --- | --- |
| A | 50,5 pontos | +5,4 \[1,5; 9,7\] | 10,7% |
| B | 51,4 pontos | +1,4 \[−1,0; 3,8\] | 2,8% |

Ganho em Q nos turnos com chamada anotada, em pontos percentuais, com intervalo de 95%.

**O que os dados mostram**

- **A memória de valores ajudou, pouco.** Foi o primeiro efeito claramente positivo: em A, +5,4 pontos com 2% e +3,1 \[0,9; 6,2\] com 10%. Com 50% e 100%, o efeito some.
- **Compartilhar entre A e B ajudou A.** Com 10%, "V3 + valores" contra "V2 + valores" deu +2,2 \[0,4; 5,0\] em A. Em B, nenhuma diferença.
- **Outros domínios não acrescentaram nada:** 0,0 em A e entre −0,4 e 0,0 em B. Cidades e datas vindas de restaurantes, hotéis e ônibus já estavam cobertas pelos valores de A e B.
- **O gargalo mudou de lugar.** A memória já continha 89% das cidades e todas as datas e subcategorias anotadas no desenvolvimento, mas só 31% dos nomes de eventos, que quase nunca se repetem. Os erros de argumento que sobraram são, na maioria, parâmetros categóricos que o desenho registrado não cobria:

| Erro mais frequente, com 2% (sorteio 0) | A (29 chamadas) | B (111 chamadas) |
| --- | --- | --- |
| Falta o número de ingressos | 11 | 46 |
| Falta o tipo de evento | 10 | 39 |
| Cidade com valor errado | 9 | 23 |

**Conclusão.** A memória de valores compartilhados funciona na direção prevista, mas não com a força necessária para justificar a infraestrutura. Uma rodada que cobrisse os parâmetros categóricos seria uma hipótese nova, a ser registrada como tal, e não uma revisão deste resultado.

Arquivos: `gc_values.py`, `run_values.py` e `r4_values_summary.json`.

## Rodada 5: suporte técnico real (AskUbuntu)

Registrado antes de rodar, em 28/09/2026. A pergunta é se, em suporte técnico real, uma memória compartilhada de problemas já resolvidos encontra soluções para uma fatia relevante dos problemas novos, e quanto o compartilhamento acrescenta à memória de cada central.

**Dados.** Conjunto AskUbuntu de Lei et al. (NAACL 2016), baixado do repositório oficial: 167 mil perguntas reais de suporte de Linux (título e até 100 palavras do corpo). As duplicatas marcadas pelos usuários do site são o gabarito de "este problema já foi resolvido". Essas marcações são incompletas, então os resultados são limites inferiores.

**Simulação**

- **Tempo:** as perguntas são ordenadas pelo ID, que cresce com a data de criação no site. As 20% mais recentes formam a janela de avaliação, e os 10% anteriores, a janela de calibração.
- **Centrais:** cada pergunta é atribuída por sorteio à central A ou B, com 50% de chance cada, em três sorteios.
- **Condições:** V0 sem memória; V2 com a memória da própria central (perguntas anteriores dela); V3 com a memória das duas centrais.
- **Acerto:** uma pergunta nova tem solução reaproveitável quando o buscador traz uma duplicata marcada e anterior a ela.
- **Buscadores:** TF-IDF e média de vetores de palavras pré-treinados que acompanham o conjunto. O IDF é ajustado só com perguntas anteriores à janela de avaliação. O critério usa o buscador com maior taxa de sugestão útil na janela de calibração.

**Métricas**

- **Sugestão útil (principal):** fração de todas as perguntas da janela de avaliação em que as 5 primeiras sugestões incluem uma duplicata marcada e anterior. Corresponde a mostrar soluções anteriores a quem atende, que confere e reaproveita.
- **Reuso automático (secundária):** fração em que a primeira sugestão tem similaridade acima de um limiar e é duplicata marcada. O limiar de cada condição é fixado na calibração como o menor valor em que pelo menos metade das sugestões confiantes são duplicatas marcadas, contando como erro as perguntas sem marcação (estimativa conservadora).

**Critério.** O Grande Cérebro tem valor neste cenário se, em V3, a sugestão útil alcançar pelo menos 5% de todas as perguntas novas e V3 superar V2 em pelo menos 2 pontos, com intervalo de 95% acima de zero. Cinco por cento dos chamados é um volume que uma operação de suporte percebe; 2 pontos mostram que o compartilhamento acrescenta uma fatia relevante.

**Fora do alcance:** comunidades realmente diferentes (não há duplicatas marcadas entre sites distintos) e o custo real de descobrir cada solução.

## Resultados da rodada 5

**O critério não foi atingido, mas o motivo é outro.** O potencial existe: pelo menos 7,2% das perguntas novas já tinham solução marcada na memória compartilhada, quase o dobro dos 3,75% da memória de uma central só. O que falhou foi encontrar essas soluções: o buscador acertou só 0,8% das perguntas.

| Medida, na janela de avaliação (33.553 perguntas) | Uma central (V2) | Duas centrais (V3) |
| --- | --- | --- |
| Teto: já existe duplicata marcada e anterior na memória | 3,75% | 7,19% |
| Sugestão útil nas 5 primeiras (TF-IDF, buscador escolhido) | 0,50% | 0,80% |
| Sugestão útil nas 5 primeiras (vetores pré-treinados) | 0,12% | 0,17% |
| Reuso automático com precisão conservadora de 50% | 0% | 0% |

O compartilhamento acrescentou 0,30 ponto \[0,24; 0,35\] na sugestão útil, muito abaixo dos 2 pontos registrados. Nenhum limiar atingiu a precisão mínima na calibração, então não houve reuso automático.

**Verificação do buscador.** No teste padrão do próprio conjunto, que ranqueia 20 candidatos pré-selecionados, o TF-IDF deu P@1 de 0,543 e MAP de 0,557, próximo do publicado para BM25 (0,53 e 0,57). A implementação está correta. Quando a busca é feita sobre todas as perguntas anteriores, como num suporte real, a duplicata marcada aparece em média na posição 138: só 15,8% ficam entre as 5 primeiras.

**O que isso mostra**

- **Existe muito problema repetido em suporte real,** e o compartilhamento dobra o que cada central poderia reaproveitar. Este é o primeiro dado a favor da premissa central do Grande Cérebro.
- **O gargalo é reconhecer que um problema novo é o mesmo de um antigo.** Com buscadores baratos, as duplicatas se perdem entre centenas de perguntas parecidas. Esse é exatamente o desafio levantado no início da conversa: semelhança de texto não é o mesmo que "isto resolve o meu problema".
- **O resultado depende da qualidade do reconhecimento,** que este ambiente não permite testar com modelos modernos, porque não há acesso a modelos pré-treinados de busca semântica ou a um LLM para reordenar candidatos.

**Próximo teste que pode mudar a conclusão:** repetir esta rodada, com o mesmo critério, usando um buscador semântico moderno e um LLM que reordene os 50 primeiros candidatos. Isso exige um ambiente com acesso a esses modelos, como o seu computador ou uma API.

Arquivos: `run_support.py`, `check_support.py` e `r5_support_summary.json`. Conjunto na revisão `4d0a916`.

## Rodada 6: piloto local com Ollama

Registrado antes de rodar, em 28/09/2026. O piloto roda na máquina do usuário, com modelos locais via Ollama, porque este ambiente não alcança modelos pré-treinados. Ele é exploratório e só decide se vale repetir a rodada 5 inteira com reconhecimento melhor.

**O que mede:** P@1 e MAP no teste padrão do AskUbuntu (perguntas com 20 candidatos anotados manualmente), para quatro métodos: TF-IDF no texto original (linha de base: P@1 de 0,543); embeddings do texto original; o LLM reescreve cada pergunta como forma padrão do problema, comparada por embeddings; e a mesma forma padrão comparada por TF-IDF.

**Regra de decisão:** a rodada 5 é repetida com o método vencedor se algum método superar o TF-IDF em pelo menos 5 pontos de P@1 no mesmo subconjunto de perguntas. Caso contrário, o reconhecimento local não é bom o bastante e o teste para aqui.

**Script:** `gc_local_pilot.py`. Ele registra os modelos, a versão do Ollama, o tempo por texto e exemplos de formas padrão.

**Primeiro resultado do piloto (60 perguntas, Mac do usuário, Ollama):** embeddings `nomic-embed-text` deram P@1 de 73,3% e MAP de 70,6%, contra 51,7% e 55,1% do TF-IDF nas mesmas perguntas. São 21,6 pontos de P@1 a mais, acima dos 5 exigidos, então a regra de decisão manda repetir a rodada 5. As formas padrão com `llama3.1:8b` ainda estão rodando, a cerca de 2 segundos por pergunta.

**Teste completo, registrado antes de rodar:** a rodada 5 é repetida com o mesmo código de simulação, as mesmas janelas, os mesmos sorteios e o mesmo critério, trocando só o buscador por embeddings na configuração do piloto. O script `gc_local_support.py` foi testado aqui com um servidor que imita o Ollama e reproduz exatamente os tetos da rodada 5 (3,75% e 7,19%). Se as formas padrão vencerem o piloto, elas não cabem no teste completo nesta máquina: gerar 167 mil levaria cerca de 4 dias. Nesse caso, o teste completo roda com embeddings e essa limitação fica registrada.

### Resultado completo do piloto

Os embeddings do texto original venceram. Reescrever a pergunta numa forma padrão antes de comparar piorou o reconhecimento em relação aos embeddings do texto original.

| Método (60 perguntas, 1.246 textos) | P@1 | MAP |
| --- | --- | --- |
| Embeddings do texto original | 73,3% | 70,6% |
| Forma padrão (`llama3.1:8b`) + embeddings | 60,0% | 58,3% |
| TF-IDF no texto original | 51,7% | 55,1% |
| Forma padrão + TF-IDF | 43,3% | 51,0% |

A forma padrão levou 1,7 segundo por pergunta no Mac do usuário (36,5 minutos no total). Com 60 perguntas, cada P@1 tem margem de cerca de 12 pontos, então a diferença de 13 pontos entre embeddings e forma padrão é um indício, não uma prova.

**Por que a forma padrão perdeu.** Nos exemplos, o modelo inventa detalhes que não estavam na pergunta, como "Ubuntu 18.04 or later" numa pergunta de 2012, "versions prior to 12.04" e uma impressora "HP LaserJet" com o driver "Gutenprint" onde o usuário só perguntou que driver usar. Ao resumir, ele também apaga detalhes que distinguem um problema de outro. É o risco apontado na conversa inicial: normalizar pode destruir exatamente a informação que decide se dois problemas são o mesmo.

**Decisão, pela regra registrada:** o teste completo roda com embeddings do texto original, como já previsto.

## Resultados do teste completo com busca semântica

**O critério não foi atingido.** Os embeddings melhoraram a sugestão útil em cerca de 50% em relação ao TF-IDF, mas ela continua em 1,2% das perguntas novas, longe dos 5% registrados. Executado no Mac do usuário (Ollama 0.30.10, `nomic-embed-text`) em 65 minutos, com as mesmas janelas e os mesmos tetos da rodada 5.

| Medida, janela de avaliação (33.553 perguntas) | TF-IDF: V2 | TF-IDF: V3 | Embeddings: V2 | Embeddings: V3 |
| --- | --- | --- | --- | --- |
| Teto: duplicata marcada e anterior na memória | 3,75% | 7,19% | 3,75% | 7,19% |
| Sugestão útil nas 5 primeiras | 0,50% | 0,80% | 0,79% | 1,19% |
| Parte do teto alcançada | 13% | 11% | 21% | 17% |
| Reuso automático | 0% | 0% | 0% | 0% |

Com embeddings, o compartilhamento somou 0,40 ponto \[0,32; 0,47\], abaixo dos 2 pontos exigidos. Nenhum limiar alcançou a precisão mínima para reuso automático.

**O que isso mostra**

- **O piloto e o teste completo medem coisas diferentes.** No piloto, os embeddings escolhiam a duplicata certa entre 20 candidatos já pré-selecionados em 73% dos casos. No teste completo, a duplicata precisa ser encontrada entre dezenas de milhares de perguntas parecidas, e aparece entre as 5 primeiras em só 17% dos casos em que existe.
- **O gargalo continua sendo reconhecer o mesmo problema em escala.** Para atingir o critério, a busca precisaria encontrar cerca de 70% das duplicatas existentes entre as 5 primeiras, quatro vezes mais do que conseguiu.
- **Ressalva importante:** a sugestão útil conta só duplicatas marcadas pelos usuários, que são incompletas. Parte das sugestões sem marcação pode ser, na verdade, uma solução válida. Medir isso exigiria uma avaliação humana ou por um modelo forte, e seria uma rodada nova, não uma revisão deste resultado.

**Conclusão, pelas regras registradas:** em suporte técnico real, a premissa do Grande Cérebro se confirmou (pelo menos 7,2% dos problemas novos já tinham solução, e compartilhar dobra esse teto), mas a viabilidade não: com os buscadores testados, só cerca de um sexto dessas soluções é encontrado.

## Rodada 7: as três peças do cérebro

Registrado antes de rodar, em 28/09/2026. As rodadas de suporte testaram só busca plana. Esta rodada testa as três peças da visão original que ficaram de fora: identidade dos problemas, peso de recorrência e aprendizado com as ligações validadas. Roda no Mac do usuário, reaproveitando os embeddings do teste completo, com as mesmas janelas, sorteios e critério da rodada 5.

**Regra de tempo.** As ligações "mesmo problema" só entram na memória se as duas perguntas forem anteriores à janela em uso: antes da calibração, para ajustar parâmetros; antes da avaliação, para medir. Em V2, cada central só conhece as ligações entre as próprias perguntas.

**Grupo gigante.** Encadeando as ligações, 3.712 perguntas formam um único grupo, o que não é uma identidade real. Por isso, cada pergunta antiga é reconhecida também pelas suas duplicatas diretas validadas, sem encadear. O sistema sempre mostra 5 perguntas, e o acerto exige que uma delas seja duplicata marcada da pergunta nova.

**Métodos**

| Método | Pontuação de cada pergunta antiga |
| --- | --- |
| M0 Busca plana | Similaridade com a pergunta nova (repete o teste completo) |
| M1 Identidade | A maior entre: similaridade com ela, com qualquer duplicata direta validada dela, e com a média dela e dessas duplicatas |
| M2 Identidade e peso | M1 mais β × log(1 + número de duplicatas validadas) |
| M3 Aprendizado | Busca plana após uma transformação dos embeddings aprendida com as ligações validadas (KISSME, forma fechada, sem treinar rede) |
| M4 Cérebro completo | M2 sobre os embeddings transformados |

**Ajustes na calibração:** β é escolhido na grade {0; 0,005; 0,01; 0,02; 0,04; 0,08} pela sugestão útil em V3. O método principal é o melhor entre M2 e M4 na calibração. A janela de avaliação não é usada para nenhuma escolha.

**Critério:** o mesmo da rodada 5, aplicado ao método principal. V3 precisa alcançar pelo menos 5% de sugestão útil, e V3 − V2 precisa ser de pelo menos 2 pontos, com intervalo de 95% acima de zero.

**Juiz (exploratório, fora do critério):** um LLM local responde se a primeira sugestão resolve a pergunta nova, em 150 perguntas sem duplicata marcada. Ele é calibrado com 60 pares de duplicatas marcadas e 60 pares aleatórios, e a taxa estimada é corrigida pela sensibilidade e pelos falsos positivos do juiz.

**Controle acrescentado depois do teste do código.** Para verificar o script, ele foi rodado aqui com embeddings substitutos (TF-IDF reduzido a 256 dimensões), que não valem como resultado. Com eles, os métodos com identidade ficaram muito acima da busca plana, o que levantou a suspeita de que o ganho viesse só de popularidade. A verificação mostrou que mostrar a todos as 5 perguntas com mais duplicatas validaadas já acerta 1,03% das perguntas novas, e que 75% das duplicatas do gabarito já tinham ligações validadas antes da avaliação (grau mediano 9). Por isso, o resultado passa a incluir o controle P0, popularidade pura. O método principal, a escolha de β e o critério não mudam. O juiz ganhou um intervalo de confiança por reamostragem.

## Resultados da rodada 7

**O critério não foi atingido por 0,16 ponto, mas as peças do cérebro quadruplicaram o reconhecimento.** O método principal (M2, identidade e peso) encontrou solução anterior para 4,84% das perguntas novas, contra 1,19% da busca plana e 1,03% da popularidade pura. O compartilhamento somou 2,26 pontos \[2,11; 2,40\], acima dos 2 exigidos. Executado no Mac do usuário em 11,6 minutos.

| Método | V2 (uma central) | V3 (duas centrais) | V3 − V2 | V3 contra busca plana |
| --- | --- | --- | --- | --- |
| P0 Popularidade pura (controle) | 0,95% | 1,03% | +0,08 \[0,00; 0,16\] | −0,16 \[−0,32; 0,01\] |
| M0 Busca plana | 0,79% | 1,19% | +0,40 \[0,32; 0,47\] | — |
| M1 Identidade | 2,08% | 3,65% | +1,57 \[1,44; 1,70\] | +2,46 \[2,28; 2,63\] |
| M2 Identidade e peso (principal) | 2,58% | 4,84% | +2,26 \[2,11; 2,40\] | +3,65 \[3,44; 3,87\] |
| M3 Aprendizado | 1,66% | 2,36% | +0,70 \[0,59; 0,81\] | +1,17 \[1,03; 1,30\] |
| M4 Cérebro completo | 2,47% | 4,67% | +2,20 \[2,06; 2,35\] | +3,48 \[3,28; 3,70\] |

Diferenças em pontos percentuais, com intervalo de 95%. Teto em V3: 7,19%.

**Escolhas feitas na calibração:** β = 0,02 para M2 e 0,005 para M4. M2 foi o melhor na calibração (5,89%, contra 5,73% de M4) e, por isso, o método principal. Na avaliação, ele caiu para 4,84%.

**O que isso mostra**

- **A identidade é a peça mais importante.** Reconhecer cada pergunta antiga também pelas duplicatas confirmadas triplicou o acerto, de 1,19% para 3,65%.
- **O peso de recorrência soma sem ser só popularidade.** Sozinha, a popularidade acerta 1,03%; combinada com a identidade, leva o acerto a 4,84%.
- **O aprendizado ajuda sozinho, mas não acrescenta à identidade:** M3 dobrou a busca plana, e M4 ficou pouco abaixo de M2.
- **O compartilhamento passou no critério:** duas centrais juntas quase dobram o que cada uma encontra sozinha (2,58% contra 4,84%).
- **Dois terços do teto foram alcançados:** das perguntas que tinham solução marcada na memória, 67% a tiveram entre as 5 sugestões, contra 17% na busca plana.

**Conclusão, pelas regras registradas:** o critério completo não foi atingido, porque a sugestão útil em V3 ficou em 4,84%, abaixo dos 5%. A parte do compartilhamento foi atingida. O resultado não será reinterpretado para passar. O juiz exploratório não foi rodado nesta execução.

## O que o M2 está reconhecendo (análise exploratória)

Motivada pelas perguntas do GPT depois da rodada 7. Nada aqui muda o resultado registrado.

**O grupo gigante é feito de guias "guarda-chuva".** As 3.712 perguntas ligadas por encadeamento giram em torno de perguntas gerais: "meu computador liga com tela preta, que opções tenho?" (535 ligações), "instalar Ubuntu num Windows 8 com UEFI" (297), "como resolver dependências não atendidas?" (226), "o que fazer quando o Ubuntu trava?" (176). No grupo, 87% das perguntas têm uma ligação só, e 57% ficam a um passo das 10 mais ligadas. O encadeamento acontece quando um caso é ligado a dois guias, e produz cadeias entre problemas diferentes, como "tela preta depois do login" → "recuperar senha de administrador" → "qual versão do Ubuntu serve para o meu Dell".

**Consequência para o conceito.** No AskUbuntu, marcar como duplicata significa "as respostas daquela pergunta resolvem esta", não "é o mesmo problema". A ligação é mais próxima de "mesma solução serve", e muitas das perguntas mais ligadas são procedimentos gerais. Isso apoia a hipótese de que o registro compartilhado precisa distinguir mesmo problema, mesma solução possível e problema relacionado, e de que a unidade reaproveitada pode ser o procedimento, com as condições em que ele vale.

**Próximo passo:** o script `gc_local_explain.py` roda no Mac do usuário, com os embeddings reais, e mostra casos em que M2 acertou e a busca plana errou (de onde veio o acerto: ponte por duplicata, centro do grupo, peso, pergunta guarda-chuva), se as 5 sugestões repetem a mesma família, e o custo por pergunta. Testado aqui com os substitutos, ele reproduz o M2 da rodada 7.

**Juiz da rodada 7: falha técnica.** A segunda execução, com `--judge gemma4:latest`, reproduziu exatamente os mesmos números da avaliação, mas o juiz respondeu "sim" em 0% dos casos, inclusive nos 60 pares de duplicatas marcadas. Um juiz que funciona acertaria boa parte desses pares, então o resultado não é um julgamento. A causa provável é o limite de 4 palavras de resposta, consumido pelo raciocínio interno do modelo antes do "YES" ou "NO". O juiz foi separado em `gc_local_judge.py`, que desliga esse raciocínio, permite até 64 palavras, mostra as primeiras respostas cruas e para se mais de 20% das respostas não forem YES ou NO. Amostras e correção continuam as registradas.

## Rodada 7 — o que o M2 está reconhecendo (resultados reais, 29/09/2026)

Rodado na máquina do Alexandre com os embeddings reais (nomic-embed-text), mesma configuração da rodada 7 (V3, β = 0,02). Análise exploratória; não altera o resultado registrado da rodada 7.

- **Reprodução:** M2 acerta 4,84% e a busca plana (M0) 1,19%, os mesmos números da rodada 7. Nas perguntas com duplicata marcada, o M2 acerta e o M0 erra em 1.293 casos; o inverso ocorre em 67.
- **De onde vem o ganho (1.293 casos):** centro do grupo 68%; ponte por uma duplicata já confirmada 32%; a própria pergunta, 0%. O peso de recorrência foi decisivo em 34%. Em 78% dos ganhos, a pergunta recuperada está entre as 50 mais ligadas da rede (pergunta "guarda-chuva").
- **Diversidade das 5 sugestões (7.412 perguntas):** tamanho da maior família entre as 5 = 1 em 2.023; 2 em 2.547; 3 em 1.619; 4 em 865; 5 em 358. Quando o M2 acerta, as sugestões são mais concentradas (4 ou 5 da mesma família em 606 de 1.625) do que quando erra (100 de 787).
- **Custo:** mediana de 2,0 ms por pergunta na busca plana e 3,14 ms no M2, com 10.377 ligações e 12.727 perguntas ligadas na memória.

**Limite da métrica encontrado nos exemplos.** Em vários dos 25 casos sorteados, a busca plana sugeriu perguntas quase idênticas à nova que não estavam marcadas como duplicata dela, enquanto o M2 recuperou o guia canônico que os moderadores marcaram. Exemplos: #15 ("dpkg was interrupted…"), em que a busca plana sugeriu justamente a duplicata já confirmada do alvo marcado; #14 (atualizar do 13.04 para o 13.10), em que as 5 sugestões planas tratam exatamente disso; #24 (tela preta no 14.04). A métrica "duplicata marcada entre as 5 sugestões" favorece o alvo canônico escolhido pelos moderadores. Parte do ganho de 4× pode ser artefato de medição. O resultado da rodada 7 continua válido para o que foi pré-registrado, mas não permite dizer que o M2 é 4× mais útil.

## Juiz comparativo M0 × M2 (exploratório, registrado antes de rodar)

**Pergunta:** independentemente da marcação dos moderadores, a primeira sugestão do M2 é mais útil que a da busca plana?

**Por que o juiz anterior foi descartado:** a execução com gemma4 devolveu sensibilidade 0 (nenhum "sim" nem em duplicatas marcadas). A causa provável é o modo de raciocínio consumir os 4 tokens de resposta. Além disso, ele só avaliava o M2, o que não responde à pergunta acima.

**Desenho (script gc\_local\_judge.py, testado aqui com juiz simulado e embeddings substitutos):**

1. **Acerto pela família, sem LLM**, em todas as perguntas marcadas da janela de avaliação. Conta como acerto sugerir a duplicata marcada ou uma duplicata já confirmada dela (vizinha na rede anterior ao corte). É reportado no top-1 e no top-5, para M0 e M2. As colunas "marcada\_top5" devem reproduzir 1,19% e 4,84%; isso serve de verificação.
2. **Juiz LLM local (gemma4), temperatura 0, sem raciocínio, até 64 tokens.** Pergunta: "A e B tratam do mesmo problema técnico, de modo que uma resposta correta a B também resolveria A? Responda YES ou NO." Ele julga a primeira sugestão de M0 e a de M2 nas mesmas perguntas: 100 perguntas com duplicata marcada e 100 sem marcação (sorteio fixo, semente 29).
3. **Controles do juiz:** 60 pares de duplicatas marcadas (sensibilidade) e 60 pares aleatórios (falsos positivos). A taxa de "sim" de cada grupo é corrigida por Rogan-Gladen e ponderada pela proporção real do grupo na janela (7,2% marcadas, 92,8% sem marcação). O IC de 95% da diferença M2 − M0 vem de bootstrap (2.000 reamostragens, estratificado por grupo e incluindo os controles). Também são reportadas as contagens de pares discordantes (só M0 útil / só M2 útil).
4. **Salvaguardas:** as 3 primeiras respostas cruas aparecem na tela. O script para se o juiz não responder YES/NO em metade dos 20 primeiros julgamentos ou em mais de 20% do total.

**Como vou ler o resultado (fixado agora):**

- Se o acerto pela família do M0 subir muito e se aproximar do M2, o ganho da rodada 7 vinha em boa parte de a marcação apontar para o guia canônico.
- Se a diferença corrigida M2 − M0 do juiz tiver IC acima de zero, o M2 é mais útil de verdade na primeira sugestão. Se o IC incluir zero, não há evidência de ganho real. Se ficar abaixo de zero, o M2 piora a primeira sugestão na prática, provavelmente trocando a resposta específica por um guia genérico.
- **Limites conhecidos:** a correção supõe que o juiz erra nas sugestões como erra nos controles. Pares aleatórios são mais fáceis que sugestões parecidas, então a taxa corrigida provavelmente superestima a utilidade dos dois métodos. A comparação M2 − M0 usa o mesmo juiz nas mesmas perguntas, então o sinal da diferença é mais confiável que os níveis. Com 200 perguntas, o IC será largo; é um sinal, não uma confirmação.

## Juiz comparativo M0 × M2 — resultados (29/09/2026)

Rodado na máquina do Alexandre com gemma4 (461 julgamentos, 3 respostas inválidas, 6,9 min). A verificação passou: "marcada\_top5" reproduziu 1,19% (M0) e 4,84% (M2).

**1. Acerto pela família (sem LLM, todas as perguntas da janela; teto de 7,19%)**

|  | top-1 marcada | top-1 família | top-5 marcada | top-5 família |
| --- | --- | --- | --- | --- |
| M0 (busca plana) | 0,46% | 1,39% | 1,19% | 3,19% |
| M2 (rede) | 3,21% | 3,35% | 4,84% | 4,91% |

Leitura, pela regra fixada antes: o acerto do M0 quase triplica quando vale a família (1,19% → 3,19%), e o do M2 praticamente não muda. **Cerca de metade da vantagem da rodada 7 vinha de a marcação apontar para o guia canônico.** A vantagem restante é real e grande: no top-5, 3,19% contra 4,91%, ou seja, 44% contra 68% do teto; no top-1, 1,39% contra 3,35%. A rede de confirmações ajuda a chegar à família certa do problema, mas não "4×".

**2. Juiz LLM na primeira sugestão (100 perguntas marcadas + 100 sem marcação)**

- **Juiz:** sensibilidade de 45% nas duplicatas marcadas e 0% de falsos positivos em pares aleatórios. Ele é rigoroso e recusa mais da metade das duplicatas que os moderadores aceitaram, sobretudo quando o alvo é um guia geral.
- **"Sim" bruto:** nas marcadas, M0 40,8% e M2 38,8%; nas sem marcação, M0 29,3% e M2 22,2%.
- **Pares discordantes (só M0 útil / só M2 útil):** 16/14 nas marcadas; 10/3 nas sem marcação.
- **Taxa corrigida e ponderada:** M0 0,669; M2 0,520; diferença −0,149, IC 95% \[−0,307; 0,000\].

Leitura, pela regra fixada antes: o IC encosta no zero. Não há evidência de que o M2 dê uma primeira sugestão mais útil, e há indício, no limite, de que ela seja pior. Nas perguntas marcadas, a marcação dá 42,9% de acerto no top-1 ao M2 contra 7,1% ao M0, mas o juiz considera as duas primeiras sugestões igualmente úteis (16 × 14). A perda aparece nas perguntas sem duplicata marcada, que são 92,8% do tráfego.

**Modo de falha visto nos exemplos:** quando a pergunta não pertence a nenhuma família, o M2 troca uma resposta específica e correta por uma pergunta popular de outra família. Exemplos: ícone do Spotify → indicador de e-mail; e-mail sobre o fim do Ubuntu One → erro de "mergelist"; ícones do Xubuntu → Unity não carrega. Quando acerta, recupera guias gerais que o juiz aceita: tela preta, 32 × 64 bits, instalação com Windows 8 e UEFI.

**Limites:** as duas medidas têm vieses opostos. A marcação favorece o guia canônico (M2). O juiz, com sensibilidade de 45%, favorece a pergunta específica quase idêntica (M0), e a correção pela sensibilidade provavelmente infla o nível do M0. O valor real está entre as duas medidas. A contagem 10 × 3 é pequena (teste de sinal, p ≈ 0,09).

**Conclusão exploratória:** a rede de ligações confirmadas melhora de forma real a chance de chegar à família certa do problema (+1,7 ponto no top-5 pela família). Porém, aplicada a toda pergunta, ela também puxa perguntas sem família para hubs populares. O problema é de precisão: o M2 não sabe quando não usar a rede.

## Rodada 8 — portão de familiaridade (registrada antes de rodar, 29/09/2026)

**Status:** exploratória, com critério fixado antes. Usa a mesma janela de avaliação das rodadas anteriores, e o desenho foi inspirado nos erros vistos no juiz comparativo. Por isso não é uma confirmação independente. As perguntas julgadas são novas: exclui as 320 usadas no juiz comparativo.

**Hipótese:** usar a rede só quando a pergunta nova de fato pertence a uma família mantém a maior parte do ganho de família do M2 sem piorar a primeira sugestão.

**Métodos** (V3, mesma rede e embeddings da rodada 7, β = 0,02):

- **M0:** busca plana. **M2:** rede em toda pergunta. Os dois são referências.
- **G(τ), método primário:** "caso parecido + família, com portão". As 5 sugestões intercalam as listas do M0 e do M2, sem repetir. O sinal do portão é g = evidência da rede para a 1ª sugestão do M2, sem o bônus de peso, menos a similaridade da 1ª sugestão plana. Se g ≥ τ, a ordem é M2-1, M0-1, M2-2, …; se não, é M0-1, M2-1, M0-2, …
- **H = G(+∞):** intercalado sem portão, com a 1ª sugestão sempre plana. É referência secundária.

**Calibração de τ** (só na janela de calibração, com rede cortada antes dela):

- Grade: −∞, −0,02, 0, 0,02, 0,04, 0,06, 0,08, 0,10, +∞.
- O juiz (gemma4, mesmo prompt) avalia a 1ª sugestão do M0 e a do M2 em 100 perguntas marcadas e 200 sem marcação (semente 88).
- Regra: entre os τ cuja diferença ponderada de "sim" bruto (G − M0) é ≥ 0, escolhe o de maior acerto pela família no top-5; no empate, o τ maior. O τ = +∞ sempre é admissível.

**Avaliação:**

- Acerto pela família sem LLM em todas as 2.412 perguntas marcadas da janela, dividido pelo total da janela.
- Juiz em 150 perguntas marcadas e 300 sem marcação, todas novas (semente 88). Controles: 60 pares marcados e 60 aleatórios.
- Julgamentos salvos em disco, retomáveis. Respostas inválidas não são salvas.

**Critérios (os dois precisam passar):**

- **C1:** acerto pela família no top-5 de G − M0 ≥ 1,0 ponto, com IC 95% (bootstrap por pergunta marcada, 2.000 reamostragens) acima de zero. Na rodada anterior, o M2 teve +1,72 ponto.
- **C2:** diferença ponderada de "sim" bruto na 1ª sugestão (G − M0), com limite inferior do IC 95% ≥ −0,03. Isso equivale a cerca de −0,07 na escala corrigida, com a sensibilidade de 45% observada.

**Secundários:** H e M2 nas mesmas medidas; o M2 no juiz também replica o achado anterior numa amostra nova. Também: acerto no top-1, frequência com que o portão troca a 1ª sugestão (marcadas e sem marcação), estimativa corrigida e exemplos.

**Leitura fixada agora:**

- **C1 e C2 passam:** a combinação "caso parecido + CID da família, com portão" mantém o ganho da rede sem custo na primeira resposta.
- **C2 passa e C1 falha:** o portão protege, mas a combinação perde ganho demais.
- **C2 falha:** o sinal escolhido não detecta quando a pergunta não tem família.
- **Se H ficar próximo de G:** o portão não acrescenta nada, e a versão simples (primeira sugestão plana + família) basta.

**Limites:** o juiz favorece a pergunta específica quase idêntica. Isso torna o C2 conservador para G. O teste com juiz simulado e embeddings substitutos serviu só para verificar o código; os números dele não têm valor.

## Diagnóstico 8b — relações ou bônus de popularidade? (registrado antes de rodar, 29/09/2026)

**Origem:** pergunta do GPT Astra. O M2 acrescenta duas coisas ao M0: as relações entre perguntas (ponte e centro do grupo) e um bônus de popularidade, β·ln(1+ligações), igual para qualquer pergunta nova. Com β = 0,02 e 535 ligações, o bônus é 0,02 × ln 536 ≈ 0,126. É exatamente o bônus observado no exemplo #24 da análise explicativa (tela preta). Concluir que "a rede não sabe quando ser usada" pode ser prematuro se o dano vier do bônus. Além disso, β foi escolhido pela régua da duplicata marcada, que favorece o guia canônico.

**Status:** exploratório e diagnóstico. Mesma janela de avaliação e mesmas perguntas julgadas da rodada 8 (semente 88). Reaproveita os julgamentos salvos e só julga os pares novos.

**Comparações:** M0 (busca plana), M1 (relações, β = 0) e M2 (relações + bônus, β = 0,02). Curva de β ∈ {0; 0,005; 0,01; 0,02; 0,04}.

- **A, sem LLM:** quando a 1ª sugestão do M2 difere da do M0, classificar a causa em três casos. Só o bônus: o M1 mantém a do M0. Só as relações: o M1 já escolhe a do M2. Os dois: o M1 escolhe uma terceira. Quando o bônus troca o 1º colocado, reportar a mediana do bônus líquido, a correspondência sacrificada e as ligações do vencedor. Também o acerto pela família de cada β.
- **B, juiz:** diferenças ponderadas de "sim" bruto na 1ª sugestão para M1 − M0, M2 − M0 e M2 − M1 (efeito do bônus), com IC 95%. Nos casos em que o M2 piorou em relação ao M0, a origem é o bônus se o M1 acerta e são as relações se o M1 também erra. O mesmo vale, ao contrário, nos casos em que o M2 melhorou.
- **C, curva de β na calibração:** qual β escolheria cada régua: duplicata marcada (a da rodada 7), família e juiz. No empate, o menor β. A curva na avaliação é só descritiva.
- **D, segundo juiz cego:** 40 perguntas em que a 1ª sugestão do M0 e a do M2 diferem, com as duas em ordem sorteada. O Claude rotula cada sugestão (resolve / não resolve) antes de abrir a chave. A chave fica em gc\_local\_bonus\_result.json, que só será lido depois da rotulagem. Mede a concordância com o gemma e a terceira situação do Astra: sugestões pertinentes que o juiz rejeita.

**Leitura fixada agora:**

- **O bônus é o problema** se o M1 passar no C2 da rodada 8 (limite inferior do IC de M1 − M0 ≥ −0,03) e M2 − M1 tiver IC abaixo de zero. Nesse caso, o conserto é a parte da pontuação, não a arquitetura. O passo seguinte seria um peso condicionado à pergunta, no lugar do bônus global.
- **As relações também prejudicam** se o limite inferior do IC de M1 − M0 ficar abaixo de −0,03.
- **O M1 preserva ganho suficiente** se passar no C1 da rodada 8 (família no top-5: M1 − M0 ≥ 1,0 ponto, IC > 0).
- **A calibração premiou o viés canônico** (hipótese do Astra) se o juiz escolher um β menor que o escolhido pela duplicata marcada.

**Nota de conceito:** o bônus atual é uma propriedade do nó ("fama"), igual para qualquer pergunta. Não é um peso de sinapse, que seria específico da ligação e do contexto. Um peso fiel à ideia original contaria só as confirmações próximas da pergunta nova.

## Rodada 8 — resultados (29/09/2026)

Rodado na máquina do Alexandre com gemma4: 1.445 julgamentos novos, 10 respostas inválidas, 24,9 min. A verificação passou: M0 e M2 reproduziram 1,19% e 4,84% na duplicata marcada. Juiz: sensibilidade de 46,7% e 0% de falsos positivos.

**Calibração:** τ = +0,02 foi o menor τ com diferença de juiz ≥ 0 (+0,0017). Com τ = 0 a diferença foi −0,0038; com −0,02, −0,018; com a 1ª sugestão sempre da rede, −0,118. O acerto pela família variou pouco entre os τ, de 5,70% a 5,84%.

**Avaliação:**

|  | família top-1 | família top-5 | "sim" do juiz na 1ª (marcadas / sem marcação) |
| --- | --- | --- | --- |
| M0 (busca plana) | 1,39% | 3,19% | 46,7% / 24,7% |
| M2 (rede em tudo) | 3,35% | 4,91% | 38,9% / 17,1% |
| G (τ = +0,02) | 1,67% | 4,60% | 47,3% / 24,3% |
| H (sem portão) | 1,39% | 4,59% | = M0 |

- **C1: passa.** Família top-5 de G − M0 = +1,41 ponto, IC \[+1,30; +1,53\].
- **C2: passa.** Diferença de juiz G − M0 = −0,0026, IC \[−0,0098; +0,0019\].
- **Rodada 8: passa** nos critérios fixados.

**Leitura, pela regra fixada antes:** H ficou praticamente igual a G no top-5 (4,59% contra 4,60%). O portão quase não dispara: troca a 1ª sugestão em 8,6% das perguntas marcadas e 2,8% das sem marcação. No top-1, ele recupera só +0,28 ponto de família, sem custo no juiz. **Quem passa, na prática, é a combinação "caso mais parecido primeiro + família intercalada"; o portão acrescenta pouco.** O C2 passou quase por construção, porque a 1ª sugestão de G é quase sempre a do M0. O resultado relevante é o C1: intercalar mantém 82% do ganho de família do M2 (+1,41 de +1,73 ponto; de 44% para 64% do teto) sem piorar a primeira resposta.

**Replicação do juiz comparativo, em amostra nova:** M2 − M0 = −0,077, IC \[−0,118; −0,031\], agora claramente abaixo de zero. Os pares discordantes foram 29 × 18 nas marcadas e 38 × 15 nas sem marcação. Aplicar a rede com bônus em toda pergunta piora a 1ª sugestão. O diagnóstico 8b vai separar quanto disso vem do bônus e quanto vem das relações.

**Limites:** é exploratório, na mesma janela das rodadas anteriores. O juiz favorece a pergunta específica. Falta uma confirmação em dados novos.

## Diagnóstico 8b — resultados (29/09/2026)

Rodado na máquina do Alexandre com gemma4: 991 julgamentos novos, 14 inválidos, 19 min. Os pares M0/M2 vieram dos julgamentos salvos na rodada 8.

**A. Quem troca o 1º colocado (sem LLM).** O M2 troca a 1ª sugestão do M0 em 85% das perguntas marcadas e em 68% das sem marcação.

| Causa da troca | Marcadas | Sem marcação |
| --- | --- | --- |
| Só o bônus | 54% | 72% |
| Relações e bônus | 23% | 16% |
| Só as relações | 23% | 12% |

Quando o bônus troca o vencedor, a mediana do bônus líquido é 0,09–0,10. Ele atropela uma vantagem de correspondência de 0,025 (marcadas) a 0,043 (sem marcação), e o vencedor tem em mediana 140 ligações.

**Família no top-5 (sem LLM, avaliação):** M0 3,19%; M1 4,16%; β 0,005 4,57%; β 0,01 4,79%; M2 (0,02) 4,91%; β 0,04 4,22%. M1 − M0 = +0,97 ponto, IC \[0,86; 1,08\]. M2 − M1 = +0,75 ponto. As relações respondem por 56% do ganho de família, e o bônus por 44%.

**B. Juiz na 1ª sugestão (diferença ponderada de "sim" bruto):**

- M1 − M0 = +0,0095, IC \[−0,012; +0,032\]. As relações sozinhas não pioram a 1ª sugestão.
- M2 − M1 (efeito do bônus) = −0,087, IC \[−0,129; −0,042\]. O bônus piora.
- M2 − M0 = −0,077, IC \[−0,118; −0,031\], o mesmo valor da rodada 8.
- **Origem das 67 pioras do M2:** bônus (o M1 acerta) em 56; relações e bônus em 7; só relações em 4.
- **Origem das 33 melhoras do M2:** bônus (o M1 erra) em 24; relações em 9. O saldo do bônus é de −32 casos em 450.

**C. Curva de β na calibração.** A régua da duplicata marcada escolhe 0,02; a da família também escolhe 0,02; a do juiz escolhe 0. As diferenças de juiz em relação ao M0 foram −0,014, −0,032, −0,043, −0,118 e −0,221 para β = 0, 0,005, 0,01, 0,02 e 0,04. Na avaliação, só descritiva, os β pequenos (0,005 e 0,01) aparecem positivos no juiz (+0,015 e +0,018). Isso contradiz a calibração e não pode ser usado para escolher β, porque seria escolher olhando o teste.

**Leitura, pela regra fixada antes:**

- **O bônus é o problema.** O M1 passa no C2 (limite inferior −0,012 ≥ −0,03), e M2 − M1 tem IC abaixo de zero.
- **As relações não prejudicam.** O limite inferior de M1 − M0 fica acima de −0,03.
- **O M1 não passa no C1 por pouco:** +0,97 ponto contra 1,0 exigido, com IC acima de zero.
- **A hipótese do Astra sobre a calibração se confirma.** A régua da rodada 7 escolheu β = 0,02, e o juiz escolheria β = 0.

O bônus tem dois gumes: dá 44% do ganho de família, porque ajuda a escolher o guia canônico dentro da família certa, e empurra guias famosos para perguntas de outras famílias. O guia de tela preta, com 535 ligações, aparece em perguntas sobre instalar servidor e desktop, drivers nvidia e HP dv6.

**Observação secundária:** o centro de uma família muito grande é genérico e eleva o guia mesmo sem bônus (ex.: própria 0,54 → com relações 0,71). No M1 isso raramente vence a pergunta específica.

**D. Segundo juiz cego: comprometido.** A chave estava dentro de gc\_local\_bonus\_result.json, que chegou e foi lido antes do arquivo cego. A rotulagem desses 40 pares não será feita. Uma nova amostra, excluindo esses 40 e com a chave em arquivo separado, fica para a próxima execução.

**Implicação:** o problema não é a rede, é um termo específico da pontuação, a "fama" global do nó. O próximo teste natural é um peso condicionado à pergunta, fiel à ideia de sinapse: contar só as confirmações do nó que são parecidas com a pergunta nova.

## Curvas de efeito de rede (registradas antes de rodar, 29/09/2026)

**Pergunta:** o sistema fica melhor quanto mais gente contribui, sem estabilizar cedo? É isso que separa "um truque melhor de busca" de uma memória compartilhada com efeito de rede.

**Status:** exploratório, sem LLM, na mesma janela de avaliação. As "aplicações" são simuladas repartindo ao acaso uma única comunidade; não são aplicações reais com domínios e estilos diferentes.

**Medida:** acerto pela família entre as 5 sugestões, nas 2.412 perguntas marcadas da janela, dividido pelo total da janela. A família-alvo é fixa, definida pela rede completa; na curva B, fica restrita às perguntas presentes na memória. Métodos: M0, M1 (relações sem bônus, o principal), M2 e H (M0 e M2 intercalados).

**Curva A, densidade de confirmações.** Todo o conteúdo fica na memória, e varia só a fração das ligações conhecidas: 0, 10, 25, 50, 75 e 100%, com 3 sorteios.

- Índice de saturação I = \[ganho(100%) − ganho(50%)\] / \[ganho(50%) − ganho(0)\], com IC por bootstrap.
- Leitura: I ≥ 0,7, sem sinal de saturação; 0,3 ≤ I < 0,7, desacelerando; I < 0,3, saturando.
- **Expectativa declarada:** saturação. Com o conteúdo fixo, quando uma família já está bem ligada, mais ligações acrescentam pouco. Saturação em A não significa ausência de efeito de rede; mostra quantas confirmações por família bastam.

**Curva B, participantes.** As perguntas antigas são repartidas ao acaso entre 10 aplicações. A memória contém as perguntas de 1, 2, 5 ou 10 aplicações e as ligações entre perguntas presentes (3 sorteios).

- **B1, ganho relativo das confirmações**, (M1 − M0)/M0, com 10 contra 5 aplicações. Se o IC da diferença estiver acima de zero, as confirmações valem proporcionalmente mais com mais participantes. Parte disso é esperada pela própria construção: uma ligação só existe quando as duas perguntas estão na memória, o mecanismo clássico de efeito de rede. A parte empírica é o tamanho.
- **B2, retornos por aplicação nova** (acerto somado por aplicação, em pontos) em H: de 5 para 10 contra de 1 para 2. São crescentes se o final for maior ou igual ao início.
- **B3, comparação de saturação:** quanto o ganho por aplicação cai do início ao fim na busca plana (M0) e na memória com confirmações (M1, H). Se a busca plana parar de melhorar antes, a vantagem da memória compartilhada cresce com a escala.

**Sinais fixados agora:**

- **Forte:** B1 positivo e, em H, o ganho por aplicação de 5 para 10 ≥ 50% do ganho de 1 para 2.
- **Moderado:** só B1 positivo.
- **Fraco:** B1 com IC incluindo zero.

**Verificação:** com 100% das ligações, a curva A precisa reproduzir M0 3,19%, M1 4,16%, M2 4,91% e H 4,59%.

**Teste do código** com embeddings substitutos (só para verificar o funcionamento; os valores não têm validade): reproduziu os valores conhecidos do substituto em 100% e deu M1 = M0 em 0%.

## Curvas de efeito de rede — resultados (29/09/2026)

Rodado na máquina do Alexandre em 4,4 min. A verificação passou: com 100% das ligações, M0 = 3,19%, M1 = 4,16%, M2 = 4,91% e H = 4,59%.

**Curva A, densidade de confirmações** (família no top-5 do M1; o M0 fica em 3,19% em toda a curva): 3,64% com 10% das ligações, 3,87% com 25%, 4,05% com 50%, 4,12% com 75% e 4,16% com 100%. O índice de saturação é 0,128, IC \[0,068; 0,195\], para o M1; 0,126 para o M2; 0,067 para o H. **Saturando,** como esperado: 10% das confirmações (≈ 1.000 ligações) já dão 46% do ganho do M1, e 25% dão 70%. Poucas confirmações por família bastam. Isso favorece o começo de uma memória nova e indica que o valor vem mais de cobrir famílias novas do que de adensar as antigas.

**Curva B, participantes:**

| Aplicações | M0 | M1 | H | Ganho relativo M1 | Ganho relativo H |
| --- | --- | --- | --- | --- | --- |
| 1 | 2,10% | 2,17% | 2,17% | +3% | +3% |
| 2 | 2,44% | 2,69% | 2,74% | +10% | +13% |
| 5 | 2,92% | 3,48% | 3,62% | +19% | +24% |
| 10 | 3,19% | 4,16% | 4,59% | +31% | +44% |

- **B1: positivo.** O ganho relativo com 10 contra 5 aplicações aumenta +0,116 no M1, IC \[0,080; 0,153\], e +0,205 no H, IC \[0,164; 0,249\]. As confirmações valem proporcionalmente mais com mais participantes. Parte disso é esperada pela construção: uma ligação precisa das duas perguntas presentes.
- **B2: retornos decrescentes.** Em H, o acerto somado por aplicação nova é 0,57 ponto de 1 para 2, 0,29 de 2 para 5 e 0,195 de 5 para 10. O final é 34% do início, abaixo dos 50% exigidos para sinal forte.
- **B3: a busca plana satura muito antes.** Por aplicação nova, de 1 para 2 e depois de 5 para 10: M0 0,332 → 0,052 (o fim é 16% do início); M1 0,516 → 0,136 (26%); H 0,57 → 0,195 (34%); M2 0,555 → 0,256 (46%). No fim da curva, cada aplicação nova acrescenta 3,75× mais em H do que na busca plana. Cerca de 73% do valor marginal de um novo participante vem da camada de confirmações (62% no M1).

**Leitura, pela regra fixada antes: sinal MODERADO de efeito de rede.** As confirmações valem proporcionalmente mais com mais participantes, mas o retorno total por participante novo é decrescente, como na maioria dos sistemas. O achado mais relevante para a ideia é o B3: com mais conteúdo, a busca comum para de melhorar, e a memória com confirmações continua melhorando. Em escala, a diferença vem cada vez mais das confirmações compartilhadas.

**Limites:** as aplicações são uma única comunidade repartida ao acaso. Aplicações reais têm domínios e estilos diferentes, o que reduz as ligações cruzadas e pode trazer famílias novas. É exploratório, na mesma janela das rodadas anteriores, e o teto da métrica é baixo (7,19%).

**Dados para a confirmação independente:** o dump do Stack Exchange de 02/04/2024 está disponível no Internet Archive: askubuntu.com com 1,0 GB, unix.stackexchange.com com 673 MB, superuser.com com 1,2 GB e serverfault.com com 820 MB. As duplicatas ficam em PostLinks (LinkTypeId = 3). Isso permite três testes: AskUbuntu de 2015 a 2024 (dados novos no mesmo domínio), outro site (domínio novo) e vários sites como aplicações reais.

## Confirmação independente — AskUbuntu 2020–2024 (pré-registrada, 29/09/2026)

**Objetivo:** confirmar, em dados nunca usados e com tudo congelado, os achados exploratórios das rodadas 7, 8 e 8b. Nada é recalibrado.

**Dados:**

- Dump público do Stack Exchange de 02/04/2024 (askubuntu.com.7z, Internet Archive). Perguntas: PostTypeId = 1. Duplicatas marcadas: PostLinks com LinkTypeId = 3, com a data da ligação.
- Perguntas ordenadas por data de criação. **Avaliação:** perguntas criadas a partir de 01/01/2020, que nunca foram vistas; o conjunto exploratório terminava por volta de 2014.
- **Memória:** todas as perguntas anteriores a cada pergunta nova. As ligações são as duplicatas marcadas antes de 01/01/2020 entre perguntas criadas antes dessa data.
- **Alvo:** duplicata marcada anterior (marcada) e essa duplicata mais as duplicatas já confirmadas dela na memória (família).

**Pré-processamento** (fixado): título + corpo, HTML removido, blocos pre truncados em 30 palavras, minúsculas, no máximo 200 palavras. Embeddings nomic-embed-text com os prefixos search\_query/search\_document.

**Diferenças em relação à fase exploratória, declaradas antes:** o grafo usa todas as duplicatas marcadas do site, não só o subconjunto de Lei et al., e por isso é mais denso e tem hubs maiores; o texto é tratado de outro jeito; e a amostra do juiz é maior.

**Métodos congelados:** M0 (busca plana), M1 (relações sem bônus), M2 (relações + bônus, β = 0,02) e H (M0 e M2 intercalados, da rodada 8). H1 (M0 e M1 intercalados) é só descritivo, porque nunca foi testado.

**Juiz:** gemma4 com o mesmo prompt, temperatura 0, sem raciocínio, 70 palavras de cada texto. Avalia a 1ª sugestão de M0, M1 e M2 em 200 perguntas marcadas e 400 sem marcação (semente 2025). Controles: 60 pares marcados e 60 aleatórios. Diferenças de "sim" bruto ponderadas pela proporção real dos grupos, com IC 95% por bootstrap.

**Critérios primários (os três precisam passar para CONFIRMAR):**

- **P1:** ganho relativo de família no top-5, (M1 − M0)/M0, com limite inferior do IC 95% acima de +10%.
- **P2:** diferença de juiz na 1ª sugestão, M1 − M0, com limite inferior do IC 95% ≥ −0,03.
- **P3:** ganho relativo de família no top-5, (H − M0)/M0, com limite inferior do IC 95% acima de +10%. A 1ª sugestão de H é a do M0 por construção.

**Secundários:**

- **S1, o bônus piora:** M2 − M1 no juiz, com limite superior do IC 95% abaixo de 0.
- **S2, artefato da régua:** razão entre família e marcada no M0 e no M2 (descritivo).
- **S3, segundo juiz cego:** 80 itens: 20 pares de duplicatas marcadas e 20 primeiras sugestões de cada método, M0, M1 e M2, com perguntas distintas e ordem sorteada. A chave fica em gc\_conf\_chave.json, arquivo separado que o Alexandre só envia depois que o Claude devolver os rótulos. São reportados a concordância com o gemma (% e kappa), a taxa de SIM do Claude nas duplicatas marcadas contra a do gemma e o SIM por método (descritivo, n = 20 cada). O resultado principal não traz exemplos das perguntas do conjunto cego.

**Leitura fixada agora:**

- **P1, P2 e P3 passam:** o achado central está confirmado em dados novos. As relações entre problemas confirmados aumentam a chance de chegar à família certa sem piorar a primeira sugestão, e o desenho intercalado funciona.
- **P1 ou P3 falham:** o ganho não se reproduz fora da janela exploratória.
- **P2 falha:** as relações também pioram a 1ª sugestão neste grafo mais denso.
- **Se o juiz cego mostrar que o gemma é muito mais rigoroso que o Claude:** as conclusões sobre a 1ª sugestão serão relidas com essa ressalva, mas os critérios não mudam.

**Teste do código:** um mini-dump sintético no formato do Stack Exchange, montado com os dados antigos (Posts.xml e PostLinks.xml com datas, respostas e ligações de outro tipo), mais um Ollama simulado, rodou de ponta a ponta. Também foram testadas a retomada no meio dos embeddings, a reprodutibilidade exata na segunda execução e a mensagem quando falta o dump. A extração do .7z não pôde ser testada aqui (sem acesso ao arquivo nem ao py7zr); o script tenta o programa 7z, depois o py7zr, e por fim dá instruções manuais.

### Revisão do pré-registro da confirmação, antes de qualquer execução (29/09/2026)

Três correções apontadas pelo GPT, todas aceitas. O script ainda não tinha sido rodado com dados reais.

**1. Juiz precisa passar nos controles.** Antes, um juiz quebrado (por exemplo, respondendo NO para tudo) empataria M1 e M0 e aprovaria o P2 sozinho. Agora o juiz só é válido com sensibilidade ≥ 0,30 nos pares marcados, falsos positivos ≤ 0,15 nos pares aleatórios e diferença entre os dois ≥ 0,25. Na fase exploratória, o gemma teve 0,45–0,47 e 0,00. Com o juiz reprovado, P2 e S1 viram "inconclusivo". A decisão passa a ter três valores:

- **NÃO:** P1 ou P3 falham.
- **INCONCLUSIVO:** P1 e P3 passam, mas o juiz foi reprovado.
- **SIM:** P1, P3 e P2 passam, com o juiz válido.

Foi testado com um juiz simulado que responde sempre NO: o resultado sai INCONCLUSIVO.

**2. Textos de época, sem informação futura.** O arquivo de 2024 traz a versão atual de cada pergunta, que pode ter sido editada depois de 2020, inclusive com a solução descoberta ou um aviso de duplicata. Escolha feita: **recuperar as versões históricas** a partir do histórico de edições (PostHistory.xml; tipos 1, 2, 4, 5, 7 e 8, texto em markdown).

- Perguntas criadas antes de 01/01/2020 entram na **versão vigente nessa data** (a última revisão anterior a ela).
- Perguntas novas e as da janela de avaliação entram na **versão inicial**, como foram escritas. Isso impede que o aviso de duplicata ou a solução editada depois vazem para a pergunta avaliada. Para perguntas da janela que servem de memória a perguntas posteriores, a versão inicial é conservadora: ignora edições feitas entre a criação e o momento da consulta.
- Perguntas sem histórico usam a versão atual, e o número delas é reportado.
- O markdown é limpo assim: blocos de código cercados ou indentados são truncados em 30 palavras, links viram só o texto, crases e marcação são removidas, e o resto segue como antes.
- Testado com um histórico sintético que tinha palavras-marcador em edições antes e depois de 2020. Nenhum marcador de edição posterior a 2020 apareceu em nenhum texto, e nenhuma edição apareceu nas perguntas de 2020 em diante.

**3. Tudo o que é reaproveitado é conferido.**

- **Dados lidos:** conferidos pela versão do pré-processamento, pela data de corte e pelo tamanho dos XML.
- **Embeddings:** conferidos por modelo, digest exato do modelo no Ollama, prefixo, número de linhas e SHA-256 dos textos.
- **Julgamentos:** o cache fica num arquivo cujo nome é a impressão digital de juiz, digest, prompt, tamanho do texto e SHA-256 dos dados.
- Se algo divergir, o script para e avisa. Testado adulterando o digest salvo. O resultado registra essas impressões digitais.

**Escopo, explicitado:**

- **Períodos:** a avaliação começa em 2020, não em 2015 como eu tinha dito na conversa. As perguntas de 2015 a 2019 também nunca foram usadas, mas entram só como memória, para a memória estar madura quando a avaliação começa.
- **O que não é medido:** o teste lê perguntas, não respostas. Pode confirmar recuperação e correspondência entre problemas. Não confirma que o problema foi resolvido nem que houve economia de trabalho.

## Hipótese: a IA como curadora da memória coletiva (Alexandre, 29/09/2026)

**Registro de autoria.** Ideia proposta por Alexandre em 29/09/2026 (horário omitido na versão pública), enquanto a confirmação independente rodava. Refinada na conversa com o Claude e registrada aqui como hipótese, ainda sem teste.

**A ideia, na formulação original:** hoje os humanos usam IAs, e modelos cada vez maiores, para gerar respostas, inclusive para problemas já resolvidos. O papel principal da IA deveria ser validar e confirmar o conteúdo de uma base compartilhada, aprimorando o Grande Cérebro, em vez de reprocessar tudo a cada pedido.

**Formulação refinada:** *gerar uma vez, validar muitas, reaproveitar sempre.* A IA gera só para o que é realmente novo. Para o que já existe, o papel central dela é de **curadoria**: confirmar ou refutar ligações entre problemas, detectar erros, consolidar famílias e registrar evidências. O Grande Cérebro deixa de ser um cache passivo e vira uma memória coletiva verificável, mantida ativamente.

**Por que se conecta aos resultados:**

- O ativo valioso são as confirmações: o ganho vem da informação "é o mesmo problema", que a busca comum não tem.
- Hoje essas confirmações são escassas porque dependem de moderadores humanos.
- Pela curva A, poucas confirmações por família bastam, e o valor está em cobrir famílias novas.

Uma IA curadora ataca exatamente esse gargalo: a memória que começa vazia e a cobertura de famílias novas.

**Correções incorporadas:**

1. **Não "exclusivamente".** Vale para problemas recorrentes com solução verificável (suporte técnico, erros de software, configuração, dúvidas frequentes), não para tarefas pessoais ou criativas únicas.
2. **Validar nem sempre é fácil.** O gemma recusou cerca de metade das duplicatas verdadeiras. O argumento econômico é a amortização: cada ligação é validada uma vez, até por um modelo caro, e reaproveitada muitas vezes. A validação mais forte continua sendo o resultado real ("resolveu"), não a opinião da IA.

**Riscos e exigências:**

- Propagação de erros: o componente gigante mostrou como uma ligação errada funde famílias.
- Monocultura: os vieses de um único modelo virando a verdade da base.
- Manipulação, e a IA confirmando conteúdo gerado por IA.
- **Exigências:** cada confirmação registra quem confirmou (humano ou IA, qual modelo e versão), com que confiança e com que evidência, e pode ser contestada; e mais de um validador independente. Com isso, a parte pública e auditável da proposta original deixa de ser opcional e vira indispensável.

**Ganhos para a humanidade, não medidos:**

- Menos computação e energia gastas regenerando respostas para problemas resolvidos.
- Soluções verificadas e com procedência, em vez de respostas novas e possivelmente inventadas.
- Acesso: uma base pública verificada usável por modelos pequenos e aparelhos baratos.

**Teste proposto** (exploratório; o desenho e os critérios serão pré-registrados antes de rodar e depois do teste cego do juiz, do qual depende):

- Nos dados exploratórios, a busca propõe pares candidatos, e o juiz local confirma ou recusa.
- As ligações confirmadas pela IA entram na memória, marcadas como "IA".
- Comparar três memórias — só ligações humanas, humanas + IA e só IA — pelas duas réguas: família no top-5 e juiz na 1ª sugestão.
- Medir também a precisão das ligações da IA contra as marcadas e a contaminação das famílias (tamanho e fusão de componentes).
- **Pergunta:** a IA validadora faz o Grande Cérebro crescer e melhorar sem se contaminar?

## Confirmação independente — resultados (29/09/2026)

Rodado na máquina do Alexandre em 93,6 minutos, com 1.313 julgamentos e 14 respostas inválidas. Os modelos ficaram registrados pelo digest: nomic-embed-text 0a109f42… e gemma4 c6eb396d…, com Ollama 0.30.10. SHA-256 dos dados: 951a20e2…

**Dados:** 414.451 perguntas; 96.333 na avaliação (2020 a março de 2024); 5.982 com duplicata marcada anterior (teto de 6,21%); 32.864 ligações na memória. Todas as perguntas tinham histórico de edições, então todos os textos estão na versão de época.

**Família no top-5, sem LLM:**

| Método | Família top-5 | Ganho relativo sobre M0 (IC 95%) | Marcada top-5 |
| --- | --- | --- | --- |
| M0 (busca plana) | 1,61% | — | 0,80% |
| M1 (relações, sem bônus) | 2,28% | +41,4% \[+36,7%; +45,9%\] | 1,90% |
| H (M0 e M2 intercalados) | 2,57% | +59,3% \[+54,2%; +65,0%\] | 2,45% |
| M2 (relações + bônus) | 2,84% | +76,0% \[+69,0%; +83,5%\] | 2,75% |
| H1 (M0 e M1 intercalados) | 2,12% | +31,3% \[+27,6%; +35,0%\] | 1,64% |

**Juiz (gemma4):** sensibilidade de 0,271 nas duplicatas marcadas e 0,000 de falsos positivos. **Reprovado pelo critério pré-registrado**, que exigia sensibilidade de pelo menos 0,30. Os falsos positivos e a diferença entre os dois passaram. Na fase exploratória, a sensibilidade tinha sido de 0,45 a 0,47; nestes dados o gemma foi ainda mais rigoroso.

**Critérios:**

- **P1: passa.** O limite inferior de M1 − M0 é +36,7%, bem acima de +10%.
- **P3: passa.** O limite inferior de H − M0 é +54,2%, bem acima de +10%.
- **P2: inconclusivo** (juiz reprovado). Registro descritivo, sem valor de critério: M1 − M0 no juiz = −0,019, IC \[−0,044; +0,004\]. Os pares discordantes foram 11 × 10 nas marcadas e 17 × 9 nas sem marcação (só M0 útil × só M1 útil). **Se o juiz tivesse sido aceito, o P2 teria falhado,** porque o limite inferior −0,044 fica abaixo de −0,03.
- **S1: inconclusivo** (juiz reprovado). Registro descritivo: M2 − M1 = −0,077, IC \[−0,116; −0,039\], na mesma direção da fase exploratória. Os exemplos repetem o padrão de puxar hubs: "black screen" com 551 ligações, "unmet dependencies" com 248, "what should I do when Ubuntu freezes" com 151.
- **CONFIRMA: INCONCLUSIVO**, pela regra fixada antes.

**Leitura:**

1. **Recuperação confirmada em dados nunca usados, com textos de época.** A rede de confirmações aumenta em 41% (M1) a 59% (H) a chance de achar a família certa entre 5 sugestões. Os ganhos relativos foram maiores que na fase exploratória (+30% e +44%), provavelmente porque a rede é mais densa. Os valores absolutos foram menores: 1,61% contra 3,19% no M0, com uma memória 2,5 vezes maior e textos tratados de outro jeito.
2. **O desenho H não depende do juiz.** A 1ª sugestão de H é a do M0 por construção. A afirmação "caso mais parecido primeiro, família intercalada: +59% de famílias encontradas sem mudar a primeira resposta" está confirmada.
3. **Em aberto:** se a rede sozinha (M1) pode dar a 1ª sugestão sem piorar. O juiz não é válido pela regra, e o que ele indica é uma leve piora, não significativa, que não atinge a margem de não inferioridade.

**S3, teste cego: comprometido de novo.** O Alexandre enviou gc\_conf\_chave.json junto com os outros dois arquivos, e o sistema abriu os três ao mesmo tempo antes da rotulagem. Esse conjunto não será rotulado. **Correção do procedimento:** nas próximas vezes, a chave nunca vem para o Claude. O Claude devolve os rótulos, e um script na máquina do Alexandre faz a comparação e retorna só os agregados.

## Etapa complementar: segundo juiz cego para o P2 (pré-registrada, 29/09/2026)

**Status:** complementar. O resultado oficial da confirmação continua INCONCLUSIVO e não será reclassificado. Esta etapa produz um "P2 complementar", reportado como tal, e mede a confiabilidade do gemma. Isso também interessa à hipótese da IA validadora.

**Quem julga:** o Claude, por meio de subagentes que recebem só a rubrica e os itens, em lotes. O Claude principal não altera rótulos; apenas junta os lotes. Declaração: o Claude principal conhece as hipóteses e o resultado agregado do gemma (M1 − M0 = −0,019), mas nenhum item individual. Os subagentes não conhecem nada além da rubrica.

**Cegamento, com o procedimento corrigido:** o script gc\_conf\_juiz2.py, na máquina do Alexandre, gera juiz2\_itens.txt (sem chave) e juiz2\_chave\_NAO\_ENVIAR.json. **A chave nunca é enviada.** O Claude devolve juiz2\_rotulos.json, e o mesmo script compara localmente e devolve só números agregados. O arquivo de itens é conferido por SHA-256 na comparação.

**Reprodução:** o script reconstrói exatamente as amostras e as 1as sugestões da confirmação, conferindo o SHA-256 dos dados e dos textos embutidos. Ele para se mais de 5% das sugestões não tiverem o julgamento do gemma salvo.

**Itens:**

- Todas as perguntas da amostra julgada (200 marcadas + 400 sem marcação, semente 2025) em que a 1ª sugestão do M0 e a do M1 diferem, com até 250 por grupo. Cada uma dá dois itens: (pergunta, sugestão do M0) e (pergunta, sugestão do M1).
- Excluídas: as perguntas do conjunto cego comprometido e os 10 exemplos mostrados no resultado.
- Controles: 40 pares de duplicatas marcadas (fora os 20 usados antes) e 40 pares aleatórios.
- Ordem sorteada (semente 31337); 90 palavras de cada texto.

**Rubrica, fixa:** "Uma resposta correta à pergunta B resolveria o problema da pergunta A? Responda SIM se o problema técnico central é o mesmo e a solução de B se aplicaria a A, mesmo com pequenas diferenças de versão ou de hardware; NÃO caso contrário." Todo item recebe SIM ou NÃO.

**Validade do segundo juiz:** as mesmas regras do gemma: sensibilidade ≥ 0,30, falsos positivos ≤ 0,15 e diferença ≥ 0,25, nos controles desta etapa.

**P2 complementar:** diferença ponderada de SIM na 1ª sugestão, M1 − M0.

- Por grupo: (fração de perguntas com 1ª sugestão diferente) × (média de SIM(M1) − SIM(M0) nessas perguntas).
- Pesos da confirmação: 0,0621 para marcadas e 0,9379 para sem marcação.
- IC 95% por bootstrap (2.000 reamostragens).
- **Passa** se o limite inferior do IC for ≥ −0,03. É inconclusivo se o Claude for reprovado nos controles.

**Também reportado:** o P2 recalculado com o gemma exatamente nos mesmos itens; a concordância Claude × gemma (% e kappa); a sensibilidade de cada um nos mesmos controles; e a taxa de SIM do gemma quando o Claude diz SIM e quando diz NÃO.

**Leitura fixada agora:**

- **Claude válido e P2 complementar passa:** a rede sem bônus pode dar a 1ª sugestão sem piorar, segundo um juiz válido.
- **Claude válido e P2 complementar falha:** a 1ª sugestão deve continuar com a busca plana, e o desenho H é o recomendado.
- **Claude reprovado:** a questão continua aberta.
- **Concordância com o gemma:** se for baixa, com o gemma dizendo NÃO onde o Claude diz SIM, o gemma é rígido demais para servir de validador na hipótese da IA curadora.

**Teste do código:** nos dados sintéticos, a geração e a comparação rodaram de ponta a ponta. A saída da comparação tem só números agregados; o script recusa rótulos incompletos e não gera os itens de novo sem --refazer.

## Etapa complementar: segundo juiz — resultados (29/09/2026)

**Execução:** 370 itens, com SHA-256 87d80f9b… conferido dos dois lados.

- 145 perguntas com 1ª sugestão diferente entre M0 e M1: 61 das 170 marcadas válidas e 84 das 360 sem marcação válidas. Cada uma deu 2 itens.
- Mais 40 controles positivos e 40 negativos.
- Rótulos: 8 subagentes Claude, lotes de 41 a 47 itens, só com a rubrica. Resultado: 134 SIM e 236 NÃO, juntados sem alteração.
- A comparação foi feita na máquina do Alexandre. A chave não foi enviada.

**Validade:**

- **Claude: sensibilidade 0,575 e falsos positivos 0,000. Válido.**
- **gemma, nos mesmos controles: sensibilidade 0,205 e falsos positivos 0,000. Reprovado de novo.**

**P2 complementar (Claude):** M1 − M0 = −0,019, IC 95% \[−0,048; +0,007\]. **Falha**, porque o limite inferior −0,048 fica abaixo de −0,03. Os pares discordantes (só M0 útil × só M1 útil) foram **8 × 13 nas marcadas**, a favor da rede, e **18 × 10 nas sem marcação**, a favor da busca plana. As sem marcação pesam 93,8%. O gemma, nos mesmos itens, deu −0,025, IC \[−0,050; −0,001\], na mesma direção.

**Concordância Claude × gemma:**

- 71,9% de acordo, kappa 0,33 (fraca) em 367 itens; nas sugestões, 69,8% de acordo e kappa 0,31.
- Quando o Claude diz SIM, o gemma diz SIM em 40%; quando o Claude diz NÃO, em 10%.
- SIM na 1ª sugestão: Claude 0,393 (M0) e 0,372 (M1); gemma 0,278 e 0,201.

**Leitura, pela regra fixada antes: "Claude válido e P2 complementar falha"**, ou seja, a 1ª sugestão deve continuar com a busca plana, e o desenho H é o recomendado.

- **Estado final da confirmação:** o resultado oficial continua INCONCLUSIVO, porque o juiz pré-registrado foi reprovado. Pela etapa complementar, com um juiz válido, não se demonstra que a rede sozinha possa dar a 1ª sugestão sem piorar. A estimativa é de uma perda pequena (−1,9 ponto ponderado), não significativa.
- **Padrão coerente com todo o projeto:** quando a pergunta nova pertence a uma família conhecida (marcadas), a rede ajuda até na 1ª sugestão (13 × 8). Quando não pertence (a maior parte do tráfego), a atração da rede, mesmo sem bônus, atrapalha um pouco (10 × 18).
- **Afirmações confirmadas em dados independentes:** a rede de confirmações aumenta em 41% a 59% a chance de achar a família certa entre 5 sugestões. O desenho "caso mais parecido primeiro + família intercalada" (H) faz isso sem mudar a 1ª sugestão.
- **Para a hipótese da IA curadora:** um validador pequeno e local (gemma4) é rígido demais para confirmar ligações. Ele aceita só cerca de 20% das duplicatas verdadeiras, e o kappa com um juiz válido é de 0,33. Um validador mais forte (nível Claude) passou nos controles. A correção "validar nem sempre é fácil" está confirmada na prática. Nenhum dos dois juizes aceitou pares aleatórios.

## Correções de interpretação (29/09/2026, após revisão do GPT Astra)

As quatro correções foram aceitas. Elas substituem as interpretações das seções "Confirmação independente — resultados" e "Segundo juiz — resultados". Os números e as decisões pelas regras pré-registradas não mudam.

**1. "Sem duplicata marcada" não significa "fora de uma família conhecida".** Uma pergunta sem marcação pode ter uma relação que ninguém marcou. O dado é este: nas perguntas com marcação, os discordantes favoreceram M1 (13 × 8); nas sem marcação, favoreceram M0 (18 × 10). A explicação "a rede ajuda quem pertence a uma família conhecida e atrapalha quem não pertence" é **uma hipótese**, não uma conclusão.

**2. Não demonstrar que mantém a qualidade não é demonstrar que piora.** O IC de M1 − M0, de −4,8 a +0,7 pontos, é compatível tanto com uma piora relevante quanto com uma diferença desprezível. Formulação correta: **ainda não há segurança suficiente para deixar M1 escolher a 1ª sugestão; manter a busca comum em primeiro é uma decisão prudente.** Frases anteriores como "atrapalha um pouco" e "é ruim para escolher a primeira resposta" estão retiradas.

**3. O segundo juiz passou nos controles; isso não o valida como curador.** Rejeitar pares aleatórios é um teste relativamente fácil. O desafio da curadoria são perguntas muito parecidas que exigem soluções diferentes (por exemplo, falha de conexão por senha errada × por driver). E a concordância entre duas IAs não diz qual delas está certa. Formulações corretas:

- "O segundo juiz passou nos controles desta avaliação; sua capacidade de criar ligações confiáveis ainda precisa ser testada."
- "A reprovação do gemma vale para a configuração testada (modelo, prompt, 70 palavras, sem raciocínio), não para todo modelo pequeno ou local."

A frase anterior "um validador mais forte funcionou" está retirada.

**4. O ganho demonstrado é encontrar discussões, não soluções verificadas.** Formulação pública adotada:

> Em perguntas novas do AskUbuntu (2020–2024, nunca usadas na fase exploratória), aproveitar relações de duplicata registradas anteriormente aumentou a recuperação de discussões da família marcada entre cinco sugestões. A combinação intercalada passou de 1,61% para 2,57% das perguntas novas (+59% relativo, IC do ganho relativo de +54% a +65%), preservando a primeira sugestão da busca comum. Ainda não medimos resolução efetiva nem economia de trabalho.

**Consequência para o teste da IA curadora:** o teste decisivo deve verificar se a IA cria ligações corretas **em casos difíceis** (pares muito parecidos com soluções diferentes), com avaliação independente, **antes** de permitir que essas ligações influenciem outras respostas. Uma fonte possível de negativos difíceis com evidência: pares muito parecidos de famílias confirmadas distintas (alvos canônicos diferentes e não ligados). Mesmo assim, "não ligados" não prova "diferentes", e isso precisa entrar no desenho.

## Notas de publicação (29/09/2026)

Acrescentadas ao preparar a versão pública, depois de uma revisão separada da documentação, feita por outro agente Claude que não a escreveu. Não alteram resultados.

- **Origem desta cópia.** Exportação da revisão 75 do documento vivo em que o protocolo foi mantido. O documento foi editado pelo Claude e estava acessível ao autor, com datas no nível do dia. Ele não teve carimbo de tempo externo antes desta publicação, que é o primeiro registro público datado.
- **Três alterações nesta cópia:**
  - a menção de autoria do cabeçalho foi trocada pelo nome do autor;
  - o horário e o fuso da seção da hipótese da IA curadora foram omitidos por privacidade (a data foi mantida);
  - estas notas foram acrescentadas.
- **Frases retiradas nas correções de interpretação.** Parte delas foi dita na conversa que acompanhou o trabalho, não neste protocolo. É o caso de "é ruim para escolher a primeira resposta" e de "um validador mais forte funcionou". As formulações próximas que aparecem aqui, como "atrapalha um pouco" e "um validador mais forte (nível Claude) passou nos controles", ficam substituídas pela errata.
- **Onde cada etapa rodou.**
  - Rodadas 1 a 5 (modelos scikit-learn, TF-IDF e os vetores de palavras pré-treinados do conjunto): no ambiente de nuvem do assistente.
  - Da rodada 6 em diante, os embeddings e os juízes LLM via Ollama: na máquina do autor.
  - A rotulagem do segundo juiz: feita por subagentes do Claude no ambiente do assistente, com a chave guardada na máquina do autor.
- **Tempo da confirmação.** Dos 93,6 minutos da confirmação, a etapa de embeddings foi estimada pelo próprio terminal em cerca de 62 minutos, pela saída enviada pelo autor.
- **Tempos da rodada 1.** Os tempos por turno da tabela da rodada 1 (2,0/4,3 ms e 2,1/3,1 ms) diferem dos de `v0_dev_summary.json` (1,88/2,19 e 1,91/2,17 ms). O arquivo publicado vem de outra execução. Tempo não era critério.
- **Texto de terceiros removido.**
  - Os arquivos de itens às cegas e de exemplos, e os campos de exemplos de quatro arquivos de resultado, continham trechos de perguntas do askubuntu.com. Eles foram retirados da versão pública e substituídos pelos SHA-256 dos originais, que o autor guarda.
  - Os scripts podem produzi-los de novo com os mesmos modelos e os caches locais das execuções originais. Não há garantia de regeneração idêntica bit a bit em outra máquina.
  - As saídas por turno `v0_dev_turns.jsonl` e `r2_dev_turns.jsonl` contêm texto do SGD e também não foram incluídas.
- **Artefatos da exportação.** "&#91;embedded content…]" marca um diagrama que não foi exportado. O título "Decisões em aberto" repetido é um deslize de formatação do original.
