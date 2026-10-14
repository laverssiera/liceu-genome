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
import hashlib
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


def prefixos_de_registro_historico(dados: dict) -> tuple[str, ...]:
    """Subarvores que sao REGISTRO FECHADO, pela declaracao da propria lei.

    Um milestone que declara `baseline_constitution_version` nao descreve o
    mundo de hoje: ele registra o que valia quando ele fechou. O M1 escreve isso
    por extenso — 'M1 foi concluido contra a Constituicao 1.0.0. O campo preserva
    lineage historico; nao sobrescrever com a versao corrente.'

    POR QUE ESTA REGRA EXISTE, e e correcao de um erro meu: eu havia classificado
    `M1.criterios.CONSTITUTION_PENDING_DECISIONS` e `M1.criterios.CANONICAL_MONOLITH_IDS`
    como derivaveis do proprio arquivo, de `len(pendencias)` e `len(monolitos)`.
    A derivacao BATIA — 0 e 15 — e batia por COINCIDENCIA: a Constituicao hoje
    esta em 1.15.0 e o M1 fechou contra a 1.0.0. Derivar ali seria sobrescrever
    historia com o valor corrente, que e exatamente o que a nota proibe. Mesma
    familia da coincidencia de zero que deixava a deriva passar.
    """
    fora: list[str] = []
    for nome, bloco in (dados.get("milestone") or {}).items():
        if isinstance(bloco, dict) and bloco.get("baseline_constitution_version"):
            fora.append(f"milestone.{nome}.")
    return tuple(fora)


def classifica(caminho: str, valor, forma: str,
               prefixos_historicos: tuple[str, ...] = ()) -> tuple[str, str]:
    folha = _folha_final(caminho)
    if folha in CHAVES_NORMA:
        return NORMA, f"chave {folha!r} ordena, posiciona ou exige"
    if any(folha.startswith(p) for p in PREFIXOS_NORMA):
        return NORMA, f"chave {folha!r} comeca por prefixo de norma"
    if folha in CHAVES_HISTORICO or any(folha.startswith(p) for p in PREFIXOS_HISTORICO):
        return HISTORICO, f"chave {folha!r} registra o passado"
    for p in prefixos_historicos:
        if caminho.startswith(p):
            return HISTORICO, (f"{p.rstrip('.')} declara baseline_constitution_version: e "
                               "registro FECHADO do que valia quando fechou, nao do mundo "
                               "de hoje — derivar ali sobrescreveria historia")
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
        historicos = prefixos_de_registro_historico(dados)
        for caminho, valor in folhas(dados):
            f = forma_de(valor)
            if f is None:
                continue
            cat, regra = classifica(caminho, valor, f, historicos)
            achadas.append(Declaracao(curto, caminho, valor, f, cat, regra))
    return achadas


def incoerencias_internas(kit: pathlib.Path) -> list[dict]:
    """Contradicoes DENTRO do mesmo arquivo, derivadas sem sair do kit.

    MILESTONE QUE NAO COMECOU COM CRITERIO EM `PASS`. Medido em 2026-10-13: o M3
    declara `status: NOT_STARTED` e os CINCO criterios dele dizem PASS; o M4
    declara NOT_STARTED e os TRES dizem PASS. Nenhum dos dois blocos tem nota
    explicando, e `PASS` aparece SO nesses dois — o M1 e o M2 usam booleanos,
    inteiros e `KNOWN`. Se PASS quisesse dizer 'criterio bem definido', o M1 e o
    M2 tambem o usariam.

    O QUE ISTO NAO DECIDE: qual das duas afirmacoes e a falsa. Ou os criterios
    foram marcados e o status nao foi atualizado, ou o status esta certo e os
    criterios sao aspiracionais. O arquivo nao diz, e esta funcao nao escolhe.

    E e o caso mais puro da classe da UNK-0018: duas declaracoes no mesmo bloco,
    nenhuma regra as lendo, e a contradicao sobrevivendo porque ninguem reconta.
    """
    dados = yaml.safe_load((kit / "liceu_constitution.yaml").read_text(encoding="utf-8"))
    fora: list[dict] = []
    for nome, bloco in (dados.get("milestone") or {}).items():
        if not isinstance(bloco, dict):
            continue
        status = bloco.get("status")
        passes = [c for c, v in (bloco.get("criterios") or {}).items() if v == "PASS"]
        if status in ("NOT_STARTED", "FROZEN") and passes:
            fora.append({
                "onde": f"constitution:milestone.{nome}",
                "status": status,
                "criterios_em_PASS": passes,
                "o_que": (f"{nome} declara status={status} e {len(passes)} criterio(s) em "
                          "PASS, no mesmo bloco e sem nota. Uma das duas afirmacoes e "
                          "falsa, e o arquivo nao diz qual"),
            })
    return fora


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

