# 2026-10-09 — a varredura exaustiva das declarações de estado na lei

Metade da `UNK-0018`, a que é minha: ler os cinco artefatos governados do kit e
classificar cada campo que afirme contagem ou situação, com o valor declarado ao
lado do medido, e **um número por artefato em vez de amostra**.

A outra metade — decidir o que a lei deve conter — é do titular, e este documento
não a antecipa.

---

## 1. O método, declarado antes do resultado

**Enumeração mecânica.** Um script percorre cada YAML e coleta todo valor que seja
inteiro, ou string que case com uma de três formas: palavra de situação (`ABERTA`,
`PASS`, `PENDENTE`, `ADR_REQUIRED`…), fração (`0/7`), ou número seguido de
substantivo contável (`114 arquivos`, `15 monolitos`).

**Uma exclusão declarada:** subárvores de `payload_schema` ficam fora. Elas são
JSON Schema — `type: integer`, `required`, `minItems` —, e isso é norma por
definição: diz o que um payload **deve** ter, nunca o que o mundo **é**. Incluí-las
daria centenas de falsos candidatos e afogaria o resultado, que é exatamente o
risco que a `UNK-0017` descreve.

**Classificação por regra, não por olho.** As regras estão escritas no script e
aplicadas mecanicamente, para a contagem por categoria ser derivada:

| categoria | regra |
|---|---|
| **NORMA** | a chave ordena, posiciona ou exige — `ordem`, `elo`, `posicao_na_cadeia`, `precede_elo`, `domain_invariants`, `required_envelope_fields`, `contract_lifecycle`, `topologia`, `REGRA` |
| **HISTÓRICO** | a chave registra o passado — `changelog`, `corrige`, `nota_versao`, `REGRESSAO_CORRIGIDA` |
| **FALSO POSITIVO** | a palavra casou como situação sendo prosa |
| **ESTADO** | o que sobra: afirma o que **é** |

---

## 2. O resultado, por artefato

```
TOTAL 105    ESTADO=48    NORMA=45    HISTORICO=8    FALSO_POSITIVO=4
```

| artefato | total | ESTADO | NORMA | HISTÓRICO | falso-pos. |
|---|---|---|---|---|---|
| `liceu_constitution.yaml` | 56 | **36** | 12 | 4 | 4 |
| `liceu_contract_registry.yaml` | 26 | 3 | 21 | 2 | — |
| `liceu_event_registry.yaml` | 18 | 5 | 12 | 1 | — |
| `liceu_producer_registry.yaml` | 4 | 4 | — | — | — |
| `liceu_event_reconciliation_ledger.yaml` | 1 | — | — | 1 | — |

**São 48 estados, não seis.** A `PRF-0126` encontrou seis **sem procurar**, e disse
que não afirmava serem seis. A varredura dá o número: **48**, e **36 deles estão na
Constituição** — o artefato que é a lei propriamente dita.

**Os quatro falsos positivos são do meu enumerador**, e vale nomeá-los porque
mostram o limite do método mecânico: `TODO monolito tem o seu JOHN local`,
`fail-closed para humano`, `ATIVA-PASSIVA com epoca`, e `todo dado que ATRAVESSA
FRONTEIRAS`. Em português, "TODO" é quantificador e "FAIL" é parte de "fail-closed";
o regex leu as duas como situação.

---

## 3. Os 11 estados conferíveis dentro do kit — e nove estão certos

Estes são os que se medem sem sair dos cinco arquivos:

| campo | declarado | medido | |
|---|---|---|---|
| `constitution meta.pendencias_abertas` | 0 | 0 | OK |
| `constitution meta.adrs_pendentes` | 1 | 1 | OK¹ |
| `constitution identidade_semantica_de_replay.total` | 12 | 12 | OK |
| `constitution campos_exigidos_pelo_protocolo.total` | 11 | 11 | OK |
| `producer meta.contagem.soberanos` | 15 | 15 | OK |
| `producer meta.contagem.total` | 16 | 16 | OK |
| `event resumo.CANONICAL_REGISTRY_EVENTS` | 13 | 13 | OK |
| `event resumo.CONTRACT_IDS` | 15 | 15 | OK |
| `event resumo.CONTRACT_VERSIONS` | 21 | 21 | OK |
| `contract meta.contagem.contract_ids` | 11 | **15** | **FALSO** |
| `contract meta.contagem.versoes` | 17 | **21** | **FALSO** |

