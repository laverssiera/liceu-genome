#!/usr/bin/env python3
"""Testes de mutacao da FIT-017 — e a superficie que a PRF-0031 cobre.

Cinco exigem recusa, um e o controle positivo contra o kit REAL, e o ultimo
prova a LIGACAO: que o juiz de fato chama esta regra e a reporta como
`VIOLACAO NOVA FIT-017`. Sem esse ultimo, mover a regra para um modulo proprio
teria criado o risco obvio — uma regra perfeita que ninguem invoca.
"""
import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import genome_check as gc  # noqa: E402
import genome_producer_hosting as gph  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
KIT_PRODUCERS = gc.load_kit_producers()


def kit(**mudancas) -> dict:
    """O Producer Registry real, com uma mutacao. Nunca altera o kit instalado."""
    reg = copy.deepcopy(KIT_PRODUCERS)["producers"]
    for pid, campos in mudancas.items():
        for k, v in campos.items():
            if v is gph:            # sentinela: remova o campo
                reg[pid].pop(k, None)
            else:
                reg[pid][k] = v
    return reg


def assuntos(producers) -> list[str]:
    return [s for s, _ in gph.achados(producers)]


class Recusas(unittest.TestCase):
    def test_sem_repository_e_sem_hosted_in(self):
        r = kit(**{"liceu.authority": {"hosted_in": gph}})
        self.assertIn("liceu.authority/hosted_in", assuntos(r))

    def test_hosted_in_para_produtor_que_nao_existe(self):
        r = kit(**{"liceu.authority": {"hosted_in": "liceu.fantasma"}})
        self.assertIn("liceu.authority/hosted_in/inexistente", assuntos(r))

    def test_hosted_in_para_quem_tambem_nao_tem_repositorio(self):
        """A cadeia de hospedagem tem de CHEGAR a codigo."""
        r = kit(**{"liceu.core": {"repository": None, "hosted_in": "liceu.authority",
                                  "hosted_in_reason": "circular de proposito"}})
        self.assertIn("liceu.authority/hosted_in/sem_repo", assuntos(r))

    def test_hosted_in_sem_razao(self):
        r = kit(**{"liceu.authority": {"hosted_in_reason": "   "}})
        self.assertIn("liceu.authority/hosted_in_reason", assuntos(r))

    def test_repository_vazio_nao_conta_como_repositorio(self):
        """String vazia nao e endereco. Se contasse, `repository: ''` viraria a
        saida silenciosa para escapar da regra inteira."""
        r = kit(**{"liceu.authority": {"repository": "", "hosted_in": gph}})
        self.assertIn("liceu.authority/hosted_in", assuntos(r))


class ControlePositivo(unittest.TestCase):
    def test_o_kit_real_passa(self):
        """Sem isto, uma funcao que devolvesse achado sempre passaria em todos
        os testes acima."""
        self.assertEqual(gph.achados(KIT_PRODUCERS["producers"]), [])

    def test_produtor_com_repositorio_nao_e_perguntado(self):
        com_repo = {p: e for p, e in KIT_PRODUCERS["producers"].items()
                    if (e or {}).get("repository")}
        self.assertTrue(com_repo, "o kit nao tem nenhum produtor com repositorio?")
        self.assertEqual(gph.achados(com_repo), [])


class Ligacao(unittest.TestCase):
    """A regra existe; o juiz a chama? Um modulo proprio so vale se estiver ligado."""

    SCHEMA = json.loads((ROOT / "schema" / "genome.schema.json").read_text(encoding="utf-8"))

    def julgar(self, producers_mutados):
        d = Path(tempfile.mkdtemp())
        try:
            for f in sorted((ROOT / "genome").glob("*.yaml")):
                (d / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
            j = gc.Judge(gc.load(d), self.SCHEMA, gc.load_kit_registry(), gc.load_scale_order(),
                         {"producers": producers_mutados}, genome_dir=d)
            j.run()
            return j
        finally:
            shutil.rmtree(d)

    def test_o_juiz_reporta_o_achado_como_violacao_nova(self):
        j = self.julgar(kit(**{"liceu.authority": {"hosted_in": gph}}))
        self.assertTrue(
            any("VIOLAÇÃO NOVA FIT-017: liceu.authority não declara repository nem hosted_in" in e
                for e in j.errors),
            f"o juiz não reportou a FIT-017; veio {j.errors}")

    def test_com_o_kit_real_o_juiz_nao_reporta_FIT_017(self):
        j = self.julgar(KIT_PRODUCERS["producers"])
        self.assertEqual([e for e in j.errors if "FIT-017" in e], [], j.errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
