#!/usr/bin/env python3
"""Testes de mutacao da FIT-019 — a cobertura declarada de busca.

Uma fitness que sempre aprova passa em qualquer teste de caminho feliz. Aqui
cada teste QUEBRA a regra de uma forma conhecida e exige que ela recuse.

O grupo que importa e `IsencaoNaoEscondeRegressao`: e ele que prova que a lista
fechada isenta o rebaixamento causado pelo INSTRUMENTO e nada mais. Catraca
furada e pior que catraca ausente, e sem estes testes a isencao seria confianca.
"""
import hashlib
import sys
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import genome_scope_check as sc  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# O sha256 da lista fechada, congelado. Ele aparece em DOIS lugares de proposito?
# Nao: aqui e a fonte, e o test_genome_check.py confere o MESMO numero contra o
# MESMO arquivo. Dois testes do mesmo fato nao e segunda fonte da verdade — a
# fonte e `genome/08-fitness.yaml`, e os dois a leem.
SHA_DA_LISTA_FECHADA = "299f4bed433112f7790659f0ab90b813469eac1115cee963de7c06cc18cdffa0"

COMPLETO = {"padrao": "X-Canonical-Service-Secret", "universo": "19 repos, ref main, .py",
            "excluidos": ["node_modules", "build"], "instrumento": "git grep -n"}


def prova(pid="PRF-9001", basis="code_reading", escopo=None, refuta="CLM-9001"):
    n = {"id": pid, "kind": "proof", "title": "fixture", "refutes": [refuta],
         "basis": basis, "date": "2026-10-12"}
    if escopo is not None:
        n["scope"] = escopo
    return n


class EscopoCompleto(unittest.TestCase):
    def test_os_quatro_presentes_passam(self):
        self.assertTrue(sc.escopo_completo(prova(escopo=COMPLETO)))

    def test_escopo_ausente_nao_passa(self):
        self.assertFalse(sc.escopo_completo(prova()))

    def test_cada_campo_que_falta_reprova(self):
        for campo in sc.SCOPE_FIELDS:
            parcial = {k: v for k, v in COMPLETO.items() if k != campo}
            with self.subTest(falta=campo):
                self.assertFalse(sc.escopo_completo(prova(escopo=parcial)),
                                 f"escopo sem {campo} foi aceito")

    def test_cada_campo_VAZIO_reprova(self):
        """String vazia e lista vazia nao se distinguem de quem nao pensou."""
        for campo, vazio in (("padrao", ""), ("universo", ""),
                             ("excluidos", []), ("instrumento", "")):
            e = dict(COMPLETO, **{campo: vazio})
            with self.subTest(vazio=campo):
                self.assertFalse(sc.escopo_completo(prova(escopo=e)),
                                 f"{campo} vazio foi aceito")

    def test_escopo_que_nao_e_objeto_reprova(self):
        for lixo in ("sim", 1, ["padrao"], None):
            with self.subTest(valor=lixo):
                self.assertFalse(sc.escopo_completo(prova(escopo=lixo)))

    def test_campo_a_mais_nao_compensa_campo_a_menos(self):
        e = {k: v for k, v in COMPLETO.items() if k != "instrumento"}
        e["comando"] = "git grep -n"
        self.assertFalse(sc.escopo_completo(prova(escopo=e)))


class QuemEhCobrado(unittest.TestCase):
    def test_leitura_sem_escopo_nao_vige(self):
        for b in sc.SCOPE_BASES:
            with self.subTest(basis=b):
                self.assertEqual(sc.indeterminadas([prova(basis=b)]), {"PRF-9001"})

    def test_leitura_com_escopo_vige(self):
        for b in sc.SCOPE_BASES:
            with self.subTest(basis=b):
                self.assertEqual(sc.indeterminadas([prova(basis=b, escopo=COMPLETO)]), set())

    def test_teste_e_observacao_externa_nao_sao_cobrados(self):
        """A fitness cobra LEITURA. As outras duas tem mechanism e environment."""
        for b in ("test", "external_observation"):
            with self.subTest(basis=b):
                self.assertEqual(sc.indeterminadas([prova(basis=b)]), set())

    def test_basis_desconhecida_nao_e_cobrada(self):
        """Lei nova sobre dado velho: history_series roda sem validar schema."""
        self.assertEqual(sc.indeterminadas([prova(basis="relato")]), set())