class FonteAusente(ClasseDefasada):
    """O artefato de ORIGEM da derivacao desapareceu.

    E a DERIVA, e ela nao e mudanca no campo: e mudanca NOUTRO LUGAR. A primeira
    versao desta funcao fazia `(no or {}).get(c)` e depois `len(no or [])`, entao
    chave de origem AUSENTE devolvia 0 em silencio — e com o campo declarando 0
    o portao dizia OK enquanto a fonte nao existia mais. Medido em 2026-10-13:
    apagar `constitution.pendencias` deixava declarado=0, derivado=0, bate=True.

    Lista VAZIA e legitima; chave AUSENTE nao. Distinguir as duas e a diferenca
    entre falhar fechado e falhar aberto, e a deriva so e pega pela primeira.
    """


def _conta(no, *chaves) -> int:
    """Conta itens no caminho, LEVANTANDO se qualquer passo do caminho faltar."""
    andado: list[str] = []
    for c in chaves:
        if not isinstance(no, dict) or c not in no:
            raise FonteAusente(
                f"a fonte da derivacao sumiu em {'.'.join([*andado, c])}: o caminho "
                "declarado nao existe mais no artefato. Isto e DERIVA — o campo nao "
                "mudou, a ORIGEM dele mudou — e falha FECHADO de proposito")
        no = no[c]
        andado.append(c)
    if no is None:
        raise FonteAusente(
            f"{'.'.join(andado)} existe mas e nulo: tratar nulo como vazio foi "
            "exatamente o que deixava a deriva passar")
    return len(no)


