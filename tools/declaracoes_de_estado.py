#!/usr/bin/env python3
"""declaracoes_de_estado — a classe da UNK-0018, derivada em vez de escrita.

A REGRA DO TITULAR, de 2026-10-09, e o que este modulo existe para servir:

    "derivavel de outro artefato" -> nao se escreve, se deriva

POR QUE ESTE MODULO EXISTE, e a razao e a propria regra aplicada a si mesma.
A varredura de 2026-10-09 (PRF-0127) achou 48 declaracoes de estado na lei, e
as regras de classificacao estavam "escritas no script e aplicadas
mecanicamente" — mas O SCRIPT NAO FOI GUARDADO. Entao o 48 NAO E
RE-DERIVAVEL: ele virou numero escrito num documento, que e exatamente a classe
que ele denuncia. A lista dos 40 restantes tambem: ela vive em prosa, agrupada
em tres grupos, e as contas da prosa nao fecham com o total.

Logo o primeiro trabalho do C25-06 nao e converter campo: e tornar a LISTA
derivavel. O numero que este ecossistema anuncia e o que o instrumento imprime,
e ate agora nao havia instrumento.

O QUE ELE LE: os cinco artefatos governados do kit INSTALADO (nao da copia de
trabalho), porque a lei que vale e a que o consumidor instala.

AS REGRAS, declaradas antes do resultado
----------------------------------------

UMA EXCLUSAO, herdada da varredura de 09/10 e pelo mesmo motivo: subarvores de
`payload_schema` ficam fora. Elas sao JSON Schema — `type`, `required`,
`minItems` — e isso e norma por definicao: diz o que um payload DEVE ter, nunca
o que o mundo E. Incluir daria centenas de falsos candidatos.

CANDIDATO e todo valor-folha que seja inteiro, ou string que case com uma de
tres formas: palavra de situacao isolada, fracao (`0/7`), ou numero seguido de
substantivo contavel (`114 arquivos`).

CLASSIFICACAO POR CHAVE, nunca por olho:

    NORMA        a chave ordena, posiciona ou exige — diz o que DEVE ser
    HISTORICO    a chave registra o passado — changelog, correcao, erro_corrigido
    PROSA        o numero esta DENTRO de uma frase argumentativa em vez de ser o
                 conteudo do campo. Nao e ESTADO e nao e NORMA: e o LIMITE do
                 metodo mecanico, e nomea-lo e mais honesto que classifica-lo.
                 A varredura de 09/10 ja dizia que o total era PISO e nao teto
                 justamente por isto; aqui a parte que o regex ALCANCA fica
                 contada em vez de somada aos estados.
    ESTADO       o que sobra: afirma o que E

O MARCADOR `[CODIGO]` E MECANICO E FOI USADO: a propria lei marca com ele as
observacoes de codigo noutros repositorios (45 ocorrencias na Constituicao).
Campo com `[CODIGO]` e ESTADO mesmo quando a frase e longa, porque ali a frase
inteira E a declaracao.

E A ORIGEM, que e o item 1 do C25-06
------------------------------------

Para cada ESTADO, de QUAL artefato ele e derivavel. Tres saidas, e a terceira
e a que o titular esperava que existisse:

    PROPRIO_ARTEFATO   conta-se das chaves do mesmo YAML. A cura e DERIVAR, e
                       aqui o valor derivado e calculado e comparado com o
                       declarado — entao a defasagem aparece sozinha.
    OUTRO_ARTEFATO     deriva-se de outro artefato que EXISTE e esta ao alcance
                       de uma CI: outro YAML do kit, os arquivos de ADR, o grafo.
    SAI_DA_CLASSE      nao e derivavel de artefato nenhum. Observacao de codigo
                       em 19 repositorios, julgamento de milestone ou estado de
                       decisao que ninguem registrou em artefato. Para estes a
                       regra do titular NAO se aplica, e o que resta e DATA E
                       PROCEDENCIA OBRIGATORIAS — com precedente dentro da
                       propria lei: `monolitos.core.forbidden[0].violacao`
                       carrega `[DECIDIDO 2026-08-29]` e foi o unico dos 48 cuja
                       defasagem era detectavel pela propria escrita.

FALHA FECHADO, nas duas direcoes. ESTADO sem origem declarada levanta
`ClasseDefasada`; origem declarada cujo campo nao existe mais, idem. Sem isso o
mapa envelheceria calado — que e o defeito que ele serve para corrigir.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from dataclasses import dataclass

import yaml

ARTEFATOS = (
    "liceu_constitution.yaml",
    "liceu_contract_registry.yaml",
    "liceu_event_registry.yaml",
    "liceu_producer_registry.yaml",
    "liceu_event_reconciliation_ledger.yaml",
)

#: Subarvores fora do escopo. Declarada, e e a mesma da varredura de 09/10.
EXCLUSAO_DE_SUBARVORE = ("payload_schema",)

#: A chave ordena, posiciona ou exige: diz o que DEVE ser.
CHAVES_NORMA = frozenset({
    "ordem", "elo", "posicao_na_cadeia", "precede_elo", "domain_invariants",
    "required_envelope_fields", "contract_lifecycle", "topologia", "minimo",
    "maximo", "teto", "limite", "obrigatorio_antes_de", "somente_entao",
})
PREFIXOS_NORMA = ("REGRA", "REQUISITO", "INVARIANTE", "PROIBIDO", "POLITICA")

#: A chave registra o passado.
PREFIXOS_HISTORICO = ("changelog", "nota_versao", "REGRESSAO")
CHAVES_HISTORICO = frozenset({
    "corrige", "erro_corrigido", "correcao_de_registro", "descricao_da_correcao",
    "o_que_isso_revela", "evidencia_de_uso", "razao_da_rejeicao",
})

#: A chave DECLARA o que e, e vence a regra de prosa: campo assim e a
#: declaracao mesmo quando escrito em frase longa. Conferida em QUALQUER
#: segmento do caminho, porque `bug_conhecido.descricao` declara pelo pai.
CHAVES_ESTADO = frozenset({
    "status", "estado", "implementation_status", "status_semantica",
    "violacao", "violacao_critica", "divida_conhecida", "bug_conhecido",
    "a_verificar", "observacao", "observacao_positiva", "medicao_atual",
    "medicao", "hipotese", "pendencias_abertas", "adrs_pendentes", "total",
    "consequencia_de_codigo", "IMPLEMENTED_IN_MONOLITH", "criterios",
})
PREFIXOS_ESTADO = ("coerencia_com_", "escopo_P", "LIMITE_NAO_DEFINIDO")

SITUACAO = re.compile(
    r"^(ABERTA|ABERTO|FECHADA|FECHADO|PENDENTE|PASS|APROVADA|APROVADO|RECUSADA|"
    r"ADR_REQUIRED|NAO_INICIADA|INICIADA|EM_ANDAMENTO|CONCLUIDA|DEFINIDO|"
    r"NAO_DEFINIDO|IMPLEMENTADO|NAO_IMPLEMENTADO)\b")
FRACAO = re.compile(r"\b\d+\s*/\s*\d+\b")
NUM_SUBSTANTIVO = re.compile(r"\b\d+\s+[a-zA-ZÀ-ſ]{3,}")
MARCADOR_DE_CODIGO = "[CODIGO]"
#: Quantas palavras tornam o campo uma FRASE em vez de uma declaracao.
PALAVRAS_QUE_FAZEM_PROSA = 10

ESTADO, NORMA, HISTORICO, PROSA = "ESTADO", "NORMA", "HISTORICO", "PROSA"

PROPRIO_ARTEFATO = "PROPRIO_ARTEFATO"
OUTRO_ARTEFATO = "OUTRO_ARTEFATO"
SAI_DA_CLASSE = "SAI_DA_CLASSE"


class ClasseDefasada(RuntimeError):
    """O mapa de origem e a lei divergiram. Falha fechado de proposito."""


@dataclass(frozen=True)
class Origem:
    classe: str
    fonte: str
    razao: str


@dataclass(frozen=True)
class Declaracao:
    artefato: str
    caminho: str
    valor: object
    forma: str
    categoria: str
    regra: str

    @property
    def chave(self) -> str:
        return f"{self.artefato}:{self.caminho}"


def kit_instalado() -> pathlib.Path:
    from liceu_protocol import KIT_DIR  # noqa: PLC0415
    return pathlib.Path(KIT_DIR)


def _folha_final(caminho: str) -> str:
    return re.sub(r"\[\d+\]$", "", caminho).rsplit(".", 1)[-1]


def folhas(no, caminho: str = ""):
    if isinstance(no, dict):
        for k, v in no.items():
            if k in EXCLUSAO_DE_SUBARVORE:
                continue
            yield from folhas(v, f"{caminho}.{k}" if caminho else str(k))
    elif isinstance(no, list):
        for i, v in enumerate(no):
            yield from folhas(v, f"{caminho}[{i}]")
    else:
        yield caminho, no


def forma_de(valor) -> str | None:
    """A forma do candidato, ou None se nao e candidato."""
    if isinstance(valor, bool):
        return None                      # bool e decisao, nao contagem
    if isinstance(valor, int):
        return "inteiro"
    if not isinstance(valor, str):
        return None
    if SITUACAO.match(valor.strip()):
        return "situacao"
    if FRACAO.search(valor):
        return "fracao"
    if NUM_SUBSTANTIVO.search(valor):
        return "numero+substantivo"
    return None


def classifica(caminho: str, valor, forma: str) -> tuple[str, str]:
    folha = _folha_final(caminho)
    if folha in CHAVES_NORMA:
        return NORMA, f"chave {folha!r} ordena, posiciona ou exige"
    if any(folha.startswith(p) for p in PREFIXOS_NORMA):
        return NORMA, f"chave {folha!r} comeca por prefixo de norma"
    if folha in CHAVES_HISTORICO or any(folha.startswith(p) for p in PREFIXOS_HISTORICO):
        return HISTORICO, f"chave {folha!r} registra o passado"
    segmentos = [re.sub(r"\[\d+\]$", "", s) for s in caminho.split(".")]
    for s in segmentos:
        if s in CHAVES_ESTADO or s.startswith(PREFIXOS_ESTADO):
            return ESTADO, f"a chave {s!r} declara o que E, e isso vence a regra de prosa"
    if isinstance(valor, str) and MARCADOR_DE_CODIGO in valor:
        return ESTADO, "a propria lei marca com [CODIGO]: a frase inteira e a declaracao"
    if isinstance(valor, str) and len(valor.split()) > PALAVRAS_QUE_FAZEM_PROSA:
        return PROSA, (f"o numero esta dentro de frase de {len(valor.split())} palavras; "
                       "o campo argumenta em vez de declarar")
    return ESTADO, f"afirma o que E, na forma {forma!r}"


def enumera(kit: pathlib.Path) -> list[Declaracao]:
    achadas: list[Declaracao] = []
    for nome in ARTEFATOS:
        caminho_arq = kit / nome
        if not caminho_arq.exists():
            raise ClasseDefasada(f"artefato governado ausente do kit instalado: {nome}")
        dados = yaml.safe_load(caminho_arq.read_text(encoding="utf-8"))
        curto = nome.removeprefix("liceu_").removesuffix(".yaml")
        for caminho, valor in folhas(dados):
            f = forma_de(valor)
            if f is None:
                continue
            cat, regra = classifica(caminho, valor, f)
            achadas.append(Declaracao(curto, caminho, valor, f, cat, regra))
    return achadas


def estados(achadas: list[Declaracao]) -> list[Declaracao]:
    return [d for d in achadas if d.categoria == ESTADO]


def por_categoria(achadas: list[Declaracao]) -> dict[str, int]:
    fora = {}
    for d in achadas:
        fora[d.categoria] = fora.get(d.categoria, 0) + 1
    return fora


def por_artefato(achadas: list[Declaracao]) -> dict[str, dict[str, int]]:
    fora: dict[str, dict[str, int]] = {}
    for d in achadas:
        fora.setdefault(d.artefato, {}).setdefault(d.categoria, 0)
        fora[d.artefato][d.categoria] += 1
    return fora


# ---------------------------------------------------------------------------
# O mapa de origem — o item 1 do C25-06. Carregado de um YAML ao lado, para que
# a REVISAO dele seja leitura de dados e nao de codigo.
# ---------------------------------------------------------------------------

#: O mapa mora em tools/ e NAO em genome/: o juiz le genome/*.yaml como nos do
#: grafo, e este arquivo nao e um no. Dado separado do codigo para que revisa-lo
#: seja leitura de dados em vez de leitura de programa.
MAPA = pathlib.Path(__file__).resolve().parent / "origem-das-declaracoes.yaml"


def carrega_mapa(caminho: pathlib.Path | None = None) -> dict[str, Origem]:
    p = caminho or MAPA
    if not p.exists():
        return {}
    bruto = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    fora: dict[str, Origem] = {}
    for chave, o in (bruto.get("origens") or {}).items():
        if o.get("classe") not in (PROPRIO_ARTEFATO, OUTRO_ARTEFATO, SAI_DA_CLASSE):
            raise ClasseDefasada(f"{chave}: classe {o.get('classe')!r} nao existe")
        fora[chave] = Origem(o["classe"], o.get("fonte", ""), o.get("razao", ""))
    return fora


def confere_mapa(achadas: list[Declaracao],
                 mapa: dict[str, Origem]) -> tuple[list[str], list[str]]:
    """(estados sem origem declarada, origens cujo campo nao existe mais)."""
    presentes = {d.chave for d in estados(achadas)}
    sem_origem = sorted(presentes - set(mapa))
    orfas = sorted(set(mapa) - presentes)
    return sem_origem, orfas


def exige_mapa_em_dia(achadas: list[Declaracao], mapa: dict[str, Origem]) -> None:
    sem_origem, orfas = confere_mapa(achadas, mapa)
    if sem_origem or orfas:
        partes = []
        if sem_origem:
            partes.append(f"{len(sem_origem)} ESTADO sem origem declarada: "
                          + ", ".join(sem_origem[:6])
                          + (" ..." if len(sem_origem) > 6 else ""))
        if orfas:
            partes.append(f"{len(orfas)} origem(ns) declarada(s) cujo campo nao existe mais: "
                          + ", ".join(orfas[:6]) + (" ..." if len(orfas) > 6 else ""))
        raise ClasseDefasada(
            "o mapa de origem e a lei divergiram — "
            + "; ".join(partes)
            + ". Isto falha FECHADO: mapa que envelhece calado e a classe que ele corrige.")


# ---------------------------------------------------------------------------
# As derivacoes de verdade. Classificar um campo como derivavel e dizer que ele
# PODE ser derivado; derivar e mostrar o numero. Sem isto o mapa seria a mesma
# classe que ele corrige — uma afirmacao sobre o mundo escrita a mao.
#
# So entram aqui os campos cujo VALOR INTEIRO e o numero. Os dois de prosa que
# carregam contagem — `ci_adoption_order.nao_bloqueador` e
# `REGRA_DE_IDENTIDADE.aplica_a` — nao se comparam numericamente, porque a cura
# deles e a frase deixar de carregar o numero, nao o numero mudar.
# ---------------------------------------------------------------------------

def _tam(no, *chaves) -> int:
    for c in chaves:
        no = (no or {}).get(c)
    return len(no or [])


DERIVACOES: dict[str, object] = {
    "constitution:meta.pendencias_abertas":
        lambda a: _tam(a["constitution"], "pendencias"),
    "constitution:meta.adrs_pendentes":
        lambda a: _tam(a["constitution"], "adrs_pendentes"),
    "constitution:global.identidade_semantica_de_replay.total":
        lambda a: _tam(a["constitution"], "global", "identidade_semantica_de_replay", "campos"),
    "constitution:global.campos_exigidos_pelo_protocolo.total":
        lambda a: _tam(a["constitution"], "global", "campos_exigidos_pelo_protocolo", "campos"),
    "constitution:milestone.M1_CONSTITUTION_DEFINITION.criterios.CONSTITUTION_PENDING_DECISIONS":
        lambda a: _tam(a["constitution"], "pendencias"),
    "constitution:milestone.M1_CONSTITUTION_DEFINITION.criterios.CANONICAL_MONOLITH_IDS":
        lambda a: len(a["constitution"].get("monolitos") or {}),
    "event_reconciliation_ledger:meta.escopo_P2_5A":
        lambda a: len(a["event_reconciliation_ledger"].get("P2_5A_minimum_causal_thread") or {}),
}


#: ISENCOES NOMEADAS da exigencia de derivacao, cada uma com razao. Lista
#: FECHADA: entrada nova declarada derivavel tem de TER derivacao, ou a CI para.
#: E o padrao da FIT-019 — isencao decidida e registrada, nunca presumida —, e
#: existe porque "classificado como derivavel" sem derivacao e exatamente a
#: afirmacao escrita a mao que a regra do titular proibe.
ISENTOS_DE_DERIVACAO = {
    "constitution:global.campos_aceitos_pelo_servidor.procedencia":
        "a derivacao e por ANCORA no cv-backend-core e pertence a CI DO CORE, que e a "
        "unica que alcanca aquele arquivo. A CI do genoma ve o genoma e o kit, nunca o "
        "CORE — derivar aqui seria fingir alcance",
    "constitution:global.campos_aceitos_pelo_servidor.verificado_em":
        "mesmo caso, e os dois campos carregam a MESMA linha: a cura e uma ancora so, "
        "no CORE, e nao duas comparacoes aqui",
    "constitution:global.ci_adoption_order.nao_bloqueador":
        "a contagem esta DENTRO de prosa ('CI universal dos 15'). A cura e a frase "
        "deixar de carregar o numero, nao o numero ser comparado — comparar "
        "legitimaria a frase continuar a carrega-lo",
    "constitution:global.federation_cognition.REGRA_DE_IDENTIDADE.aplica_a":
        "idem: 'os 15 JOHNs locais' e prosa com contagem, e a cura e reescrever",
}


def exige_derivacao_declarada(mapa: dict[str, Origem]) -> None:
    """Derivavel DECLARADO tem de ser derivavel DE VERDADE, ou isento com razao.

    Este e o buraco que o mapa sozinho deixava: alguem acrescenta um campo,
    declara-o PROPRIO_ARTEFATO, e o mapa fica "em ordem" enquanto o valor
    continua escrito a mao. Fechar aqui custa ZERO no denominador do grafo.
    """
    pendentes = [k for k, o in mapa.items()
                 if o.classe in (PROPRIO_ARTEFATO, OUTRO_ARTEFATO)
                 and k not in DERIVACOES and k not in ISENTOS_DE_DERIVACAO]
    if pendentes:
        raise ClasseDefasada(
            f"{len(pendentes)} campo(s) declarado(s) derivavel(eis) SEM derivacao e sem "
            f"isencao nomeada: {', '.join(pendentes)}. Classificar como derivavel sem "
            "derivar e a mesma afirmacao a mao que a regra proibe — ou escreva a "
            "derivacao, ou declare a isencao com a razao.")
    orfas = sorted(set(ISENTOS_DE_DERIVACAO) - set(mapa))
    if orfas:
        raise ClasseDefasada(
            f"{len(orfas)} isencao(oes) de derivacao cujo campo nao esta mais no mapa: "
            f"{', '.join(orfas)}. Isencao que sobrevive ao campo e permissao orfa.")


def carrega_artefatos(kit: pathlib.Path) -> dict:
    return {nome.removeprefix("liceu_").removesuffix(".yaml"):
            yaml.safe_load((kit / nome).read_text(encoding="utf-8"))
            for nome in ARTEFATOS}


def confere_derivaveis(achadas: list[Declaracao], artefatos: dict) -> list[dict]:
    """Declarado x derivado, para os campos cujo valor E o numero."""
    por_chave = {d.chave: d for d in achadas}
    fora = []
    for chave, fn in DERIVACOES.items():
        d = por_chave.get(chave)
        if d is None:
            fora.append({"chave": chave, "declarado": None, "derivado": None,
                         "bate": None, "nota": "o campo nao existe mais no kit lido"})
            continue
        derivado = fn(artefatos)
        declarado = d.valor
        if isinstance(declarado, str):
            achados = re.findall(r"\d+", declarado)
            bate = bool(achados) and int(achados[0]) == derivado
            declarado_cmp = int(achados[0]) if achados else None
        else:
            declarado_cmp = declarado
            bate = declarado == derivado
        fora.append({"chave": chave, "declarado": declarado_cmp, "derivado": derivado,
                     "bate": bate, "nota": ""})
    return fora


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kit", help="diretorio do kit; o default e o INSTALADO")
    ap.add_argument("--listar", choices=[ESTADO, NORMA, HISTORICO, PROSA, "todos"],
                    help="imprime as declaracoes de uma categoria")
    ap.add_argument("--json", help="grava o resultado")
    ap.add_argument("--conferir-derivaveis", action="store_true",
                    help="declarado x derivado, para os campos cujo valor E o numero")
    ap.add_argument("--exigir-mapa", action="store_true",
                    help="falha se o mapa de origem e a lei divergirem")
    a = ap.parse_args(argv)

    kit = pathlib.Path(a.kit) if a.kit else kit_instalado()
    achadas = enumera(kit)
    cats = por_categoria(achadas)
    est = estados(achadas)
    mapa = carrega_mapa()

    print("DECLARACOES DE ESTADO NA LEI — derivadas, nao escritas")
    print("=" * 74)
    versao = (kit / "VERSION")
    if versao.exists():
        linhas = dict(l.split("=", 1) for l in versao.read_text(encoding="utf-8").splitlines()
                      if "=" in l)
        print(f"kit lido ....... {kit}")
        print(f"               constitution={linhas.get('constitution','?')} "
              f"conformance_kit={linhas.get('conformance_kit','?')}")
    print(f"candidatos ..... {len(achadas)}")
    for c in (ESTADO, NORMA, HISTORICO, PROSA):
        print(f"  {c:11s} {cats.get(c, 0)}")
    print()
    print("por artefato (ESTADO / total):")
    for art, d in por_artefato(achadas).items():
        print(f"  {art:34s} {d.get(ESTADO, 0):3d} / {sum(d.values()):3d}")

    if mapa:
        sem_origem, orfas = confere_mapa(achadas, mapa)
        print()
        print("ORIGEM DOS ESTADOS (item 1 do C25-06)")
        contagem: dict[str, int] = {}
        for d in est:
            o = mapa.get(d.chave)
            if o:
                contagem[o.classe] = contagem.get(o.classe, 0) + 1
        for cl in (PROPRIO_ARTEFATO, OUTRO_ARTEFATO, SAI_DA_CLASSE):
            print(f"  {cl:18s} {contagem.get(cl, 0)}")
        print(f"  sem origem declarada ... {len(sem_origem)}")
        print(f"  origem orfa ............ {len(orfas)}")
    else:
        print()
        print(f"MAPA DE ORIGEM AUSENTE ({MAPA.name}): os {len(est)} ESTADO estao sem origem.")

    if a.conferir_derivaveis:
        print()
        print("DERIVADO x DECLARADO — e aqui a defasagem aparece sozinha")
        linhas_c = confere_derivaveis(achadas, carrega_artefatos(kit))
        for r in linhas_c:
            marca = {True: "OK   ", False: "FALSO", None: "AUSENTE"}[r["bate"]]
            print(f"  [{marca}] {r['chave'].split(':', 1)[1][:62]:62s} "
                  f"declarado={r['declarado']} derivado={r['derivado']} {r['nota']}")
        falsos = [r for r in linhas_c if r["bate"] is False]
        print(f"  {len(linhas_c)} conferidos, {len(falsos)} defasado(s)")

    if a.listar:
        print()
        alvo = achadas if a.listar == "todos" else [d for d in achadas if d.categoria == a.listar]
        for d in alvo:
            o = mapa.get(d.chave)
            marca = f"  <{o.classe}>" if o else ""
            print(f"[{d.categoria:9s}] {d.artefato}:{d.caminho}{marca}")
            print(f"            {d.forma}: {str(d.valor)[:100]}")
            print(f"            regra: {d.regra}")

    if a.json:
        pathlib.Path(a.json).write_text(json.dumps({
            "instrumento": "tools/declaracoes_de_estado.py",
            "kit": str(kit),
            "candidatos": len(achadas),
            "por_categoria": cats,
            "por_artefato": por_artefato(achadas),
            "estados": [{"artefato": d.artefato, "caminho": d.caminho,
                         "valor": d.valor if not isinstance(d.valor, str) else d.valor[:200],
                         "forma": d.forma, "regra": d.regra,
                         "origem": (mapa[d.chave].classe if d.chave in mapa else None)}
                        for d in est],
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    if a.exigir_mapa:
        exige_mapa_em_dia(achadas, mapa)
        exige_derivacao_declarada(mapa)
        print("\nmapa de origem EM DIA: todo ESTADO tem origem, toda origem tem campo,")
        print(f"e todo derivavel tem derivacao ou isencao nomeada "
              f"({len(DERIVACOES)} derivadas, {len(ISENTOS_DE_DERIVACAO)} isentas).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ClasseDefasada as exc:
        print(f"\nCLASSE DEFASADA: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
