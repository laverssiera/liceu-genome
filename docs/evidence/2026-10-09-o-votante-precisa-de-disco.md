# 2026-10-09 — o votante precisa de disco, e o gargalo não é RAM

O titular levantou, ao responder as três perguntas do §7: se a camada A usa consenso
com três votantes, a Testemunha é votante, e **votante de consenso precisa de log
persistente e `fsync`** — ou seja, de disco. A premissa "sem banco", que sustentava
o arranjo barato, deixa de valer.

Este documento mede as duas pontas: o que a Testemunha é hoje, lido no código, e o
que um votante exige, lido na documentação oficial do etcd.

---

## 1. O que a Testemunha é hoje — medido no código

`LICEU_6.0_CONSTRUTORA_VIRTUAL/infra/authority/sonda_testemunha.py`:

| | |
|---|---|
| tamanho | **247 linhas** |
| dependências | **stdlib pura** — `argparse`, `json`, `os`, `socket`, `sys`, `urllib`, `dataclasses` |
| escreve em disco? | **não.** As duas ocorrências de `with` são `urllib.request.urlopen`, não `open()` |
| toca banco? | **não.** Zero referências a `sqlalchemy`, `Session`, `psycopg` |
| RSS medido (PR 85 do CONSTRUTORA) | 21,0 MiB importada, 23,8 após sondagem, **23,8 após 51 sondagens** — não acumula |

A premissa estava certa, e agora está conferida: a Testemunha, como sonda, é um
processo que só fala pela rede.

---

## 2. O que um votante exige — lido na documentação do etcd

Fonte: `https://etcd.io/docs/v3.5/op-guide/hardware/` e
`https://etcd.io/docs/v3.5/tuning/`, lidas em 2026-10-09.

### Disco deixa de ser opcional

A página de hardware diz que disco rápido é o fator mais crítico, e dá a razão:
o protocolo de consenso depende de gravar metadados num log de forma persistente, e
**a maioria dos membros tem de escrever cada requisição em disco**.

Os números que ela declara:

| requisito | valor |
|---|---|
| IOPS **sequenciais** mínimos | **50** (um disco de 7200 RPM atende) |
| IOPS sequenciais recomendados em carga | 500 (SSD local) |
| banda de disco | 10 MB/s recupera 100 MB em ~15 s |
| CPU | duas a quatro vCPUs para cluster típico |
| rede | 1 GbE suficiente |

**E há uma armadilha de leitura que a própria página nomeia:** provedores publicam
IOPS **concorrentes**, não sequenciais, e o número concorrente pode ser **dez vezes
maior** que o sequencial. Então o IOPS anunciado num plano **não é comparável** com
o requisito de 50 sequenciais. Qualquer comparação de preço que use o número da
página do provedor está comparando grandezas diferentes.

### O gargalo real num plano barato não é RAM — é contenção de `fsync`

A página de tuning diz que o cluster é muito sensível a latência de disco, e que,
como o etcd tem de persistir propostas no log, **atividade de disco de outros
processos pode causar latências longas de `fsync`** — e a consequência é perder
heartbeats, com timeouts de requisição e **perda temporária de líder**.

Isso é o oposto do que a estimativa anterior supunha. O risco de um plano
compartilhado não é falta de memória: é o vizinho usando o disco.

### Sobre RAM, uma ressalva contra inflar o custo

A página diz que tipicamente 8 GB bastam — mas a frase vale para clusters servindo
centenas de clientes e milhões de chaves. A mesma página abre dizendo que o etcd
roda bem com recursos limitados para desenvolvimento, e que é comum rodá-lo num
laptop ou numa máquina de nuvem barata. O caso aqui é **um operador, escala LOCAL,
tráfego próximo de zero**, e o §2 do ADR-003 diz que a camada A tem "dezenas de
linhas".

**Então não é honesto concluir "precisa de 8 GB".** O que a documentação sustenta é:
RAM deixa de ser a variável, e **latência de escrita em disco passa a ser**.

### Três domínios independentes: possível, com timeouts ajustados

