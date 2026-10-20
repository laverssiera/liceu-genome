#!/usr/bin/env python3
"""C29-02 — o modelo do protocolo de autoridade das Tres Maes, e o verificador.

O QUE ISTO NAO E, antes de tudo: nao e TLC e nao e Alloy. Nenhum dos dois esta
disponivel nesta maquina -- nao ha Java -- e baixar e executar binario de fora
nao e ato meu. O que roda aqui e um VERIFICADOR DE ESTADOS EXPLICITO escrito a
mao: busca exaustiva em largura sobre um espaco de estados finito, com os
invariantes conferidos em CADA estado alcancavel.

POR QUE ISSO AINDA VALE ALGUMA COISA: porque a pergunta do C29-02 nao e "o
protocolo e correto" e sim "QUE PROPRIEDADES O LOG PRECISA OFERECER para os
invariantes valerem". Essa pergunta se responde ligando e desligando cada
propriedade do log e vendo qual invariante quebra. Um verificador exaustivo
sobre espaco pequeno responde isso; o que ele NAO da e a confianca de uma
ferramenta revisada por terceiros, e essa diferenca fica declarada.

E POR QUE VOCE DEVE DESCONFIAR DELE: verificador escrito pelo mesmo autor do
modelo pode nao estar olhando. Por isso ele vem com MUTACOES: variantes do
protocolo com violacao CONHECIDA, e o verificador tem de encontrar todas. Se
`--self-test` nao acusar as mutacoes, nenhum resultado deste arquivo vale.

A INVERSAO QUE O CICLO 29 CORRIGIU: nao se modela "etcd" nem "PySyncObj". Modela-
se o PROTOCOLO sobre um log com propriedades parametrizadas, e a saida e a lista
de propriedades exigidas -- contra a qual os dois mecanismos passam a ser
comparaveis por evidencia em vez de por intuicao.
"""
from __future__ import annotations

import argparse
import itertools
import sys
from dataclasses import dataclass, replace
from typing import Iterator

# ---------------------------------------------------------------------------
# AS PROPRIEDADES DO LOG, que sao o objeto da pergunta
# ---------------------------------------------------------------------------
#: P1 unicidade por indice: duas entradas diferentes nunca ocupam o mesmo indice
#: P2 monotonia: a epoca comprometida nunca decresce nem repete
#: P3 leitura linearizavel: ler a epoca corrente devolve a ULTIMA comprometida
#: P4 durabilidade: entrada comprometida nunca desaparece
#: P5 unicidade de lider por epoca: o log so compromete UM lider para cada epoca
PROPRIEDADES = ("P1_unicidade_por_indice", "P2_monotonia", "P3_leitura_linearizavel",
                "P4_durabilidade", "P5_lider_unico_por_epoca")


@dataclass(frozen=True)
class Estado:
    """Um estado do sistema. Tudo imutavel para poder ir num conjunto."""
    #: entradas comprometidas no log: tupla de (epoca, instancia_lider)
    log: tuple
    #: o que cada instancia ACREDITA ser a epoca corrente (visao local)
    visao: tuple
    #: instancias servindo agora, com a epoca que cada uma carimba
    servindo: tuple
    #: o que a Testemunha registrou: tupla de (epoca, lider)
    testemunha: tuple
    #: instancias vivas
    vivas: tuple
    #: UM BIT, e nao um historico: o I3a diz NUNCA, e para "nunca" basta
    #: lembrar que aconteceu uma vez. Historico de conclusoes multiplicaria o
    #: espaco de estados sem dizer nada a mais.
    efeito_sob_revogada: bool = False

    def chave(self):
        return (self.log, self.visao, self.servindo, self.testemunha,
                self.vivas, self.efeito_sob_revogada)


@dataclass(frozen=True)
class Modelo:
    instancias: tuple
    epoca_max: int
    props: frozenset
    #: variante de protocolo, usada pelas mutacoes do self-test
    mutacao: str = ""

    def tem(self, p: str) -> bool:
        return p in self.props


def inicial(m: Modelo) -> Estado:
    return Estado(log=(), visao=tuple(0 for _ in m.instancias), servindo=(),
                  testemunha=(), vivas=tuple(m.instancias))


def epoca_comprometida(e: Estado) -> int:
    return e.log[-1][0] if e.log else 0


