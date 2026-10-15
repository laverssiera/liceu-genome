# 2026-10-15 — etcd ou PySyncObj, com o contrato aplicado

O contrato foi aplicado hoje (`CLM-0150` TESTED, `PRF-0180`): *"votar no log"*
não autoriza atos, e a lista de prefixos da Testemunha deixou de ser constante
no consumidor para virar a **fonte** no Producer Registry.

A `PRF-0173` havia dito que o contrato era **a montante** do mecanismo, e que
aplicá-lo poderia tornar a `UNK-0001` mais barata. Então a primeira obrigação
deste documento não é repetir a recomendação de ontem — é **reexaminar se ela
sobrevive**.

---

## 1. O número que faltava: a retenção de GIL, medida

A `PRF-0176` estabeleceu que o risco de Raft no processo é **inanição de
temporizador** por trabalho CPU-bound, e nomeou o piso que decide, lido do fonte
do `PySyncObj` 0.3.17: `raftMinTimeout` **0,4 s**, com `appendEntriesPeriod` de
**0,1 s**. O que faltava era saber se algum handler cruza os 400 ms.

**Instrumento:** uma thread que tenta acordar a cada 1 ms e registra o atraso de
cada acordar, dentro do processo que roda a suíte do CORE — 396 testes, a mesma
seleção que a CI usa. Atraso grande = o GIL ficou retido por trabalho que não o
libera. Não é perfilagem por handler: é o **limite superior observado** de
retenção contínua, que é a grandeza que o temporizador do Raft sofreria.

```
acordares: 65 706        alvo: 1 ms
mediana  0,199 ms   p95  0,804 ms   p99  4,628 ms   p999  16,301 ms
MAXIMO 205,496 ms

acordares >= 400 ms (piso de eleição) ......... 0
acordares >= 100 ms (período de heartbeat) .... 4
```

### E a atribuição muda a leitura — para menos do meu lado

| pico | o que estava correndo |
|---|---|
| **205,5 ms** | *(antes do primeiro teste)* — coleta e import, **não handler** |
| **201,1 ms** | `test_campos_aceitos` — instrumento meu: AST do modelo + carga do kit |
| **199,9 ms** | `test_campos_aceitos` — o mesmo instrumento |
| **117,8 ms** | `test_payload_refs` — **código de produção**: resolução de lineage |

**Só um pico é atribuível a código de produção: 117,8 ms**, na resolução de
`resolvable_refs`, que está no caminho crítico do publish. Os de 200 ms são
instrumentos de teste que não existem num processo servidor.

> **E o máximo é ruidoso.** Entre duas execuções da mesma suíte ele foi 282,4 ms
> e 205,5 ms — 77 ms de variação. O p99 e o p999 ficaram estáveis (5,6/15,7 e
> 4,6/16,3). Reportar um máximo isolado como "o número" seria exagero: o que é
> estável é a cauda até o p999, **~16 ms**.

### O que isso faz com o meu próprio argumento

| | contra o piso de 400 ms |
|---|---|
| p999 estável | **~16 ms** — 25× abaixo |
| máximo atribuível a produção | **117,8 ms** — 3,4× abaixo |
| máximo bruto, com instrumentos de teste | 205–282 ms — 1,4 a 1,9× abaixo |

**O argumento do GIL não é decisivo, e eu o usei como se fosse.** Ontem escrevi
que "escolher Raft no processo é escolher viver dentro da classe de falha de
pausa de processo". Isso segue verdadeiro como *mecanismo*; medido, a
**magnitude** fica entre 3,4× e 25× abaixo do gatilho, com o código que existe.
E o `raftMinTimeout` é configurável — é argumento de parâmetro, não de natureza.

**A composição com a cauda de disco também não fecha mais.** Ontem eu insinuei
que somar os dois cruzaria o piso: 117,8 + 123,4 (o máximo de `fsync` do
`ADR-005`) = **241,2 ms**, ainda abaixo de 400.

---

## 2. O que o contrato aplicado muda — e o que ele **não** muda

A `PRF-0173` previu: se votar no log nunca autoriza atos, a camada de consenso é
**um log**, e log errado é detectável a jusante pela atestação — o ônus de
correção sob partição cai muito.

**Metade disso se confirma, e a outra metade não.**

| pergunta da camada A | o contrato aplicado ajuda? |
|---|---|
| **autorização** — um nó de consenso pode autorizar ato? | **Sim.** Está escrito que não, e a porta da atestação é **ativa e testada** (`PRF-0177`). Promoção sem a Testemunha é recusada |
| **linearizabilidade** — uma única sequência de épocas, visível igual em todos os domínios | **Não.** O `§2` do `ADR-003` exige exatamente isso, e a porta da atestação **não confere épocas**. Ela recusa promoção sem atestação; não detecta duas épocas |

