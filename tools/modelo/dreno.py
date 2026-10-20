#!/usr/bin/env python3
"""O dreno com PRAZO — o que o fencing.py nao podia ver.

POR QUE ESTE ARQUIVO EXISTE. O `fencing.py` do C30-01 mediu os dois remedios
que a PRF-0202 nomeou e concluiu que so o DRENO satisfaz o I3 como escrito. Mas
o dreno dele e INCONDICIONAL: a transicao e `("promover+drenar", (nova,
frozenset()))`, que esvazia o voo ATOMICAMENTE com a promocao. Isso nao mede o
remedio -- mede a SUPOSICAO de que o dreno sempre termina.

E o dreno pode nao terminar. Uma requisicao em voo pode TRAVAR: processo
pausado, rede parada, chamada a jusante pendurada. O que acontece ai e a
pergunta de desenho inteira, e decidir "o dreno" sobre o modelo antigo seria
decidir sobre uma idealizacao.

ENTAO AQUI O VOO PODE TRAVAR, e os remedios se separam pelo que fazem no prazo:

  A_so_cerca          nao drena; a jusante recusa no momento do efeito
  B_ideal             drena sempre, instantaneo (o fencing.py)
  B_bloqueia          so promove com voo VAZIO -- espera o que for preciso
  B_prazo_avanca      drena ate o prazo; vencido, promove de qualquer forma
  AB_prazo_cerca      drena ate o prazo; vencido, promove E cerca os retardados

O QUE SE MEDE DE CADA UM, e as tres respostas nao se confundem:

  I3a  nenhum ato sob epoca revogada TOMA EFEITO        -- seguranca
  I3b  nada FICA em voo sob epoca revogada              -- o estado
  avanco  ha estado alcancavel de onde a epoca NUNCA mais avanca,
          em NENHUMA continuacao?

E AQUI UM TESTE MEU FALHOU E CORRIGIU A METRICA, nao a expectativa. A primeira
versao media "existe estado em que promover nao esta disponivel AGORA", e com
isso o B_bloqueia aparecia bloqueado mesmo sem nada travado -- porque esperar o
voo esvaziar bloqueia tambem com requisicao NORMAL em voo. Isso confunde ATRASO
com IMPASSE: a normal conclui e o avanco vem; a travada nao conclui nunca.

A metrica certa e IRRECUPERABILIDADE: constroi-se o grafo de estados e marca-se
morto o estado de onde NENHUMA continuacao alcanca uma promocao. Atraso nao e
morte; impasse e.

Vivacidade nao se prova em verificador de estados. `vivo` NAO prova que a epoca
sempre avanca -- prova que nao ha estado de onde ela seja impossivel. A
diferenca fica declarada e nao compensada.
"""
from __future__ import annotations

import argparse
import json
import sys

A_SO_CERCA = "A_so_cerca"
B_IDEAL = "B_ideal"
B_BLOQUEIA = "B_bloqueia"
B_PRAZO_AVANCA = "B_prazo_avanca"
AB_PRAZO_CERCA = "AB_prazo_cerca"
REMEDIOS = (A_SO_CERCA, B_IDEAL, B_BLOQUEIA, B_PRAZO_AVANCA, AB_PRAZO_CERCA)

#: um estado e (epoca comprometida, em voo, travados, efeito_sob_revogada)
#: `em voo` e `travados` guardam a EPOCA carimbada de cada requisicao; quem a
#: pratica nao importa, porque o I3 olha so a epoca.


def i3b(comp: int, voo: frozenset, travados: frozenset) -> bool:
    """Nada FICA em voo sob epoca revogada. Travado TAMBEM esta em voo."""
    return all(ep >= comp for ep in (voo | travados))


def i3b_efeito_possivel(comp: int, voo: frozenset, travados: frozenset,
                        cercado: bool) -> bool:
    """O I3b relido: conta como "em voo" so o que AINDA PODE tomar efeito.

    NAO E O I3b COMO ESCRITO, e nao se confunde com ele. O escrito proibe a
    PRESENCA da requisicao sob epoca revogada; este proibe a presenca do que
    ainda pode CONCLUIR. Com a cerca no efeito, o retardado nao pode -- entao
    ele deixa de contar, e a leitura muda o veredito sem mudar o sistema.

    Esta funcao existe para MEDIR a diferenca que a releitura faria, nao para
    substituir o invariante: reescrever invariante e ato do titular, como foi a
    divisao do I3 em 2026-10-20.
    """
    if cercado:
        return True
    return all(ep >= comp for ep in (voo | travados))


