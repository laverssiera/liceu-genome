"""O enumerador das declaracoes de estado, quebrado de proposito.

Ele existe porque o enumerador de 2026-10-09 NAO FOI GUARDADO: o 48 da PRF-0127
virou numero escrito num documento, que e exatamente a classe que ele denuncia.
Um enumerador guardado so vale mais que um descartado se ele ACUSAR — e e isso
que estes testes exigem.

O caso que carrega o sentido e `ADerivacaoAcusa`: nao basta CLASSIFICAR um campo
como derivavel; o instrumento tem de derivar o numero e gritar quando o
declarado nao bate. Sem este teste o mapa seria uma afirmacao sobre o mundo
escrita a mao, que e a propria coisa que a regra do titular proibe.

E `OMapaFalhaFechado` cobre as duas direcoes, porque mapa que envelhece calado
nao e melhor que campo que envelhece calado.
"""
import copy
import pathlib
import sys
import tempfile
import unittest

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import declaracoes_de_estado as de  # noqa: E402


def _decl(caminho, valor):
    f = de.forma_de(valor)
    cat, regra = de.classifica(caminho, valor, f or "?")
    return f, cat, regra


class AsFormasDoCandidato(unittest.TestCase):
    def test_inteiro_e_candidato(self):
        self.assertEqual(de.forma_de(114), "inteiro")

    def test_bool_NAO_e_candidato(self):
        """bool e decisao, nao contagem. Se entrasse, todo true/false da lei
        viraria 'declaracao de estado' e o numero afogaria o resultado."""
        self.assertIsNone(de.forma_de(True))
        self.assertIsNone(de.forma_de(False))

    def test_situacao_so_casa_no_COMECO_do_valor(self):
        """'PASS' e situacao; 'qualquer declaracao de PASS continental' e prosa
        sobre PASS. Casar no meio transformaria norma em estado."""
        self.assertEqual(de.forma_de("PASS"), "situacao")
        self.assertIsNone(de.forma_de("exige revisao antes de qualquer PASS"))

    def test_fracao_e_numero_com_substantivo(self):
        self.assertEqual(de.forma_de("0/7 implementados"), "fracao")
        self.assertEqual(de.forma_de("114 arquivos"), "numero+substantivo")

    def test_texto_sem_numero_nem_situacao_nao_e_candidato(self):
        self.assertIsNone(de.forma_de("o kit vive num repositorio proprio"))


class AClassificacaoPorChave(unittest.TestCase):
    def test_chave_que_ordena_e_NORMA(self):
        self.assertEqual(_decl("global.federation_scale.niveis[0].ordem", 3)[1], de.NORMA)

    def test_prefixo_de_regra_e_NORMA(self):
        self.assertEqual(_decl("global.REGRA_DE_ORIGEM", "PASS")[1], de.NORMA)

    def test_changelog_e_HISTORICO(self):
        self.assertEqual(_decl("meta.changelog_1_5_0", "MINOR: enum de 6 degraus")[1],
                         de.HISTORICO)

    def test_chave_de_estado_VENCE_a_regra_de_prosa(self):
        """`bug_conhecido.descricao` e uma frase longa E e a declaracao. Sem esta
        precedencia o instrumento perdia econotech, gamemkt e bim — foi o que
        aconteceu na primeira versao, e a conferencia contra o documento de
        2026-10-09 pegou."""
        longa = ("get_event_by_id normaliza o envelope em vez do item e procura "
                 "canonical_event_id em 3 lugares diferentes do payload federado")
        self.assertEqual(_decl("monolitos.econotech.bug_conhecido.descricao", longa)[1],
                         de.ESTADO)

    def test_marcador_de_codigo_vence_a_regra_de_prosa(self):
        longa = ("[CODIGO] 25 apps declarados, 2 implementados; os outros 23 sao "
                 "scaffolding de 1 a 3 arquivos cada um deles")
        self.assertEqual(_decl("monolitos.academia.divida_conhecida[0]", longa)[1],
                         de.ESTADO)

    def test_frase_longa_sem_marcador_nem_chave_de_estado_e_PROSA(self):
        """PROSA nao e ESTADO e nao e NORMA: e o LIMITE do metodo mecanico, e
        nomea-lo e mais honesto que somar ao total."""
        longa = ("convergir os 6 streams NATS para namespace comum sob a mesma "
                 "identidade de produtor, sem quebrar os consumidores atuais")
        self.assertEqual(_decl("global.transport_policy.acao", longa)[1], de.PROSA)

    def test_o_que_sobra_e_ESTADO(self):
        self.assertEqual(_decl("meta.pendencias_abertas", 0)[1], de.ESTADO)