**É aqui que a decisão mora.** O que a camada A requer, e o `§2` escreve com
todas as letras, é *linearizável*. Um Raft com defeito quebra isso — e nenhum
portão deste ecossistema confere linearizabilidade de época.

As **sete recusas** de `valid_attestation_for`, lidas uma a uma, são todas sobre
validade de atestação: `active_unobservable`, `attestation_already_consumed`,
`attestation_concurs_with_another_instance`, `attestation_expired`,
`both_mothers_down`, `no_attestation_for_current_epoch`, `witness_did_not_concur`.
A mais próxima do problema é a terceira — ela impede uma Testemunha de concordar
com **duas instâncias** —, e ainda assim ela não vê época simultânea: vê
atestação incoerente.

> **E isto não é achado novo.** Dizer que seria roubaria crédito de um registro
> que já existe: a prova de sucessão declara na própria abertura
> (`infra/authority/prova_de_sucessao.py:63`) que **o ciclo 25 não resolve
> split-brain**, e tem seções F1 e F2 sobre as duas formas — store compartilhado
> e store separado. A Constituição responde ao split-brain com a **exigência de
> atestação**: *"a promoção passa a exigir concordância da testemunha"*.
>
> O que este documento acrescenta é a **distinção fina**: essa exigência cobre
> **promoção indevida** e não cobre **divergência de época**. São coisas
> diferentes, e é a segunda que o `§2` pede.

---

## 3. As duas opções, com o que mudou

### etcd

| | |
|---|---|
| compra | a implementação canônica; correção sob partição que ninguém aqui precisa provar; régua publicada (p99 de WAL fsync < 10 ms; 50/500 IOPS sequenciais) |
| custa | dependência nova, 3 nós em 3 domínios, operação nova, cliente de consenso no caminho crítico de publish |
| preço | fixado por **isolamento de disco**, não por capacidade — a carga da camada A é ≤ 288 escritas/dia (`PRF-0173`) |

### PySyncObj

| | |
|---|---|
| compra | nenhum processo novo para operar; e o contrato aplicado **remove** a tensão normativa do voto |
| custa | **correção sob partição sem prova citável** — e é justamente linearizabilidade, que é o que o `§2` exige e nenhum portão confere |
| GIL | **medido, e não decisivo**: p999 ~16 ms, máximo de produção 117,8 ms, contra piso de 400 ms configurável |
| régua | **nenhuma.** Sem limiar publicado não há como dizer se o disco serve |

---

## 4. NÃO-MENSURÁVEL, e a lista encolheu de novo

- **A correção do `PySyncObj` sob partição.** Segue sem prova citável. É o único
  que não caiu em dois dias, e é o que decide.
- **A retenção de GIL sob carga de PRODUÇÃO.** O número acima é a suíte, não
  produção: handler pesado que nenhum teste chama não aparece. **É piso do
  piso** — mas deixou de ser "não-mensurável" e passou a ser "medido com escopo
  declarado".
- **Host-vs-cauda do nível barato.** Mensurável reprovisionando N vezes; exige
  criar recurso, e isso não é meu.

---

## 5. O que eu recomendaria, em uma linha — e ela mudou de razão

**Ainda etcd, mas por um motivo mais estreito do que eu dei ontem:** não pelo
GIL, que medido fica 3,4× a 25× abaixo do gatilho, e não pelo ônus de prova em
geral, que o contrato aplicado reduziu — mas porque o que a camada A exige é
**linearizabilidade de época**, e isso é precisamente o que ninguém provou no
`PySyncObj` e o que **nenhum portão deste ecossistema confere**.

**O que mudaria para `PySyncObj`:** um portão que confira linearizabilidade de
época — duas épocas visíveis ao mesmo tempo em domínios diferentes viram recusa.
Com esse portão, log errado passa a ser detectável a jusante **de verdade**, e aí
o argumento da `PRF-0173` fecha. Sem ele, "detectável a jusante" cobre
autorização e não cobre o que o `§2` pede.

E a aceitação por escrito, se for `PySyncObj`, precisa de **gatilho** e não de
data: primeira eleição espúria atribuível a inanição de GIL, primeira violação
observada de época única, ou primeira medição de retenção por handler que cruze
os 400 ms.

---

## 6. O que isto não decide

1. **A escolha.** Entrada de decisão, não decisão.
2. **A porta `promotion_requires_witness_attestation` sob quorum.** A `CLM-0086`
   afirma que o consenso a preserva por si, e está **STALE** — com três votantes,
   ACTIVE e SUCCESSOR já são maioria.
3. **A infraestrutura.** A `PRF-0066` mediu que não há Testemunha nem Sucessora
   implantadas. Decidir o mecanismo não cria os três domínios de falha.
4. **A janela de 300 s** da atestação, que segue sem documentação.
