# A borda não estava fechada

**2026-09-30** · medido com dois instrumentos independentes. Nenhum valor de segredo aqui.

## O que se foi fazer

Medir o `smoke-compose` do 3C273, que estava vermelho (Y4 do ciclo 15). O compose
dele publicava `"${POSTGRES_PORT:-5432}:5432"` — e a guarda da borda dizia
**"borda fechada"** para aquele repositório.

## O defeito, na linha

`infra/security/borda_compose.py` exigia dígitos no lado do host:

```python
(?P<host>[0-9]{1,5}):(?P<alvo>[0-9]{1,5})
```

`"${POSTGRES_PORT:-5432}:5432"` não casa com isso. A linha não casava, o laço
fazia `continue`, e a porta sumia da varredura **em silêncio**.

## A medida

| repositório | exposições | onde |
|---|---|---|
| `3C273-Analytics-Data-Science` | 4 | Postgres 5432, MinIO 9000, MinIO console 9001, Redis 6379 |
| `John-Brasileiro-` | 3 | Postgres 5432, Redis 6379, NATS 4222 (compose do sandbox) |

**7 no total. A guarda anterior dizia zero nos dois.**

Dois instrumentos deram o mesmo 7: a guarda corrigida, e uma sonda independente
escrita **antes** da correção, que procurava a forma com variável sem usar a
guarda. As 387 linhas literais seguem sem falso positivo.

No JOHN, as portas de host altas — 55432, 56379, 54222 — faziam parecer que
havia isolamento. Não há: porta alta em todas as interfaces continua alcançável
de outra máquina. Quem separa é o endereço, não o número.

## O controle positivo da PRF-0055 passou, e não bastou

A PRF-0055 trazia um controle positivo: um compose temporário publicando 5432 em
todas as interfaces, para provar que o scanner enxergava. Ele passou.

E usava a forma **literal** — a mesma que a guarda já via. Confirmava que o
instrumento enxergava aquilo que ele já enxergava.

**Controle positivo só mede o que a amostra dele contém.** É a mesma lição dos
12 testes da guarda: todos bons, todos escrevendo a porta com dígitos, nenhum
escrevendo a forma que faltava. Sob a mutação que devolve o defeito, os 12
passam todos — o defeito era invisível para eles.

## O que isto não é

**Não é uma regressão do mundo.** Nenhuma porta foi aberta hoje. O que mudou foi
o que se consegue ver. A borda esteve aberta nesses 7 pontos o tempo todo,
inclusive em 2026-09-29, quando foi anunciada fechada.

## O que fica

A `CLM-0038` volta a **REFUTED**. As 7 linhas estão sendo fechadas em PR próprio
por repositório, e a afirmação volta a ser candidata a PROVEN depois disso — com
prova nova, não com esta.

**Reprodução:** `python infra/security/borda_compose.py --root <cada repositório>`