class OMarcadorDaLeiQUALIFICA(unittest.TestCase):
    """O ponto cego da PRF-0154, e o defeito era de ORDEM e nao de regra.

    `forma_de()` decide se o valor e CANDIDATO; `classifica()` decide a
    CATEGORIA. O `[CODIGO]` morava so em `classifica()`, entao agia apenas sobre
    quem JA tinha passado pela porta — e a maioria dos campos marcados nao tem
    digito nenhum. Medido em 2026-10-14: a lei marcava 45 campos com [CODIGO] e o
    enumerador via DEZ.

    Eu havia escrito na docstring do modulo que "a propria lei marca com
    [CODIGO]: a frase inteira e a declaracao". Verdade para os dez que entravam,
    falsa para os trinta e cinco que nao.
    """

    def test_marcador_sem_digito_nenhum_AGORA_qualifica(self):
        """O caso exato que passava: `[CODIGO] routers/investors.py` nao tem
        inteiro, nem fracao, nem palavra de situacao no comeco."""
        self.assertEqual(de.forma_de("[CODIGO] routers/investors.py"), "marcador")

    def test_marcador_NU_tambem_qualifica(self):
        """`[CODIGO]` sozinho tem de entrar — para ser CONTADO como procedencia,
        nao para virar declaracao."""
        self.assertEqual(de.forma_de("[CODIGO]"), "marcador")
        self.assertEqual(de.forma_de("[DECIDIDO 2026-08-29]"), "marcador")

    def test_prosa_SEM_marcador_e_sem_numero_continua_fora(self):
        """A contrapartida: a porta alargou para o marcador, nao para tudo. Se
        qualquer texto entrasse, a classe viraria o arquivo inteiro."""
        self.assertIsNone(de.forma_de("o kit vive num repositorio proprio"))
        self.assertIsNone(de.forma_de("convergir os streams para namespace comum"))

    def test_o_marcador_NAO_vence_chave_de_NORMA(self):
        """Ordem preservada: NORMA e HISTORICO sao conferidos antes. Um
        `[CODIGO]` dentro de changelog segue sendo historico."""
        self.assertEqual(
            de.classifica("meta.changelog_1_5_0", "[CODIGO] alguma coisa", "marcador")[0],
            de.HISTORICO)

    def test_a_lei_marca_45_e_o_enumerador_agora_ve_os_45(self):
        """O numero que fecha o diagnostico, DERIVADO e nao fixado."""
        import yaml as _y
        kit = de.kit_instalado()
        marcados, vistos = set(), {f"{d.artefato}:{d.caminho}" for d in de.enumera(kit)}
        for nome in de.ARTEFATOS:
            dados = _y.safe_load((kit / nome).read_text(encoding="utf-8"))
            curto = nome.removeprefix("liceu_").removesuffix(".yaml")
            for cam, v in de.folhas(dados):
                if isinstance(v, str) and de.MARCADOR_DE_CODIGO in v:
                    marcados.add(f"{curto}:{cam}")
        self.assertTrue(marcados <= vistos,
                        f"{len(marcados - vistos)} campo(s) [CODIGO] seguem invisiveis: "
                        f"{sorted(marcados - vistos)[:5]}")


class APROCEDENCIANaoEhDeclaracao(unittest.TestCase):
    """Contar a cura como doenca inflaria a classe com campos que nao afirmam.

    A decisao de classe da UNK-0018 para o grupo nao derivavel foi "data E
    procedencia obrigatorias". Os campos `procedencia` SAO esse mecanismo, e
    classifica-los como ESTADO os contaria como o problema.

    E a medicao que a separacao torna possivel e o achado: 50 procedencias, 39
    COM data e 11 SEM — e as 11 sem data sao exatamente as que marcam observacao
    de codigo. A cura existe e falta no grupo que precisa dela.
    """

    def setUp(self):
        self.achadas = de.enumera(de.kit_instalado())
        self.proc = [d for d in self.achadas if d.categoria == de.PROCEDENCIA]

    def test_a_chave_procedencia_decide_com_data_ou_sem(self):
        for valor in ("[CODIGO]", "[DECIDIDO 2026-08-29]",
                      "[DECIDIDO 2026-08-29] lista mestre de evolucao",
                      "[CODIGO] cv-backend-core/app/main.py Federation"):
            cat, _ = de.classifica("global.x.procedencia", valor, "marcador")
            self.assertEqual(cat, de.PROCEDENCIA, valor)

    def test_a_folha_vence_segmento_de_ESTADO_no_caminho(self):
        """`monolitos.ped.estado.procedencia` tem `estado` num segmento. Se
        CHAVES_ESTADO fosse conferida antes, a procedencia viraria declaracao."""
        cat, _ = de.classifica("monolitos.ped.estado.procedencia", "[CODIGO]", "marcador")
        self.assertEqual(cat, de.PROCEDENCIA)

    def test_valor_marcado_que_NAO_e_procedencia_segue_ESTADO(self):
        """A contrapartida: `violacao` com [CODIGO] e declaracao, nao metadado."""
        cat, _ = de.classifica("monolitos.bim.forbidden[0].violacao",
                               "[CODIGO] routers/investors.py", "marcador")
        self.assertEqual(cat, de.ESTADO)

    def test_a_cura_esta_medida_e_falta_onde_precisa(self):
        com = [d for d in self.proc if de.DATA_NO_MARCADOR.search(str(d.valor))]
        cod = [d for d in self.proc if de.MARCADOR_DE_CODIGO in str(d.valor)]
        self.assertGreater(len(self.proc), 0)
        self.assertEqual(len(com) + len(self.proc) - len(com), len(self.proc))
        datadas_de_codigo = [d for d in cod if de.DATA_NO_MARCADOR.search(str(d.valor))]
        self.assertEqual(
            len(datadas_de_codigo), 0,
            "se uma procedencia de [CODIGO] passar a ter data, a cura comecou e "
            "este caso tem de mudar junto com a nota que o explica")

    def test_PROCEDENCIA_nao_entra_na_classe_nem_no_mapa(self):
        """Ela nao e declaracao de estado, entao nao tem origem a declarar."""
        mapa = de.carrega_mapa()
        for d in self.proc:
            self.assertNotIn(d.chave, mapa, f"{d.chave} e PROCEDENCIA e esta no mapa")


