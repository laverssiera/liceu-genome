#!/usr/bin/env python3
"""Testes da imposicao do fencing.

O que eles afirmam, e por que cada um existe:

  1. a imposicao (conferencia no EFEITO) satisfaz as seis exigencias do C30-01;
  2. a variante que confere so na ADMISSAO NAO satisfaz -- e falha exatamente
     nas duas ordens adversas que o C29-02 previu, nem uma a mais nem a menos;
  3. removida a verificacao de epoca, o portao passa a ACEITAR o que recusava:
     portao que nao denuncia a propria remocao nao e portao;
  4. o ato apresentado depois da transicao e o MESMO, byte a byte -- senao o
     passo 3 mediria outro ato;
  5. e o que mais importa guardar: a imposicao NAO satisfaz o I3 como a
     PRF-0202 o escreve, e o dreno satisfaz. Isso nao e falha do ensaio: o I3
     escrito proibe o ESTADO em voo, nao o efeito dele.

O teste 5 e o que impede este arquivo de ser lido como "I3 fechado".
"""
import importlib.util
import pathlib
import sys
import unittest

# O modulo ENTRA em sys.modules ANTES de executar: `@dataclasses.dataclass`
# procura o modulo da classe ali durante a decoracao, e sem o registro ele
# levanta AttributeError em `_is_type`. Carregar por spec sem registrar e o
# atalho que parece funcionar ate alguem usar dataclass.
_raiz = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("fencing", _raiz / "fencing.py")
f = importlib.util.module_from_spec(_spec)
sys.modules["fencing"] = f
_spec.loader.exec_module(f)


class AImposicao(unittest.TestCase):
    """Conferencia no momento do EFEITO."""

    def setUp(self):
        self.r = f.ensaio(f.MOMENTO_EFEITO)

    def test_satisfaz_as_seis_exigencias(self):
        self.assertEqual(self.r["faltando"], [], self.r["faltando"])
        self.assertEqual(self.r["veredito"], "SUFICIENTE")

    def test_o_ato_apos_a_transicao_e_o_MESMO_byte_a_byte(self):
        """Sem isto, o passo 3 poderia estar medindo outro ato."""
        p = next(x for x in self.r["passos"] if x["caso"].startswith("3."))
        self.assertTrue(p["o_ato_e_identico"])
        self.assertEqual(p["resultado"], "RECUSADO")

    def test_as_tres_ordens_adversas_sao_recusadas(self):
        for pref in ("5a", "5b-ii", "5c-ii"):
            p = next(x for x in self.r["passos"] if x["caso"].startswith(pref))
            self.assertEqual(p["resultado"], "RECUSADO", p["caso"])

    def test_a_mutacao_e_denunciada(self):
        """Removida a verificacao, o que era recusado passa a ser aceito."""
        p = next(x for x in self.r["passos"] if x["caso"].startswith("4."))
        self.assertEqual(p["resultado"], "ACEITO")

    def test_vigente_vem_do_log_e_nao_da_alegacao(self):
        """Regra 3: o receptor le o log. Se nao lesse, a leitura ficaria em 0."""
        log = f.LogDeMentira(1)
        rec = f.Receptor(log)
        rec.executar(f.Ato("r", "op", 1, "x"))
        self.assertGreater(log.leituras, 0,
                           "o receptor nao consultou o log -- estaria "
                           "acreditando no que o ato alega")

    def test_epoca_futura_tambem_e_recusada(self):
        """Escolha declarada: a regra 2 e `!=`, mais estrita que o I3.

        Ato que alega epoca que o log nao comprometeu esta ALEGANDO, e alegacao
        do remetente nao e fonte. Custo: receptor atrasado recusa ato legitimo.
        """
        rec = f.Receptor(f.LogDeMentira(1))
        with self.assertRaises(f.Recusado):
            rec.executar(f.Ato("r", "op", 2, "x"))


class AVarianteInsuficiente(unittest.TestCase):
    """Conferencia so na ADMISSAO -- o achado do C29-02, medido e nao citado."""

    def setUp(self):
        self.r = f.ensaio(f.MOMENTO_ADMISSAO)

    def test_nao_satisfaz(self):
        self.assertEqual(self.r["veredito"], "INSUFICIENTE")

    def test_falha_EXATAMENTE_nas_duas_que_o_C29_02_previu(self):
        """Nem uma a mais nem a menos: em voo e reordenado.

        O duplicado que CHEGA depois da transicao e pego na admissao, e por isso
        ele NAO esta nesta lista -- a distincao e do achado, nao do acaso.
        """
        faltando = sorted(k.split(".")[0] for k in self.r["faltando"])
        self.assertEqual(faltando, ["5a", "5c"], self.r["faltando"])

    def test_o_duplicado_que_chega_depois_e_pego_mesmo_na_admissao(self):
        p = next(x for x in self.r["passos"] if x["caso"].startswith("5b-ii"))
        self.assertEqual(p["resultado"], "RECUSADO")


class OI3ComoEstaEscrito(unittest.TestCase):
    """O teste que impede este trabalho de ser lido como "I3 fechado"."""

    def setUp(self):
        self.inv = f.invariante_do_modelo()

    def test_a_imposicao_NAO_satisfaz_o_I3_como_escrito(self):
        """E nao e falha do ensaio: o I3 escrito proibe o ESTADO em voo.

        `all(ep >= corrente for _, ep in servindo)` fala do que esta EM VOO.
        Recusar no efeito nao remove a entrada de `servindo`. O contraexemplo
        tem dois passos: admitir sob 1, promover para 2.
        """
        a = self.inv["A_valida_na_escrita"]
        self.assertTrue(a["viola_o_I3"],
                        "se isto passar a NAO violar, o enunciado do I3 mudou "
                        "e esta prova precisa ser refeita")
        self.assertEqual(a["contraexemplo"]["caminho"], ["admitir", "promover"])
        self.assertEqual(a["contraexemplo"]["estado"],
                         {"comprometida": 2, "em_voo": [1]})

    def test_o_dreno_satisfaz(self):
        self.assertFalse(self.inv["B_drena"]["viola_o_I3"])

    def test_as_duas_correcoes_sao_as_que_a_PRF_0202_nomeou(self):
        """Controle de escopo: nao ha uma terceira sendo medida em silencio."""
        self.assertEqual(sorted(self.inv), ["A_valida_na_escrita", "B_drena"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
