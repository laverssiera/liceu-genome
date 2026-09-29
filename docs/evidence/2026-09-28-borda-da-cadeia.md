# A borda dos seis repositórios da cadeia — 2026-09-28

Evidência da PRF-0054 (prova a CLM-0055).

## O que foi medido

`infra/security/borda_compose.py`, do LICEU_6.0_CONSTRUTORA_VIRTUAL, sobre o
`main` mergeado de cada repositório. Ele acusa serviço de **estado** — Postgres,
NATS, Redis, Neo4j — publicado fora do loopback; porta de aplicação e de proxy
não são acusadas.

## Antes e depois

| repo | elo | portas presas |
|---|---|---|
| HUB-BACKOFICE | 0 | 12 |
| Archimedes-ImobTech | 1 | 10 |
| 3C273 (CEFEIDA) | 2 | 4 |
| John-Brasileiro- | 3 | 10 |
| ANCHOR.OS | 4 | 11 |
| OPERA-ES | 5 | 7 |
| **total** | | **54** |

O scanner, rodado isoladamente em cada um sobre o `main` mergeado, diz
**"borda fechada"** nos seis.

No ecossistema: **119 → 65**.

## A forma da mudança

Uma só, aplicada linha a linha e recusando o que não casasse exatamente:

```diff
-      - "5432:5432"
+      - "127.0.0.1:5432:5432"
```

Prender ao loopback **não** tira acesso do próprio host — `127.0.0.1` continua
alcançável de quem roda o compose. O que sai é o alcance de outras máquinas.
Conferido nos workflows antes de mexer; no JOHN eles já usavam `127.0.0.1:5432`
e afins, que é exatamente o que o loopback permite.

## O que a medição achou de quebra

O JOHN tinha um teste de contrato — `test_nats_exposes_monitoring_port` — que
exigia a string `"8222:8222"`, **a forma que publica em todas as interfaces**.
Ele falhou, e estava certo em falhar: guardava um contrato, e o contrato mudou.

A exigência foi invertida, e ficou mais forte: `assertIn "127.0.0.1:8222:8222"`
mais `assertNotIn "8222:8222"`. Era o único teste do ecossistema a asserir
string entre as portas alteradas (4222, 8222, 6379, 5432, 9000).

## O que isto NÃO prova

**A CLM-0038 continua REFUTED.** Sessenta e cinco exposições seguem abertas,
todas fora da cadeia:

```
P-D 16 · BIM 16 · CEA 9 · ACADEMIA 6 · ECONO 6 · JURIDICO 4 · GAME-MKT 4 · FORNECEDORES 4
```

Fechar a cadeia reduz exposição; não torna verdadeira a afirmação sobre o
ecossistema. Registrar "119 → 65" como progresso rumo a PROVEN seria contar o
denominador errado.

E fechar porta **não é revogar credencial**: a F0-C segue bloqueada na prova de
revogação, que é outra coisa.