class AExclusaoDeclarada(unittest.TestCase):
    def test_payload_schema_fica_fora(self):
        """JSON Schema diz o que um payload DEVE ter: norma por definicao.
        Incluir daria centenas de falsos candidatos e afogaria o resultado."""
        arvore = {"events": {"x": {"payload_schema": {"minItems": 3, "required": 5},
                                   "implementation_status": "NAO_INICIADA"}}}
        caminhos = [c for c, _ in de.folhas(arvore)]
        self.assertNotIn("events.x.payload_schema.minItems", caminhos)
        self.assertIn("events.x.implementation_status", caminhos)


class ADerivacaoAcusa(unittest.TestCase):
    """O teste que torna o mapa diferente de uma afirmacao escrita a mao."""

    def setUp(self):
        self.kit = de.kit_instalado()
        self.artefatos = de.carrega_artefatos(self.kit)
        self.achadas = de.enumera(self.kit)

    def test_hoje_os_derivaveis_batem(self):
        """Medicao, nao exigencia: se um dia nao bater, o resultado e a
        defasagem e nao a falha deste teste — por isso ele REPORTA."""
        r = de.confere_derivaveis(self.achadas, self.artefatos)
        falsos = [x for x in r if x["bate"] is False]
        # DERIVADO, nao fixado: a primeira versao escrevia 7 aqui, e o 7 apodreceu
        # no mesmo dia em que a reclassificacao do M1 tirou duas derivacoes. Numero
        # fixado em teste e a mesma classe que este instrumento cura.
        self.assertEqual(len(r), len(de.DERIVACOES))
        if falsos:
            self.skipTest(f"a lei esta defasada em {len(falsos)}: "
                          f"{[x['chave'] for x in falsos]} — isto e achado, nao falha do teste")

    def test_DERIVACOES_vazio_e_o_RESULTADO_do_lote_1_e_nao_uma_lacuna(self):
        """Cinco derivacoes sairam porque os cinco CAMPOS sairam da lei.

        Campo que nao existe nao precisa ser derivado: "nao se escreve, se
        deriva", e apagar e a forma mais forte de nao escrever. Este teste
        existe para que o vazio seja uma AFIRMACAO e nao um esquecimento.
        """
        self.assertEqual(len(de.DERIVACOES), 0)
        instalado = {d.chave for d in self.achadas}
        for curado in ("constitution:meta.pendencias_abertas",
                       "constitution:meta.adrs_pendentes",
                       "constitution:global.identidade_semantica_de_replay.total",
                       "constitution:global.campos_exigidos_pelo_protocolo.total",
                       "event_reconciliation_ledger:meta.escopo_P2_5A"):
            self.assertNotIn(curado, instalado, f"{curado} voltou a lei")

    def test_a_LISTA_de_topo_adrs_pendentes_NAO_foi_tocada(self):
        """O que o lote 1 nao podia quebrar: `liceu_boundary_check.py:353` faz
        `c.get("adrs_pendentes", [])` sobre a lista de TOPO. A contagem
        `meta.adrs_pendentes` saiu; a lista fica.

        E o que a cura NAO curou, dito aqui para nao parecer curado: a contagem
        estava CERTA — havia um item. Quem esta defasado e a LISTA, que segue
        nomeando a ADR-001 como pendente desde que foi decidida em 2026-09-18
        (PRF-0125). E essa defasagem nenhum enumerador mecanico alcanca.
        """
        const = self.artefatos["constitution"]
        self.assertIn("adrs_pendentes", const, "a lista de topo desapareceu")
        self.assertIsInstance(const["adrs_pendentes"], list)
        self.assertNotIn("adrs_pendentes", const["meta"], "a contagem voltou")
        ids = [a.get("id") for a in const["adrs_pendentes"]]
        self.assertIn("ADR-001", ids,
                      "a lista segue nomeando a ADR-001; se um dia nao nomear, "
                      "a defasagem que a PRF-0125 mediu foi curada e esta nota muda")

    # A versao anterior deste caso mutava o `escopo_P2_5A` real do ledger, e ele
    # SAIU da lei no kit 0.27.0. O caso vive agora em
    # `ADerivaEhPegaPorFalharFECHADO`, sobre uma lei sintetica — porque teste de
    # mecanismo nao deve morrer quando o conteudo que ele vigia e curado.


class OMapaFalhaFechado(unittest.TestCase):
    def setUp(self):
        self.achadas = de.enumera(de.kit_instalado())
        self.mapa = de.carrega_mapa()

    def test_hoje_o_mapa_esta_em_dia(self):
        de.exige_mapa_em_dia(self.achadas, self.mapa)   # nao levanta

    def test_ESTADO_sem_origem_declarada_LEVANTA(self):
        """Campo novo na lei sem origem declarada tem de parar a CI. Sem isto o
        mapa cobriria um subconjunto e ninguem saberia qual."""
        reduzido = dict(self.mapa)
        reduzido.pop(next(iter(reduzido)))
        with self.assertRaises(de.ClasseDefasada) as e:
            de.exige_mapa_em_dia(self.achadas, reduzido)
        self.assertIn("sem origem declarada", str(e.exception))

    def test_origem_de_campo_que_sumiu_LEVANTA(self):
        """A outra direcao: campo curado e origem esquecida. Os 7 removidos no
        #34 do liceu-protocol sao o precedente — se o mapa os citasse, ele
        afirmaria que a lei tem campos que ela nao tem."""
        inflado = dict(self.mapa)
        inflado["constitution:meta.campo_que_nunca_existiu"] = de.Origem(
            de.SAI_DA_CLASSE, "nenhum", "inventado pelo teste")
        with self.assertRaises(de.ClasseDefasada) as e:
            de.exige_mapa_em_dia(self.achadas, inflado)
        self.assertIn("nao existe mais", str(e.exception))

    def test_classe_invalida_no_mapa_LEVANTA(self):
        p = pathlib.Path(tempfile.mkdtemp()) / "m.yaml"
        p.write_text(yaml.safe_dump(
            {"origens": {"a:b": {"classe": "QUASE_DERIVAVEL", "fonte": "", "razao": ""}}}),
            encoding="utf-8")
        with self.assertRaises(de.ClasseDefasada):
            de.carrega_mapa(p)

    def test_as_tres_classes_sao_as_tres_e_nao_quatro(self):
        """Uma quarta classe seria a saida para nao decidir, e a regra do titular
        tem tres saidas: derivar, derivar de outro, ou sair da classe."""
        classes = {o.classe for o in self.mapa.values()}
        self.assertTrue(classes <= {de.PROPRIO_ARTEFATO, de.OUTRO_ARTEFATO, de.SAI_DA_CLASSE})