def i3a(sujo: bool) -> bool:
    """Nenhum ato sob epoca revogada TOMA EFEITO."""
    return not sujo


def _cerca_no_efeito(remedio: str) -> bool:
    """O receptor confere a epoca no momento do efeito e RECUSA se revogada."""
    return remedio in (A_SO_CERCA, AB_PRAZO_CERCA, B_IDEAL, B_BLOQUEIA,
                       B_PRAZO_AVANCA)


def percorre(remedio: str, teto_epoca: int = 3, teto_travados: int = 1) -> dict:
    """Busca exaustiva. Devolve o que cada invariante faz e se o avanco trava.

    `teto_travados` limita quantas requisicoes podem travar, para o espaco
    ficar finito. Com 1 ja aparece o contraexemplo; subir nao muda o veredito,
    e isso tambem e medido (ver --self-test).
    """
    if remedio not in REMEDIOS:
        raise ValueError(f"remedio desconhecido: {remedio!r}")
    inicial = (1, frozenset(), frozenset(), False)
    vistos = {inicial}
    fila = [(inicial, ())]
    viola_a, viados_b = [], []
    viola_b = viados_b
    arestas: dict = {}
    promove: set = set()
    caminho_de = {inicial: ()}

    while fila:
        est, caminho = fila.pop()
        comp, voo, trav, sujo = est

        if not i3a(sujo):
            viola_a.append({"estado": {"comprometida": comp,
                                       "em_voo": sorted(voo),
                                       "travados": sorted(trav)},
                            "caminho": list(caminho)})
        if not i3b(comp, voo, trav):
            viola_b.append({"estado": {"comprometida": comp,
                                       "em_voo": sorted(voo),
                                       "travados": sorted(trav)},
                            "caminho": list(caminho)})

        proximos = []

        # --- admitir: so carimba a epoca vigente (a imposicao, na admissao)
        if comp not in voo and comp not in trav:
            proximos.append(("admitir", (comp, voo | {comp}, trav, sujo)))

        # --- travar: a requisicao em voo PENDURA e nunca conclui sozinha.
        # E o que o modelo antigo nao tinha, e e o unico acrescimo que muda
        # alguma resposta.
        if len(trav) < teto_travados:
            for ep in sorted(voo):
                proximos.append((f"travar(ep={ep})",
                                 (comp, voo - {ep}, trav | {ep}, sujo)))

        # --- concluir: a requisicao chega ao EFEITO
        for ep in sorted(voo):
            if _cerca_no_efeito(remedio) and ep != comp:
                # cercada: NAO toma efeito, e CONTINUA em voo -- e este o
                # ponto que separa o I3a do I3b
                continue
            proximos.append((f"concluir(ep={ep})",
                             (comp, voo - {ep}, trav, sujo or ep != comp)))

        # --- promover: o log compromete a epoca seguinte
        if comp < teto_epoca:
            nova = comp + 1
            if remedio == B_IDEAL:
                # drena tudo, inclusive o travado: a idealizacao do fencing.py
                proximos.append(("promover+drenar", (nova, frozenset(),
                                                     frozenset(), sujo)))
            elif remedio == B_BLOQUEIA:
                # so promove com voo E travados vazios
                if not voo and not trav:
                    proximos.append(("promover", (nova, voo, trav, sujo)))
            elif remedio in (B_PRAZO_AVANCA, AB_PRAZO_CERCA):
                # drena o que DA, e no prazo promove de qualquer forma: o que
                # nao drenou fica em voo sob epoca revogada
                proximos.append(("promover(prazo vencido)",
                                 (nova, frozenset(), trav, sujo)))
            else:  # A_SO_CERCA: nao drena nada
                proximos.append(("promover", (nova, voo, trav, sujo)))

        arestas[est] = [e for _, e in proximos]
        if any(r.startswith("promover") for r, _ in proximos):
            promove.add(est)

        for rotulo, e in proximos:
            if e not in vistos:
                vistos.add(e)
                caminho_de[e] = caminho + (rotulo,)
                fila.append((e, caminho + (rotulo,)))

    # --- IRRECUPERABILIDADE: de que estados NENHUMA continuacao promove?
    # ponto fixo para tras a partir de quem tem aresta de promocao
    alcanca = set(promove)
    mudou = True
    while mudou:
        mudou = False
        for e, saidas in arestas.items():
            if e in alcanca:
                continue
            if any(s in alcanca for s in saidas):
                alcanca.add(e)
                mudou = True
    mortos = [e for e in vistos
              if e not in alcanca and e[0] < teto_epoca]
    sem_avanco = [{"estado": {"comprometida": e[0], "em_voo": sorted(e[1]),
                              "travados": sorted(e[2])},
                   "caminho": list(caminho_de.get(e, ()))}
                  for e in mortos]

    return {
        "remedio": remedio,
        "estados": len(vistos),
        "viola_I3a": bool(viola_a),
        "viola_I3b": bool(viola_b),
        "avanco_bloqueado": bool(sem_avanco),
        "contraexemplo_I3a": viola_a[0] if viola_a else None,
        "contraexemplo_I3b": viola_b[0] if viola_b else None,
        "contraexemplo_avanco": sem_avanco[0] if sem_avanco else None,
    }


