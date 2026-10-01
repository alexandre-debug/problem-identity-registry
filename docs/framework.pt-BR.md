# Framework: um registro compartilhado de identidades de problemas

**Autor:** Alexandre Cardoso Rego · versão 0.2.2 · 1º de outubro de 2026 (primeira versão em 29 de setembro de 2026) · [English](framework.md)

As seções 1 e 2 descrevem a motivação e o desenho. Da seção 3 em diante, cada ponto leva um de quatro rótulos:

- **[Evidência]** foi medido, e o registro dos experimentos diz onde.
- **[Interpretação]** é a nossa leitura da evidência; é plausível, mas não foi medida diretamente.
- **[Hipótese]** é uma afirmação testável que ainda não foi testada.
- **[Proposta]** é uma escolha de projeto, não uma afirmação sobre o mundo.

---

## 1. Motivação

Pessoas e sistemas de IA continuam resolvendo problemas que já foram resolvidos em outro lugar. As soluções ficam em fóruns, chamados e conversas privadas, onde é difícil encontrá-las de novo. Com os modelos de linguagem, problemas repetidos também são regenerados do zero, com custo de computação e o risco de uma resposta diferente, possivelmente errada, a cada vez.

O projeto faz uma pergunta simples: **e se problemas recorrentes tivessem uma identidade própria, compartilhada entre aplicações, para que soluções conhecidas pudessem ser encontradas e reaproveitadas?**

## 2. Conceitos centrais [Proposta]

**Identidade de problema.** Um identificador persistente que agrupa **situações consideradas equivalentes segundo critérios explícitos**, como o mesmo sintoma, a mesma causa e o mesmo contexto. **Os procedimentos (soluções) ficam ligados a essas situações**, cada um com as condições em que se aplica.

- A identidade **não** é definida por compartilhar uma solução. Um procedimento amplo pode servir a problemas diferentes, como os guias gerais "guarda-chuva" fizeram nos experimentos (seção 3.5).
- O identificador faz o papel que o CID tem para doenças ou o CVE para falhas de segurança, aplicado a problemas técnicos do dia a dia.
- Ele não é atribuído por uma autoridade central. Surge das confirmações, cujos tipos são definidos abaixo.

**Confirmação (ligação).** Uma afirmação de que dois problemas relatados estão relacionados, guardada com:

- um **tipo**: *mesmo problema*, *a mesma solução serve* ou *relacionado*. Eles se comportam de jeitos diferentes: "mesmo problema" é quase transitivo, "a mesma solução serve" não é;
- **procedência**: quem confirmou (uma pessoa, ou um sistema de IA com modelo e versão), quando e com que evidência. A evidência mais forte é um resultado ("isso resolveu"), não uma opinião;
- uma **confiança** e a possibilidade de ser **contestada** e corrigida, com histórico.

**Registro.** Um repositório compartilhado de identidades e confirmações, usado por várias aplicações. É auditável sempre que o conteúdo permitir. Problemas privados entram só com consentimento e anonimização.

**Camada de busca.** Como uma aplicação usa o registro quando chega um problema novo. O desenho sustentado hoje pela evidência está na seção 3.

## 3. O que os experimentos ensinaram sobre o desenho

1. **Relações confirmadas ajudam a encontrar a família certa de problemas. [Evidência, confirmada em dados independentes]**
   - Em perguntas do AskUbuntu de 2020 a 2024, acrescentar relações de duplicata confirmadas à busca semântica comum aumentou em 41% (só relações) a 59% (desenho intercalado) a recuperação da família marcada entre cinco sugestões.
   - São discussões, não soluções verificadas.
