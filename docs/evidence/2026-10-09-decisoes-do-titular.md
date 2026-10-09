# 2026-10-09 — Decisões do titular, registradas como decisões

Este documento registra seis decisões do titular e a regra final que as governa.
Nada aqui é implementação, prova ou escala promovida — e essa separação é a
própria regra final, nas palavras dele: **"Decisão, execução e comprovação são
estados distintos."**

O genoma não tem tipo de nó para decisão, e criar um subiria o denominador, que
está congelado em 30. Então cada decisão entra onde ela age: nas incógnitas que
ela instrui, e em afirmações que ficam **UNPROVEN** até a prova existir.

---

## D-TOPOLOGIA — e uma divergência de rótulo que precisa da sua palavra

**O que o titular decidiu, nas palavras dele:** duas pontas completas de
autoridade em um provedor principal e uma Testemunha mínima em segundo provedor,
com domínio administrativo e faturamento independentes. Falha da Testemunha
produz `UNOBSERVABLE`, sem promoção automática. Autoriza implementação, testes e
coleta de evidências; **não** autoriza declarar REGIONAL comprovada. `CLM-0006`,
`CLM-0007` e `UNK-0001` seguem pendentes.

**Uma parte disso já está satisfeita e provada.** A exigência de que a falha da
Testemunha produza `UNOBSERVABLE` sem promoção automática é o comportamento
atual, medido: `ACTIVE_UNOBSERVABLE` existe, e a nota da `PRF-0061` descreve o
que ele corrigiu — *"antes, Testemunha sem rota até a Ativa tinha de escolher
entre sã e morta, escolheria morta, e ACTIVE_DOWN com concordância PROMOVE"*.
Essa metade da decisão não espera trabalho; espera só ser lida como já feita.

**E agora a divergência.** O título diz "Opção B", e a Opção B do ADR-003 não
está no eixo que a decisão descreve. Lido no §3 do
`liceu-protocol/docs/ADR-003-replicacao-do-estado-de-autoridade.md`:

> **B — protocolo de consenso (Raft/etcd) para a camada A.** Só o estado de
> arbitragem vive num cluster de consenso com **3 nós em 3 domínios**.

A decisão do titular descreve **hospedagem e faturamento**; a Opção B do ADR
descreve **mecanismo de replicação**. São eixos diferentes, e três tensões
aparecem quando se tenta sobrepor um ao outro — todas escritas no próprio ADR,
antes desta decisão existir:

**1. O quórum.** O §7.2 pergunta "A Testemunha vota?" e responde:

> Em B, é nó de consenso. A Constituição diz "só informa". Ou se separa em
> contrato *votar no log* de *autorizar atos*, ou a Testemunha fica fora do
> quórum (2 nós de consenso + 1 observador — e 2 nós não têm maioria numa
> partição: volta-se a "duas Mães sem quórum", que a própria Constituição
> reconhece).

"Testemunha **mínima**" e "sem promoção automática" apontam para observador, não
para nó votante. Então a decisão, como está escrita, cai exatamente no caso que
o ADR nomeia como regresso a duas Mães sem quórum.

**2. Os dois nós votantes no mesmo provedor.** B pede 3 nós em **3** domínios. A
decisão põe as duas pontas completas num provedor principal e só a Testemunha
noutro: são **2** domínios. Se o provedor principal cair, a maioria cai com ele,
e a Testemunha sozinha não avança época — o que é seguro (fail-closed) e
indisponível. Isso não contradiz a decisão; contradiz o rótulo.

**3. O tamanho da ponta.** O §7.1 diz que B pede a forma menor:

> Três Mães = três CORE completos (cada um com kit, boundary, store) ou um
> control plane extraído do CORE (só a camada A) e um CORE por domínio
> consumindo-o? **A segunda é menor e é a que B pede.**

"Duas pontas **completas**" é a primeira leitura, não a segunda.

**E uma pergunta que a decisão não responde**, §7.5: em B a promoção não
planejada passa a existir (o lease expira e a sucessora propõe), e a Constituição
deixa `modo: A DEFINIR`. A decisão proíbe promoção automática **na falha da
Testemunha** — que é outro evento. O caso do lease da Ativa segue aberto.

**O que eu registrei:** a decisão **como ela foi escrita**, no eixo da
hospedagem, e não o rótulo "Opção B" com os compromissos do §3 embutidos.
Registrar "Opção B" importaria etcd/Raft, 3 domínios votantes e um cliente de
consenso no caminho crítico de publish — nada disso está na decisão, e a parte
do quórum a contradiz. **Qual leitura governa é sua palavra**, e até ela chegar a
`UNK-0001` guarda as duas.

---

## D-CREDENCIAL — preservar o histórico, e não confundir duas credenciais

**Decisão proposta** (a palavra é do titular): preservar o histórico Git, sem
reescrita neste momento. Ele declara não haver reutilização conhecida da
credencial fora dos 19 repositórios e ser o único operador atual.

Nada foi reescrito, então a decisão coincide com o estado atual e não exige ato.

