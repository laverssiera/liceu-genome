#!/usr/bin/env python3
"""A data que o juiz compara — forma, calendario e futuro.

O juiz nao conferia data NENHUMA. O schema dizia `"type": "string"` e so, e
TODA comparacao de data dentro dele e comparacao de TEXTO:

    _expired()   str(expires_at) < today
    FIT-016      p["date"] < pred["registered_at"]
    historia     sorted(..., key=lambda x: str(x.get("date")))

Texto so se compara como data numa forma: YYYY-MM-DD com zero a esquerda.
"2026-9-30" e MAIOR que "2026-09-30" para o computador e MENOR para o
calendario — a inversao e silenciosa, e nenhuma delas levanta excecao.

Tres regras, e cada uma mora onde pode ser exprimida:

  forma       no SCHEMA, com `pattern` — e lei, e outras ferramentas leem o
              schema
  calendario  aqui: "2026-02-30" casa com a forma e nao existe, e `pattern`
              nao sabe dizer isso
  futuro      aqui: uma prova datada de depois de hoje e observacao que ainda
              nao foi feita. E na FIT-016 a data futura AFROUXA a regra, porque
              la a pergunta e se a prova veio depois do pre-registro: quanto
              mais tarde a prova se declara, menos ela parece explicacao depois
              do ocorrido

`expires_at` e o unico campo em que o futuro e o uso NORMAL — ele diz quando a
evidencia vence. Dele se exige so a forma.

Por que este arquivo existe separado do juiz
--------------------------------------------
Pelo mesmo motivo que `genome_producer_hosting.py`: a prova desta regra cobre
uma superficie, e superficie de 1700 linhas invalida a prova a cada ciclo por
mudanca que nao tem nada a ver com ela. Aqui a superficie e este modulo e o
teste dele. A funcao e PURA — recebe os nos e devolve achados; o juiz so chama
e acrescenta aos erros.
"""
from __future__ import annotations

import datetime
import re

FORMA_DA_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# (kind, campo, o futuro e normal neste campo?)
CAMPOS = (("proof", "date", False),
          ("proof", "expires_at", True),
          ("pfc", "date", False))


def data_invalida(valor) -> str | None:
    """O motivo pelo qual a data nao serve para comparar, ou None."""
    if not isinstance(valor, str):
        # `date: 2026-10-01` sem aspas o YAML converte em datetime.date, e dai
        # a comparacao com string levanta TypeError em vez de dar veredito.
        return f"{valor!r} nao e texto (o YAML a converteu em {type(valor).__name__}) — use aspas"
    if not FORMA_DA_DATA.match(valor):
        return f"{valor!r} nao esta em YYYY-MM-DD"
    try:
        datetime.date.fromisoformat(valor)
    except ValueError:
        return f"{valor!r} tem a forma certa e nao existe no calendario"
    return None


def hoje_utc() -> str:
    """O 'hoje' do juiz e UTC, e isto e decisao declarada, nao detalhe.

    `datetime.date.today()` devolve a data do FUSO de quem roda. A CI roda em
    UTC e a maquina de quem escreve, em UTC-3: entre 21h e meia-noite local os
    dois discordam sobre que dia e hoje, e o MESMO grafo receberia dois
    vereditos. Foi o que aconteceu em 2026-09-30 as 23h26 locais — seis provas
    datadas de 2026-10-01 pareciam do futuro aqui e eram do dia corrente la, e
    o relatorio daquela hora afirmou que o grafo tinha data futura. Nao tinha.
    Com o fuso declarado, o veredito e o mesmo nos dois lugares.
    """
    return datetime.datetime.now(datetime.timezone.utc).date().isoformat()


def achados(nos_por_kind: dict, today: str) -> list[str]:
    """Erros de data, por no. Pura: nao le relogio nem arquivo."""
    out: list[str] = []
    for kind, campo, futuro_e_normal in CAMPOS:
        for n in nos_por_kind.get(kind) or []:
            if campo not in n:
                continue
            motivo = data_invalida(n[campo])
            if motivo:
                out.append(f"{n.get('id')}: {campo} {motivo}")
            elif not futuro_e_normal and n[campo] > today:
                out.append(f"{n.get('id')}: {campo} {n[campo]} e depois de hoje "
                           f"({today}, UTC) — prova datada do futuro e observacao "
                           f"que ainda nao foi feita")
    for c in nos_por_kind.get("claim") or []:
        pred = c.get("prediction")
        if not isinstance(pred, dict) or "registered_at" not in pred:
            continue
        motivo = data_invalida(pred["registered_at"])
        if motivo:
            out.append(f"{c.get('id')}: prediction.registered_at {motivo}")
        elif pred["registered_at"] > today:
            out.append(f"{c.get('id')}: prediction.registered_at {pred['registered_at']} "
                       f"e depois de hoje ({today}, UTC) — pre-registro no futuro "
                       f"nao pre-registra nada")
    return out