2. **Manter o caso mais parecido em primeiro e acrescentar a família em volta. [Evidência mais uma decisão prudente]**
   - O desenho intercalado mantém a primeira sugestão idêntica à da busca comum.
   - Se a rede sozinha pode escolher com segurança a primeira sugestão continua sem resposta: o intervalo do juiz que passou nos controles vai de −4,8 a +0,7 pontos.
   - **Preservar a primeira sugestão não garante preservar a qualidade da resposta final. [Evidência, rodada 9]** Nas perguntas do AskUbuntu sem duplicata marcada, as respostas escritas com o contexto do H (primeira sugestão idêntica à da busca comum) não passaram na margem pré-registrada de não inferioridade frente à busca comum: −0,070 [−0,138; 0,000]. As outras sugestões também entram no contexto e podem atrapalhar. [Interpretação]
3. **Um peso global de popularidade tem dois gumes. [Evidência, exploratória; mesma direção, de forma descritiva, na confirmação]**
   - Um bônus pelo número de ligações de um nó, uma espécie de "fama", puxava guias gerais famosos para perguntas de outros assuntos. Foi a principal fonte de dano à primeira sugestão (56 de 67 casos piorados no diagnóstico exploratório).
   - O mesmo termo respondeu por 44% do ganho de família nesse diagnóstico. [Evidência, exploratória] A nossa leitura é que ele traz para a lista os guias de referência da família. [Interpretação]
   - O desenho confirmado H, definido na rodada 8, antes desse diagnóstico, usa o M2 só depois da primeira sugestão da busca comum. Sem o termo (H1, reportado de forma descritiva na confirmação), o ganho é de +31% em vez de +59%.
   - **Nas respostas finais, retirar o termo ajudou em relação ao H. [Evidência, pré-registrada, rodada 11, só no Super User]** Nas perguntas sem duplicata marcada, as respostas com o contexto do H1 foram preferidas às do H: +0,060 [+0,013; +0,109]. Nas perguntas elegíveis, o H1 ficou dentro da margem de 3 pontos frente à busca comum (+0,006 [−0,016; +0,029]). A superioridade do H1 sobre a busca comum **não** foi demonstrada, e essa comparação ainda não foi feita no AskUbuntu.
4. **O peso deve depender do contexto. [Proposta / Hipótese]**
   - Uma ligação, ou um nó, só deve ganhar peso a partir de confirmações parecidas com o problema novo.
   - É a versão formal da intuição original das "sinapses", próxima da ativação por propagação nos modelos cognitivos de memória e do PageRank personalizado na teoria de grafos.
5. **Identidade não é o fecho transitivo das ligações. [Evidência]**
   - Encadear confirmações juntou 3.712 perguntas do AskUbuntu num grupo gigante, através de poucos guias "guarda-chuva".
   - As identidades devem vir de uma partição que tolere confirmações ruidosas e contraditórias; o correlation clustering é uma formalização natural. [Proposta]
6. **No AskUbuntu, "duplicata" muitas vezes significa "as respostas de lá resolvem isto". [Interpretação]**
   - Isso é mais próximo de "a mesma solução serve" do que de "mesmo problema", e é um dos motivos para as ligações terem tipos.
7. **Uma fração das ligações capturou boa parte do ganho.**
   - Com o conteúdo fixo, retirando ligações ao acaso da rede inteira, 10% das confirmações deram cerca de metade do ganho, e 25% deram 70%. [Evidência, exploratória]
   - Esse teste reduziu as ligações da rede inteira. Ele não determina quantas confirmações cada família precisa. *Correção (1º/10/2026): a versão 0.1.1 dizia "poucas confirmações por família capturam a maior parte do valor", o que ia além do teste.*
   - Priorizar famílias novas em vez de adensar as antigas continua sendo uma hipótese. [Hipótese]
8. **O sinal de efeito de rede é moderado. [Evidência, simulação exploratória]**
   - Com uma comunidade dividida em dez aplicações simuladas, as confirmações valeram proporcionalmente mais à medida que mais aplicações entravam: ganho relativo de +3% com uma, +31% com dez. Parte disso é esperada pela própria construção, porque uma ligação só existe quando as duas perguntas estão na memória.
   - No fim da curva, a busca comum ganhou bem menos por aplicação acrescentada do que a memória com confirmações: 0,052 ponto contra 0,195 do H.
   - O ganho absoluto de cada aplicação nova continuou diminuindo.