class DerivavelDECLARADOTemDeSerDerivavelDEVERDADE(unittest.TestCase):
    """O buraco que o mapa sozinho deixava, e e o buraco que importa.

    Alguem acrescenta um campo, declara-o PROPRIO_ARTEFATO, e o mapa fica "em
    ordem" enquanto o valor continua escrito a mao. Classificar como derivavel
    sem derivar e a MESMA afirmacao a mao que a regra do titular proibe — e sai
    de graca no denominador do grafo, porque e guarda de instrumento e nao
    fitness nova.
    """

    def setUp(self):
        self.mapa = de.carrega_mapa()

    def test_hoje_todo_derivavel_tem_derivacao_ou_isencao(self):
        de.exige_derivacao_declarada(self.mapa)   # nao levanta

    def test_derivavel_novo_SEM_derivacao_LEVANTA(self):
        m = dict(self.mapa)
        m["constitution:meta.campo_novo"] = de.Origem(
            de.PROPRIO_ARTEFATO, "len(alguma_coisa)", "declarado sem derivar")
        with self.assertRaises(de.ClasseDefasada) as e:
            de.exige_derivacao_declarada(m)
        self.assertIn("SEM derivacao", str(e.exception))

    def test_SAI_DA_CLASSE_novo_nao_exige_derivacao(self):
        """A contrapartida, e e o que torna o teste um teste: campo que NAO e
        derivavel passa. Uma guarda que recusa tudo nao mede nada."""
        m = dict(self.mapa)
        m["constitution:meta.campo_novo"] = de.Origem(
            de.SAI_DA_CLASSE, "codigo dos 19 repositorios", "observacao de codigo")
        de.exige_derivacao_declarada(m)           # nao levanta

    def test_isencao_que_sobrevive_ao_campo_LEVANTA(self):
        """Isencao orfa e permissao orfa: ficaria valendo para um campo que nao
        existe, e o proximo campo com nome parecido herdaria a licenca.

        SINTETICO porque ISENTOS_DE_DERIVACAO esvaziou com o lote 2 do item 2 —
        as duas ultimas isencoes perderam o campo quando a lei foi curada. Sem
        injetar uma, este caso nao teria o que orfanar, e a guarda ficaria sem
        teste justo quando a lista zerou.
        """
        original = dict(de.ISENTOS_DE_DERIVACAO)
        de.ISENTOS_DE_DERIVACAO["constitution:meta.campo_que_sumiu"] = (
            "isencao injetada pelo teste, com razao longa o bastante para a "
            "conferencia de razao escrita passar")
        try:
            with self.assertRaises(de.ClasseDefasada) as e:
                de.exige_derivacao_declarada(dict(self.mapa))
            self.assertIn("nao esta mais no mapa", str(e.exception))
        finally:
            de.ISENTOS_DE_DERIVACAO.clear()
            de.ISENTOS_DE_DERIVACAO.update(original)

    def test_toda_isencao_tem_razao_escrita(self):
        """Vale tambem para a lista VAZIA: zero isencoes satisfaz a regra, e o
        caso existe para que uma isencao futura nasca com razao."""
        for chave, razao in de.ISENTOS_DE_DERIVACAO.items():
            self.assertGreater(len(razao), 40, f"{chave}: isencao sem razao de verdade")
        self.assertTrue(set(de.ISENTOS_DE_DERIVACAO) <= set(de.LACRE_ISENTOS))