Os defaults do etcd — heartbeat 100 ms, election timeout 1000 ms — são declarados
para rede local. A página de tuning dá a regra para o caso de múltiplos
datacenters:

- heartbeat ≈ 0,5 a 1,5× o RTT entre membros
- **election timeout de no mínimo 10× o RTT**
- os dois valores têm de ser **iguais em todos os membros**, senão a estabilidade do
  cluster é prejudicada
- o limite superior é 50 s, reservado a cluster globalmente distribuído

Com RTT entre provedores europeus na casa de dezenas de milissegundos, o default de
1000 ms já cobre a regra dos 10×. **A escolha de três domínios é viável sem tuning
exótico** — e isso é a favor da decisão.

### Uma tensão que fica registrada, e não é resolvida aqui

A página de hardware recomenda implantar os membros **dentro de um único
datacenter** quando possível, para evitar latência e reduzir a possibilidade de
eventos de partição. E diz que, para o etcd ser consistente e tolerante a partição,
uma rede instável com partições leva a **disponibilidade pobre**.

A decisão do titular vai deliberadamente na direção oposta — três domínios, com
faturamento e domínio administrativo independentes — e **está certa pela Constituição**,
que exige da Testemunha domínio de falha distinto, com a razão escrita: *se as três
compartilham infraestrutura, a testemunha não acrescenta independência, apenas custo*.

As duas coisas são verdadeiras ao mesmo tempo: o etcd prefere um datacenter por
desempenho, e a Constituição exige domínios distintos por independência. **A
Constituição manda**, e o preço disso é o que esta nota registra: latência maior
entre membros, mais chance de eventos de partição, e timeouts que precisam ser
escolhidos em vez de herdados.

---

## 3. O que isto muda na entrada de preço

A entrada registrada na `UNK-0001` em 2026-10-01 dizia: piso de ~EUR 7-8/mês para
**duas pontas completas** na OVH, com a Testemunha cabendo em plano gratuito ou em
hardware do titular, pelo argumento da assimetria — a ponta que exige independência
é a que menos precisa de confiabilidade, porque a falha dela é segura
(`ACTIVE_UNOBSERVABLE` bloqueia a promoção).

**Três coisas dessa entrada deixam de valer:**

1. **"duas pontas"** — já havia caído com a escolha de três domínios votantes.
2. **"cabe em plano gratuito"** — um votante grava cada requisição em disco, e
   `fsync` lento custa perda de líder. Plano gratuito não publica latência
   sequencial de escrita.
3. **a assimetria** — ela valia enquanto a Testemunha só observava. Votante não é
   observador: a falha dele tira um voto do quórum. Com três nós, perder um ainda
   deixa maioria (dois de três), então o sistema segue — mas a ressalva da Oracle
   passa a pesar mais, porque um membro de quórum que **não consegue ser recriado**
   reduz o cluster a dois permanentemente, e aí perder qualquer um dos dois para o
   ecossistema inteiro de publicar.

**O que NÃO muda:** a assimetria do modo de falha segue medida e verdadeira
(`PRF-0061`). A Testemunha caindo bloqueia a promoção e escala ao humano. Votante ou
não, a falha dela é segura — ela custa disponibilidade, nunca promoção indevida.

---

## 4. O que fica para medir, e não está medido aqui

- **o preço de três VPS que publiquem latência de escrita sequencial.** Nenhum
  provedor lido até hoje a publica; todos publicam IOPS concorrente. Isso é
  `NAO_MENSURAVEL` pelas páginas dos provedores, e só um benchmark (`fio`, como a
  própria documentação sugere) responderia — num plano já contratado.
- **o RTT real entre os provedores escolhidos**, que decide o election timeout. Só
  se mede com as máquinas de pé.
- **se a camada A precisa de etcd ou de um Raft embutido.** O §3 do ADR fala de
  "etcd ou um Raft embutido", e os números acima são do etcd. Um Raft embutido com
  log próprio tem outro perfil, e nada aqui o mede.
