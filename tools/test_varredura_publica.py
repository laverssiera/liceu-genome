"""A varredura dos repositorios publicos: arvore, historico e mascara.

O teste que mais importa aqui e o de HISTORICO com isca plantada. Sem ele,
"0 achados" nao se distingue de "a varredura esta quebrada" — e a primeira
versao ESTAVA: usava `git grep -E`, que fala ERE POSIX e nao entende `\\d` nem
`\\b`, entao os padroes de CPF, CEP e telefone casavam nada em silencio. Quem
pegou foi a isca, nao a leitura do codigo.
"""
from __future__ import annotations

import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from genome_privacy_check import PADROES
from varredura_publica import (extensoes_varridas, mascarar, varrer_arvore,
                               varrer_historico)

# Isca montada por concatenacao: este arquivo tambem vive num repositorio
# publico, e literal de CPF aqui continua sendo CPF num repositorio publico.
# E o mesmo cuidado que o test_genome_check.py tomou depois de errar.
CPF_ISCA = "123" + "." + "456" + "." + "789" + "-" + "09"
EMAIL_ISCA = "dono" + "@" + "exemplo" + "." + "com.br"


class Mascara(unittest.TestCase):
    def test_o_valor_nunca_sai_na_saida(self):
        fora = mascarar(f"proprietario {CPF_ISCA} no cadastro")
        self.assertNotIn(CPF_ISCA, fora)
        self.assertIn("<CPF>", fora)

    def test_mascara_todos_os_tipos_de_uma_vez(self):
        fora = mascarar(f"{CPF_ISCA} e {EMAIL_ISCA}")
        self.assertNotIn(CPF_ISCA, fora)
        self.assertNotIn(EMAIL_ISCA, fora)

    def test_texto_limpo_passa_intacto(self):
        # Controle: se a mascara mexesse em tudo, o teste de cima passaria
        # mesmo com a regra quebrada.
        limpo = "taxa de ocupacao 55,54% em 175 m2, zona ZM"
        self.assertEqual(mascarar(limpo), limpo)

    def test_todo_padrao_tem_nome_proprio_na_mascara(self):
        for nome in PADROES:
            self.assertIn(f"<{nome}>", mascarar(f"x {_amostra(nome)} y"),
                          f"{nome} nao aparece nomeado na mascara")


def _amostra(nome: str) -> str:
    return {
        "CPF": CPF_ISCA,
        # Os 11 digitos ficam PARTIDOS no fonte: juntos, este arquivo casaria
        # com o proprio padrao — e a FIT-015 ampliada pegou isso aqui.
        "CPF sem pontuacao": "cpf " + "1234" + "5678" + "909",
        "CNPJ": "12" + "." + "345" + "." + "678" + "/" + "0001" + "-" + "95",
        "e-mail": EMAIL_ISCA,
        "telefone BR": "(" + "11" + ") " + "98765" + "-" + "4321",
        "matricula/inscricao imobiliaria": "matr" + "icula " + "123456",
        "CEP": "06730" + "-" + "000",
    }[nome]


class Extensoes(unittest.TestCase):
    def test_cobre_o_que_existe_nos_publicos_e_ficava_de_fora(self):
        for ext in (".sh", ".css"):
            self.assertIn(ext, extensoes_varridas(),
                          f"{ext} existe nos repositorios publicos e nao era varrido")

    def test_nao_perdeu_as_que_ja_eram_varridas(self):
        for ext in (".yaml", ".py", ".md", ".json"):
            self.assertIn(ext, extensoes_varridas())


class IscaPlantada(unittest.TestCase):
    """Sem isto, "0 achados" nao se distingue de varredura quebrada."""

    def _repo(self, tmp: Path) -> Path:
        r = tmp / "repo"
        r.mkdir()
        for args in (["init", "-q"], ["config", "user.email", "t@t.t"],
                     ["config", "user.name", "t"]):
            subprocess.run(["git", "-C", str(r), *args], check=True,
                           capture_output=True)
        return r

    def _commit(self, r: Path, msg: str) -> None:
        subprocess.run(["git", "-C", str(r), "add", "-A"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(r), "commit", "-q", "-m", msg],
                       check=True, capture_output=True)

    def test_repo_limpo_nao_acusa_nada(self):
        with tempfile.TemporaryDirectory() as t:
            r = self._repo(Path(t))
            (r / "a.py").write_text("zona = 'ZM'\n", encoding="utf-8")
            self._commit(r, "limpo")
            self.assertEqual(varrer_arvore(r), [])
            self.assertEqual(varrer_historico(r), [])

    def test_isca_na_arvore_e_encontrada(self):
        with tempfile.TemporaryDirectory() as t:
            r = self._repo(Path(t))
            (r / "a.py").write_text(f"dono = '{CPF_ISCA}'\n", encoding="utf-8")
            self._commit(r, "com isca")
            achados = varrer_arvore(r)
            self.assertTrue(any("CPF" in a for a in achados), achados)

    def test_isca_APAGADA_continua_no_historico(self):
        # O coracao da coisa: apagar nao e remover. Quem clonar o repositorio
        # publico leva o blob junto.
        with tempfile.TemporaryDirectory() as t:
            r = self._repo(Path(t))
            (r / "a.py").write_text(f"dono = '{CPF_ISCA}'\n", encoding="utf-8")
            self._commit(r, "com isca")
            (r / "a.py").write_text("dono = 'removido'\n", encoding="utf-8")
            self._commit(r, "apagou")

            self.assertEqual(varrer_arvore(r), [],
                             "a arvore ficou limpa, como se esperava")
            achados = varrer_historico(r)
            self.assertTrue(any("CPF" in a for a in achados),
                            f"o blob apagado sumiu da varredura: {achados}")

    def test_isca_em_extensao_que_nao_era_varrida(self):
        with tempfile.TemporaryDirectory() as t:
            r = self._repo(Path(t))
            (r / "x.sh").write_text(f"# {CPF_ISCA}\n", encoding="utf-8")
            self._commit(r, "isca em .sh")
            self.assertTrue(any("CPF" in a for a in varrer_arvore(r)))
            self.assertTrue(any("CPF" in a for a in varrer_historico(r)))

    def test_os_padroes_com_classe_do_python_funcionam_no_historico(self):
        # Foi exatamente aqui que a primeira versao mentiu: `git grep -E` nao
        # entende \\d, entao CPF/CEP/telefone nunca casavam no historico.
        with tempfile.TemporaryDirectory() as t:
            r = self._repo(Path(t))
            (r / "a.py").write_text(
                "\n".join(_amostra(n) for n in ("CPF", "CEP", "telefone BR")) + "\n",
                encoding="utf-8")
            self._commit(r, "tres padroes com \\d")
            tipos = {a.rsplit(": ", 1)[-1] for a in varrer_historico(r)}
            for esperado in ("CPF", "CEP", "telefone BR"):
                self.assertIn(esperado, tipos, f"{esperado} nao foi visto no historico")


if __name__ == "__main__":
    unittest.main(verbosity=2)