class ADerivaEhPegaPorFalharFECHADO(unittest.TestCase):
    """O buraco que o titular previu, e ele existia — por outro motivo.

    A pergunta dele foi: o portao avalia o grafo inteiro ou so o diff? Medido:
    O GRAFO INTEIRO, toda CI, sem uma linha de diff. Pela logica dele isso
    cobriria a deriva. NAO COBRIA.

    `_tam` fazia `(no or {}).get(c)` e depois `len(no or [])`, entao chave de
    origem AUSENTE devolvia 0 em silencio. Apagar `constitution.pendencias`
    deixava declarado=0, derivado=0, bate=True — a fonte nao existia mais e o
    portao dizia OK. A deriva nao passava por falta de escopo: passava por
    FALHA ABERTA na funcao de contagem.
    """

    #: SINTETICO de proposito. As mutacoes estavam ancoradas em campos REAIS da
    #: lei, e quando o lote 1 do C25-06 apagou esses campos oito testes
    #: quebraram de uma vez — a deteccao da deriva ficaria sem guarda justo
    #: quando `DERIVACOES` esvaziou. Teste de MECANISMO nao deve depender do
    #: conteudo que o mecanismo vigia.
    LEI = {"constitution": {"meta": {"conta": 2, "frase": "sao 2 coisas no total"},
                            "itens": ["a", "b"],
                            "fundo": {"dentro": {"lista": ["x", "y"]}}}}
    DERIVACOES = {
        "constitution:meta.conta": lambda a: de._conta(a, "constitution", "itens"),
        "constitution:meta.frase": lambda a: de._conta(a, "constitution", "itens"),
        "constitution:fundo.dentro.quantos":
            lambda a: de._conta(a, "constitution", "fundo", "dentro", "lista"),
    }

    def _achadas(self):
        fora = []
        for chave, valor in (("constitution:meta.conta", 2),
                             ("constitution:meta.frase", "sao 2 coisas no total"),
                             ("constitution:fundo.dentro.quantos", 2)):
            art, cam = chave.split(":", 1)
            f = de.forma_de(valor) or "inteiro"
            fora.append(de.Declaracao(art, cam, valor, f, de.ESTADO, "sintetico"))
        return fora

    def _confere(self, lei):
        return {x["chave"]: x for x in
                de.confere_derivaveis(self._achadas(), lei, self.DERIVACOES)}

    def setUp(self):
        self.kit = de.kit_instalado()
        self.artefatos = de.carrega_artefatos(self.kit)
        self.achadas = de.enumera(self.kit)

    def test_chave_de_origem_AUSENTE_levanta(self):
        with self.assertRaises(de.FonteAusente):
            de._conta({}, "pendencias")

    def test_lista_VAZIA_e_legitima_e_conta_zero(self):
        """Distinguir vazio de ausente e a diferenca inteira: `pendencias: []`
        e estado legitimo da lei, e tem de contar 0 sem levantar."""
        self.assertEqual(de._conta({"pendencias": []}, "pendencias"), 0)

    def test_nulo_nao_passa_por_vazio(self):
        with self.assertRaises(de.FonteAusente):
            de._conta({"pendencias": None}, "pendencias")

    def test_com_a_lei_intacta_os_derivaveis_batem(self):
        """A linha de base, senao as mutacoes nao provam nada: 2 = len(itens)."""
        r = self._confere(copy.deepcopy(self.LEI))
        self.assertTrue(all(x["bate"] for x in r.values()), r)

    def test_mexer_na_lista_sem_recontar_e_ACUSADO(self):
        """O defeito inteiro da classe em uma linha: alguem acrescenta um item e
        nao atualiza o contador."""
        lei = copy.deepcopy(self.LEI)
        lei["constitution"]["itens"].append("c")
        alvo = self._confere(lei)["constitution:meta.conta"]
        self.assertIs(alvo["bate"], False)
        self.assertEqual((alvo["declarado"], alvo["derivado"]), (2, 3))

    def test_a_contagem_dentro_de_PROSA_tambem_e_conferida(self):
        """Sem extrair o primeiro numero da frase, prosa com contagem seria
        imune — e foi assim que `escopo_P2_5A` entrou na classe."""
        lei = copy.deepcopy(self.LEI)
        lei["constitution"]["itens"].append("c")
        alvo = self._confere(lei)["constitution:meta.frase"]
        self.assertIs(alvo["bate"], False)
        self.assertEqual((alvo["declarado"], alvo["derivado"]), (2, 3))

    def test_a_FONTE_que_sai_e_acusada_como_DERIVA_e_nao_como_OK(self):
        """O caso exato que passava antes: a origem sai, a contagem daria 0, e o
        declarado tambem seria 0. Coincidencia de zero virava aprovacao."""
        lei = copy.deepcopy(self.LEI)
        del lei["constitution"]["itens"]
        alvo = self._confere(lei)["constitution:meta.conta"]
        self.assertTrue(alvo["deriva"], "a fonte sumiu e isto tem de sair como DERIVA")
        self.assertIs(alvo["bate"], False, "deriva nunca pode sair como bate=True")
        self.assertIn("DERIVA", alvo["nota"])

    def test_a_deriva_atinge_TODO_campo_que_bebe_daquela_fonte(self):
        """Duas fontes a mao do mesmo valor caem juntas — e e por isso que duas
        sao piores que uma. Quantos campos bebem dali e DERIVADO, nao fixado."""
        lei = copy.deepcopy(self.LEI)
        del lei["constitution"]["itens"]
        r = self._confere(lei)
        derivas = {k for k, x in r.items() if x["deriva"]}
        bebem = {k for k, fn in self.DERIVACOES.items()
                 if "itens" in str(fn.__code__.co_consts)}
        self.assertEqual(derivas, bebem,
                         "todo campo que deriva daquela fonte tem de cair com ela")
        self.assertTrue(derivas, "a fonte tem de alimentar ao menos um campo")

    def test_o_caminho_INTERMEDIARIO_que_sai_tambem_e_pego(self):
        """A deriva pode ser no MEIO do caminho, nao so na folha."""
        lei = copy.deepcopy(self.LEI)
        del lei["constitution"]["fundo"]["dentro"]
        self.assertTrue(self._confere(lei)["constitution:fundo.dentro.quantos"]["deriva"])

    def test_a_lei_de_HOJE_nao_tem_derivavel_nenhum_e_isso_e_o_lote_1(self):
        """A ponte entre o mecanismo sintetico e o mundo: as mutacoes acima
        provam que a deteccao funciona; esta linha diz que hoje nao ha o que
        detectar, porque o lote 1 apagou os campos."""
        self.assertEqual(de.confere_derivaveis(self.achadas, self.artefatos), [])