9. **A rede ajuda a resposta quando traz a família certa, e saber de antemão quando isso vai acontecer não foi atingido. [Evidência, pré-registrada, rodadas 9 e 10]**
   - Rodada 9 (AskUbuntu): quando o desenho intercalado trouxe a família marcada que a busca comum perdeu, os juízes preferiram as respostas dele: +0,153 [+0,024; +0,282], 124 perguntas.
   - Rodada 10: um portão baseado em quanto o candidato da rede superava a busca comum não pôde ser calibrado para esse sinal, essa grade e essas exigências.
   - São preferências de um juiz cego, guiado pela resposta aceita por quem perguntou, e não problemas verificados como resolvidos.
10. **Ganhos menores numa rede mais esparsa. [Evidência, rodada 10]** No Super User, onde só 1,89% das perguntas novas têm uma duplicata marcada anterior, as relações melhoraram muito menos a recuperação do que no AskUbuntu (M1 +15,5% contra +41,4%). Isso compara dois sites; não isola o efeito da esparsidade.

## 4. Hipótese: a IA como curadora da memória coletiva

*Proposta por Alexandre Cardoso Rego em 29 de setembro de 2026. Registrada como hipótese; ainda não testada.* **[Hipótese]**

**Formulação original.** Hoje, as pessoas usam IAs, e modelos cada vez maiores, para gerar respostas, inclusive para problemas já resolvidos. O papel principal da IA deveria ser validar e confirmar o conteúdo de uma base compartilhada, aprimorando-a, em vez de reprocessar tudo a cada pedido.

**Formulação refinada: gerar uma vez, validar muitas, reaproveitar sempre.** A IA gera só para o que é realmente novo. Para o que já existe, o papel central dela é de curadoria:

- confirmar ou refutar ligações;
- detectar erros;
- consolidar famílias;
- registrar evidências.

O registro deixa de ser um cache passivo e vira uma memória coletiva verificável, mantida ativamente.

**Por que se conecta aos resultados.** O valor medido vem das confirmações, e elas são escassas porque dependem de moderadores humanos. Uma IA curadora pode reduzir a dependência de moderação humana para ampliar a rede. Mesmo um bom curador só julga as candidatas que a busca traz, e famílias raras podem continuar descobertas. *Correção (1º/10/2026): a versão 0.1.1 dizia que uma IA curadora "ataca exatamente esse gargalo", o que é mais forte do que a evidência permite.*

**Correções incorporadas.**

1. **Não "exclusivamente".** Vale para problemas recorrentes com solução verificável, como suporte técnico, erros de software e configuração. Não vale para tarefas únicas, pessoais ou criativas.
2. **Validar nem sempre é fácil.**
   - Na confirmação, um juiz local pequeno, na configuração testada (gemma4, prompt fixo, trechos de 70 palavras), reconheceu só cerca de um quarto das duplicatas verdadeiras. Isso vale para essa configuração, não para todo modelo pequeno ou local.
   - O argumento econômico é a amortização: uma ligação é validada uma vez, mesmo por um modelo caro, e reaproveitada muitas vezes.
3. **Passar em controles fáceis não valida uma IA como curadora.** Rejeitar pares aleatórios é fácil. O teste decisivo é se a curadora cria ligações corretas em casos difíceis: problemas muito parecidos que pedem soluções diferentes. Esse teste exige avaliação independente, antes de deixar ligações criadas por IA influenciarem outras respostas.

**Riscos e exigências.**

- **Riscos:**
  - erros que se propagam pelas ligações;
  - monocultura, em que os vieses de um único modelo viram a "verdade" da base;
  - manipulação;
  - IA confirmando conteúdo gerado por IA.
- **Exigências:**
  - procedência em cada confirmação;
  - mais de um validador independente;
  - evidência de resultado sempre que possível;
  - direito de contestação.

Essas exigências tornam o caráter público e auditável do registro indispensável, não opcional.

