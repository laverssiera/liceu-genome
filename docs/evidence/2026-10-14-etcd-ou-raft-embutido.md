# 2026-10-14 — etcd ou Raft embutido: as duas opções, medidas

A `UNK-0001` está atrás de uma decisão, e o `ADR-005 §5.1` nomeia esta como a
primeira das pendentes: **etcd ou Raft embutido na camada A**. Ela não é "A, B ou
C" — a topologia já foi decidida (opção B do `ADR-003 §3`, consenso para a camada
A). É a escolha do mecanismo **dentro** da B.

**O que está em jogo é pequeno e é o que mais importa:** só a camada A — época,
ativa, papéis e atestações vigentes. O `§2` do `ADR-003` exige dela
*"LINEARIZÁVEL: uma única sequência de épocas visível igual em todos os
domínios; e é o que o fencing compara"*. As camadas B (histórico) e C (event
store) precisam só de durabilidade.

---

## 1. A medição que muda a economia da decisão

Os **US$ 96–144/mês** do `ADR-005 §3` foram levantados **pela recomendação de
hardware do etcd** — e o próprio ADR marca isso como não-veredito: *"o etcd
apresenta as figuras como recomendação"*. Então a pergunta certa é: **qual é a
carga real da camada A?**

Medido no `authority_control_plane.py`, operação por operação:

| escreve na camada A | onde | quando |
|---|---|---|
| `promote()` | `:341`, commit em `:418` | avanço de época — **raro** |
| `attest()` | `:495`, commit em `:601` | uma atestação, com TTL |
| `ensure_state()` | `:132`, commit em `:149` | semeadura, **uma vez** |

`_audit()` e `escalate_to_human()` também escrevem, e **não são camada A**: são
histórico, e o `§2` diz que durabilidade basta para elas.

O TTL governa a taxa:

```
AUTHORITY_ATTESTATION_TTL_SECONDS = 300      app/config.py:86
```

**E ninguém renova automaticamente.** `attest()` é chamado só pelo endpoint HTTP
(`main.py:5799`); não há scheduler, nem laço, nem daemon. A sonda da Testemunha
também não tem intervalo — ela é invocada.

| | |
|---|---|
| teto de escritas na camada A, com renovação contínua a cada 300 s | **288/dia** ≈ **0,0033/s** |
| escritas automáticas hoje | **0** |

**O que isso faz com o argumento do preço — e é menos do que parece.** A
recomendação do etcd (*"two to four cores"*, *"Typically 8GB is enough"*) é
dimensionada para carga de ordens de grandeza acima disso, então ela deixa de ser
*a* referência de **capacidade** para este caso.

**Mas não é capacidade que fixa o preço aqui, e isso já estava medido.** O
`ADR-005` mediu em 2026-10-13 a latência de `fsync` no nível barato: mediana
estável entre 0,664 e 0,738 ms e p95 ≤ 1,53 ms em **seis** amostras — e **uma**
com p95 de **92,75 ms** e máximo de **123,4 ms**. A mediana quase não se move; o
que explode é a cauda. É o modo de falha que a documentação do etcd descreve:
atividade de disco de outros processos causa `fsync` longo → heartbeat perdido →
perda temporária de líder.

**Carga baixa não resolve cauda de disco.** Uma escrita a cada 300 s que espera
92 ms de `fsync` no momento errado perde o heartbeat do mesmo jeito. O que
compra isolamento de disco é disco dedicado, e é isso que o preço paga — não
núcleos nem RAM.

**E isso vale igual para o Raft embutido:** a cauda não distingue qual
implementação de consenso está esperando o `fsync`. Então o piso de EUR 7–8/mês
medido para duas pontas da **aplicação** não transfere para o consenso, em
nenhuma das duas opções.

---

## 2. A medição que estreita o campo

"Raft embutido", num CORE que é Python, significa uma biblioteca Raft em Python.
Medido **no índice de pacotes**, não em página de terceiro:

| | última versão no índice | estado |
|---|---|---|
| `pysyncobj` | **0.3.17** | lançamentos recentes; Raft em Python puro |
| `raftify` | **0.1.67** | **descontinuado em Python** pelo próprio autor — reescrito em Rust, e a página do PyPI avisa "very experimental stage" |
| `rraft-py` | **0.2.27** | binding **não oficial** do `tikv/raft-rs`; só o módulo de consenso — transporte e armazenamento são trabalho de quem usa |

E a própria página do `rraft-py` diz que **não há biblioteca Raft de fato padrão
em Python**, e aponta seus usuários para `Raftify` ou `PySyncObj` — sendo que o
primeiro está descontinuado em Python.

**Então "Raft embutido" não é um campo de opções: é uma, o `PySyncObj`.** Os
outros candidatos que a busca trouxe se autodeclaram inadequados para produção —
um deles declarando, na própria descrição do projeto, que não deve ser
usado em ambiente de produção.

> **Uma correção de procedência:** a busca na web dava o `rraft-py` em 0.2.2. O
> índice diz **0.2.27**. Quando a página de terceiro e o índice discordam, vale o
> índice — é a mesma regra que o genoma já aplicou ao preço do netcup.

---

## 3. As duas opções