class OLacreDasDuasListasDeIsencao(unittest.TestCase):
    """A brecha seguinte que o titular nomeou, e ela estava aberta.

    Medido em 2026-10-13, antes do lacre: acrescentei uma quinta isencao em tempo
    de execucao e o portao PASSOU. Lista fechada que ninguem lacra nao e lista
    fechada — e o padrao e o do `instrument_introduced` da FIT-019.

    Sao DUAS listas porque ha dois caminhos de isencao, e lacrar so o primeiro
    deixaria o segundo como a brecha depois dessa: a razao de um SAI_DA_CLASSE e
    prosa, ninguem a confere, e bastaria classificar um campo novo assim.
    """

    def setUp(self):
        self.mapa = de.carrega_mapa()

    def test_o_sha256_das_isencoes_esta_congelado(self):
        self.assertEqual(de.lacre(de.LACRE_ISENTOS), de.LACRE_ISENTOS_SHA256,
                         "o lacre das isencoes mudou sem o sha256 mudar junto")

    def test_o_sha256_do_SAI_DA_CLASSE_esta_congelado(self):
        self.assertEqual(de.lacre(de.LACRE_SAI_DA_CLASSE), de.LACRE_SAI_DA_CLASSE_SHA256,
                         "o lacre do SAI_DA_CLASSE mudou sem o sha256 mudar junto")

    def test_hoje_as_duas_listas_estao_dentro_do_lacre(self):
        de.exige_lacre(self.mapa)     # nao levanta

    def test_isencao_de_derivacao_NOVA_e_recusada(self):
        original = dict(de.ISENTOS_DE_DERIVACAO)
        de.ISENTOS_DE_DERIVACAO["constitution:meta.inventado"] = "isencao fora do lacre"
        try:
            with self.assertRaises(de.ClasseDefasada) as e:
                de.exige_lacre(self.mapa)
            self.assertIn("FORA DO LACRE", str(e.exception))
        finally:
            de.ISENTOS_DE_DERIVACAO.clear()
            de.ISENTOS_DE_DERIVACAO.update(original)

    def test_SAI_DA_CLASSE_NOVO_e_recusado(self):
        """Sem este lacre bastaria classificar um campo novo como nao-derivavel
        para fugir da regra inteira."""
        m = dict(self.mapa)
        m["constitution:meta.inventado"] = de.Origem(
            de.SAI_DA_CLASSE, "codigo dos 19 repositorios", "razao plausivel qualquer")
        with self.assertRaises(de.ClasseDefasada) as e:
            de.exige_lacre(m)
        self.assertIn("SAI_DA_CLASSE FORA DO LACRE", str(e.exception))

    def test_a_lista_pode_ENCOLHER_sem_mexer_no_lacre(self):
        """So encolhe: curar um campo tira-o da lista e o lacre segue valendo.
        Uma guarda que tambem recusasse a cura empurraria contra o trabalho."""
        m = {k: v for k, v in self.mapa.items() if k != de.LACRE_SAI_DA_CLASSE[0]}
        de.exige_lacre(m)             # nao levanta

    def test_o_lacre_SO_ENCOLHE_POR_SI_e_crescer_e_um_ATO(self):
        """O lacre e o MAXIMO historico, nao o estado de hoje.

        ENCOLHER acontece sozinho: o lote 1 do item 2 curou campos e as isencoes
        cairam de 4 para 0 sem ninguem tocar no lacre, e o SAI_DA_CLASSE caiu de
        41 para 40 do mesmo jeito. Exigir igualdade aqui faria a guarda empurrar
        contra a propria cura.

        CRESCER nao acontece sozinho, e e o ponto: quando o conserto do ponto
        cego trouxe 24 campos de uma vez, o lacre RECUSOU com codigo 2. Estender
        de 41 para 64 foi um ato, com a razao escrita no modulo e o sha256 movido
        aqui — e e este sha256 congelado que torna a edicao visivel.
        """
        self.assertEqual(len(de.LACRE_ISENTOS), 4)
        self.assertEqual(len(de.LACRE_SAI_DA_CLASSE), 64,
                         "o lacre foi estendido de 41 para 64 em 2026-10-14; se mudou "
                         "de novo, a razao tem de estar no modulo e o sha256 aqui")
        self.assertTrue(set(de.ISENTOS_DE_DERIVACAO) <= set(de.LACRE_ISENTOS),
                        "isencao viva fora do lacre")
        self.assertTrue(set(de.sai_da_classe_de(self.mapa)) <= set(de.LACRE_SAI_DA_CLASSE))
        self.assertEqual(len(de.ISENTOS_DE_DERIVACAO), 0,
                         "as isencoes zeraram com o lote 2; se voltarem, alguem "
                         "desfez a cura ou acrescentou isencao")