**Ganhos possíveis (não medidos).**

- Menos computação e energia gastas regenerando respostas para problemas resolvidos.
- Respostas com procedência, em vez de respostas novas, possivelmente inventadas.
- Acesso: uma base pública verificada que modelos pequenos e aparelhos baratos poderiam usar.

## 5. Governança e riscos [Proposta]

- **Propagação de erros.** Ligações não são transitivas por padrão; fundir grupos exige evidência mais forte que uma ligação isolada.
- **Manipulação.** Alguém pode plantar ligações falsas ou criar variações para escapar das verdadeiras. As defesas são procedência, validação independente e contestação.
- **Privacidade.** Os problemas muitas vezes vêm de contextos pessoais. O conteúdo só entra com consentimento e anonimização.
- **Concentração de autoridade.** Quem controla o validador define o que conta como "o mesmo". A governança deve ser independente e auditável.

## 6. Além do suporte técnico [Hipótese]

O mecanismo geral, dar identidade a coisas que aparecem espalhadas em várias fontes por meio de ligações confirmadas "isto é o mesmo que aquilo", pode servir em outras áreas. Cada uso traz riscos sérios próprios.

- **Checagem de fatos.** Reconhecer que uma afirmação nova é a mesma que já foi checada, com outras palavras.
- **Direito.** Os tribunais já agrupam casos repetitivos em temas numerados; uma identidade compartilhada de questões jurídicas generaliza isso.
- **Administração pública.** Compartilhar quais problemas outros municípios resolveram, e como.
- **Controle de registros públicos, inclusive contra a corrupção.** Ligar a mesma pessoa, empresa ou contrato em bases fragmentadas.
  - Uma ligação automática pode destruir a reputação de um inocente.
  - A mesma ferramenta pode servir para perseguição.
  - Um sistema assim deve gerar pistas para investigação, nunca acusações, com fortes salvaguardas legais e governança independente.

Nenhum desses usos foi testado aqui.

## 7. Relação com trabalhos existentes

Muitas peças já existem:

- sistemas de identificadores (CID, CVE);
- agrupamento de travamentos que reúne falhas idênticas de milhões de computadores;
- bancos de "erros conhecidos" do suporte de TI;
- detecção de perguntas duplicadas em comunidades de perguntas e respostas;
- caches semânticos e camadas de memória para agentes de IA;
- busca baseada em grupos de documentos;
- a literatura sobre viés de popularidade e sobre hubs em espaços de alta dimensão.

O que parece incomum é a combinação: um **registro de identidades de problemas entre aplicações, público e auditável, com curadoria assistida por IA**, junto com evidência pré-registrada do que ajuda e do que atrapalha. Nenhuma prioridade é reivindicada além do registro datado neste repositório.

## 8. Próximos experimentos

1. **Ligações sobre uma busca híbrida (rodada 12, congelada e publicada antes de rodar):** as ligações confirmadas ainda acrescentam algo a uma fusão da busca por palavras (BM25) com um modelo de embeddings selecionado por um piloto em dados exploratórios?
2. **IA curadora em casos difíceis (rodada 13, rascunho):** um modelo local de baixo custo consegue criar ligações corretas do tipo "as respostas de B resolvem A" entre perguntas muito parecidas, sob avaliação independente, e como isso se compara com treinar uma métrica com os mesmos pares?
3. **Pesos de contexto:** ativação por propagação ou PageRank personalizado a partir da pergunta, no lugar da popularidade global. O objetivo é manter o benefício do termo de popularidade na recuperação sem o prejuízo.
4. **Identidade como correlation clustering**, no lugar da vizinhança de um passo.
5. **Entre aplicações reais:** sites diferentes do Stack Exchange, ou issues duplicadas entre repositórios do GitHub.
6. **Resolução e economia:** as rodadas 9 a 11 mediram as preferências de um juiz cego entre respostas finais. Se os problemas são de fato resolvidos, se há trabalho poupado e se o custo total cai continua em aberto.