¹ a contagem está certa, mas a **lista** que ela conta está defasada: a ADR-001 foi
decidida em 2026-09-18 e segue listada como pendente (`PRF-0125`).

**A lei é majoritariamente verdadeira sobre si mesma.** Nove de onze. O defeito não
é generalizado — ele se concentra num ponto só: **onde alguém muda e não reconta.**

**E os dois falsos fui eu, hoje.** Ao aplicar os quatro contratos no PR 31 do
`liceu-protocol`, atualizei o `resumo` do Event Registry e o `meta.escopo`, e não
sabia que havia um terceiro lugar com os mesmos números. Na `v0.24.0` o bloco
declarava 11/17 e eram 11/17 — estava correto. Corrigido no PR 33, kit 0.25.1.

**E a lei já registrava uma ocorrência anterior do mesmo defeito**, no próprio
`changelog_2_5_0`: *"Corrige contagem (estava 8/10 desde 2.3.0)"*. O mesmo bloco
ficou falso **duas vezes, por duas mãos, pelo mesmo motivo**.

---

## 4. Os 37 restantes, e por que não são conferíveis aqui

Agrupados pelo que seria necessário para medi-los:

### a. Observação de código nos 19 repositórios — 13 campos

`monolitos.core.forbidden[0].violacao` (114 arquivos), `monolitos.john.observacao_positiva`
(119 arquivos), `monolitos.juridicotech.divida_conhecida` (2338 arquivos),
`monolitos.academia.divida_conhecida` (1059 arquivos, 25 apps / 2 implementados),
`monolitos.econotech.bug_conhecido` (2000 eventos), `monolitos.gamemkt.violacao_critica`
(9 eventos), `monolitos.anchor...external_effect 0/3`, `global.authority_model.observacao`
(1 de 15 monólitos), `global.internal_reference_implementations...fail_closed`
(9 monólitos), `global.federation_authority.LIMITE_NAO_DEFINIDO` (`ABERTO` e
4 representações), e `global.federation_cognition...medicao_atual` (44 e 24).

Destes, **um já está medido e é falso**: o `114`, onde há **96** — e 71 dentro do
`cv-backend-core` (`PRF-0111`). Os outros doze exigem varredura dos 19
repositórios, cada um com um padrão próprio. **NÃO MENSURÁVEL sem essa varredura**,
e ela não é a mesma coisa que esta.

Dois deles merecem nota pelo nome: `medicao_atual` diz, na própria chave, que é
medição — e não carrega data. E `LIMITE_NAO_DEFINIDO.estado: ABERTO` é estado de
decisão, não de código.

### b. Status de milestone — 11 campos

Oito `PASS` em `M3` e `M4`, mais os critérios inteiros de `M1` e `M2`. Verificar um
`PASS` de milestone exige reavaliar os critérios dele contra o mundo, que é o
trabalho do próprio milestone. **NÃO MENSURÁVEL por leitura**, e é o grupo mais
pesado dos três.

Um deles está em tensão aparente com o genoma e vale registrar sem resolver:
`M4_FIRST_CAUSAL_AUTHORITY_CHAIN` tem três critérios `PASS`, enquanto a cadeia
substantiva medida pelo juiz é **0/5**. Os dois podem ser verdadeiros se o
milestone fala de outra coisa que a cadeia substantiva — mas o que ele afirma não
está escrito ao lado do `PASS`.

### c. Estado de decisão e de processo — 13 campos