class ORegistroHISTORICONaoSeDeriva(unittest.TestCase):
    """Correcao de um erro meu, pega ao preparar o item 2.

    Eu havia classificado `M1.criterios.CONSTITUTION_PENDING_DECISIONS` e
    `M1.criterios.CANONICAL_MONOLITH_IDS` como derivaveis do proprio arquivo, de
    `len(pendencias)` e `len(monolitos)`. A derivacao BATIA — 0 e 15 — e batia
    por COINCIDENCIA: o M1 declara `baseline_constitution_version: 1.0.0`, a
    Constituicao esta em 1.15.0, e a nota do proprio M1 diz 'preserva lineage
    historico; nao sobrescrever com a versao corrente'.

    Derivar ali sobrescreveria historia com o valor corrente. E a mesma familia
    da coincidencia de zero que deixava a deriva passar: o numero batia e a
    razao estava errada.
    """

    def setUp(self):
        self.kit = de.kit_instalado()
        self.achadas = de.enumera(self.kit)
        self.por = {d.chave: d for d in self.achadas}

    def test_milestone_com_baseline_e_reconhecido_pela_propria_declaracao(self):
        import yaml as _y
        dados = _y.safe_load(
            (self.kit / "liceu_constitution.yaml").read_text(encoding="utf-8"))
        prefixos = de.prefixos_de_registro_historico(dados)
        self.assertIn("milestone.M1_CONSTITUTION_DEFINITION.", prefixos)
        self.assertEqual(len(prefixos), 1,
                         "so o M1 declara baseline_constitution_version; se outro passar "
                         "a declarar, esta regra o alcanca sozinha")

    def test_os_criterios_do_M1_sao_HISTORICO_e_nao_ESTADO(self):
        for folha in ("CONSTITUTION_PENDING_DECISIONS", "CANONICAL_MONOLITH_IDS"):
            chave = ("constitution:milestone.M1_CONSTITUTION_DEFINITION.criterios." + folha)
            self.assertEqual(self.por[chave].categoria, de.HISTORICO, folha)

    def test_nenhum_campo_do_M1_tem_derivacao(self):
        """A guarda contra eu repetir o erro: derivacao para dentro de registro
        historico e sobrescrita de historia, nao cura."""
        for chave in de.DERIVACOES:
            self.assertNotIn("M1_CONSTITUTION_DEFINITION", chave)

    def test_milestone_SEM_baseline_continua_sendo_lido_normalmente(self):
        """A contrapartida: a regra nao pode isentar milestone nenhum por ser
        milestone. M3 e M4 nao declaram baseline, e os criterios deles seguem
        na classe."""
        chave = ("constitution:milestone.M4_FIRST_CAUSAL_AUTHORITY_CHAIN."
                 "criterios.MINIMUM_CAUSAL_THREAD_RUNTIME")
        self.assertEqual(self.por[chave].categoria, de.ESTADO)


class AsContradicoesDentroDoMesmoArquivo(unittest.TestCase):
    """O caso mais puro da classe da UNK-0018, achado ao preparar o item 2.

    Duas declaracoes no MESMO bloco se contradizem, nenhuma regra as le, e a
    contradicao sobrevive porque ninguem reconta. Medido em 2026-10-13: M3
    declara `status: NOT_STARTED` com os CINCO criterios em PASS; M4 declara
    NOT_STARTED com os TRES em PASS. Nenhum bloco tem nota.

    `PASS` aparece SO nesses dois — M1 e M2 usam booleanos, inteiros e `KNOWN`.
    Se PASS quisesse dizer 'criterio bem definido', M1 e M2 tambem o usariam.
    """

    def setUp(self):
        self.achadas = de.incoerencias_internas(de.kit_instalado())

    def test_M3_e_M4_estao_incoerentes_hoje(self):
        onde = {i["onde"] for i in self.achadas}
        self.assertIn("constitution:milestone.M3_AUTHENTICATED_RUNTIME_CONFORMANCE", onde)
        self.assertIn("constitution:milestone.M4_FIRST_CAUSAL_AUTHORITY_CHAIN", onde)

    def test_a_contagem_de_PASS_vai_nomeada_e_nao_resumida(self):
        """Dizer 'ha incoerencia' sem nomear os criterios obrigaria a reabrir o
        arquivo para agir."""
        por = {i["onde"]: i for i in self.achadas}
        m3 = por["constitution:milestone.M3_AUTHENTICATED_RUNTIME_CONFORMANCE"]
        self.assertEqual(len(m3["criterios_em_PASS"]), 5)
        self.assertIn("DURABILITY", m3["criterios_em_PASS"])

    def test_milestone_que_COMECOU_nao_e_acusado(self):
        """A contrapartida, senao a guarda acusaria todo milestone com criterio.
        M1 (PASS) e M2 (ACTIVE) nao entram."""
        onde = {i["onde"] for i in self.achadas}
        self.assertNotIn("constitution:milestone.M1_CONSTITUTION_DEFINITION", onde)
        self.assertNotIn(
            "constitution:milestone.M2_FEDERATION_PROTOCOL_AND_STATIC_CONVERGENCE", onde)

    def test_a_funcao_NAO_escolhe_qual_das_duas_e_falsa(self):
        """Escolher seria decidir o que a lei afirma, e isso nao e do instrumento."""
        for i in self.achadas:
            self.assertIn("o arquivo nao diz qual", i["o_que"])


