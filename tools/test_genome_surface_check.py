#!/usr/bin/env python3
"""O detector de superficie alterada, testado como o juiz e testado: por mutacao.

A invalidacao por hash acontece na CI do monolito — o juiz roda no repositorio
do genoma e nao tem os arquivos dos outros. Entao e AQUI que vive o teste de
morte epistemica "content_hash diferente do arquivo".
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import genome_surface_check as gsc  # noqa: E402

REPO = "Repo-De-Teste"


def _proof(paths, content_hash):
    return [{"id": "PRF-0099", "kind": "proof", "title": "prova de superficie", "basis": "test",
             "mechanism": {"repo": REPO, "paths": paths, "content_hash": content_hash,
                           "commit": "abc1234"}}]


class SuperficieTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "app").mkdir()
        (self.root / "app" / "servico.py").write_text("def x():\n    return 1\n", encoding="utf-8")
        (self.root / "app" / "teste.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")
        self.paths = ["app/servico.py", "app/teste.py"]
        self.hash, faltando = gsc.surface_hash(self.root, self.paths)
        self.assertEqual(faltando, [])

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_superficie_inalterada_passa(self):
        self.assertEqual(gsc.check(_proof(self.paths, self.hash), REPO, self.root), [])

    def test_content_hash_diferente_do_arquivo_falha_na_ci_do_monolito(self):
        # EPISTEMIC KILL TEST: o codigo provado mudou; a CI DESTE repo tem de acusar
        (self.root / "app" / "servico.py").write_text("def x():\n    return 2\n", encoding="utf-8")
        problemas = gsc.check(_proof(self.paths, self.hash), REPO, self.root)
        self.assertEqual(len(problemas), 1, problemas)
        self.assertIn("altera uma superficie provada", problemas[0])
        self.assertIn("PRF-0099", problemas[0])

    def test_arquivo_provado_que_sumiu_falha(self):
        (self.root / "app" / "teste.py").unlink()
        problemas = gsc.check(_proof(self.paths, self.hash), REPO, self.root)
        self.assertTrue(any("nao existe mais" in p for p in problemas), problemas)

    def test_crlf_nao_invalida_a_prova(self):
        # checkout Windows nao pode fazer a prova parecer invalida
        (self.root / "app" / "servico.py").write_bytes(b"def x():\r\n    return 1\r\n")
        self.assertEqual(gsc.check(_proof(self.paths, self.hash), REPO, self.root), [])

    def test_prova_superseded_nao_e_cobrada(self):
        """A guarda cobrava para sempre uma superficie que o grafo aposentou.

        Apareceu no PR 74 do CONSTRUTORA: a PRF-0015 provava que attest()
        recebia o veredito pronto no corpo do POST. O PR desfez isso, uma prova
        nova a superseded — e a guarda continuou exigindo o hash antigo, que
        nenhum codigo correto produz mais.

        A unica saida seria editar o content_hash da prova velha: reescrever a
        historia, que e exatamente o que a supersessao existe para evitar. O
        esquema do genoma ja dizia que so as vigentes entram na derivacao; o
        juiz respeitava, esta guarda nao. Duas ferramentas lendo o mesmo grafo
        com regras diferentes sao duas verdades, e a segunda envelhece calada.
        """
        (self.root / "app" / "servico.py").write_text("def x():" + chr(10) + "    return 2" + chr(10),
                                                      encoding="utf-8")
        velha = _proof(self.paths, self.hash)[0]
        nova = {"id": "PRF-0100", "kind": "proof", "title": "a que substitui",
                "basis": "test", "supersedes": ["PRF-0099"],
                "mechanism": {"repo": REPO, "paths": self.paths,
                              "content_hash": gsc.surface_hash(self.root, self.paths)[0],
                              "commit": "def5678"}}
        self.assertEqual(gsc.check([velha, nova], REPO, self.root), [])

    def test_a_prova_vigente_continua_sendo_cobrada(self):
        """Controle positivo: sem ele, uma guarda que ignorasse TUDO passaria no
        teste de cima e nao acusaria mudanca nenhuma."""
        (self.root / "app" / "servico.py").write_text("def x():" + chr(10) + "    return 3" + chr(10),
                                                      encoding="utf-8")
        velha = _proof(self.paths, self.hash)[0]
        nova = {"id": "PRF-0100", "kind": "proof", "title": "a que substitui",
                "basis": "test", "supersedes": ["PRF-0099"],
                "mechanism": {"repo": REPO, "paths": self.paths,
                              "content_hash": "0" * 64, "commit": "def5678"}}
        problemas = gsc.check([velha, nova], REPO, self.root)
        self.assertEqual(len(problemas), 1, problemas)
        self.assertIn("PRF-0100", problemas[0])
        self.assertNotIn("PRF-0099", problemas[0])

    def test_prova_de_outro_repo_e_ignorada(self):
        self.assertEqual(gsc.check(_proof(self.paths, "0" * 64), "Outro-Repo", self.root), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