class ListaFechada(unittest.TestCase):
    def _fit(self):
        return yaml.safe_load((ROOT / "genome" / "08-fitness.yaml").read_text(encoding="utf-8"))

    def _ids(self):
        return sc.lista_fechada(self._fit())

    def test_o_sha256_da_lista_esta_congelado(self):
        h = hashlib.sha256("\n".join(sorted(self._ids())).encode()).hexdigest()
        self.assertEqual(h, SHA_DA_LISTA_FECHADA,
                         "a lista fechada mudou. Se foi para RETIRAR um id — uma prova "
                         "ganhou escopo —, atualize este sha no mesmo PR. Se foi para "
                         "ACRESCENTAR, pare: a lista nao isenta prova nova, e e exatamente "
                         "isso que este teste existe para impedir.")

    def test_acrescentar_um_id_quebra_o_lacre(self):
        """MUTACAO DO PROPRIO LACRE. Sem ela, o sha congelado seria enfeite."""
        h = hashlib.sha256("\n".join(sorted(list(self._ids()) + ["PRF-9001"])).encode()).hexdigest()
        self.assertNotEqual(h, SHA_DA_LISTA_FECHADA)

    def test_remover_um_id_tambem_quebra_o_lacre(self):
        resto = sorted(self._ids())[1:]
        h = hashlib.sha256("\n".join(resto).encode()).hexdigest()
        self.assertNotEqual(h, SHA_DA_LISTA_FECHADA)

    def test_fitness_sem_o_campo_e_ignorada(self):
        self.assertEqual(sc.lista_fechada([{"id": "FIT-001", "kind": "fitness"}]), {})

    def test_a_lista_diz_qual_fitness_e_quando(self):
        selo = sc.lista_fechada([{"id": "FIT-019", "kind": "fitness", "instrument_introduced": {
            "date": "2026-10-12", "proofs": ["PRF-0001"], "note": "n"}}])
        self.assertEqual(selo, {"PRF-0001": ("FIT-019", "2026-10-12")})

    def test_dois_instrumentos_convivem(self):
        """Quando a FIT-020 nascer, a isencao dela nao pode apagar a da FIT-019."""
        selo = sc.lista_fechada([
            {"id": "FIT-019", "kind": "fitness", "instrument_introduced": {
                "date": "2026-10-12", "proofs": ["PRF-0001"], "note": "n"}},
            {"id": "FIT-020", "kind": "fitness", "instrument_introduced": {
                "date": "2026-11-01", "proofs": ["PRF-0200"], "note": "n"}}])
        self.assertEqual(selo["PRF-0001"][0], "FIT-019")
        self.assertEqual(selo["PRF-0200"][0], "FIT-020")


class IsencaoNaoEscondeRegressao(unittest.TestCase):
    """O grupo que o titular exigiu: a isencao cobre o instrumento e nada mais."""

    SELO = {"PRF-0001": ("FIT-019", "2026-10-12"), "PRF-0006": ("FIT-019", "2026-10-12")}

    def test_perda_so_da_lista_e_isentada(self):
        self.assertEqual(sc.isenta(["PRF-0001", "PRF-0006"], self.SELO),
                         ("FIT-019", "2026-10-12"))

    def test_UMA_prova_de_fora_cancela_a_isencao(self):
        """O coracao da coisa: perda MISTA nao e isentada."""
        self.assertIsNone(sc.isenta(["PRF-0001", "PRF-9001"], self.SELO))

    def test_prova_nova_sozinha_nao_e_isentada(self):
        self.assertIsNone(sc.isenta(["PRF-9001"], self.SELO))

    def test_perda_vazia_nao_e_isentada(self):
        """Sem rebaixamento por instrumento nao ha o que isentar: a catraca decide."""
        self.assertIsNone(sc.isenta([], self.SELO))

    def test_lista_vazia_nao_isenta_ninguem(self):
        self.assertIsNone(sc.isenta(["PRF-0001"], {}))

    def test_a_ordem_da_perda_nao_muda_o_veredito(self):
        """Mutacao: `any` sobre lista invertida tem de dar o mesmo."""
        self.assertIsNone(sc.isenta(["PRF-9001", "PRF-0001"], self.SELO))
        self.assertIsNone(sc.isenta(["PRF-0001", "PRF-9001"], self.SELO))


class OsNumeros(unittest.TestCase):
    def test_separa_quem_caiu_na_introducao_de_quem_caiu_depois(self):
        provas = [prova("PRF-0001"), prova("PRF-9001"), prova("PRF-0002", escopo=COMPLETO)]
        vig = {"PRF-0001", "PRF-9001", "PRF-0002"}
        selo = {"PRF-0001": ("FIT-019", "2026-10-12")}
        c = sc.cobertura(provas, vig, selo, sc.indeterminadas(provas))
        self.assertEqual(c["alvo"], 3)
        self.assertEqual(c["com_scope"], 1)
        self.assertEqual(c["na_introducao"], ["PRF-0001"])
        self.assertEqual(c["depois_da_introducao"], ["PRF-9001"])

    def test_prova_superseded_sai_da_conta(self):
        provas = [prova("PRF-0001"), prova("PRF-9001")]
        c = sc.cobertura(provas, {"PRF-9001"}, {}, sc.indeterminadas(provas))
        self.assertEqual(c["alvo"], 1)
        self.assertEqual(c["indeterminadas"], ["PRF-9001"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