def lider_comprometido(e: Estado):
    return e.log[-1][1] if e.log else None


# ---------------------------------------------------------------------------
# AS TRANSICOES
# ---------------------------------------------------------------------------
def sucessores(m: Modelo, e: Estado) -> Iterator[tuple]:
    idx = {n: i for i, n in enumerate(m.instancias)}

    # --- promover: uma instancia viva propoe ser lider na proxima epoca
    for inst in e.vivas:
        nova = e.visao[idx[inst]] + 1
        if nova > m.epoca_max:
            continue
        if m.tem("P2_monotonia") and nova <= epoca_comprometida(e):
            # o log recusa epoca que nao avanca
            continue
        if m.tem("P5_lider_unico_por_epoca") and any(ep == nova for ep, _ in e.log):
            continue
        if m.mutacao == "sem_recusa_de_epoca_repetida":
            pass  # a mutacao deixa passar o que P5 recusaria
        novo_log = e.log + ((nova, inst),)
        nova_visao = list(e.visao)
        nova_visao[idx[inst]] = nova
        yield (f"promover({inst},e{nova})",
               replace(e, log=novo_log, visao=tuple(nova_visao)))

    # --- atualizar visao: uma instancia le a epoca do log
    for inst in e.vivas:
        atual = e.visao[idx[inst]]
        if m.tem("P3_leitura_linearizavel"):
            vistos = [epoca_comprometida(e)]
        else:
            # sem leitura linearizavel, a instancia pode ler QUALQUER epoca ja
            # comprometida -- inclusive uma antiga. E a leitura obsoleta.
            vistos = sorted({ep for ep, _ in e.log} | {0})
        for v in vistos:
            if v == atual:
                continue
            nv = list(e.visao)
            nv[idx[inst]] = v
            yield (f"ler({inst})->e{v}", replace(e, visao=tuple(nv)))

    # --- servir: uma instancia viva passa a servir carimbando a epoca que ve
    for inst in e.vivas:
        ep = e.visao[idx[inst]]
        if ep == 0 or (inst, ep) in e.servindo:
            continue
        if m.mutacao != "serve_sem_conferir_fencing":
            # FENCING: so serve quem carimba a epoca corrente do log
            if ep != epoca_comprometida(e):
                continue
            # e so o lider daquela epoca
            if m.tem("P5_lider_unico_por_epoca") and lider_comprometido(e) != inst:
                continue
        yield (f"servir({inst},e{ep})",
               replace(e, servindo=e.servindo + ((inst, ep),)))

    # --- CONCLUIR: o ato em voo toma EFEITO. Esta transicao entrou em
    # 2026-10-20 com a divisao do I3, e sem ela o I3a nao teria onde ser
    # violado -- invariante que nenhum estado alcancavel viola e decoracao.
    for (inst, ep) in e.servindo:
        comp = epoca_comprometida(e)
        resto = tuple(x for x in e.servindo if x != (inst, ep))
        if m.mutacao != "conclui_sem_conferir_no_efeito" and ep != comp:
            # A IMPOSICAO DO C30-01: confere no momento do efeito e RECUSA.
            # O ato sai de voo sem tomar efeito -- e e exatamente por isso
            # que ela satisfaz o I3a e nao satisfaz o I3b.
            yield (f"recusar({inst},e{ep})", replace(e, servindo=resto))
            continue
        yield (f"concluir({inst},e{ep})",
               replace(e, servindo=resto,
                       efeito_sob_revogada=e.efeito_sob_revogada or ep != comp))

    # --- parar de servir (pausa de processo / perda de lideranca)
    for s in e.servindo:
        yield (f"parar({s[0]})",
               replace(e, servindo=tuple(x for x in e.servindo if x != s)))

    # --- a Testemunha registra uma transicao que o log mostra
    if e.log:
        ult = e.log[-1]
        if ult not in e.testemunha:
            if m.mutacao == "testemunha_registra_sem_commit":
                falsa = (epoca_comprometida(e) + 1, m.instancias[0])
                yield ("testemunha(FALSA)",
                       replace(e, testemunha=e.testemunha + (falsa,)))
            yield (f"testemunha{ult}",
                   replace(e, testemunha=e.testemunha + (ult,)))

    # --- queda e volta de instancia
    for inst in e.vivas:
        if len(e.vivas) > 1:
            yield (f"cair({inst})",
                   replace(e, vivas=tuple(x for x in e.vivas if x != inst),
                           servindo=tuple(s for s in e.servindo if s[0] != inst)))
    for inst in m.instancias:
        if inst not in e.vivas:
            yield (f"voltar({inst})", replace(e, vivas=tuple(sorted(e.vivas + (inst,)))))

    # --- perda de entrada do log, quando nao ha durabilidade
    if not m.tem("P4_durabilidade") and e.log:
        yield ("log_perde_ultima", replace(e, log=e.log[:-1]))