DERIVACOES: dict[str, object] = {
    "constitution:meta.pendencias_abertas":
        lambda a: _conta(a, "constitution", "pendencias"),
    "constitution:meta.adrs_pendentes":
        lambda a: _conta(a, "constitution", "adrs_pendentes"),
    "constitution:global.identidade_semantica_de_replay.total":
        lambda a: _conta(a, "constitution", "global", "identidade_semantica_de_replay", "campos"),
    "constitution:global.campos_exigidos_pelo_protocolo.total":
        lambda a: _conta(a, "constitution", "global", "campos_exigidos_pelo_protocolo", "campos"),
    # NAO ENTRAM AQUI, e isto foi correcao de erro meu em 2026-10-13:
    # `M1.criterios.CONSTITUTION_PENDING_DECISIONS` e `M1.criterios.CANONICAL_MONOLITH_IDS`
    # pareciam derivaveis de `len(pendencias)` e `len(monolitos)`, e a derivacao
    # BATIA (0 e 15). Batia por COINCIDENCIA: o M1 declara
    # `baseline_constitution_version: 1.0.0` e a Constituicao esta em 1.15.0, e a
    # nota do proprio M1 diz 'preserva lineage historico; nao sobrescrever com a
    # versao corrente'. Derivar ali sobrescreveria historia. Agora o classificador
    # os trata como HISTORICO, por regra mecanica — ver
    # `prefixos_de_registro_historico`.
    "event_reconciliation_ledger:meta.escopo_P2_5A":
        lambda a: _conta(a, "event_reconciliation_ledger", "P2_5A_minimum_causal_thread"),
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


#: O LACRE DAS DUAS LISTAS DE ISENCAO, no padrao do `instrument_introduced` da
#: FIT-019: lista fechada, lacrada por sha256, que SO ENCOLHE.
#:
#: Sao DUAS porque ha dois caminhos de isencao, e tratar so o primeiro deixaria o
#: segundo como a brecha seguinte:
#:   ISENTOS_DE_DERIVACAO  derivavel que nao se deriva aqui, com razao
#:   SAI_DA_CLASSE         declarado nao-derivavel de artefato nenhum
#: O segundo e o mais fundo: a razao e prosa e ninguem a confere, entao sem lacre
#: bastaria classificar um campo novo como SAI_DA_CLASSE para fugir da regra.
#:
#: Medido em 2026-10-13, antes do lacre: acrescentei uma quinta isencao em tempo
#: de execucao e o portao PASSOU. O lacre existe por causa dessa medicao.
#:
#: SO ENCOLHE: `conferido ⊆ lacrado`. Curar um campo tira-o da lista e o lacre
#: segue valendo; acrescentar exige editar o lacre, e o sha256 congelado no teste
#: torna essa edicao visivel em vez de silenciosa.
LACRE_ISENTOS_SHA256 = "ffd84eeb4c4f577bbb3b8d5792d1275c1e351a02ee3226fe70528e47bcfdcb7b"
LACRE_SAI_DA_CLASSE_SHA256 = "4b36b3d6e1e8b281e4182e544a0ad88b9f9ccd6ebacefd1bfe471cf9ab51c812"

LACRE_ISENTOS = (
    "constitution:global.campos_aceitos_pelo_servidor.procedencia",
    "constitution:global.campos_aceitos_pelo_servidor.verificado_em",
    "constitution:global.ci_adoption_order.nao_bloqueador",
    "constitution:global.federation_cognition.REGRA_DE_IDENTIDADE.aplica_a",
)


#: Os 41 campos declarados NAO derivaveis em 13/10/2026. Lista lacrada que SO
#: ENCOLHE: curar um campo tira-o daqui, acrescentar exige editar isto E o
#: sha256 do teste. Sem este lacre bastaria classificar um campo novo como
#: SAI_DA_CLASSE para fugir da regra, porque a razao e prosa e ninguem a confere.
LACRE_SAI_DA_CLASSE = (
    "constitution:global.antipadroes.antipadrao_3_fallback_silencioso.referencia_correta",
    "constitution:global.authority_model.observacao",
    "constitution:global.campos_exigidos_pelo_protocolo.implementation_status",
    "constitution:global.core_dna.extracao_fisica_do_kernel.estado",
    "constitution:global.federation_authority.LIMITE_NAO_DEFINIDO.estado",
    "constitution:global.federation_authority.LIMITE_NAO_DEFINIDO.no_codigo.representacoes",
    "constitution:global.federation_cognition.REGRA_DE_IDENTIDADE.medicao_atual.geracoes_de_campo_alheio_em_producao",
    "constitution:global.federation_cognition.REGRA_DE_IDENTIDADE.medicao_atual.reivindicacoes_de_identidade",
    "constitution:global.internal_reference_implementations.referencias.fail_closed.aplica_a",
    "constitution:milestone.M1_CONSTITUTION_DEFINITION.status",
    "constitution:milestone.M2_FEDERATION_PROTOCOL_AND_STATIC_CONVERGENCE.criterios.DIRECT_CROSS_DOMAIN_DB",
    "constitution:milestone.M2_FEDERATION_PROTOCOL_AND_STATIC_CONVERGENCE.criterios.MINIMUM_THREAD_AUTHORITY_VIOLATIONS",
    "constitution:milestone.M3_AUTHENTICATED_RUNTIME_CONFORMANCE.criterios.CORE_ARCHIMEDES_AUTHENTICATED_BOUNDARY",
    "constitution:milestone.M3_AUTHENTICATED_RUNTIME_CONFORMANCE.criterios.DURABILITY",
    "constitution:milestone.M3_AUTHENTICATED_RUNTIME_CONFORMANCE.criterios.EVENT_DELIVERY",
    "constitution:milestone.M3_AUTHENTICATED_RUNTIME_CONFORMANCE.criterios.IDEMPOTENCY",
    "constitution:milestone.M3_AUTHENTICATED_RUNTIME_CONFORMANCE.criterios.REPLAY",
    "constitution:milestone.M4_FIRST_CAUSAL_AUTHORITY_CHAIN.criterios.MINIMUM_CAUSAL_THREAD_LINEAGE",
    "constitution:milestone.M4_FIRST_CAUSAL_AUTHORITY_CHAIN.criterios.MINIMUM_CAUSAL_THREAD_REPLAY",
    "constitution:milestone.M4_FIRST_CAUSAL_AUTHORITY_CHAIN.criterios.MINIMUM_CAUSAL_THREAD_RUNTIME",
    "constitution:monolitos.academia.divida_conhecida[0]",
    "constitution:monolitos.academia.divida_conhecida[1]",
    "constitution:monolitos.anchor.fronteira_de_continuidade.coerencia_com_external_effect",
    "constitution:monolitos.bim.violacao_critica.descricao",
    "constitution:monolitos.cea.divida_conhecida[2]",
    "constitution:monolitos.cea.forbidden[0].violacao",
    "constitution:monolitos.core.forbidden[0].violacao",
    "constitution:monolitos.core.fronteira_fisica.P1_07A_fronteira_semantica",
    "constitution:monolitos.core.fronteira_fisica.P1_07B_extracao_fisica",
    "constitution:monolitos.econotech.bug_conhecido.descricao",
    "constitution:monolitos.fornecedores.a_verificar[1]",
    "constitution:monolitos.gamemkt.violacao_critica.descricao",
    "constitution:monolitos.john.observacao_positiva",
    "constitution:monolitos.juridicotech.divida_conhecida[2]",
    "constitution:monolitos.ped.estado.descricao",
    "constitution:separacao_de_artifacts.razao",
    "contract_registry:meta.status",
    "event_reconciliation_ledger:P2_5B_duplicate_authority.federation.runtime.register.hipotese",
    "event_reconciliation_ledger:meta.escopo_P2_5B",
    "event_registry:events.authority.human.decision.recorded.implementation_status",
    "event_registry:resumo.IMPLEMENTED_IN_MONOLITH",
)


def lacre(chaves) -> str:
    return hashlib.sha256("\n".join(sorted(chaves)).encode("utf-8")).hexdigest()


def sai_da_classe_de(mapa: dict[str, Origem]) -> list[str]:
    return sorted(k for k, o in mapa.items() if o.classe == SAI_DA_CLASSE)


def exige_lacre(mapa: dict[str, Origem]) -> None:
    """As duas listas de isencao SO ENCOLHEM, e o lacre e por hash."""
    atuais_isentos = set(ISENTOS_DE_DERIVACAO)
    if not atuais_isentos <= set(LACRE_ISENTOS):
        novos = sorted(atuais_isentos - set(LACRE_ISENTOS))
        raise ClasseDefasada(
            f"{len(novos)} isencao(oes) de derivacao FORA DO LACRE: {', '.join(novos)}. "
            "A lista so encolhe. Acrescentar exige editar LACRE_ISENTOS e o sha256 do "
            "teste — que e o que torna a decisao visivel em vez de silenciosa.")
    atuais_sai = set(sai_da_classe_de(mapa))
    if not atuais_sai <= set(LACRE_SAI_DA_CLASSE):
        novos = sorted(atuais_sai - set(LACRE_SAI_DA_CLASSE))
        raise ClasseDefasada(
            f"{len(novos)} campo(s) classificado(s) SAI_DA_CLASSE FORA DO LACRE: "
            f"{', '.join(novos)}. Sem lacre bastaria classificar um campo novo como "
            "nao-derivavel para fugir da regra, porque a razao e prosa e ninguem a "
            "confere. A lista so encolhe.")


def classe_viva(mapa: dict[str, Origem]) -> list[str]:
    """Os campos que a regra do titular ainda alcanca: derivaveis nao curados.

    SAI_DA_CLASSE nao conta — por definicao a regra nao se aplica a eles, e
    conta-los faria a classe parecer eterna.
    """
    return sorted(k for k, o in mapa.items()
                  if o.classe in (PROPRIO_ARTEFATO, OUTRO_ARTEFATO))


def gatilho_fit_020(mapa: dict[str, Origem]) -> tuple[bool, str]:
    """O gatilho da FIT-020, MECANICO em vez de lembrado.

    DECISAO DO TITULAR, 2026-10-13: a FIT-020 nao foi recusada — foi ADIADA COM
    GATILHO, e a diferenca importa. "Recusada" fecha a pergunta; ela nao esta
    fechada, esta agendada. O freio NAO foi excepcionado: o denominador do grafo
    permanece 31.

    POR QUE ADIAR E BARATO AQUI: o portao desta CI ja recusa as tres formas, com
    42 mutacoes, entao a classe so pode encolher. Quando ela chegar a ZERO, a
    FIT-020 entra como guarda de REGRESSAO com zero membros vivos — sempre
    verde, barata, e guardando para sempre. E a forma mais limpa que uma fitness
    pode ter, e e por isso que a ordem (converter, depois guardar) e melhor que
    a inversa.

    O GATILHO VIVE AQUI, E NAO NUMA NOTA, por um motivo medido neste ciclo: o
    enumerador de 2026-10-09 era uma decisao que dependia de alguem lembrar, e
    ninguem lembrou. Gatilho escrito em prosa e da mesma familia.
    """
    viva = classe_viva(mapa)
    if viva:
        return False, (f"FIT-020 ADIADA: {len(viva)} membro(s) vivo(s) na classe. "
                       "O gatilho arma quando chegar a ZERO.")
    return True, ("FIT-020: GATILHO ARMADO — a classe chegou a ZERO. A fitness que o "
                  "C25-06 pediu pode entrar agora como guarda de REGRESSAO, com zero "
                  "membros vivos, e o custo no denominador passa a comprar uma guarda "
                  "permanente em vez de um remendo. Isto NAO e autorizacao: a excecao "
                  "ao freio continua sendo decisao do titular.")


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
                         "bate": None, "deriva": False,
                         "nota": "o campo nao existe mais no kit lido"})
            continue
        try:
            derivado = fn(artefatos)
        except FonteAusente as exc:
            # DERIVA: a origem saiu e o campo ficou. Entra como achado proprio,
            # nunca como "bate=True por coincidencia de zero".
            fora.append({"chave": chave, "declarado": d.valor, "derivado": None,
                         "bate": False, "deriva": True, "nota": str(exc)})
            continue
        declarado = d.valor
        if isinstance(declarado, str):
            achados = re.findall(r"\d+", declarado)
            bate = bool(achados) and int(achados[0]) == derivado
            declarado_cmp = int(achados[0]) if achados else None
        else:
            declarado_cmp = declarado
            bate = declarado == derivado
        fora.append({"chave": chave, "declarado": declarado_cmp, "derivado": derivado,
                     "bate": bate, "deriva": False, "nota": ""})
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
        armado, texto = gatilho_fit_020(mapa)
        print()
        print(f"{'>>> ' if armado else ''}{texto}")

    incoerentes = incoerencias_internas(kit)
    print()
    print("CONTRADICOES DENTRO DO MESMO ARQUIVO — insuficiencia declarada, nao violacao")
    if not incoerentes:
        print("  nenhuma.")
    for i in incoerentes:
        print(f"  {i['onde']}")
        print(f"    status={i['status']} e {len(i['criterios_em_PASS'])} criterio(s) em PASS: "
              f"{', '.join(i['criterios_em_PASS'])}")
        print("    uma das duas afirmacoes e falsa, e o arquivo nao diz qual")
    else:
        print()
        print(f"MAPA DE ORIGEM AUSENTE ({MAPA.name}): os {len(est)} ESTADO estao sem origem.")

    if a.conferir_derivaveis:
        print()
        print("DERIVADO x DECLARADO — e aqui a defasagem aparece sozinha")
        linhas_c = confere_derivaveis(achadas, carrega_artefatos(kit))
        for r in linhas_c:
            if r.get("deriva"):
                marca = "DERIVA"
            else:
                marca = {True: "OK    ", False: "FALSO ", None: "AUSENTE"}[r["bate"]]
            print(f"  [{marca}] {r['chave'].split(':', 1)[1][:62]:62s} "
                  f"declarado={r['declarado']} derivado={r['derivado']} {r['nota']}")
        falsos = [r for r in linhas_c if r["bate"] is False and not r.get("deriva")]
        derivas = [r for r in linhas_c if r.get("deriva")]
        print(f"  {len(linhas_c)} conferidos, {len(falsos)} defasado(s), "
              f"{len(derivas)} com a FONTE sumida")

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
        exige_lacre(mapa)
        # A DERIVA tambem para a CI: fonte sumida nao e "0 por coincidencia".
        derivas = [r for r in confere_derivaveis(achadas, carrega_artefatos(kit))
                   if r.get("deriva")]
        if derivas:
            raise ClasseDefasada(
                f"{len(derivas)} derivacao(oes) com a FONTE sumida: "
                + "; ".join(f"{r['chave']} — {r['nota']}" for r in derivas))
        print("\nmapa de origem EM DIA: todo ESTADO tem origem, toda origem tem campo,")
        print(f"todo derivavel tem derivacao ou isencao nomeada "
              f"({len(DERIVACOES)} derivadas, {len(ISENTOS_DE_DERIVACAO)} isentas),")
        print(f"as duas listas de isencao estao DENTRO do lacre "
              f"({len(LACRE_ISENTOS)} + {len(LACRE_SAI_DA_CLASSE)} lacrados, so encolhem),")
        print("e nenhuma derivacao perdeu a fonte.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ClasseDefasada as exc:
        print(f"\nCLASSE DEFASADA: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
