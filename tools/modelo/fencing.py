#!/usr/bin/env python3
"""A imposicao do fencing, ensaiada contra um LOG DE MENTIRA.

Por que este arquivo existe, e por que ele nao espera etcd
----------------------------------------------------------
O C29-02 mediu, com verificador exaustivo, que o `I3` -- "token de epoca
revogada nunca e aceito" -- VIOLA nos 32 subconjuntos das cinco propriedades de
log. Nenhuma combinacao o conserta, porque validar na ADMISSAO nao impede
CONCLUSAO depois da revogacao. O etcd entrega linearizabilidade e lease; ele nao
entrega "a aplicacao recusa ato de epoca revogada". Essa parte e protocolo.

Entao o `I3` nao espera mecanismo. O item que toca o log e um so -- "vigente vem
do LOG, nunca da alegacao do remetente" -- e para ENSAIAR a imposicao basta um
log que responda a pergunta. Um stub. O `I3` nao mede se o log esta certo; mede
se a APLICACAO recusa. O mecanismo real entra depois, substituindo o stub sem
tocar a regra.

As quatro regras, enunciadas para serem recusaveis
--------------------------------------------------
    1. todo ato que carrega autoridade carrega a sua EPOCA
    2. o receptor recusa ato cuja epoca nao seja a vigente
    3. "vigente" vem do LOG, nunca da alegacao do remetente
    4. revogacao e definitiva: superada a epoca N, nenhum ato sob N e aceito,
       em NENHUMA ordem de entrega -- nem o que estava em transito, nem o
       duplicado, nem o reordenado

DUAS ESCOLHAS DE DESENHO QUE VAO DECLARADAS, porque mudam o resultado:

(a) `MOMENTO DO EFEITO` versus `MOMENTO DA ADMISSAO`. O achado do C29-02 e que a
    conferencia na admissao e insuficiente: a requisicao admitida sob a epoca 1
    segue em voo quando a epoca vira 2. Entao a imposicao confere no EFEITO. As
    duas variantes ficam no codigo, e o ensaio RODA AS DUAS -- para que a
    insuficiencia da admissao seja medida aqui e nao apenas citada.

(b) A regra 2 diz "nao seja a vigente", e isso e `!=`, mais ESTRITO que o `I3`
    do modelo, que e `epoca >= comprometida`. A diferenca e o ato de epoca
    FUTURA: o `I3` o tolera, esta imposicao o recusa. A razao e a regra 3 -- um
    ato que alega epoca que o log nao comprometeu esta alegando, e alegacao do
    remetente nao e fonte. O CUSTO, nomeado: um receptor atrasado recusa ato
    legitimo do lider, e isso e perda de DISPONIBILIDADE para ganho de
    SEGURANCA. A direcao esta certa nesta camada; noutra camada poderia nao
    estar, e ai a escolha se refaz.

O que este arquivo NAO faz
--------------------------
Nao mede cauda de fsync, custo nem jitter: isso e propriedade de dispositivo e
de rede, e segue dependendo de host e de fatura (C28-01). Nao prova que um log
real responde a epoca certa -- prova que a aplicacao recusa quando o log diz que
a epoca virou. Sao duas perguntas, e esta fecha uma.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys

# ---------------------------------------------------------------------------
# o log de mentira
# ---------------------------------------------------------------------------


class LogDeMentira:
    """Responde "a epoca vigente e N", e nada mais.

    E stub de proposito. O `I3` nao mede se o log esta certo: mede se a
    aplicacao recusa quando o log diz que a epoca virou. Trocar isto por etcd ou
    PySyncObj nao altera nenhuma regra deste arquivo -- e e esse o ponto.
    """

    def __init__(self, epoca: int = 1) -> None:
        self._epoca = epoca
        self.leituras = 0

    def vigente(self) -> int:
        self.leituras += 1
        return self._epoca

    def transicionar(self, nova: int) -> None:
        if nova <= self._epoca:
            raise ValueError(f"epoca nao retrocede: {self._epoca} -> {nova}")
        self._epoca = nova


# ---------------------------------------------------------------------------
# o ato, e ele carrega a propria epoca
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Ato:
    """Regra 1: todo ato que carrega autoridade carrega a sua epoca.

    `frozen` nao e enfeite: o ensaio apresenta O MESMO ATO antes e depois da
    transicao, e "o mesmo, byte a byte" so e afirmavel se ele nao puder ser
    mexido no caminho. O `impressao()` e o que se compara.
    """
    recurso: str
    operacao: str
    epoca: int
    corpo: str

    def impressao(self) -> str:
        return json.dumps(dataclasses.asdict(self), sort_keys=True,
                          ensure_ascii=False)


class Recusado(Exception):
    """O ato foi recusado, e o motivo vem no texto."""


# ---------------------------------------------------------------------------
# a imposicao
# ---------------------------------------------------------------------------

MOMENTO_EFEITO = "efeito"
MOMENTO_ADMISSAO = "admissao"


class Receptor:
    """Impoe o fencing. Duas fases, porque o voo existe entre elas.

    `admitir()` aceita o ato para processamento e devolve um bilhete.
    `efetivar()` aplica. A transicao de epoca pode acontecer NO MEIO, e e
    exatamente ai que o achado do C29-02 vive.

    `momento`:
        MOMENTO_EFEITO     confere na admissao E no efeito -- a imposicao
        MOMENTO_ADMISSAO   confere so na admissao -- a variante INSUFICIENTE,
                           mantida para que o ensaio MECA a insuficiencia
    `confere_epoca`:
        False desliga a verificacao -- e a MUTACAO do passo 4. Portao que nao
        denuncia a propria remocao nao e portao.
    """

    def __init__(self, log: LogDeMentira, momento: str = MOMENTO_EFEITO,
                 confere_epoca: bool = True) -> None:
        if momento not in (MOMENTO_EFEITO, MOMENTO_ADMISSAO):
            raise ValueError(momento)
        self.log = log
        self.momento = momento
        self.confere_epoca = confere_epoca
        self.efetivados: list[str] = []
        self.recusas: list[str] = []

    # -- regras 2 e 3 juntas: compara com o LOG, nunca com o que o ato alega
    def _confere(self, ato: Ato, fase: str) -> None:
        if not self.confere_epoca:
            return
        vigente = self.log.vigente()
        if ato.epoca != vigente:
            motivo = (f"epoca {ato.epoca} nao e a vigente {vigente} "
                      f"(recusado no {fase})")
            self.recusas.append(motivo)
            raise Recusado(motivo)

    def admitir(self, ato: Ato) -> Ato:
        self._confere(ato, "admissao")
        return ato

    def efetivar(self, bilhete: Ato) -> str:
        if self.momento == MOMENTO_EFEITO:
            self._confere(bilhete, "efeito")
        self.efetivados.append(bilhete.impressao())
        return bilhete.impressao()

    def executar(self, ato: Ato) -> str:
        """Caminho sem voo: admite e efetiva na mesma respiracao."""
        return self.efetivar(self.admitir(ato))



# ---------------------------------------------------------------------------
# e o I3 COMO ESTA ESCRITO no modelo: o ensaio fecha ele, ou fecha outra coisa?
# ---------------------------------------------------------------------------

# O I3 da PRF-0202 e `all(ep >= corrente for _, ep in servindo)`: ele proibe a
# ENTRADA EM VOO sob epoca revogada, e nao o EFEITO dela. Recusar no efeito, que
# e o que o ensaio acima prova, nao remove a entrada de `servindo`.
#
# A propria PRF-0202 nomeou DUAS correcoes, e aqui se mede qual satisfaz o I3
# como ele esta escrito:
#     A) validar o token no momento da ESCRITA  -- o ensaio acima
#     B) DRENAR o que esta em voo antes de comprometer a epoca nova
#
# Busca exaustiva sobre espaco pequeno, e sem tocar o autoridade.py: a
# superficie dele esta provada pela PRF-0202 e pela PRF-0203, e reescreve-lo
# para responder isto invalidaria as duas.

REMEDIO_ESCRITA = "A_valida_na_escrita"
REMEDIO_DRENO = "B_drena_antes_de_comprometer"


def _i3(comprometida: int, servindo: frozenset) -> bool:
    """O I3 como a PRF-0202 o escreve, copiado e nao reinterpretado."""
    return all(ep >= comprometida for ep in servindo)


def percorre(remedio: str, teto_epoca: int = 2) -> dict:
    """Todos os estados alcancaveis de (epoca comprometida, em voo).

    Estado minimo que basta para a pergunta: a epoca que o log comprometeu, e o
    conjunto de epocas das requisicoes EM VOO. Quem esta em voo nao importa --
    o I3 olha so a epoca carimbada.
    """
    inicial = (1, frozenset())
    vistos = {inicial}
    fila = [(inicial, ())]
    violacoes = []
    while fila:
        (comp, voo), caminho = fila.pop()
        if not _i3(comp, voo):
            violacoes.append({"estado": {"comprometida": comp,
                                         "em_voo": sorted(voo)},
                              "caminho": list(caminho)})
            continue
        proximos = []
        # admitir: so se carimba a epoca vigente (regras 2 e 3, na admissao)
        if comp not in voo:
            proximos.append(("admitir", (comp, voo | {comp})))
        # concluir: o remedio A RECUSA concluir sob epoca revogada; nos dois
        # casos a entrada sai de voo quando a conclusao acontece
        for ep in sorted(voo):
            if remedio == REMEDIO_ESCRITA and ep != comp:
                # recusada: NAO toma efeito. E a entrada continua em voo, que e
                # exatamente o ponto desta medicao.
                continue
            proximos.append((f"concluir(ep={ep})", (comp, voo - {ep})))
        # promover: o log comete a epoca seguinte
        if comp < teto_epoca:
            nova = comp + 1
            if remedio == REMEDIO_DRENO:
                # B: drena o que esta em voo ANTES de comprometer
                proximos.append(("promover+drenar", (nova, frozenset())))
            else:
                proximos.append(("promover", (nova, voo)))
        for rotulo, est in proximos:
            if est not in vistos:
                vistos.add(est)
                fila.append((est, caminho + (rotulo,)))
    return {"remedio": remedio, "estados": len(vistos),
            "viola_o_I3": bool(violacoes),
            "contraexemplo": violacoes[0] if violacoes else None}


def invariante_do_modelo() -> dict:
    a = percorre(REMEDIO_ESCRITA)
    b = percorre(REMEDIO_DRENO)
    return {"A_valida_na_escrita": a, "B_drena": b}


def imprime_invariante(r: dict) -> None:
    print("  O I3 como a PRF-0202 o escreve proibe a ENTRADA EM VOO sob epoca")
    print("  revogada, e nao o EFEITO dela. Entao a pergunta nao e se a")
    print("  aplicacao recusa -- isso o ensaio provou -- e sim se o I3 do papel")
    print("  fica satisfeito. As duas correcoes que a PRF-0202 nomeou:")
    print()
    for chave, nome in (("A_valida_na_escrita", "A) validar na ESCRITA (o ensaio acima)"),
                        ("B_drena", "B) DRENAR antes de comprometer")):
        x = r[chave]
        print(f"    {nome}")
        print(f"       {x['estados']} estados alcancaveis; "
              f"viola o I3? {'SIM' if x['viola_o_I3'] else 'NAO'}")
        if x["contraexemplo"]:
            c = x["contraexemplo"]
            print(f"       contraexemplo: {' -> '.join(c['caminho'])}")
            print(f"         estado: comprometida={c['estado']['comprometida']}, "
                  f"em voo={c['estado']['em_voo']}")
        print()

# ---------------------------------------------------------------------------
# o ensaio
# ---------------------------------------------------------------------------


def _caso(nome: str, fn) -> dict:
    """Roda um caso e devolve o que de fato aconteceu, nao o que se esperava."""
    try:
        fn()
        return {"caso": nome, "resultado": "ACEITO", "motivo": None}
    except Recusado as e:
        return {"caso": nome, "resultado": "RECUSADO", "motivo": str(e)}


def ensaio(momento: str = MOMENTO_EFEITO) -> dict:
    """Os cinco passos do C30-01, nesta ordem, com o 'antes' gravado."""
    r: dict = {"momento_da_conferencia": momento, "passos": []}
    ato_n = Ato("authority_instances", "promover", 1, "a=1")

    # ---- passo 1: o "antes". Modelo da PRF-0108: a linha de base e GRAVADA,
    #      porque sem ela "foi recusado" nao distingue imposicao de quebra.
    log = LogDeMentira(1)
    rec = Receptor(log, momento)
    antes = _caso("1. ato sob a epoca vigente", lambda: rec.executar(ato_n))
    antes["impressao_do_ato"] = ato_n.impressao()
    antes["epoca_vigente_no_log"] = 1
    antes["esperado"] = "ACEITO"
    r["passos"].append(antes)

    # ---- passo 2 e 3: forca a transicao e apresenta O MESMO ato
    log.transicionar(2)
    depois = _caso("3. o MESMO ato, apos a transicao para 2",
                   lambda: rec.executar(ato_n))
    depois["impressao_do_ato"] = ato_n.impressao()
    depois["o_ato_e_identico"] = (depois["impressao_do_ato"]
                                  == antes["impressao_do_ato"])
    depois["epoca_vigente_no_log"] = 2
    depois["esperado"] = "RECUSADO"
    r["passos"].append(depois)

    # ---- passo 4: MUTACAO. Removida a verificacao, o passo 3 passa a aceitar?
    log_m = LogDeMentira(1)
    rec_m = Receptor(log_m, momento, confere_epoca=False)
    rec_m.executar(ato_n)
    log_m.transicionar(2)
    mut = _caso("4. MUTACAO: mesma cena, sem a verificacao de epoca",
                lambda: rec_m.executar(ato_n))
    mut["esperado"] = "ACEITO — e se nao for, o portao nao estava impondo nada"
    r["passos"].append(mut)

    # ---- passo 5: as tres ordens adversas. O coracao do ciclo.
    # 5a EM VOO: admitido sob 1, transicao, efetivado depois
    log_a = LogDeMentira(1)
    rec_a = Receptor(log_a, momento)
    bilhete = rec_a.admitir(ato_n)
    log_a.transicionar(2)
    voo = _caso("5a. EM VOO: admitido sob 1, efetivado apos a transicao",
                lambda: rec_a.efetivar(bilhete))
    voo["esperado"] = "RECUSADO"
    r["passos"].append(voo)

    # 5b DUPLICADO: o mesmo ato duas vezes, uma antes e uma depois
    log_b = LogDeMentira(1)
    rec_b = Receptor(log_b, momento)
    primeiro = _caso("5b-i. DUPLICADO, a primeira copia, antes da transicao",
                     lambda: rec_b.executar(ato_n))
    primeiro["esperado"] = "ACEITO"
    r["passos"].append(primeiro)
    log_b.transicionar(2)
    segundo = _caso("5b-ii. DUPLICADO, a segunda copia, apos a transicao",
                    lambda: rec_b.executar(ato_n))
    segundo["esperado"] = "RECUSADO"
    r["passos"].append(segundo)

    # 5c REORDENADO: dois atos admitidos sob 1, efetivados fora de ordem,
    #    com a transicao no meio
    log_c = LogDeMentira(1)
    rec_c = Receptor(log_c, momento)
    a1 = Ato("authority_instances", "promover", 1, "a=1")
    a2 = Ato("authority_instances", "promover", 1, "a=2")
    b1, b2 = rec_c.admitir(a1), rec_c.admitir(a2)
    reord_antes = _caso("5c-i. REORDENADO: o SEGUNDO efetivado primeiro, "
                        "ainda sob 1", lambda: rec_c.efetivar(b2))
    reord_antes["esperado"] = "ACEITO"
    r["passos"].append(reord_antes)
    log_c.transicionar(2)
    reord = _caso("5c-ii. REORDENADO: o PRIMEIRO efetivado por ultimo, apos a "
                  "transicao", lambda: rec_c.efetivar(b1))
    reord["esperado"] = "RECUSADO"
    r["passos"].append(reord)

    # ---- o veredito, derivado e nao declarado
    def achou(pref: str) -> dict:
        return next(p for p in r["passos"] if p["caso"].startswith(pref))

    exigencias = {
        "1. ato sob epoca vigente e ACEITO": achou("1.")["resultado"] == "ACEITO",
        "3. o MESMO ato apos a transicao e RECUSADO":
            achou("3.")["resultado"] == "RECUSADO" and achou("3.")["o_ato_e_identico"],
        "4. sem a verificacao, o passo 3 ACEITA (a mutacao e denunciada)":
            achou("4.")["resultado"] == "ACEITO",
        "5a. em voo e RECUSADO": achou("5a")["resultado"] == "RECUSADO",
        "5b. duplicado apos a transicao e RECUSADO":
            achou("5b-ii")["resultado"] == "RECUSADO",
        "5c. reordenado apos a transicao e RECUSADO":
            achou("5c-ii")["resultado"] == "RECUSADO",
    }
    r["exigencias"] = exigencias
    r["faltando"] = [k for k, v in exigencias.items() if not v]
    r["veredito"] = "SUFICIENTE" if not r["faltando"] else "INSUFICIENTE"
    return r


def imprime(r: dict) -> None:
    print(f"  conferencia no momento do {r['momento_da_conferencia'].upper()}")
    for p in r["passos"]:
        bate = "ok  " if p["resultado"] in str(p.get("esperado", "")) else "NAO "
        print(f"    [{bate}] {p['caso']}")
        print(f"             -> {p['resultado']}"
              + (f": {p['motivo']}" if p.get("motivo") else ""))
        if "o_ato_e_identico" in p:
            print(f"             o ato e identico ao do passo 1: "
                  f"{p['o_ato_e_identico']}")
    print()
    for k, v in r["exigencias"].items():
        print(f"    {'OK   ' if v else 'FALTA'} {k}")
    print()
    print(f"    VEREDITO: {r['veredito']}")
    if r["faltando"]:
        for f in r["faltando"]:
            print(f"      falta: {f}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--json", help="escreve o ensaio completo neste arquivo")
    a = p.parse_args(argv)

    print("A IMPOSICAO DO FENCING, contra um log de mentira")
    print("  O I3 nao e propriedade de log (C29-02, PRF-0202): ele viola nos 32")
    print("  subconjuntos das cinco propriedades. Entao a imposicao e protocolo,")
    print("  e se ensaia com stub -- o mecanismo real troca o stub, nao a regra.")
    print()

    print("=" * 70)
    print("A IMPOSICAO: conferencia no momento do EFEITO")
    print("=" * 70)
    bom = ensaio(MOMENTO_EFEITO)
    imprime(bom)

    print()
    print("=" * 70)
    print("A VARIANTE INSUFICIENTE: conferencia so na ADMISSAO")
    print("=" * 70)
    print("  Nao esta aqui como alternativa: esta para MEDIR o achado do C29-02")
    print("  em vez de cita-lo. Se a admissao bastasse, este bloco passaria.")
    print()
    ruim = ensaio(MOMENTO_ADMISSAO)
    imprime(ruim)

    print()
    print("=" * 70)
    print("O QUE A COMPARACAO DIZ")
    print("=" * 70)
    so_efeito = [k for k in bom["exigencias"]
                 if bom["exigencias"][k] and not ruim["exigencias"][k]]
    if so_efeito:
        print("  Exigencias que SO a conferencia no efeito satisfaz:")
        for k in so_efeito:
            print(f"    {k}")
        print("  E este e o achado do C29-02, agora executavel: conferir na")
        print("  ADMISSAO nao impede CONCLUSAO depois da revogacao.")
    else:
        print("  Nenhuma diferenca entre os dois momentos neste ensaio -- e isso")
        print("  CONTRADIRIA o C29-02. Resultado a investigar, nao a celebrar.")

    print()
    print("=" * 70)
    print("E O I3 COMO ELE ESTA ESCRITO: o ensaio fecha ele, ou outra coisa?")
    print("=" * 70)
    inv = invariante_do_modelo()
    imprime_invariante(inv)
    fecha = not inv["A_valida_na_escrita"]["viola_o_I3"]
    if fecha:
        print("  A validacao na escrita satisfaz o I3 como escrito.")
    else:
        print("  A VALIDACAO NA ESCRITA **NAO** SATISFAZ O I3 COMO ESCRITO, e")
        print("  isso nao e falha do ensaio: e o enunciado do I3 proibindo o")
        print("  ESTADO em voo, nao o efeito. O que o ensaio fecha e a")
        print("  propriedade de seguranca -- nenhum ato sob epoca revogada toma")
        print("  efeito. O que o I3 escrito exige e mais: que a requisicao nem")
        print("  FIQUE em voo, e isso so o DRENO entrega.")
        print("  CONSEQUENCIA PARA O CICLO: o C30-01 entrega a imposicao e a")
        print("  prova dela, e NAO autoriza marcar o I3 como PROVEN. Ou o I3 se")
        print("  divide em dois invariantes, ou falta o dreno -- e as duas sao")
        print("  decisao de desenho, nao resultado de medicao.")

    if a.json:
        import pathlib
        pathlib.Path(a.json).write_text(
            json.dumps({"efeito": bom, "admissao": ruim,
                        "exigencias_so_do_efeito": so_efeito,
                        "invariante_do_modelo": inv,
                        "o_ensaio_satisfaz_o_I3_como_escrito": fecha},
                       indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n  ensaio escrito em {a.json}")

    return 0 if bom["veredito"] == "SUFICIENTE" else 1


if __name__ == "__main__":
    sys.exit(main())