# ---------------------------------------------------------------------------
# OS CINCO INVARIANTES
# ---------------------------------------------------------------------------
def i1(e: Estado, m: Modelo) -> bool:
    """Nunca duas instancias servindo a MESMA epoca."""
    epocas = [ep for _, ep in e.servindo]
    return len(epocas) == len(set(epocas))


def i2(e: Estado, m: Modelo) -> bool:
    """authority_epoch monotonica: nunca decresce, nunca repete."""
    eps = [ep for ep, _ in e.log]
    return all(b > a for a, b in zip(eps, eps[1:]))


def i3a(e: Estado, m: Modelo) -> bool:
    """I3a -- SEGURANCA: nenhum ato sob epoca revogada TOMA EFEITO.

    E o que a imposicao do C30-01 entrega, conferindo no momento do efeito.
    Falsificavel pela mutacao `conclui_sem_conferir_no_efeito`.
    """
    return not e.efeito_sob_revogada


def cerca_no_efeito(m: Modelo) -> bool:
    """O receptor confere a epoca no EFEITO e recusa se revogada.

    E propriedade do PROTOCOLO e nao do estado, e e por isso que os
    invariantes recebem o modelo. A mutacao que a desliga e o unico jeito de
    o I3b relido ser falsificavel.
    """
    return m.mutacao != "conclui_sem_conferir_no_efeito"


def i3b_escrito(e: Estado, m: Modelo) -> bool:
    """O I3b COMO ESTAVA ESCRITO, guardado para a releitura ser comparavel.

    "Nada FICA em voo sob epoca revogada" -- proibe a PRESENCA. Fica FORA do
    dicionario de invariantes desde 2026-10-20: nao e mais o que o LICEU
    exige, e continua aqui para que a mudanca de leitura possa ser MEDIDA
    contra o que havia antes, em vez de afirmada.
    """
    corrente = epoca_comprometida(e)
    return all(ep >= corrente for _, ep in e.servindo)


def i3b(e: Estado, m: Modelo) -> bool:
    """I3b -- RELIDO em 2026-10-20, por decisao do titular: nada que ainda
    POSSA TOMAR EFEITO fica sob epoca revogada.

    O que mudou e o que se proibe. A leitura escrita proibia a PRESENCA da
    requisicao sob epoca revogada, e so o dreno a satisfazia -- um dreno que
    nao pode falhar, porque o que trava nao drena (PRF-0260). Esta leitura
    proibe a presenca do que ainda pode CONCLUIR: com a cerca no momento do
    efeito, o retardado nao pode, e deixa de contar.

    NAO E O I3a, e ha teste para isso. O I3a olha o PASSADO -- nenhum efeito
    sob epoca revogada ACONTECEU. Este olha o PRESENTE -- nada que possa
    acontecer esta ali. Existe estado em que este viola e o I3a ainda vale:
    o retardado existe e pode concluir, e nada concluiu ainda.
    """
    if cerca_no_efeito(m):
        return True
    corrente = epoca_comprometida(e)
    return all(ep >= corrente for _, ep in e.servindo)


def i4(e: Estado, m: Modelo) -> bool:
    """Se a Testemunha registra transicao, houve transicao real."""
    return all(t in e.log for t in e.testemunha)