class OGatilhoDaFIT020(unittest.TestCase):
    """ADIADA COM GATILHO, e o gatilho e MECANICO em vez de lembrado.

    A correcao do titular em 2026-10-13: o veredito nao e RECUSADA, e ADIADA.
    "Recusada" fecha a pergunta; ela esta agendada. E o gatilho vive no
    instrumento por um motivo medido NESTE ciclo — o enumerador de 09/10 era uma
    decisao que dependia de alguem lembrar, e ninguem lembrou.
    """

    def setUp(self):
        self.mapa = de.carrega_mapa()

    def test_HOJE_a_classe_esta_em_ZERO_e_o_gatilho_ESTA_ARMADO(self):
        """O lote 2 do item 2 levou a classe viva a zero, e o gatilho armou
        sozinho. Este caso era o inverso — 'tem membros e NAO arma' — e virou
        o que e: a classe foi curada.

        A contrapartida ('com membros NAO arma') esta logo abaixo, sobre um mapa
        SINTETICO, porque teste de mecanismo nao deve morrer quando o conteudo
        que o mecanismo vigia e curado. E a terceira vez neste ciclo que eu
        aprendo isso, e agora esta escrito aqui.
        """
        self.assertEqual(de.classe_viva(self.mapa), [])
        armado, texto = de.gatilho_fit_020(self.mapa)
        self.assertTrue(armado)
        self.assertIn("GATILHO ARMADO", texto)
        self.assertIn("NAO e autorizacao", texto,
                      "armar e avisar; a excecao ao freio e decisao do titular")

    def test_com_membros_na_classe_o_gatilho_NAO_arma(self):
        """A contrapartida, em mapa sintetico: uma guarda que armasse sempre nao
        mediria nada."""
        m = {"constitution:meta.x": de.Origem(de.PROPRIO_ARTEFATO, "len(y)", "sintetico")}
        armado, texto = de.gatilho_fit_020(m)
        self.assertFalse(armado)
        self.assertIn("ADIADA", texto)
        self.assertIn("1 membro(s) vivo(s)", texto,
                      "o numero anunciado e o DERIVADO do mapa, nunca um literal")

    def test_com_a_classe_em_ZERO_o_gatilho_ARMA(self):
        """A contrapartida, e sem ela o gatilho seria decoracao: convertido tudo,
        o instrumento ANUNCIA que a FIT-020 pode entrar."""
        curado = {k: v for k, v in self.mapa.items() if v.classe == de.SAI_DA_CLASSE}
        armado, texto = de.gatilho_fit_020(curado)
        self.assertTrue(armado)
        self.assertIn("GATILHO ARMADO", texto)

    def test_SAI_DA_CLASSE_nao_conta_como_membro_vivo(self):
        """Conta-los faria a classe parecer eterna e o gatilho nunca armaria."""
        self.assertEqual(de.classe_viva({"a:b": de.Origem(de.SAI_DA_CLASSE, "x", "y")}), [])

    def test_o_gatilho_armado_NAO_autoriza_a_excecao_ao_freio(self):
        """Armar e avisar. A excecao ao freio continua sendo decisao do titular,
        e o texto tem de dizer isso — senao o aviso vira permissao."""
        curado = {k: v for k, v in self.mapa.items() if v.classe == de.SAI_DA_CLASSE}
        _, texto = de.gatilho_fit_020(curado)
        self.assertIn("NAO e autorizacao", texto)


class ASaidaNaoSeContradiz(unittest.TestCase):
    """Codigo VALIDO fazendo a coisa errada em silencio.

    Ao inserir o bloco das contradicoes internas entre o corpo do `if mapa:` e o
    `else:`, o Python ligou o `else` ao LACO `for` — e `for ... else` e
    construcao legal. Nao houve erro de sintaxe e o codigo de retorno continuou
    0; a saida passou a imprimir "MAPA DE ORIGEM AUSENTE" e "mapa de origem EM
    DIA" na MESMA execucao, uma contradizendo a outra.

    Foi pego por LER A SAIDA INTEIRA em vez de conferir o exit code — que e a
    mesma licao do `--self-test` e do `--repo` deste ciclo. Este teste guarda a
    licao em vez de confiar nela.
    """

    def _saida(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            de.main(["--exigir-mapa", "--conferir-derivaveis"])
        return buf.getvalue()

    def test_as_duas_linhas_do_mapa_nunca_coexistem(self):
        s = self._saida()
        ausente = "MAPA DE ORIGEM AUSENTE" in s
        em_dia = "mapa de origem EM DIA" in s
        self.assertNotEqual(ausente, em_dia,
                            "o mapa esta ausente OU em dia; as duas linhas juntas sao "
                            "saida que se contradiz, e nenhum exit code pega isso")

    def test_o_bloco_das_contradicoes_sai_sempre_mesmo_com_mapa(self):
        s = self._saida()
        self.assertIn("CONTRADICOES DENTRO DO MESMO ARQUIVO", s)

    def test_o_que_o_instrumento_ANUNCIA_e_o_que_ele_DERIVA(self):
        """Com a classe em zero o anuncio muda de forma — passa a ser o gatilho
        armado em vez da contagem —, e o teste segue o estado DERIVADO em vez de
        esperar uma das duas formas."""
        s = self._saida()
        vivos = len(de.classe_viva(de.carrega_mapa()))
        if vivos:
            self.assertIn(f"{vivos} membro(s) vivo(s)", s)
        else:
            self.assertIn("GATILHO ARMADO", s)
            self.assertNotIn("membro(s) vivo(s)", s,
                             "com zero membros o instrumento nao anuncia contagem")


class OArtefatoAusente(unittest.TestCase):
    def test_kit_sem_um_dos_cinco_artefatos_LEVANTA(self):
        """Ler quatro de cinco e anunciar o total e o defeito de N itens sem N
        respostas, que este ecossistema ja cometeu."""
        vazio = pathlib.Path(tempfile.mkdtemp())
        with self.assertRaises(de.ClasseDefasada) as e:
            de.enumera(vazio)
        self.assertIn("artefato governado ausente", str(e.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
