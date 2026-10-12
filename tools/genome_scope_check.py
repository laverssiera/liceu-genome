#!/usr/bin/env python3
"""FIT-019 — a cobertura declarada de busca.

Prova de LEITURA (`code_reading`, `record_reading`) declara o `scope` da busca
que a produziu: `padrao`, `universo`, `excluidos`, `instrumento`. Sem os quatro,
a prova NAO VIGE — veredito INDETERMINADO, que e insuficiencia declarada e nao
violacao: a prova fica no grafo como historia e a afirmacao que ela sustentava
vira STALE, "prove de novo", nunca UNPROVEN nem falsa.

POR QUE ESTE MODULO EXISTE SEPARADO DO JUIZ, e a razao e a mesma que a PRF-0031
e a PRF-0073 escreveram: a SUPERFICIE da prova tem de ser o modulo, nao o
`genome_check.py` de 1700 linhas que muda a cada ciclo. Prova cuja superficie e
o juiz inteiro fica vermelha no proximo ciclo por motivo nenhum, e guarda que
acusa sem motivo ensina a ignorar a guarda.

VEREDITO, NAO ACHADO — e isto e desenho, nao conveniencia. Um achado por prova
sem escopo entraria em `Judge.findings`, e o braco 1 da catraca acusaria 40
VIOLACAO NOVA na primeira execucao, obrigando a uma isencao larga o bastante
para tambem absorver regressao real. Catraca furada e pior que catraca ausente.
"""
from __future__ import annotations

SCOPE_BASES = ("code_reading", "record_reading")
SCOPE_FIELDS = ("padrao", "universo", "excluidos", "instrumento")


def escopo_completo(prova: dict) -> bool:
    """Os quatro campos presentes e nao vazios.

    O schema ja garante a FORMA quando `scope` existe; conferir campo a campo
    aqui nao e redundancia: `history_series` roda o juiz em commits antigos SEM
    validar schema, e dado velho nao satisfaz lei nova.
    """
    s = prova.get("scope")
    return isinstance(s, dict) and all(s.get(c) for c in SCOPE_FIELDS)


def indeterminadas(provas: list[dict]) -> set[str]:
    """Provas de leitura sem escopo completo. Nao vigem."""
    return {p["id"] for p in provas
            if p.get("basis") in SCOPE_BASES and not escopo_completo(p)}


def lista_fechada(fitnesses: list[dict]) -> dict[str, tuple[str, str]]:
    """prova -> (fitness, data) da LISTA FECHADA de quem o instrumento rebaixou ao nascer.

    LISTA DE IDS, NUNCA PREDICADO DE DATA. Um critterio como "prova anterior a
    tal data" isenta qualquer prova retrodatada, e uma regressao real que caia
    na mesma fitness no mesmo dia fica indistinguivel de um rebaixamento por
    instrumento — o rebaixamento tem a MESMA FORMA nos dois casos.

    A lista de ids nao tem esse furo: prova NOVA nasce fora dela, prova EDITADA
    nao ganha isencao de conteudo, e a lista so encurta (um id sai quando a
    prova ganha escopo completo). O lacre e um teste: o sha256 da lista ordenada
    esta congelado em test_genome_scope_check.py e em test_genome_check.py.
    """
    out: dict[str, tuple[str, str]] = {}
    for f in fitnesses:
        ii = f.get("instrument_introduced")
        if not ii:
            continue
        for pid in ii.get("proofs") or []:
            out[pid] = (f["id"], ii["date"])
    return out


def isenta(perdidas: list[str], selo: dict[str, tuple[str, str]]) -> tuple[str, str] | None:
    """A perda da refutacao e SO por prova da lista fechada?

    Devolve (fitness, data) quando sim; None quando ha QUALQUER prova de fora —
    e e isso que impede a isencao de esconder regressao. Perda vazia tambem
    devolve None: nao houve rebaixamento por instrumento, entao nao ha o que
    isentar, e a catraca decide pelos proprios motivos.
    """
    if not perdidas or any(pid not in selo for pid in perdidas):
        return None
    return selo[perdidas[0]]


def cobertura(provas: list[dict], vigentes: set[str],
              selo: dict[str, tuple[str, str]], indet: set[str]) -> dict:
    """Os numeros da FIT-019.

    `depois_da_introducao` e a lista que importa: prova de leitura sem escopo
    que NAO esta na lista fechada nasceu ou foi editada depois do instrumento, e
    nenhuma isencao a cobre.
    """
    alvo = [p["id"] for p in provas
            if p.get("basis") in SCOPE_BASES and p["id"] in vigentes]
    ind = sorted(i for i in alvo if i in indet)
    return {"alvo": len(alvo), "com_scope": len(alvo) - len(ind),
            "indeterminadas": ind,
            "na_introducao": [i for i in ind if i in selo],
            "depois_da_introducao": [i for i in ind if i not in selo],
            "introducao": sorted({v for v in selo.values()})}