#: O I3b FOI RELIDO EM 2026-10-20, por decisao do titular, em termos de
#: EFEITO POSSIVEL: ele proibia a PRESENCA da requisicao sob epoca revogada e
#: passa a proibir a presenca do que ainda PODE tomar efeito. A leitura antiga
#: fica em `i3b_escrito`, fora deste dicionario, para a mudanca ser medivel.
#: O I3 FOI DIVIDIDO EM 2026-10-20, por decisao do titular. O enunciado
#: unico -- "token de epoca revogada NUNCA aceito" -- carregava duas
#: exigencias de forca diferente, e por isso nao tinha veredito: a imposicao
#: do C30-01 satisfaz uma e nao a outra. A divisao nao fecha nada; ela separa
#: o que esta fechado do que nao esta.
INVARIANTES = {"I1_uma_instancia_por_epoca": i1, "I2_epoca_monotonica": i2,
               "I3a_nenhum_efeito_sob_epoca_revogada": i3a,
               "I3b_nada_que_possa_tomar_efeito_sob_epoca_revogada": i3b,
               "I4_testemunha_nao_inventa": i4}
# I5 (progresso) e propriedade de VIVACIDADE e nao de seguranca: nao se confere
# estado a estado. Fica declarada como NAO EXPRESSAVEL neste verificador.


def explorar(m: Modelo, teto: int = 300000):
    """Busca em largura exaustiva. Devolve (violacoes, estados, truncou)."""
    ini = inicial(m)
    vistos = {ini.chave()}
    fila = [(ini, ())]
    violacoes = {}
    truncou = False
    while fila:
        if len(vistos) > teto:
            truncou = True
            break
        atual, caminho = fila.pop(0)
        for nome, inv in INVARIANTES.items():
            if nome not in violacoes and not inv(atual, m):
                violacoes[nome] = caminho
        for rotulo, prox in sucessores(m, atual):
            k = prox.chave()
            if k not in vistos:
                vistos.add(k)
                fila.append((prox, caminho + (rotulo,)))
    return violacoes, len(vistos), truncou


def roda(props, instancias=("ativa", "sucessora"), epoca_max=2, mutacao=""):
    m = Modelo(instancias=instancias, epoca_max=epoca_max,
               props=frozenset(props), mutacao=mutacao)
    return explorar(m)


# ---------------------------------------------------------------------------
# O SELF-TEST: sem ele, nenhum resultado deste arquivo vale
# ---------------------------------------------------------------------------
I3B_NOME = "I3b_nada_que_possa_tomar_efeito_sob_epoca_revogada"


def _existe_estado(m: Modelo, pred, teto: int = 300000) -> bool:
    """Existe estado alcancavel que satisfaz `pred`? Busca exaustiva."""
    ini = inicial(m)
    vistos = {ini.chave()}
    fila = [ini]
    while fila and len(vistos) <= teto:
        atual = fila.pop(0)
        if pred(atual):
            return True
        for _, prox in sucessores(m, atual):
            k = prox.chave()
            if k not in vistos:
                vistos.add(k)
                fila.append(prox)
    return False


