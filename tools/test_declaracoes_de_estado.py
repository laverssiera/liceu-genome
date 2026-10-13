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
        self.assertEqual(len(r), 7, "o conjunto de derivacoes mudou de tamanho")
        if falsos:
            self.skipTest(f"a lei esta defasada em {len(falsos)}: "
                          f"{[x['chave'] for x in falsos]} — isto e achado, nao falha do teste")

    def test_mexer_na_lista_sem_recontar_e_ACUSADO(self):
        """O defeito inteiro da classe em uma linha: alguem acrescenta uma
        pendencia e nao atualiza o contador."""
        mutado = copy.deepcopy(self.artefatos)
        mutado["constitution"]["pendencias"] = ["uma pendencia nova que ninguem contou"]
        r = {x["chave"]: x for x in de.confere_derivaveis(self.achadas, mutado)}
        alvo = r["constitution:meta.pendencias_abertas"]
        self.assertIs(alvo["bate"], False)
        self.assertEqual((alvo["declarado"], alvo["derivado"]), (0, 1))

    def test_a_SEGUNDA_FONTE_tambem_e_acusada(self):
        """`M1.criterios.CONSTITUTION_PENDING_DECISIONS` carrega o MESMO numero
        que `meta.pendencias_abertas`. Duas fontes a mao divergem — e a objecao
        e a do ADR-002, que recusou A+B por isso."""
        mutado = copy.deepcopy(self.artefatos)
        mutado["constitution"]["pendencias"] = ["x", "y"]
        r = {x["chave"]: x for x in de.confere_derivaveis(self.achadas, mutado)}
        a = r["constitution:meta.pendencias_abertas"]
        b = r["constitution:milestone.M1_CONSTITUTION_DEFINITION.criterios."
              "CONSTITUTION_PENDING_DECISIONS"]
        self.assertIs(a["bate"], False)
        self.assertIs(b["bate"], False)
        self.assertEqual(a["derivado"], b["derivado"],
                         "as duas fontes derivam do mesmo lugar, logo so divergem a mao")

    def test_remover_um_monolito_sem_recontar_e_ACUSADO(self):
        mutado = copy.deepcopy(self.artefatos)
        mutado["constitution"]["monolitos"].pop("ped")
        r = {x["chave"]: x for x in de.confere_derivaveis(self.achadas, mutado)}
        alvo = r["constitution:milestone.M1_CONSTITUTION_DEFINITION.criterios."
                 "CANONICAL_MONOLITH_IDS"]
        self.assertIs(alvo["bate"], False)
        self.assertEqual((alvo["declarado"], alvo["derivado"]), (15, 14))

    def test_a_contagem_dentro_de_PROSA_tambem_e_conferida(self):
        """`escopo_P2_5A` diz '(5 eventos)' no meio de uma frase. O instrumento
        extrai o primeiro numero e compara — senao a frase seria imune."""
        mutado = copy.deepcopy(self.artefatos)
        mutado["event_reconciliation_ledger"]["P2_5A_minimum_causal_thread"].popitem()
        r = {x["chave"]: x for x in de.confere_derivaveis(self.achadas, mutado)}
        alvo = r["event_reconciliation_ledger:meta.escopo_P2_5A"]
        self.assertIs(alvo["bate"], False)
        self.assertEqual((alvo["declarado"], alvo["derivado"]), (5, 4))


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
        existe, e o proximo campo com nome parecido herdaria a licenca."""
        m = {k: v for k, v in self.mapa.items() if k not in de.ISENTOS_DE_DERIVACAO}
        with self.assertRaises(de.ClasseDefasada) as e:
            de.exige_derivacao_declarada(m)
        self.assertIn("nao esta mais no mapa", str(e.exception))

    def test_toda_isencao_tem_razao_escrita(self):
        for chave, razao in de.ISENTOS_DE_DERIVACAO.items():
            self.assertGreater(len(razao), 40, f"{chave}: isencao sem razao de verdade")


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

    def test_a_FONTE_que_sai_e_acusada_como_DERIVA_e_nao_como_OK(self):
        """O caso exato que passava antes: a origem sai, a contagem da 0, e o
        declarado tambem e 0. Coincidencia de zero virava aprovacao."""
        mutado = copy.deepcopy(self.artefatos)
        del mutado["constitution"]["pendencias"]
        r = {x["chave"]: x for x in de.confere_derivaveis(self.achadas, mutado)}
        alvo = r["constitution:meta.pendencias_abertas"]
        self.assertTrue(alvo["deriva"], "a fonte sumiu e isto tem de sair como DERIVA")
        self.assertIs(alvo["bate"], False, "deriva nunca pode sair como bate=True")
        self.assertIn("DERIVA", alvo["nota"])

    def test_a_deriva_atinge_as_DUAS_fontes_do_mesmo_numero(self):
        """`pendencias` alimenta dois campos. Perder a fonte derruba os dois, e
        e por isso que duas fontes a mao do mesmo valor sao piores que uma."""
        mutado = copy.deepcopy(self.artefatos)
        del mutado["constitution"]["pendencias"]
        derivas = [x for x in de.confere_derivaveis(self.achadas, mutado) if x["deriva"]]
        self.assertEqual(len(derivas), 2, f"esperava dois campos afetados, vi {derivas}")

    def test_o_caminho_INTERMEDIARIO_que_sai_tambem_e_pego(self):
        """A deriva pode ser no meio do caminho, nao so na folha."""
        mutado = copy.deepcopy(self.artefatos)
        del mutado["constitution"]["global"]["identidade_semantica_de_replay"]
        r = {x["chave"]: x for x in de.confere_derivaveis(self.achadas, mutado)}
        self.assertTrue(
            r["constitution:global.identidade_semantica_de_replay.total"]["deriva"])


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

    def test_o_lacre_cobre_os_41_e_os_4_de_hoje(self):
        self.assertEqual(len(de.LACRE_SAI_DA_CLASSE), 41)
        self.assertEqual(len(de.LACRE_ISENTOS), 4)
        self.assertEqual(set(de.ISENTOS_DE_DERIVACAO), set(de.LACRE_ISENTOS))


class OGatilhoDaFIT020(unittest.TestCase):
    """ADIADA COM GATILHO, e o gatilho e MECANICO em vez de lembrado.

    A correcao do titular em 2026-10-13: o veredito nao e RECUSADA, e ADIADA.
    "Recusada" fecha a pergunta; ela esta agendada. E o gatilho vive no
    instrumento por um motivo medido NESTE ciclo — o enumerador de 09/10 era uma
    decisao que dependia de alguem lembrar, e ninguem lembrou.
    """

    def setUp(self):
        self.mapa = de.carrega_mapa()

    def test_hoje_a_classe_tem_membros_e_o_gatilho_NAO_arma(self):
        armado, texto = de.gatilho_fit_020(self.mapa)
        self.assertFalse(armado)
        self.assertIn("ADIADA", texto)
        self.assertEqual(len(de.classe_viva(self.mapa)), 11)

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