### etcd

| | |
|---|---|
| **o que compra** | a implementação canônica de consenso, a mais exercitada da indústria; ferramental de operação pronto (snapshots, compactação, TLS); correção sob partição que ninguém aqui precisa provar |
| **o que custa** | dependência nova (binário Go, 3 nós em 3 domínios), operação nova, e o CORE ganha um cliente de consenso **no caminho crítico de publish** (`ADR-003 §3 B`) |
| **o preço** | US$ 96–144/mês **pela recomendação do etcd**. O §1 mostra que a carga real não justifica os núcleos e a RAM recomendados — mas também que o que fixa o preço é **isolamento de disco**, e esse não cai com a carga |

### Raft embutido (`PySyncObj`)

| | |
|---|---|
| **o que compra** | nenhum processo novo para operar, nenhum binário novo; o voto vive no runtime da aplicação |
| **o que custa** | a correção do consenso passa a ser **risco do operador**. E há um modo de falha nomeável: Raft em **Python puro** compartilha o GIL com um FastAPI de 321 rotas — uma requisição lenta atrasa o heartbeat, e heartbeat atrasado é eleição espúria. Trocar de líder sem motivo, numa camada cuja única exigência é *uma sequência de épocas igual em todos os domínios*, é o defeito que a camada existe para não ter |
| **o preço** | **não é menor**: a cauda de `fsync` medida no nível barato derruba heartbeat de qualquer Raft, embutido inclusive. O que ele economiza é **um processo para operar**, não o disco. E o custo migra para prova de correção, que é trabalho e não assinatura |

---

## 4. NÃO-MENSURÁVEL, nomeado em vez de estimado

- **A correção do `PySyncObj` sob partição.** Não há prova de linearizabilidade
  publicada que eu possa citar, e afirmar que ele está certo seria exatamente o
  tipo de afirmação sem prova que este ecossistema recusa. Medir isso é projeto,
  não leitura.
- **A magnitude do risco do GIL.** O mecanismo é certo (Python puro, mesmo
  processo, heartbeat concorrendo com requisição); **o tamanho** depende da cauda
  de latência da aplicação sob carga real — e a `PRF-0066` mediu que **não existe
  Testemunha nem Sucessora implantadas**, então não há onde medir.
- **Se o nível mais barato de um provedor sobrevive ao padrão de `fsync` do
  etcd.** O `ADR-005` já cita o modo de falha que o etcd descreve (*"disk
  activity"*); confirmar exige rodar, não ler.
- **As datas de lançamento.** O índice dá versões, não datas. A busca deu datas
  para o `pysyncobj` (0.3.17 em 30/08/2026) e eu **não** as confirmei no índice.

---

## 5. O que eu recomendaria, em uma linha

**etcd** — porque o que se replica aqui é a época que o `enforce()` compara, e um
Raft em Python puro dividindo o GIL com a aplicação transferiria para mim a prova
de correção sob partição, que é precisamente o trabalho que a existência do etcd
torna desnecessário.

**O que mudaria isso:** se o titular recusar por princípio uma dependência
operacional nova — e para operador sozinho isso é razão legítima, não teimosia —,
então `PySyncObj`; mas aí o risco de correção tem de ser **aceito por escrito**,
com a cláusula de caducidade, exatamente como o incidente da credencial. Risco não
medido que ninguém assinou não é risco aceito: é risco esquecido.

**E o preço não é argumento para nenhum dos dois lados.** A carga medida
(≤ 288 escritas/dia) não sustenta os núcleos e a RAM que os US$ 96–144 pagam —
mas o que o preço compra de verdade é **isolamento de disco**, e a cauda de
`fsync` de 92,75 ms medida no nível barato derruba heartbeat de qualquer Raft,
embutido ou não. **Eu escrevi o contrário na primeira versão deste documento** —
que a carga baixa faria o custo cair para o piso de EUR 7–8 — e isso estava
errado: confundi capacidade com isolamento, e a medição que me corrige já estava
no `ADR-005` desde 13/10.

---

## 6. O que esta medição **não** decide, e segue do titular

1. **A escolha.** Esta é entrada de decisão, não decisão.
2. **A separação dita em contrato** — *"votar no log"* não é *"autorizar atos"*.
   O `ADR-005 §5.1` já diz que é redação e não espera mais nada, e sem ela **a
   opção B viola "nunca autoriza"** ou cai no caso do `§7.2`: dois nós de
   consenso mais um observador **não têm maioria** numa partição.
3. **A preservação da porta `promotion_requires_witness_attestation`.** Com três
   votantes, ACTIVE e SUCCESSOR já são maioria; se `promote()` virar "proposta
   aceita pela maioria" sem preservar a porta, promove-se **sem** a Testemunha. E
   não se pode presumir que o quorum a preserve: a `CLM-0086`, que afirma isso,
   está **STALE**.
4. **A infraestrutura.** A `PRF-0066` mediu que não há Testemunha nem Sucessora
   implantadas. Decidir o mecanismo não cria os três domínios de falha, e a
   Constituição diz o que a ausência deles custa: *"se as três compartilham
   infraestrutura, a testemunha não acrescenta independência — apenas custo"*.
