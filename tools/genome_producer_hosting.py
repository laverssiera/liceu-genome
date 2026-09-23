#!/usr/bin/env python3
"""FIT-017 — produtor sem repositorio declara ONDE esta, para o juiz.

Nenhuma fitness conferia o kit contra o mundo, e o buraco aparecia assim:
`repository: null` pode ser a verdade — o Authority Control Plane nao e
monolito soberano e nao tem dominio proprio — e mesmo assim nao dizer onde o
codigo esta. A razao vinha escrita em campo de nome MAIUSCULO: prosa, que
explica para humano e que nenhuma verificacao consegue seguir.

Por que este arquivo existe separado do juiz
--------------------------------------------
A PRF-0031 prova esta regra, e o `mechanism` dela cobria `genome_check.py`
inteiro — 1500 linhas que crescem a cada ciclo. Resultado: TODA fitness nova
invalidava a prova da FIT-017, que nao tinha mudado. Aconteceu na FIT-018, e a
CI acusou corretamente uma prova que continuava verdadeira.

A FIT-012 proibe superficie de repositorio inteiro porque ela ficaria obsoleta
a cada commit, o genoma viraria ruido e as pessoas o ignorariam. Um arquivo de
1500 linhas e o mesmo defeito em escala menor. Aqui a superficie da prova e
este modulo e o teste dele, e nada mais: mexer no juiz por outro motivo nao
pede que a FIT-017 seja provada de novo.

A funcao e PURA de proposito — recebe o dicionario de produtores e devolve
achados. O juiz so a chama e traduz para `find`. Assim o teste desta regra nao
precisa montar um genoma inteiro para exercitar quatro recusas.
"""
from __future__ import annotations


def achados(producers: dict | None) -> list[tuple[str, str]]:
    """(subject, mensagem) para cada produtor que nao diz onde esta seu codigo.

    Quatro recusas, e a ordem importa: sem `hosted_in` nao ha o que conferir;
    com `hosted_in` que nao existe, a cadeia nao comeca; com anfitriao que
    tambem nao tem repositorio, ela nao CHEGA a codigo nenhum; e com tudo isso
    certo mas sem razao, o ponteiro existe sem motivo.
    """
    out: list[tuple[str, str]] = []
    producers = producers or {}
    for pid, entry in producers.items():
        entry = entry or {}
        if entry.get("repository"):
            continue
        hospedeiro = entry.get("hosted_in")
        if not hospedeiro:
            out.append((f"{pid}/hosted_in",
                        f"{pid} não declara repository nem hosted_in: nada no kit diz onde "
                        f"procurar o código deste produtor"))
            continue
        anfitriao = producers.get(hospedeiro)
        if anfitriao is None:
            out.append((f"{pid}/hosted_in/inexistente",
                        f"{pid} declara hosted_in {hospedeiro!r}, que não é produtor do registry"))
        elif not (anfitriao or {}).get("repository"):
            out.append((f"{pid}/hosted_in/sem_repo",
                        f"{pid} declara hosted_in {hospedeiro!r}, que também não tem "
                        f"repositório: a cadeia de hospedagem não chega a código nenhum"))
        elif not str(entry.get("hosted_in_reason") or "").strip():
            out.append((f"{pid}/hosted_in_reason",
                        f"{pid} diz onde está mas não diz por que não tem repositório próprio: "
                        f"hosted_in sem razão é um ponteiro sem motivo"))
    return out