`global.core_dna.extracao_fisica_do_kernel.estado: ABERTA` e o par
`P1_07A: APROVADA` / `P1_07B: ADR_REQUIRED`, já medidos como **defasados** pela
`PRF-0125`: a ADR-001 foi decidida e executada. Mais
`campos_exigidos_pelo_protocolo.implementation_status: NAO_INICIADA`,
`events.authority.human.decision.recorded.implementation_status: NAO_INICIADA`,
`resumo.IMPLEMENTED_IN_MONOLITH: 0`, `contract meta.status: DEFINIDO — 0/7
implementados` (há 15 contract_ids), `contract meta.escopo`,
`producers.liceu.authority.NAO_E_MONOLITO_SOBERANO`,
`global.federation_authority.delegacao.universalidade` e
`global.camadas_transversais.REGRA_UNICA`.

O `IMPLEMENTED_IN_MONOLITH: 0` é o caso mais instrutivo dos 48: **não é falso nem
verdadeiro**, porque ninguém escreveu o que conta como implementado — e quatro
eventos passaram a ter `EMITIDO_COMO_AUDITORIA_NAO_COMO_FATO`. Número sem
definição não é verificável nem refutável, e por isso sobrevive mais que número
errado.

---

## 5. Um achado estrutural que a varredura entrega de graça

**O bloco `meta.contagem` do Contract Registry é redundante com o `resumo` do Event
Registry.** Os mesmos dois números, em dois arquivos, mantidos à mão em dois
lugares — e foi exatamente a cópia esquecida que ficou falsa.

Isso muda a forma da decisão para esses dois: não é entre *derivar* e *manter com
data*, é entre **eliminar a segunda fonte** ou aceitar duas. E a objeção já existe
escrita no ecossistema, no ADR-002, que recusou a saída A+B com a razão *"duas
funções calculando identidade divergiriam, mesmo escritas iguais"*.

---

## 6. O que a medição sugere, e que não é decisão

O padrão dos 48 separa-os em dois tipos com riscos diferentes:

**Contagem do próprio arquivo** — 11 campos, todos mecanicamente deriváveis, e os
únicos onde a falsidade é **detectável sem sair do kit**. Nove estão certos hoje
porque alguém os corrigiu; dois ficaram falsos porque alguém não recontou. Para
estes, derivar custa pouco e remove a classe inteira.

**Observação do mundo** — os 37. Estes **não podem** ser derivados pela CI do kit,
porque o mundo que descrevem está em outros repositórios ou em critérios de
milestone. Para estes, o que a medição aponta não é derivação: é **data e
procedência obrigatórias**. E há precedente dentro dos próprios 48 — o campo
`violacao` do nó `core` carrega `[DECIDIDO 2026-08-29]`, e foi **o único cuja
defasagem era detectável pela própria escrita**.

Nada disso decide. A escolha entre DERIVAR, RETIRAR e MANTER COM DATA, campo a
campo, é do titular, e a `UNK-0018` segue aberta esperando-a.

---

## 7. O que esta varredura não alcança

- **os nove arquivos de ferramental** do kit (`liceu_conformance.py`,
  `liceu_federation_sdk.py`, `liceu_boundary_check.py`, `liceu_registry_check.py`,
  `liceu_contract_vectors.py`): o escopo declarado da `UNK-0018` é a lei, não o
  código. Há pelo menos uma ocorrência conhecida fora dela — o comentário
  `# esperado: 59/59` no workflow do kit, que hoje devolve **106/106**.
- **a Constituição de versões anteriores.** A varredura é do estado de hoje; não
  diz quando cada campo ficou defasado, exceto onde o próprio changelog diz.
- **o que o enumerador não vê.** Ele acha inteiro, fração, palavra de situação e
  número-mais-substantivo. Uma afirmação de estado escrita só em prosa — *"o
  ANCHOR não publica hoje"* — passa sem casar nenhum padrão. **O 48 é piso, não
  teto**, e esta frase existe para que ninguém o leia como total.