def self_test() -> int:
    casos = []
    todas = list(PROPRIEDADES)

    # 1. COM TODAS AS PROPRIEDADES, o unico invariante que ainda viola e o I3 --
    #    e isso NAO e defeito do modelo, e o achado. A expectativa original era
    #    "nenhuma violacao"; o verificador a derrubou em tres passos:
    #        promover(ativa,e1) -> servir(ativa,e1) -> promover(ativa,e2)
    #    uma requisicao ADMITIDA sob a epoca 1 segue em voo quando a epoca vira
    #    2. Admissao validada no momento do pedido nao impede conclusao depois
    #    da revogacao.
    v, n, _ = roda(todas)
    # A RELEITURA DE 2026-10-20 MUDA ESTE RESULTADO, e a mudanca fica MEDIDA
    # nas duas leituras ao lado: com o log completo o protocolo passa a nao
    # violar NADA sob a leitura vigente, e a leitura ESCRITA segue violando.
    casos.append(("log completo nao viola NADA sob o I3b relido",
                  set(v) == set(),
                  f"esperava nenhuma violacao, violou {sorted(v)}"))
    m_cheio = Modelo(instancias=("ativa", "sucessora"), epoca_max=2,
                     props=frozenset(PROPRIEDADES))
    escrito_viola = _existe_estado(m_cheio, lambda e: not i3b_escrito(e, m_cheio))
    casos.append(("e a leitura ESCRITA do I3b SEGUE violando no mesmo modelo",
                  escrito_viola,
                  "a leitura escrita parou de violar -- entao a releitura nao "
                  "mudou nada e nao havia o que decidir"))

    # A DIVISAO DE 2026-10-20 SEPAROU, e isso se mede na leitura ESCRITA --
    # que e a que estava em vigor quando ela foi feita. Sob a releitura os dois
    # valem, e e exatamente o que a releitura foi decidida para fazer.
    casos.append(("a divisao SEPAROU na leitura escrita: I3a vale, escrito viola",
                  "I3a_nenhum_efeito_sob_epoca_revogada" not in v and escrito_viola,
                  "os dois sairam iguais na leitura escrita -- a divisao teria "
                  "sido decoracao"))

    # E O I3a PRECISA SER FALSIFICAVEL, senao e decoracao pelo outro lado.
    vm = roda(list(PROPRIEDADES), mutacao="conclui_sem_conferir_no_efeito")[0]
    casos.append(("I3a e FALSIFICAVEL: desguarnecer o efeito o quebra",
                  "I3a_nenhum_efeito_sob_epoca_revogada" in vm,
                  f"a mutacao nao quebrou o I3a; violou {sorted(vm)}"))

    # 1b. E A PROVA DE QUE O I3 NAO E PROPRIEDADE DO LOG: ele viola nos 32
    #     subconjuntos das cinco propriedades. Nenhuma combinacao o conserta.
    import itertools as _it
    sempre = all(_existe_estado(
        Modelo(instancias=("ativa", "sucessora"), epoca_max=2,
               props=frozenset(s)),
        lambda e, _s=s: not i3b_escrito(e, Modelo(
            instancias=("ativa", "sucessora"), epoca_max=2,
            props=frozenset(_s))))
                 for r in range(len(todas) + 1)
                 for s in _it.combinations(todas, r))
    casos.append(("o I3b ESCRITO viola nos 32 subconjuntos: o log NAO basta",
                  sempre,
                  "algum subconjunto do log conserta o I3b escrito — refaca a "
                  "conclusao da PRF-0202"))

    # 2. MUTACOES do protocolo: violacao CONHECIDA, o verificador tem de achar
    v, _, _ = roda(todas, mutacao="serve_sem_conferir_fencing")
    casos.append(("mutacao: servir sem conferir fencing e PEGA",
                  "I3b_nada_que_possa_tomar_efeito_sob_epoca_revogada" in v
                  or "I1_uma_instancia_por_epoca" in v,
                  f"nao pegou; violou {sorted(v)}"))

    v, _, _ = roda(todas, mutacao="testemunha_registra_sem_commit")
    casos.append(("mutacao: testemunha inventando transicao e PEGA",
                  "I4_testemunha_nao_inventa" in v, f"nao pegou; violou {sorted(v)}"))

    # 3. DESLIGAR propriedade do log tem de quebrar invariante -- com uma
    #    correcao que o proprio self-test imps: P5 MASCARA P2. Tirando so o P2,
    #    a monotonia NAO quebra, porque o P5 ja recusa epoca repetida. A
    #    necessidade do P2 e CONDICIONAL, e a expectativa ingenua estava errada.
    v, _, _ = roda([p for p in todas if p != "P2_monotonia"])
    casos.append(("sem P2 sozinho a monotonia NAO quebra: o P5 a mascara",
                  "I2_epoca_monotonica" not in v,
                  f"quebrou sozinho; a mascara do P5 sumiu: {sorted(v)}"))
    v, _, _ = roda([p for p in todas
                    if p not in ("P2_monotonia", "P5_lider_unico_por_epoca")])
    casos.append(("sem P2 E sem P5 a monotonia quebra",
                  "I2_epoca_monotonica" in v, f"nao quebrou; violou {sorted(v)}"))

    v, _, _ = roda([p for p in todas if p != "P5_lider_unico_por_epoca"])
    casos.append(("sem P5 duas instancias servem a mesma epoca",
                  "I1_uma_instancia_por_epoca" in v, f"nao quebrou; violou {sorted(v)}"))

    v, _, _ = roda([p for p in todas if p != "P4_durabilidade"])
    casos.append(("sem P4 o fencing quebra (entrada comprometida some)",
                  "I3b_nada_que_possa_tomar_efeito_sob_epoca_revogada" in v
                  or "I4_testemunha_nao_inventa" in v,
                  f"nao quebrou; violou {sorted(v)}"))

    ruins = 0
    # A RELEITURA PRECISA SER FALSIFICAVEL, senao ela so apaga o invariante.
    vm = roda(list(PROPRIEDADES), mutacao="conclui_sem_conferir_no_efeito")[0]
    casos.append(("o I3b RELIDO e FALSIFICAVEL: sem a cerca no efeito ele cai",
                  I3B_NOME in vm,
                  f"a mutacao nao quebrou o I3b relido; violou {sorted(vm)}"))

    # E NAO PODE SER O I3a COM OUTRO NOME: ha de existir estado em que o
    # relido viola e o I3a ainda vale -- o retardado esta ali e pode concluir,
    # e nada concluiu ainda.
    m_mut = Modelo(instancias=("ativa", "sucessora"), epoca_max=2,
                   props=frozenset(PROPRIEDADES),
                   mutacao="conclui_sem_conferir_no_efeito")
    casos.append(("o I3b relido NAO e o I3a: existe estado que viola um e nao o outro",
                  _existe_estado(m_mut,
                                 lambda e: not i3b(e, m_mut) and i3a(e, m_mut)),
                  "todo estado que viola o relido tambem viola o I3a -- entao o "
                  "relido e o I3a com outro nome, e um dos dois e redundante"))

    print("SELF-TEST — o verificador enxerga?")
    for nome, ok, erro in casos:
        print(f"  {'ok   ' if ok else 'FALHA'} {nome}")
        if not ok:
            print(f"         {erro}")
            ruins += 1
    print(f"\n  {len(casos) - ruins} de {len(casos)} passaram")
    if ruins:
        print("  NENHUM RESULTADO DESTE ARQUIVO VALE ENQUANTO ISTO FALHAR.")
    return 1 if ruins else 0


