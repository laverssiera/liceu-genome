#!/usr/bin/env python3
"""O detector de PFC sem prova executavel, testado por mutacao.

A FIT-014 confere, no proprio genoma, que o teste de regressao existe. Quando o
PFC nasce de um processo real, o teste mora no monolito — e o juiz nao tem esse
arquivo. Entao e AQUI que vive a morte epistemica "o teste sumiu do arquivo e o
PFC continuou contando".
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import genome_pfc_check as gpc  # noqa: E402

REPO = "Repo-De-Teste"


def _pfc(file, name, repo=REPO):
    return [{"id": "FC-099", "kind": "pfc", "title": "falsa afirmacao de teste",
             "false_claim": "x", "mechanism": "y", "date": "2026-09-22",
             "regression_tests": [{"repo": repo, "file": file, "name": name}]}]


class PfcTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "tests").mkdir()
        (self.root / "tests" / "test_regra.py").write_text(
            "def test_o_caso_real_e_pego():\n"
            "    assert True\n"
            "\n"
            "\n"
            "class Grupo:\n"
            "    def test_dentro_de_classe(self):\n"
            "        assert True\n",
            encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_teste_presente_passa(self):
        self.assertEqual(
            gpc.check(_pfc("tests/test_regra.py", "test_o_caso_real_e_pego"), REPO, self.root), [])

    def test_metodo_dentro_de_classe_tambem_conta(self):
        self.assertEqual(
            gpc.check(_pfc("tests/test_regra.py", "test_dentro_de_classe"), REPO, self.root), [])

    def test_teste_que_sumiu_do_arquivo_falha_na_ci_do_monolito(self):
        # EPISTEMIC KILL TEST: sem isto, o PFC continua contando sem prova nenhuma
        (self.root / "tests" / "test_regra.py").write_text(
            "def test_outra_coisa():\n    assert True\n", encoding="utf-8")
        problemas = gpc.check(_pfc("tests/test_regra.py", "test_o_caso_real_e_pego"), REPO, self.root)
        self.assertEqual(len(problemas), 1, problemas)
        self.assertIn("FC-099", problemas[0])
        self.assertIn("nao esta mais", problemas[0])

    def test_arquivo_de_teste_que_sumiu_falha(self):
        (self.root / "tests" / "test_regra.py").unlink()
        problemas = gpc.check(_pfc("tests/test_regra.py", "test_o_caso_real_e_pego"), REPO, self.root)
        self.assertTrue(any("nao existe mais" in p for p in problemas), problemas)

    def test_nome_so_em_comentario_ou_string_nao_conta(self):
        # citar o nome do teste nao e ter o teste
        (self.root / "tests" / "test_regra.py").write_text(
            "# test_o_caso_real_e_pego foi removido\n"
            'NOMES = ["test_o_caso_real_e_pego"]\n',
            encoding="utf-8")
        problemas = gpc.check(_pfc("tests/test_regra.py", "test_o_caso_real_e_pego"), REPO, self.root)
        self.assertEqual(len(problemas), 1, problemas)

    def test_pfc_de_outro_repo_e_ignorado(self):
        self.assertEqual(
            gpc.check(_pfc("tests/nao_existe.py", "test_x", repo="Outro-Repo"), REPO, self.root), [])

    def test_pfc_sem_repo_e_do_proprio_genoma_e_nao_e_conferido_aqui(self):
        pfc = _pfc("tools/test_genome_check.py", "test_02_afirmacao_nao_declara_status")
        del pfc[0]["regression_tests"][0]["repo"]
        self.assertEqual(gpc.check(pfc, REPO, self.root), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
