#!/usr/bin/env python3
"""Mutacoes da regra "N itens, N respostas" — e a superficie que a prova cobre.

A regra existe por um erro concreto: uma varredura de CI percorreu 19
repositorios, o comando que ela chamava saiu com erro, a saida veio vazia nas
19 iteracoes, e o laco relatou "nenhum vermelho". Um dos 19 estava vermelho.

Os casos aqui separam as tres coisas que antes viravam a MESMA frase:
nada encontrado · nada conferido · nao consegui conferir.

A ligacao com a varredura de privacidade esta junto de proposito: uma regra que
ninguem invoca nao protege nada, e foi o guarda de dado pessoal do repositorio
PUBLICO que tinha `except OSError: continue`.
"""
import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import genome_check as gc  # noqa: E402
import genome_privacy_check as gpc  # noqa: E402
import varredura  # noqa: E402

# Isca montada por concatenacao: este arquivo tambem vive num repositorio
# publico, e literal de CPF aqui continua sendo CPF num repositorio publico.
ROOT = Path(__file__).resolve().parent.parent

CPF_ISCA = "123" + "." + "456" + "." + "789" + "-" + "09"


class ARegra(unittest.TestCase):
    def test_n_itens_n_respostas_e_MEDIDO(self):
        r = varredura.responder_por_item([1, 2, 3], lambda x: x * 2)
        self.assertEqual(r.estado, varredura.MEDIDO)
        self.assertTrue(r.mediu)
        self.assertEqual(r.respostas, [2, 4, 6])
        self.assertEqual(r.itens, 3)

    def test_zero_itens_nao_e_resultado_limpo(self):
        """CONTROLE do outro lado: lista vazia nao autoriza a frase de
        aprovacao. Era o que a varredura de CI fazia — zero respostas lidas
        como zero problemas."""
        r = varredura.responder_por_item([], lambda x: x)
        self.assertEqual(r.estado, varredura.NADA_A_CONFERIR)
        self.assertFalse(r.mediu)
        self.assertIn("NAO e um resultado limpo", r.resumo())

    def test_um_item_sem_resposta_derruba_a_varredura_inteira(self):
        def responder(x):
            if x == 2:
                raise OSError("arquivo travado")
            return x

        r = varredura.responder_por_item([1, 2, 3], responder)
        self.assertEqual(r.estado, varredura.NAO_MENSURAVEL)
        self.assertFalse(r.mediu)
        self.assertEqual(r.respostas, [1, 3])        # os outros dois responderam
        self.assertEqual(len(r.sem_resposta), 1)

    def test_o_item_sem_resposta_e_NOMEADO_com_motivo(self):
        """'Alguma coisa falhou' nao conserta nada: o relatorio diz QUAL item e
        POR QUE."""
        r = varredura.responder_por_item(["a", "b"],
                                         lambda x: 1 / 0 if x == "b" else x)
        item, motivo = r.sem_resposta[0]
        self.assertEqual(item, "b")
        self.assertIn("ZeroDivisionError", motivo)
        self.assertIn("  ? b", r.resumo())

    def test_o_motivo_nao_carrega_caminho_absoluto(self):
        """O log da CI tambem e publico. O item ja foi nomeado em relativo;
        repetir o caminho da maquina de quem rodou e vazamento gratuito."""
        r = varredura.responder_por_item(
            ["ff.md"], lambda i: open("/caminho/que/nao/existe/ff.md").read())
        _, motivo = r.sem_resposta[0]
        self.assertIn("FileNotFoundError", motivo)
        self.assertNotIn("/caminho/que/nao/existe", motivo)

    def test_o_resumo_do_MEDIDO_traz_o_denominador(self):
        """Sem o numero, quem le 'nada encontrado' nao distingue um conjunto
        limpo de uma varredura que nao leu nada."""
        self.assertIn("3 item(ns)", varredura.responder_por_item([1, 2, 3], lambda x: x).resumo())

    def test_nenhum_item_responde_e_o_caso_do_erro_real(self):
        """Os 19 repositorios, com o comando saindo com erro em todos."""
        r = varredura.responder_por_item(range(19), lambda x: (_ for _ in ()).throw(
            RuntimeError('unknown command "s"')))
        self.assertEqual(r.estado, varredura.NAO_MENSURAVEL)
        self.assertEqual(len(r.sem_resposta), 19)
        self.assertIn("19 de 19", r.resumo())


