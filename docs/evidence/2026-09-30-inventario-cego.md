# O inventário que a rotação consulta estava cego em 55 nomes

**2026-09-30** · medido, não lembrado. Nenhum valor de segredo aparece aqui — só nomes.

## O que se foi fazer, e o que apareceu

A F0-C ia escolher o alvo da **primeira rotação** pelo critério declarado no ciclo:
*menor raio de dano* — o objetivo é provar o mecanismo, não reduzir exposição.

O mapa que mede esse raio é o inventário da F0-A,
`LICEU_6.0_CONSTRUTORA_VIRTUAL/infra/security/inventario_segredos.py`.

Ao conferir `JWT_SECRET_KEY` — um dos três nomes que a `UNK-0004` pergunta — ele
**não estava no inventário**, e `git grep` o achava em vários repositórios. O filtro
de falsos positivos trazia a alternativa `KEYS?$`, que barrava **todo** nome
terminado em `_KEY`.

Não era uma exceção conferida. Era uma regra genérica derrubando uma classe inteira
de nomenclatura, em silêncio, contra o comentário do próprio código duas linhas
acima: *"é melhor listar um nome que não é segredo do que deixar um de fora"*.

## A medida

A mesma varredura, no mesmo dia, sobre os mesmos 19 repositórios, nas duas versões
da regra:

| | regra antiga | regra corrigida |
|---|---|---|
| nomes de segredo | 103 | **134** |
| compartilhados entre repositórios | 18 | **33** |
| listados para conferência humana | 0 | **24** |

**55 nomes voltaram**: 31 como segredo, 24 para a lista A CONFERIR.

**15 dos 33 compartilhados existem só por causa da correção.** O mapa ignorava
**45% dos segredos compartilhados** do ecossistema:

| nome | repositórios |
|---|---|
| `SECRET_KEY` | 7 |
| `JWT_SECRET_KEY` | 6 · **nomeado na `UNK-0004`** |
| `MINIO_SECRET_KEY`, `MINIO_ACCESS_KEY`, `ACCESS_TOKEN_KEY`, `REFRESH_TOKEN_KEY` | 3 cada |
| `ANCHORS_SIGNING_KEY`, `JWT_RS256_PRIVATE_KEY`, `NATS_TLS_CLIENT_KEY`, `FERNET_KEY`, `STRIPE_SECRET_KEY`, `OPENAI_API_KEY`, `CEFEIDA_SECRET_KEY`, `ADMIN_API_KEY`, `API_KEY` | 2 cada |

`AWS_SECRET_ACCESS_KEY` também estava fora, em 1 repositório.

## Por que isso bloqueia a escolha, e não só a contagem

A primeira linha do documento da F0-A é *"trocar um segredo antes de saber quem
depende dele é como descobrir o consumidor pela falha"*. Escolher o **menor** raio
sobre um mapa que não enxerga o raio de 15 segredos compartilhados era sortear.

Não é hipótese: `JWT_SECRET_KEY` aparece em **6 repositórios**. Uma rotação feita com
o mapa antigo trataria como local um segredo com seis consumidores.

## A separação do desvio

Dois efeitos distintos, medidos separadamente de propósito — misturados, o defeito
se esconderia dentro do crescimento:

- **defeito da regra**: +31 nomes de segredo, +15 compartilhados, +24 a conferir;
- **ecossistema em sete dias**: pela regra antiga, 101 → 103 nomes e 17 → 18
  compartilhados entre 23/09 e 30/09.

## Por que viveu sete dias

O inventário **não tinha teste nenhum**. Agora tem 12, em
`infra/security/test_inventario_segredos.py`.

O que importa não confere nome: confere **precedência**.

    FALSO antes de FORTE     API_KEY_HEADER carrega API_KEY e é cabeçalho.
    FORTE antes da genérica  AWS_SECRET_ACCESS_KEY termina em _KEY e é credencial.

**Mutação:** reintroduzindo a linha `KEYS?$`, **5 dos 12 testes caem**. O guarda é
carregador, não decorativo.

## O que a correção NÃO faz

Decidir sozinha o que é chave de dicionário. `USER_KEY`, `VALIDATION_KEYS`,
`MFA_HARDWARE_KEY`, `ANCHOR_PIX_KEY` e outros 20 terminam em `_KEY` sem dizer o que
são. Saem numa lista própria — **nomeados, não sumidos**. Um inventário que descarta
o que não sabe classificar é exatamente o defeito que isto desfez.

## O que esta prova não alcança

Ela **não é uma rotação** e **não é prova de revogação**. Corrige o mapa que a F0-C
consulta antes de escolher o alvo. A `UNK-0004` continua aberta, e continua
bloqueando `scale:REGIONAL`. Um mapa correto não revoga credencial nenhuma.

**Reprodução:**
`LICEU_REPOS_DIR=<pasta dos repos> python infra/security/inventario_segredos.py saida.json`
`python infra/security/test_inventario_segredos.py`