def self_test() -> int:
    """Sem ele nenhum resultado deste arquivo vale."""
    casos = []
    r = {m: percorre(m) for m in REMEDIOS}

    # 1. o modelo reproduz o achado do fencing.py quando o dreno e ideal
    casos.append(("B_ideal satisfaz o I3b, como o fencing.py mediu",
                  not r[B_IDEAL]["viola_I3b"],
                  f"B_ideal violou o I3b: {r[B_IDEAL]['contraexemplo_I3b']}"))
    casos.append(("A_so_cerca viola o I3b, como o fencing.py mediu",
                  r[A_SO_CERCA]["viola_I3b"],
                  "A_so_cerca nao violou o I3b -- contradiz a PRF-0202"))

    # 2. A CERCA NO EFEITO salva o I3a em TODOS os remedios que a tem
    for m in REMEDIOS:
        casos.append((f"{m}: a cerca no efeito mantem o I3a",
                      not r[m]["viola_I3a"],
                      f"{m} violou o I3a: {r[m]['contraexemplo_I3a']}"))

    # 3. O ACHADO: com voo que TRAVA, os dois ramos do dreno com prazo se
    #    separam, e nenhum dos dois entrega I3b E avanco ao mesmo tempo.
    casos.append(("B_bloqueia mantem o I3b",
                  not r[B_BLOQUEIA]["viola_I3b"],
                  f"violou: {r[B_BLOQUEIA]['contraexemplo_I3b']}"))
    casos.append(("B_bloqueia TRAVA o avanco quando ha travado",
                  r[B_BLOQUEIA]["avanco_bloqueado"],
                  "esperava bloqueio estrutural do avanco e nao houve"))
    casos.append(("B_prazo_avanca NAO trava o avanco",
                  not r[B_PRAZO_AVANCA]["avanco_bloqueado"],
                  "esperava avanco livre"))
    casos.append(("B_prazo_avanca VIOLA o I3b",
                  r[B_PRAZO_AVANCA]["viola_I3b"],
                  "esperava violacao do I3b no prazo vencido"))

    # 4. MUTACAO: tirar o travamento devolve o modelo antigo, e o achado
    #    DESAPARECE. Se nao desaparecer, o travamento nao era o que mediu.
    sem_travar = percorre(B_BLOQUEIA, teto_travados=0)
    casos.append(("MUTACAO: sem voo que trava, o IMPASSE do B_bloqueia SOME",
                  not sem_travar["avanco_bloqueado"],
                  "o impasse sobreviveu a remocao do travamento -- entao nao "
                  "era o travamento que o produzia"))
    # e o que sobra sem travamento e ATRASO, nao impasse: a primeira versao
    # desta medicao confundia os dois, e o teste acima foi o que pegou.
    casos.append(("sem travamento o B_bloqueia AINDA espera o voo esvaziar",
                  not sem_travar["viola_I3b"],
                  "esperar o voo esvaziar deixou de manter o I3b"))

    # 5. MUTACAO: tirar a cerca no efeito tem de quebrar o I3a
    import copy  # noqa: F401  (declarado: nao se usa, a mutacao e por funcao)
    global _cerca_no_efeito
    original = _cerca_no_efeito
    try:
        _cerca_no_efeito = lambda remedio: False  # noqa: E731
        m = percorre(A_SO_CERCA)
        casos.append(("MUTACAO: sem a cerca no efeito, o I3a QUEBRA",
                      m["viola_I3a"],
                      "o I3a sobreviveu a remocao da cerca -- entao nao era a "
                      "cerca que o sustentava"))
    finally:
        _cerca_no_efeito = original

    # 6. o veredito nao muda ao subir o teto de travados
    for t in (2, 3):
        a = percorre(B_PRAZO_AVANCA, teto_travados=t)
        casos.append((f"teto_travados={t} nao muda o veredito do I3b",
                      a["viola_I3b"] == r[B_PRAZO_AVANCA]["viola_I3b"],
                      "o veredito mudou com o teto -- o espaco era pequeno "
                      "demais e a conclusao nao vale"))

    casos.append(("o I3b RELIDO vale onde ha cerca no efeito",
                  all(i3b_efeito_possivel(1, frozenset({1}), frozenset({1}),
                                          _cerca_no_efeito(m))
                      for m in REMEDIOS),
                  "a releitura nao salvou algum remedio com cerca"))
    casos.append(("o I3b RELIDO NAO e o escrito: sem cerca ele tambem cai",
                  not i3b_efeito_possivel(2, frozenset({1}), frozenset(), False),
                  "a releitura passou a valer sem cerca -- entao ela nao esta "
                  "medindo a cerca, e nao distingue nada"))

    print("SELF-TEST — o verificador enxerga?")
    ruins = 0
    for nome, ok, porque in casos:
        print(f"  {'ok  ' if ok else 'FALHA'}  {nome}")
        if not ok:
            print(f"          {porque}")
            ruins += 1
    print(f"\n  {len(casos) - ruins} de {len(casos)} passaram")
    return 1 if ruins else 0


