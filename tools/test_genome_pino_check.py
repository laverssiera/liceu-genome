#!/usr/bin/env python3
"""Testes do detector de pino: a ancora casa o que deve, e so o que deve.

ESTE ARQUIVO EXISTE POR CAUSA DE UM DEFEITO CONCRETO. A alternativa de ancora
em prosa foi escrita com `\\b` dentro de um heredoc e chegou ao modulo como
BACKSPACE (0x08). A regex passou a exigir um byte de backspace em volta da data
e NUNCA casou -- e nao deu erro nenhum, porque regra que nao casa nao reclama,
so silencia. Historia legitima virou NAO_MENSURAVEL; com as alternativas em
outra ordem, um pino VIVO teria virado HISTORIA e deixado de ser conferido.

A licao e sobre o tipo de teste: nao basta testar o veredito final da varredura,
porque ele era plausivel com a regra morta. O que pega isto e afirmar, FORMA POR
FORMA, que cada ancora casa o seu caso e recusa o que nao e dela.
"""
import importlib.util
import pathlib
import unittest

_raiz = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "pino", _raiz / "genome_pino_check.py")
pino = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pino)


class AncoraDeTempo(unittest.TestCase):
    """Cada forma de dizer QUANDO, e o que nao diz quando."""

    def test_campo_date_casa(self):
        self.assertTrue(pino.ANCORA_DE_TEMPO.search('  date: "2026-10-19"'))
        self.assertTrue(pino.ANCORA_DE_TEMPO.search("  date: 2026-10-19"))

    def test_pr_em_mapa_de_fluxo_casa(self):
        self.assertTrue(pino.ANCORA_DE_TEMPO.search(
            "  source: {repo: liceu-protocol, pr: 15, note: \'x\'}"))

    def test_pr_em_campo_casa(self):
        self.assertTrue(pino.ANCORA_DE_TEMPO.search("    pr: 89"))

    def test_data_em_prosa_casa(self):
        """O caso que o 0x08 matava: data no meio da frase, nao em campo."""
        self.assertTrue(pino.ANCORA_DE_TEMPO.search(
            '  required_evidence: "DECISAO TOMADA (titular, 2026-09-22): a sonda"'))

    def test_sem_byte_de_controle_na_regex(self):
        """A causa raiz, afirmada diretamente: nenhum caractere de controle."""
        for c in pino.ANCORA_DE_TEMPO.pattern:
            self.assertFalse(
                ord(c) < 32,
                f"caractere de controle 0x{ord(c):02x} na regex de ancora -- "
                f"foi exatamente assim que `\\b` virou backspace")

    def test_linha_sem_quando_nao_casa(self):
        for linha in ("  note: \'kit v0.14.0 sem data nenhuma\'",
                      # v0.NN.0 e nao uma versao de verdade: escrever numero que nao se quer
                      # dizer e o defeito que este modulo mede, e o teste nao o pratica
                      "# O kit vem do requirements.txt (liceu-protocol v0.NN.0).",
                      "  pr: nao-e-numero",
                      "  versao: 1.18.0"):
            self.assertFalse(pino.ANCORA_DE_TEMPO.search(linha),
                             f"casou sem dizer quando: {linha!r}")


class Classificacao(unittest.TestCase):
    """Pino vivo, historia, e o terceiro estado."""

    def test_arquivo_de_instalacao_e_vivo(self):
        for rel in ("backend/requirements.txt", "requirements-dev.txt",
                    "pyproject.toml", "constraints.txt"):
            self.assertEqual(pino.classifica(rel, 1, []), pino.VIVO, rel)

    def test_fonte_unica_e_readme_do_kit_sao_vivos(self):
        self.assertEqual(
            pino.classifica("liceu_protocol/VERSION", 1, []), pino.VIVO)
        self.assertEqual(pino.classifica("README.md", 1, []), pino.VIVO)

    def test_nome_datado_e_historia(self):
        self.assertEqual(
            pino.classifica("docs/evidence/2026-09-20-primeiro-fato.md", 9, []),
            pino.HISTORIA)

    def test_dentro_de_bloco_ancorado_e_historia(self):
        self.assertEqual(
            pino.classifica("genome/07-proofs.yaml", 50, [(10, 100)]),
            pino.HISTORIA)

    def test_fora_de_tudo_e_o_terceiro_estado(self):
        """Nao e aprovacao e nao e reprovacao: e nao-medicao, e sera nomeada."""
        self.assertEqual(
            pino.classifica(".github/workflows/ci.yml", 172, []),
            pino.NAO_MENSURAVEL)

    def test_bloco_ancorado_nao_cobre_linha_de_fora(self):
        self.assertEqual(
            pino.classifica("genome/07-proofs.yaml", 500, [(10, 100)]),
            pino.NAO_MENSURAVEL)


class BlocosComData(unittest.TestCase):
    def test_bloco_com_date_entra_e_bloco_sem_ancora_fica_fora(self):
        texto = "\n".join([
            "- id: PRF-0001",          # 1
            '  date: "2026-10-01"',    # 2
            '  note: "kit v0.14.0"',   # 3
            "- id: PRF-0002",          # 4
            '  note: "kit v0.15.0"',   # 5
            "  basis: test",           # 6
        ])
        faixas = pino.blocos_com_data(texto)
        dentro = lambda n: any(a <= n < b for a, b in faixas)
        self.assertTrue(dentro(3), "a citacao do bloco DATADO deveria ser historia")
        self.assertFalse(dentro(5), "a do bloco SEM ancora nao deveria ser")


class FonteUnica(unittest.TestCase):
    def test_fonte_sem_conformance_kit_recusa_em_vez_de_assumir(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8") as f:
            f.write("constitution=1.18.0\n")
            caminho = pathlib.Path(f.name)
        try:
            with self.assertRaises(SystemExit):
                pino.le_fonte(caminho)
        finally:
            caminho.unlink()


if __name__ == "__main__":
    unittest.main(verbosity=2)