def matriz() -> int:
    import itertools as _it
    todas = list(PROPRIEDADES)
    I3A = "I3a_nenhum_efeito_sob_epoca_revogada"
    I3B = "I3b_nada_que_possa_tomar_efeito_sob_epoca_revogada"

    print("O MODELO: duas instancias (ativa, sucessora), epocas ate 2.")
    print("Seguranca conferida em CADA estado alcancavel; busca exaustiva.")
    print("I5 (progresso) e VIVACIDADE: NAO EXPRESSAVEL neste verificador.")
    print("")

    v, n, tr = roda(todas)
    marca = " — TRUNCADO" if tr else ""
    print(f"LOG COMPLETO (as cinco propriedades): {n} estados{marca}")
    print(f"  ainda viola: {sorted(v) if v else 'nada'}")
    print("")

    # --- o I3 sai da matriz, e a razao e MEDIDA e nao suposta
    sempre = all(I3B in roda(list(s))[0]
                 for r in range(len(todas) + 1)
                 for s in _it.combinations(todas, r))
    print("O I3 FOI DIVIDIDO EM 2026-10-20 (decisao do titular):")
    print("  I3a  nenhum ato sob epoca revogada TOMA EFEITO  -- a imposicao")
    print("       do C30-01 o satisfaz, e ele e falsificavel pela mutacao")
    print("       `conclui_sem_conferir_no_efeito`.")
    print("  I3b  RELIDO em 2026-10-20 (decisao do titular): nada que ainda")
    print("       POSSA TOMAR EFEITO fica sob epoca revogada. Com a cerca no")
    print("       efeito o retardado nao pode, e deixa de contar -- e por isso")
    print("       o protocolo passa a nao violar NADA sob esta leitura.")
    print("       NAO LEIA ISSO COMO PROTOCOLO CONSERTADO: nada no protocolo")
    print("       mudou com a releitura; mudou o que se EXIGE dele. A leitura")
    print("       ESCRITA -- `i3b_escrito`, proibindo a PRESENCA -- segue")
    print("       violando, e so o dreno a satisfaria. Ela fica no arquivo")
    print("       para que a diferenca continue medivel.")
    print()
    print("NENHUM DOS DOIS E PROPRIEDADE DO LOG, e por isso saem da matriz:")
    print(f"  viola nos 32 subconjuntos das cinco propriedades: {sempre}")
    print("  contraexemplo de 3 passos:")
    print("    promover(ativa,e1) -> servir(ativa,e1) -> promover(ativa,e2)")
    print("  uma requisicao ADMITIDA sob a epoca 1 segue em voo quando a epoca")
    print("  vira 2. Validar na ADMISSAO nao impede CONCLUSAO apos a revogacao.")
    print("  Mante-lo na matriz faria as cinco parecerem necessarias: artefato,")
    print("  nao achado.")
    print("")

    alvos = [k for k in INVARIANTES if k not in (I3A, I3B)]
    print("MATRIZ sobre os invariantes que o log PODE afetar (I1, I2, I4):")
    exig = {k: [] for k in alvos}
    for pp in todas:
        v, n, tr = roda([x for x in todas if x != pp])
        q = sorted(k for k in v if k not in (I3A, I3B))
        curtos = ", ".join(x.split("_")[0] for x in q) if q else "nada"
        print(f"  sem {pp:28s} {n:7d} estados; quebra: {curtos}")
        for inv in q:
            exig[inv].append(pp)

    print("")
    orfaos = [k for k in alvos if not exig[k]]
    print("  pares removidos, para achar necessidade CONDICIONAL.")
    print(f"  SO para os invariantes ainda sem exigencia isolada: "
          f"{', '.join(x.split('_')[0] for x in orfaos) if orfaos else 'nenhum'}")
    print("  E so os pares de propriedades que NAO incluem P4, porque sem P4 o")
    print("  espaco passa de 180 mil estados e o par chega ao teto -- reducao de")
    print("  escopo do INSTRUMENTO, declarada aqui e nao escondida.")
    pares = {}
    if orfaos:
        candidatos = [(a, b) for a, b in _it.combinations(todas, 2)
                      if "P4_durabilidade" not in (a, b)]
        for a, b in candidatos:
            if not [k for k in orfaos if k not in {x for ks in pares.values()
                                                   for x in ks}]:
                break
            v, _, _ = roda([x for x in todas if x not in (a, b)])
            q = sorted(k for k in v if k not in (I3A, I3B))
            novos = [k for k in q
                     if k in orfaos and a not in exig[k] and b not in exig[k]]
            if novos:
                pares[(a, b)] = novos
                ca, cb = a.split("_")[0], b.split("_")[0]
                cn = ", ".join(x.split("_")[0] for x in novos)
                print(f"    sem {ca} E sem {cb} -> quebra {cn}"
                      f"   (nenhuma das duas sozinha quebrava)")
        sem_resposta = [k for k in orfaos
                        if k not in {x for ks in pares.values() for x in ks}]
        if sem_resposta:
            print(f"    SEM EXPLICACAO nos pares varridos: "
                  f"{', '.join(x.split('_')[0] for x in sem_resposta)}")

    print("")
    print("A LISTA DE PROPRIEDADES EXIGIDAS DO LOG:")
    for inv in alvos:
        if exig[inv]:
            cs = ", ".join(x.split("_")[0] for x in exig[inv])
            print(f"  {inv:32s} exige {cs}")
        else:
            cond = [f"{a.split('_')[0]} ou {b.split('_')[0]}"
                    for (a, b), ks in pares.items() if inv in ks]
            alvo = " / ".join(cond) if cond else "nada neste modelo"
            suf = "   (CONDICIONAL)" if cond else ""
            print(f"  {inv:32s} exige {alvo}{suf}")

    nec = sorted({pp for ex in exig.values() for pp in ex})
    cond = sorted({x for par in pares for x in par})
    naos = [pp for pp in todas if pp not in nec and pp not in cond]
    f = lambda xs: ", ".join(x.split("_")[0] for x in xs) or "nenhuma"
    print("")
    print(f"  NECESSARIAS isoladamente : {f(nec)}")
    print(f"  NECESSARIAS em conjunto  : {f(cond)}")
    print(f"  NAO exigidas NESTE MODELO: {f(naos)}")
    if naos:
        print("    ISTO NAO AS TORNA DISPENSAVEIS. O modelo nao exercita conflito")
        print("    por indice nem leitura obsoleta que leve a violacao de")
        print("    seguranca, e essa e limitacao DO MODELO e nao propriedade do")
        print("    protocolo. Concluir 'nao precisa' daqui seria o FIT-019.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true",
                    help="roda as mutacoes; sem isto nenhum resultado vale")
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else matriz())