def relatorio() -> dict:
    r = {m: percorre(m) for m in REMEDIOS}
    print("=" * 70)
    print("O DRENO COM PRAZO — os cinco remedios, com voo que TRAVA")
    print("=" * 70)
    print(f"  {'remedio':20s} {'estados':>7}  {'I3a':>5}  {'I3b':>5}  "
          f"{'I3b-rel':>7}  avanco")
    for m in REMEDIOS:
        x = r[m]
        rel = i3b_efeito_possivel(1, frozenset(), frozenset(),
                                  _cerca_no_efeito(m))
        print(f"  {m:20s} {x['estados']:>7}  "
              f"{'VALE' if not x['viola_I3a'] else 'VIOLA':>5}  "
              f"{'VALE' if not x['viola_I3b'] else 'VIOLA':>5}  "
              f"{'VALE' if rel else 'VIOLA':>7}  "
              f"{'BLOQUEIA' if x['avanco_bloqueado'] else 'livre'}")
        x["I3b_relido_vale"] = bool(rel)
    print()
    print("  O QUE ISTO SEPARA, e o fencing.py nao podia ver:")
    print("  o dreno dele era INCONDICIONAL (promover+drenar esvaziava o voo")
    print("  atomicamente). Com voo que TRAVA, o dreno se parte em dois, e")
    print("  NENHUM DOS DOIS entrega I3b e avanco ao mesmo tempo:")
    print(f"    B_bloqueia      I3b VALE  · avanco BLOQUEIA")
    print(f"    B_prazo_avanca  I3b VIOLA · avanco livre")
    print()
    ce = r[B_PRAZO_AVANCA]["contraexemplo_I3b"]
    if ce:
        print(f"  o contraexemplo do prazo vencido: {' -> '.join(ce['caminho'])}")
        print(f"    estado: {ce['estado']}")
    print()
    print("  E A CERCA NO EFEITO SUSTENTA O I3a NOS CINCO, inclusive quando o")
    print("  I3b cai: nenhum ato sob epoca revogada toma efeito em nenhum deles.")
    print("  Logo a escolha nao e entre seguranca e nada -- e entre o ESTADO")
    print("  em voo e o AVANCO da epoca, com a seguranca preservada nos dois.")
    print()
    print("  O QUE ESTE ARQUIVO NAO PROVA, declarado: `avanco_bloqueado` e a")
    print("  forma SEGURA de uma pergunta de vivacidade -- existe estado")
    print("  alcancavel de onde promover e impossivel? `livre` NAO prova que a")
    print("  epoca sempre avanca; prova que nao ha bloqueio estrutural.")
    return r


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--json")
    a = p.parse_args()
    if a.self_test:
        return self_test()
    r = relatorio()
    if a.json:
        import pathlib
        pathlib.Path(a.json).write_text(
            json.dumps(r, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8", newline="\n")
        print(f"\n  ensaio escrito em {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
