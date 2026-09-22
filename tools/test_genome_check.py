#!/usr/bin/env python3
"""
Testes de mutação do genome_check.

Um validador que sempre aprova passa em qualquer teste que só confira o caminho feliz.
Aqui cada teste QUEBRA o genoma de uma forma conhecida e exige que o juiz recuse.

O último teste é o CONTROLE POSITIVO: prova que a contagem da cadeia SOBE quando há
prova real. Sem ele, um juiz que devolvesse sempre 0/5 passaria em todos os outros.

Só biblioteca padrão + yaml + jsonschema, as mesmas dependências do juiz.
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

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schema" / "genome.schema.json").read_text(encoding="utf-8"))


def base():
    """O genoma real, como {arquivo: [nós]}."""
    return {f.name: yaml.safe_load(f.read_text(encoding="utf-8")) or []
            for f in sorted((ROOT / "genome").glob("*.yaml"))}


def judge(files):
    d = Path(tempfile.mkdtemp())
    try:
        for name, nodes in files.items():
            (d / name).write_text(yaml.safe_dump(nodes, allow_unicode=True, sort_keys=False),
                                  encoding="utf-8")
        j = gc.Judge(gc.load(d), SCHEMA)
        return j, j.run()
    finally:
        shutil.rmtree(d)


def node(files, nid):
    for nodes in files.values():
        for n in nodes:
            if n.get("id") == nid:
                return n
    raise KeyError(nid)


def add(files, fname, n):
    files[fname].append(n)


class Integro(unittest.TestCase):
    def test_genoma_real_e_integro(self):
        j, m = judge(base())
        self.assertEqual(j.errors, [], j.errors)
        self.assertEqual(m["chain"]["structural"], 0)
        self.assertEqual(m["claims"]["CLM-0001"]["status"], "REFUTED")


class Mutacoes(unittest.TestCase):
    def assertFails(self, files, contains):
        j, _ = judge(files)
        self.assertTrue(any(contains in e for e in j.errors),
                        f"esperava erro com {contains!r}; veio {j.errors}")

    def test_01_john_nao_exibe_resultado_de_autoridade(self):
        f = base()
        node(f, "SCR-04")["displays"]["decision_result"] = ["GRANTED"]
        node(f, "SCR-04")["must_not_display"].remove("decision_result")
        self.assertFails(f, "sem ler contrato de quem pode autorizar")

    def test_02_afirmacao_nao_declara_status(self):
        f = base()
        node(f, "CLM-L1")["status"] = "PROVEN"
        self.assertFails(f, "Additional properties")

    def test_03_divida_apagada_do_livro_vira_violacao_nova(self):
        f = base()
        f["10-violations.yaml"] = [v for v in f["10-violations.yaml"] if v["id"] != "VIO-0001"]
        self.assertFails(f, "VIOLAÇÃO NOVA FIT-006")

    def test_04_proposta_nao_e_usada_como_autoritativa(self):
        f = base()
        node(f, "SCR-05")["used_by"][0]["used_as"] = "authoritative_decision"
        self.assertFails(f, "VIOLAÇÃO NOVA FIT-004")

    def test_05_teste_sozinho_nao_prova_elo(self):
        f = base()
        add(f, "07-proofs.yaml", {"id": "PRF-0099", "kind": "proof", "title": "teste do elo 1",
            "proves": ["CLM-L1"], "basis": "test",
            "test": {"repo": "x", "path": "t.py"}, "date": "2026-09-22"})
        j, m = judge(f)
        self.assertEqual(j.errors, [])
        self.assertEqual(m["claims"]["CLM-L1"]["status"], "TESTED")
        self.assertEqual(m["chain"]["structural"], 0, "teste sem observação externa não conta elo")

    def test_06_ler_codigo_nao_prova(self):
        f = base()
        add(f, "07-proofs.yaml", {"id": "PRF-0098", "kind": "proof", "title": "li o código",
            "proves": ["CLM-L1"], "basis": "code_reading",
            "location": {"repo": "x"}, "date": "2026-09-22"})
        self.assertFails(f, "PRF-0098")

    def test_07_dominio_nao_emite_evento_alheio(self):
        f = base()
        node(f, "liceu.john.recommendation@2.0.0")["emitters_observed"].append("liceu.opera")
        self.assertFails(f, "VIOLAÇÃO NOVA FIT-001")

    def test_08_divida_corrigida_mas_mantida_no_livro(self):
        f = base()
        del node(f, "liceu.anchor.authorization@1.1.0")["implementation_observed"]
        self.assertFails(f, "DÍVIDA OBSOLETA VIO-0001")

    def test_09_tela_nao_exibe_e_proibe_ao_mesmo_tempo(self):
        f = base()
        node(f, "SCR-02")["displays"]["planning_state_status"].append("VALIDATED")
        self.assertFails(f, "exibe e proíbe")

    def test_10_vigente_exige_dono_e_revisor(self):
        f = base()
        node(f, "P-001")["validity"] = "VIGENTE"
        self.assertFails(f, "P-001")

    def test_11_proposta_nao_tem_dono(self):
        f = base()
        node(f, "P-003")["owner"] = "alguem"
        self.assertFails(f, "P-003")

    def test_12_john_nao_autoriza_nem_por_escrito(self):
        f = base()
        node(f, "SCR-04")["john_participation"][0]["role"] = "AUTHORIZES"
        self.assertFails(f, "SCR-04")

    def test_13_tela_nao_le_contrato_aposentado(self):
        f = base()
        node(f, "SCR-04")["reads"] = ["liceu.john.recommendation@1.0.0"]
        self.assertFails(f, "contrato aposentado")

    def test_14_truncamento_silencioso_do_yaml(self):
        d = Path(tempfile.mkdtemp())
        try:
            (d / "x.yaml").write_text("- id: CLM-9\n  kind: claim\n  statement: s\n"
                                      "  asserted_by: CORE #50\n", encoding="utf-8")
            self.assertTrue(gc.lint(d), "o juiz tem de acusar ' #' fora de aspas")
        finally:
            shutil.rmtree(d)


    def test_16_genoma_incompleto_nao_derruba_o_juiz(self):
        # Achado lendo o Drive: 8 dos 11 arquivos ausentes faziam o juiz quebrar com
        # IndexError. Agora ele recusa com veredito, nomeando as arestas quebradas.
        f = {k: v for k, v in base().items()
             if k in ("05-screens.yaml", "06-claims.yaml", "07-proofs.yaml")}
        j, m = judge(f)
        self.assertIsNone(m, "sobre grafo partido não se calcula Self-Model")
        self.assertTrue(any("nó meta" in e for e in j.errors))
        self.assertTrue(any("aresta quebrada" in e for e in j.errors))


class ControlePositivo(unittest.TestCase):
    def test_15_prova_real_faz_a_contagem_subir(self):
        f = base()
        add(f, "07-proofs.yaml", {"id": "PRF-0097", "kind": "proof",
            "title": "elo 1 observado", "proves": ["CLM-L1"], "basis": "external_observation",
            "external_observation": {"instrument": "connz + subscriber",
                                     "observed": "archimedes.planning-state na tabela events"},
            "evidence_artifact": {"repo": "x", "path": "docs/evidence/e.md"},
            "environment": "durable", "date": "2026-09-22"})
        j, m = judge(f)
        self.assertEqual(j.errors, [])
        self.assertEqual(m["claims"]["CLM-L1"]["status"], "PROVEN")
        self.assertEqual(m["chain"]["structural"], 1,
                         "com prova externa real, a cadeia tem de subir para 1/5")


if __name__ == "__main__":
    unittest.main(verbosity=2)