class ALigacaoComAVarreduraDePrivacidade(unittest.TestCase):
    """A regra so vale se alguem a chama — e o guarda do repositorio publico e
    quem tinha o defeito."""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_arquivo_limpo_e_MEDIDO_e_a_frase_traz_o_numero(self):
        (self.d / "a.md").write_text("taxa de ocupacao 55,54% na zona ZM\n", encoding="utf-8")
        r = gpc.scan(self.d)
        self.assertTrue(r.mediu)
        self.assertEqual(r.itens, 1)
        self.assertEqual(gpc.main(["--root", str(self.d)]), 0)

    def test_a_frase_de_aprovacao_diz_QUANTOS_arquivos(self):
        """A mutacao que apaga o numero da frase so era pega de rabo de olho,
        pelo codigo de saida de outro caso. Aqui ela e cobrada de frente: o
        denominador E parte do resultado, nao enfeite."""
        (self.d / "a.md").write_text("zona ZM\n", encoding="utf-8")
        (self.d / "b.md").write_text("area 175 m2\n", encoding="utf-8")
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            self.assertEqual(gpc.main(["--root", str(self.d)]), 0)
        self.assertIn("2 arquivo(s) conferido(s)", saida.getvalue())

    def test_dado_pessoal_e_achado_CONTROLE_POSITIVO(self):
        """Sem este caso, uma varredura que nao achasse NADA passaria em todos
        os outros — inclusive uma que nao lesse arquivo nenhum."""
        (self.d / "b.md").write_text(f"proprietario {CPF_ISCA}\n", encoding="utf-8")
        r = gpc.scan(self.d)
        self.assertTrue(r.mediu)
        self.assertTrue(any("CPF" in x for lista in r.respostas for x in lista), r.respostas)
        self.assertEqual(gpc.main(["--root", str(self.d)]), 1)

    def test_arquivo_que_nao_se_deixa_ler_vira_NAO_MENSURAVEL(self):
        """Antes era `except OSError: continue`: o arquivo sumia da conta e o
        silencio dele valia como limpeza. Agora a varredura inteira recusa, o
        arquivo e NOMEADO, e a saida e 2 — nem 0 nem 1."""
        (self.d / "a.md").write_text("limpo\n", encoding="utf-8")
        alvos_reais = gpc.alvos
        gpc.alvos = lambda root: alvos_reais(root) + [self.d / "sumiu.md"]
        try:
            r = gpc.scan(self.d)
            self.assertEqual(r.estado, varredura.NAO_MENSURAVEL)
            self.assertIn("sumiu.md", r.sem_resposta[0][0])
            self.assertEqual(gpc.main(["--root", str(self.d)]), 2)
        finally:
            gpc.alvos = alvos_reais

    def test_diretorio_sem_arquivo_de_texto_nao_recebe_aprovacao(self):
        (self.d / "imagem.png").write_bytes(b"\x89PNG")
        r = gpc.scan(self.d)
        self.assertEqual(r.estado, varredura.NADA_A_CONFERIR)
        self.assertFalse(r.mediu)

    def test_o_repositorio_real_passa_e_diz_quantos(self):
        r = gpc.scan(Path(__file__).resolve().parent.parent)
        self.assertTrue(r.mediu, r.resumo())
        self.assertGreater(r.itens, 10)
        self.assertEqual([x for lista in r.respostas for x in lista], [])


class AFIT015(unittest.TestCase):
    """O juiz usa o mesmo motor, e tem de ver o nao-mensuravel.

    Sem este caso, o ramo novo da FIT-015 seria codigo que ninguem exercita —
    e o juiz voltaria a dar o grafo por limpo com arquivo nao lido.
    """

    SCHEMA = json.loads((ROOT / "schema" / "genome.schema.json").read_text(encoding="utf-8"))

    def julgar(self):
        d = Path(tempfile.mkdtemp())
        try:
            for f in sorted((ROOT / "genome").glob("*.yaml")):
                (d / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
            j = gc.Judge(gc.load(d), self.SCHEMA, gc.load_kit_registry(),
                         gc.load_scale_order(), gc.load_kit_producers(), genome_dir=d)
            j.run()
            return j
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_o_juiz_acusa_varredura_que_nao_mediu(self):
        alvos_reais = gpc.alvos
        gpc.alvos = lambda root: alvos_reais(root) + [root / "sumiu.md"]
        try:
            j = self.julgar()
            self.assertTrue(any("FIT-015" in e and "nao mediu" in e.replace("ã", "a")
                                for e in j.errors),
                            f"o juiz nao acusou a varredura incompleta; veio {j.errors}")
        finally:
            gpc.alvos = alvos_reais

    def test_com_a_varredura_inteira_o_juiz_nao_acusa_FIT_015(self):
        """CONTROLE POSITIVO do caso de cima."""
        j = self.julgar()
        self.assertEqual([e for e in j.errors if "FIT-015" in e], [], j.errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