**Os quatro critérios de encerramento, como ele os escreveu:** identificação do
escopo, rotação/revogação efetiva, prova de rejeição da credencial antiga e
registro explícito do risco residual.

**Um deles não é alcançável hoje, e isso tem de ficar dito.** A "prova de
rejeição" exige um serviço que aceite ou recuse a credencial. Medido em
2026-10-02: nenhum arquivo de ambiente, em nenhum dos 19 repositórios, atribui
valor a `CANONICAL_EVENT_STORE_API_SECRET` — as duas atribuições existentes
estão em `.env.example` e são vazias. Com a `CLM-0062` REFUTED, não há ambiente
implantado. A prova de revogação sobre essa credencial devolveria
`NAO_MENSURAVEL`, que é o resultado certo e não um resultado baixo. Logo o
incidente **não pode ser encerrado** sob esses critérios até existir ambiente —
e é por isso que a `CLM-0084` entra UNPROVEN em vez de entrar provada.

**E a instrução de não confundir está certa, com evidência de que são
diferentes.** As duas credenciais têm impressão distinta, nome distinto e
repositório distinto:

| | credencial do incidente | credencial da cerimônia |
|---|---|---|
| nome | `CANONICAL_EVENT_STORE_API_SECRET` | `LEGAL_AI_OPENAI_API_KEY` |
| impressão | `402f633e52d80787…` | `718983711cbbbc2f…` |
| forma | 11 caracteres, escolhida por pessoa | 164 caracteres, `sk-proj-` |
| provedor | nenhum | OpenAI |

A rotação provada na `PRF-0108` mitigou a segunda e **não tocou** a primeira. Eu
havia citado a conclusão da OpenAI como **analogia** na nota da `PRF-0100` — "a
consequência é a mesma que o titular tirou da rotação da OpenAI" —, e analogia
não é identidade; mas a instrução é justa, porque a frase convidava à confusão.
A `CLM-0085` existe para que a confusão fique refutada por medição, e não por
boa intenção.

---

## D-P001 — e duas partes já estão feitas

**O que ele decidiu:** preservar a ART substituída como `SUPERADA`, identificar a
retificadora vigente, incorporar ao acervo os protocolos, caderneta e
comprovantes. Nenhum documento ausente pode ser considerado disponível por
declaração verbal.

**As duas primeiras já estão no acervo**, e com a distinção explícita:

- `DOC-03` — ART registrada em **2026-09-15**, *"RETIFICADORA da anterior"*
- `DOC-04` — ART registrada em **2026-08-24**, *"SUBSTITUIDA pela DOC-03"*

O estado existe; a palavra é `SUBSTITUIDA` e não `SUPERADA`. São o mesmo estado
com rótulo diferente, e trocar a palavra é cosmético — fica como escolha dele,
não como pendência.

**A terceira depende do mundo:** a caderneta está `EM_ESPERA` porque a
Associação ainda não a entregou, e o comprovante da taxa de R$ 315,00 não está em
peça legível do conjunto. Incorporar o que não chegou não é possível, e a regra
dele cobre exatamente esse caso: declaração verbal não torna documento
disponível. O acervo já aplica isso — foi o que manteve os itens 4 e 5 abertos.

---

## D-DHAP — o que a resposta tem de carregar

Obter esclarecimento formal sobre os itens 13 e 14, preservando **resposta,
data, autoridade emissora, processo e aplicabilidade**.

Isso endurece o que a `UNK-0014` e a `UNK-0015` pedem: deixa de bastar "o DHAP
disse"; passa a exigir peça com emissor nomeado e processo identificado. Os cinco
campos foram acrescentados ao `required_evidence` das duas.

---

## D-JOHN — o vermelho fica

Manter a pendência até existir cluster e certificado legítimo. Não simular prova
de implantação.

É o estado atual, e a guarda já diz isso na própria saída da CI: `OPENAI_API_KEY`
tem 36 caracteres e `DATABASE_URL` tem 34, contra o piso de 100 — *"um envelope
selado não cabe em menos de 100: isto é placeholder, não valor"*, e *"o que fecha
isto não é um commit"*. O `main` do `John-Brasileiro-` segue vermelho por
desenho, e a decisão confirma que ele deve seguir.

---

## A regra final

> Nenhuma decisão do titular deve ser registrada como implementação concluída,
> prova obtida ou escala promovida.

Como ela foi respeitada aqui, item por item:

- a cadeia segue `estrutural 3/5`, `substantiva 0/5`
- a REGIONAL segue **bloqueada por 3**: `CLM-0006` REFUTED, `CLM-0007`
  UNPROVEN, `UNK-0001` UNKNOWN — nenhuma delas tocada
- `UNK-0001` **não foi encerrada**: recebeu a decisão como entrada
- `CLM-0084` (incidente encerrado) entra **UNPROVEN**, com os critérios dele
  como barra
- a única coisa provada neste registro é uma **refutação**: a `CLM-0085`, de que
  a cerimônia da OpenAI teria mitigado a credencial do incidente
- o denominador segue **30**
