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
# O Contract Registry do kit INSTALADO: a FIT-010 julga o genoma contra ele.
# As mutações da FIT-010 alteram uma cópia, nunca o kit.
KIT_REGISTRY = gc.load_kit_registry()


def base():
    """O genoma real, como {arquivo: [nós]}."""
    return {f.name: yaml.safe_load(f.read_text(encoding="utf-8")) or []
            for f in sorted((ROOT / "genome").glob("*.yaml"))}


def judge(files, registry=None):
    d = Path(tempfile.mkdtemp())
    try:
        for name, nodes in files.items():
            (d / name).write_text(yaml.safe_dump(nodes, allow_unicode=True, sort_keys=False),
                                  encoding="utf-8")
        j = gc.Judge(gc.load(d), SCHEMA, registry if registry is not None else KIT_REGISTRY)
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
    def assertFails(self, files, contains, registry=None):
        j, _ = judge(files, registry)
        self.assertTrue(any(contains in e for e in j.errors),
                        f"esperava erro com {contains!r}; veio {j.errors}")

    # FIT-010 — o genoma não é a segunda fonte da verdade sobre contratos
    def test_17_lifecycle_mudado_no_genoma_sem_mudar_no_kit(self):
        f = base()
        c = next(n for n in f["03-contracts.yaml"] if n["in_registry"] and n.get("lifecycle") == "ACTIVE")
        c["lifecycle"] = "RETIRED"
        self.assertFails(f, f"VIOLAÇÃO NOVA FIT-010: {c['id']} lifecycle RETIRED no genoma, ACTIVE no kit")

    def test_18_produtor_mudado_no_genoma_sem_mudar_no_kit(self):
        f = base()
        c = next(n for n in f["03-contracts.yaml"] if n["in_registry"])
        c["producer"] = "liceu.opera"
        self.assertFails(f, f"VIOLAÇÃO NOVA FIT-010: {c['id']} produtor liceu.opera no genoma")

    def test_19_in_registry_para_contrato_que_o_kit_nao_tem(self):
        f = base()
        add(f, "03-contracts.yaml", {"id": "liceu.hub.planning-request@9.9.9", "kind": "contract",
                                     "title": "versão inventada", "producer": "liceu.hub",
                                     "in_registry": True, "lifecycle": "ACTIVE"})
        self.assertFails(f, "VIOLAÇÃO NOVA FIT-010: liceu.hub.planning-request@9.9.9 diz in_registry mas o kit")

    def test_20_genoma_atras_do_kit(self):
        # O kit ganha uma versão que o genoma ainda declara fora do registry:
        # é a FIT-010 avisando que o genoma tem de acompanhar o bump.
        f = base()
        c = next(n for n in f["03-contracts.yaml"] if n["in_registry"])
        c["in_registry"] = False
        c.pop("lifecycle", None)
        self.assertFails(f, f"VIOLAÇÃO NOVA FIT-010: {c['id']} diz in_registry: false, mas o kit")

    # G2 — provas têm tempo: supersedes
    def test_22_prova_que_supersede_a_refutacao_desfaz_o_REFUTED(self):
        f = base()
        add(f, "07-proofs.yaml", {"id": "PRF-0099", "kind": "proof",
                                  "title": "corrigido: comparação de texto removida", "proves": ["CLM-0011"],
                                  "basis": "test", "test": {"repo": "ANCHOR.OS", "path": "tests/test_x.py"},
                                  "supersedes": ["PRF-0007"], "date": "2026-09-22"})
        # a dívida no código (VIO-0002) sai junto: a refutação não vige mais
        f["10-violations.yaml"] = [v for v in f["10-violations.yaml"] if v["id"] != "VIO-0002"]
        j, m = judge(f)
        self.assertEqual(j.errors, [], j.errors)
        self.assertEqual(m["claims"]["CLM-0011"]["status"], "TESTED")
        # a história fica: a PRF-0007 não foi apagada
        self.assertIn("PRF-0007", [n.get("id") for n in f["07-proofs.yaml"]])
        self.assertIn(("PRF-0007", "PRF-0099"), [tuple(x) for x in m["proofs_superseded"]])
        self.assertTrue(any("REFUTED por PRF-0007 até 2026-09-22" in h for h in m["claims"]["CLM-0011"]["history"]))
        self.assertTrue(any("TESTED por PRF-0099 desde 2026-09-22" in h for h in m["claims"]["CLM-0011"]["history"]))

    def test_23_supersede_prova_que_nao_existe_e_aresta_quebrada(self):
        f = base()
        add(f, "07-proofs.yaml", {"id": "PRF-0098", "kind": "proof", "title": "x", "proves": ["CLM-0011"],
                                  "basis": "test", "test": {"repo": "r", "path": "p"},
                                  "supersedes": ["PRF-0777"], "date": "2026-09-22"})
        self.assertFails(f, "PRF-0098: aresta quebrada -> 'PRF-0777' não existe")

    def test_24_ciclo_de_supersessao_e_recusado(self):
        f = base()
        add(f, "07-proofs.yaml", {"id": "PRF-0097", "kind": "proof", "title": "a", "refutes": ["CLM-0011"],
                                  "basis": "code_reading", "location": {"repo": "r", "path": "p"},
                                  "supersedes": ["PRF-0096"], "date": "2026-09-22"})
        add(f, "07-proofs.yaml", {"id": "PRF-0096", "kind": "proof", "title": "b", "refutes": ["CLM-0011"],
                                  "basis": "code_reading", "location": {"repo": "r", "path": "p"},
                                  "supersedes": ["PRF-0097"], "date": "2026-09-22"})
        self.assertFails(f, "ciclo de supersessão")

    def test_25_apagar_a_prova_refutada_em_vez_de_superseder(self):
        # A PRF-0007 some; a VIO-0002 (dívida no código, FIT-009 -> CLM-0011) fica.
        # CLM-0011 vira UNPROVEN e a catraca acusa a dívida obsoleta.
        f = base()
        f["07-proofs.yaml"] = [p for p in f["07-proofs.yaml"] if p["id"] != "PRF-0007"]
        j, m = judge(f)
        self.assertEqual(m["claims"]["CLM-0011"]["status"], "UNPROVEN")
        self.assertFails(f, "DÍVIDA OBSOLETA VIO-0002")

    def test_26_prova_superseded_nao_deriva_mesmo_sem_a_nova_provar(self):
        # superseder com uma refutação nova mantém REFUTED; superseder e não
        # afirmar nada sobre a mesma afirmação deixa a afirmação sem prova vigente
        f = base()
        add(f, "07-proofs.yaml", {"id": "PRF-0095", "kind": "proof", "title": "releitura", "refutes": ["CLM-0006"],
                                  "basis": "code_reading", "location": {"repo": "r", "path": "p"},
                                  "supersedes": ["PRF-0006"], "date": "2026-09-22"})
        j, m = judge(f)
        self.assertEqual(j.errors, [], j.errors)
        self.assertEqual(m["claims"]["CLM-0006"]["status"], "REFUTED")
        self.assertEqual(m["claims"]["CLM-0006"]["history"][0], "REFUTED por PRF-0006 até 2026-09-22 (superseded por PRF-0095)")

    def test_21_kit_que_muda_por_baixo_do_genoma(self):
        # O caso real do bump: o kit aposenta a versão, o genoma continua ACTIVE.
        reg = copy.deepcopy(KIT_REGISTRY)
        f = base()
        c = next(n for n in f["03-contracts.yaml"] if n["in_registry"] and n.get("lifecycle") == "ACTIVE")
        cid, _, ver = c["id"].partition("@")
        reg["contracts"][cid][ver]["status"] = "RETIRED"
        self.assertFails(f, f"VIOLAÇÃO NOVA FIT-010: {c['id']} lifecycle ACTIVE no genoma, RETIRED no kit", reg)

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
        node(f, "liceu.john.recommendation@2.1.0")["emitters_observed"].append("liceu.opera")
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
