# A borda fecha — agora com um instrumento que enxerga

**2026-09-30** · medido. Segunda vez que esta afirmação é dada como provada, e a
primeira em que o instrumento vê a forma que faltava.

## A medida

```
0 exposicao(oes) em 56 arquivo(s) de compose, 19 repositorios
```

As 7 que a `PRF-0063` apurou foram fechadas:

| repositório | portas | commit |
|---|---|---|
| `3C273-Analytics-Data-Science` | 4 · Postgres, MinIO, MinIO console, Redis | `6d6485f` |
| `John-Brasileiro-` | 3 · Postgres, Redis, NATS (sandbox) | `5d66baf` |

## O controle positivo tem três formas, e não uma

Este é o ponto em que esta prova difere da `PRF-0055`, que também anunciou zero e
estava errada.

O controle positivo da PRF-0055 usava **só a forma literal** — a mesma que a
guarda já via. Confirmava que o instrumento enxergava aquilo que ele já
enxergava. **Controle positivo só mede o que a amostra dele contém.**

Aqui o controle tem as três, e a do meio é exatamente a que estava cega:

| forma | acusou | saída |
|---|---|---|
| literal · `5432:5432` | 1 | 1 |
| host vindo de variável · `${POSTGRES_PORT:-5432}:5432` | 1 | 1 |
| **interface** vinda de variável · `${BIND:-127.0.0.1}:${P:-5432}:5432` | 1 | 1 |

## Conferido além do compose

A afirmação fala do **ecossistema**, não do compose. Então:

- `network_mode: host` — não aparece em nenhum arquivo.
- `ports:` em estilo de fluxo (`ports: ["5432:5432"]`) — não existe em nenhum dos 19.
- **88 Services de k8s** lidos: 87 `ClusterIP`, 1 `LoadBalancer`.
- **3 arquivos Terraform**, de 12 a 22 linhas, sem regra de porta ou grupo de segurança.

O único `LoadBalancer` é o `workflow-service` do BIM.ARQ.ENG, com `targetPort:
9001` — que a tabela `ESTADO` mapeia como console do MinIO **e não é**. Lido o
`k8s/workflow-deployment.yaml`: 9001 é a porta HTTP do próprio motor de workflow
(imagem `workflow:local-v3`, probes `httpGet /health` e `/health/ready` na mesma
porta). Porta de aplicação atrás de LoadBalancer é normal.

Fica registrado: **a tabela mapeia por número de porta**, o que é certo para
porta conhecida de banco e produz falso positivo em porta alta genérica. Este
caso só se resolveu lendo o manifesto.

## O que esta prova não alcança

A medição é **estática**, sobre arquivo versionado. Não alcança porta que um
operador publique à mão, nem cluster em execução, nem regra de rede fora destes
arquivos.

E **fechar porta não é revogar credencial**: a F0-C segue bloqueada na prova de
revogação, e a `UNK-0004` segue aberta.

**Reprodução:** `python infra/security/borda_compose.py --root <cada repositório>`
