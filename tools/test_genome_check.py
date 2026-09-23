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
import genome_surface_check as gsc  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schema" / "genome.schema.json").read_text(encoding="utf-8"))
# O Contract Registry do kit INSTALADO: a FIT-010 julga o genoma contra ele.
# As mutações da FIT-010 alteram uma cópia, nunca o kit.
KIT_REGISTRY = gc.load_kit_registry()
SCALE_ORDER = gc.load_scale_order()
KIT_PRODUCERS = gc.load_kit_producers()


def base():
    """O genoma real, como {arquivo: [nós]}."""
    return {f.name: yaml.safe_load(f.read_text(encoding="utf-8")) or []
            for f in sorted((ROOT / "genome").glob("*.yaml"))}


def judge(files, registry=None, producers=None):
    d = Path(tempfile.mkdtemp())
    try:
        for name, nodes in files.items():
            (d / name).write_text(yaml.safe_dump(nodes, allow_unicode=True, sort_keys=False),
                                  encoding="utf-8")
        j = gc.Judge(gc.load(d), SCHEMA, registry if registry is not None else KIT_REGISTRY,
                     SCALE_ORDER, producers if producers is not None else KIT_PRODUCERS,
                     genome_dir=d)
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


def cadeia(m, escala="LOCAL"):
    """(estrutural agregada, estrutural na escala) — para medir DIFERENCA."""
    return m["chain"]["structural"], m["chain_by_scale"].get(escala, {}).get("structural", 0)


def linha_de_base(escala="LOCAL"):
    _, m = judge(base())
    return cadeia(m, escala)


class Integro(unittest.TestCase):
    def test_genoma_real_e_integro(self):
        j, m = judge(base())
        self.assertEqual(j.errors, [], j.errors)
        # A contagem e DERIVADA: tem de bater com os elos cujo claim esta PROVEN.
        # Numero fixo aqui seria afirmar o estado do genoma, e apodreceria a
        # cada elo novo — foi o que aconteceu quando a cadeia da P-001 andou.
        elos = {c["id"]: c for c in base()["06-claims.yaml"] if c.get("chain_link")}
        esperado = sum(1 for cid, c in elos.items()
                       if c["chain_link"]["measure"] == "structural"
                       and 1 <= c["chain_link"]["position"] <= m["chain"]["positions"]
                       and m["claims"][cid]["status"] == "PROVEN")
        self.assertEqual(m["chain"]["structural"], esperado)
        self.assertEqual(m["claims"]["CLM-0001"]["status"], "REFUTED")


class Mutacoes(unittest.TestCase):
    def assertFails(self, files, contains, registry=None, producers=None):
        j, _ = judge(files, registry, producers)
        self.assertTrue(any(contains in e for e in j.errors),
                        f"esperava erro com {contains!r}; veio {j.errors}")

    # B4 — o kit contra o mundo: produtor sem repositório diz onde está.
    # As mutações da FIT-017 saíram daqui para tools/test_genome_producer_hosting.py,
    # junto com a regra: a PRF-0031 cobria este arquivo e o genome_check.py, e
    # toda fitness nova invalidava uma prova que continuava verdadeira. O teste
    # de LIGAÇÃO — o juiz realmente chama a regra? — foi junto, para a superfície
    # da prova ser inteira num lugar só.

    # U4 — pré-registro: previsão registrada depois do fato não é previsão
    def test_56_previsao_resolvida_por_teste_e_violacao(self):
        f = base()
        add(f, "07-proofs.yaml", {"id": "PRF-0080", "kind": "proof", "title": "teste como oráculo",
                                  "proves": ["CLM-0023"], "basis": "test", "environment": "ci",
                                  "test": {"repo": "r", "path": "p", "name": "n"},
                                  "date": "2026-12-01",
                                  "mechanism": {"repo": "r", "paths": ["a.py"],
                                                "content_hash": "0" * 64, "commit": "abc1234"}})
        self.assertFails(f, "VIOLAÇÃO NOVA FIT-016: PRF-0080 resolve a previsão CLM-0023 por test")

    def test_57_prova_anterior_ao_registro_nao_confirma_previsao(self):
        # o fato veio antes: isto é explicação depois do ocorrido, não previsão
        f = base()
        add(f, "07-proofs.yaml", {"id": "PRF-0081", "kind": "proof", "title": "o alvará saiu antes",
                                  "proves": ["CLM-0023"], "basis": "external_observation",
                                  "external_observation": {"instrument": "protocolo", "observed": "alvara"},
                                  "evidence_artifact": {"repo": "r", "path": "p"},
                                  "environment": "durable", "date": "2020-01-01"})
        self.assertFails(f, "VIOLAÇÃO NOVA FIT-016: PRF-0081 é de 2020-01-01 e a previsão CLM-0023")

    def test_58_observacao_externa_posterior_confirma_a_previsao(self):
        f = base()
        add(f, "07-proofs.yaml", {"id": "PRF-0082", "kind": "proof", "title": "alvará sem exigência",
                                  "proves": ["CLM-0023"], "basis": "external_observation",
                                  "external_observation": {"instrument": "protocolo na Prefeitura",
                                                            "observed": "alvara emitido sem exigencia"},
                                  "evidence_artifact": {"repo": "privado", "path": "alvara"},
                                  "environment": "durable", "date": "2026-12-01"})
        j, m = judge(f)
        self.assertEqual(j.errors, [], j.errors)
        self.assertEqual(m["claims"]["CLM-0023"]["status"], "PROVEN")
        self.assertEqual([p["status"] for p in m["predictions"] if p["id"] == "CLM-0023"], ["PROVEN"])

    def test_59_o_registro_de_comparacao_conta_as_quatro_previsoes(self):
        j, m = judge(base())
        self.assertEqual(len(m["predictions"]), 4, [p["id"] for p in m["predictions"]])
        self.assertTrue(all(p["status"] not in ("PROVEN", "REFUTED") for p in m["predictions"]))

    # U3 — o PFC do mundo real: o teste mora em outro repositório
    def test_53_pfc_com_teste_em_repo_sem_superficie_provada_e_violacao(self):
        f = base()
        node(f, "FC-001")["regression_tests"] = [
            {"repo": "Repositorio-Que-Ninguem-Confere", "file": "tests/t.py", "name": "test_x"}]
        self.assertFails(f, "VIOLAÇÃO NOVA FIT-014: FC-001 aponta teste em "
                            "'Repositorio-Que-Ninguem-Confere', onde o genoma não prova superfície")

    def test_54_pfc_com_teste_em_repo_com_superficie_provada_passa(self):
        # o juiz não abre o arquivo de lá; quem confere é a CI daquele repositório
        f = base()
        repo = next(n["mechanism"]["repo"] for n in f["07-proofs.yaml"] if n.get("mechanism"))
        node(f, "FC-001")["regression_tests"] = [
            {"repo": repo, "file": "tests/t.py", "name": "test_que_o_juiz_nao_ve"}]
        j, _ = judge(f)
        self.assertEqual(j.errors, [], j.errors)

    def test_55_teste_do_proprio_genoma_continua_conferido_arquivo_a_arquivo(self):
        f = base()
        node(f, "FC-001")["regression_tests"] = [
            {"repo": "liceu-genome", "file": "tools/test_genome_check.py", "name": "test_que_nao_existe"}]
        self.assertFails(f, "VIOLAÇÃO NOVA FIT-014: FC-001 aponta test_que_nao_existe")

    # U0 — o genoma é público: dado pessoal não entra
    #
    # As amostras são MONTADAS em tempo de execução, nunca escritas literalmente:
    # este arquivo também vive no repositório público e também é varrido. Escrever
    # um CPF de exemplo aqui seria cometer o defeito ao testá-lo.
    @staticmethod
    def _amostra(tipo):
        return {
            "cpf": ".".join(["123", "456", "789"]) + "-" + "01",
            "email": "dono" + "@" + "exemplo" + "." + "com.br",
            "telefone": "(" + "11" + ") " + "98765" + "-" + "4321",
            "matricula": "matr" + "icula " + "123456" + " do cartorio",
            "cep": "06730" + "-" + "000",
        }[tipo]

    def test_50_cpf_no_genoma_falha_a_ci(self):
        f = base()
        node(f, "CASO-P001")["source"]["note"] += " proprietario " + self._amostra("cpf")
        self.assertFails(f, "VIOLAÇÃO NOVA FIT-015: dado pessoal em repositório público")

    def test_51_email_telefone_e_matricula_tambem_falham(self):
        for tipo in ("email", "telefone", "matricula", "cep"):
            f = base()
            node(f, "CASO-P001")["source"]["note"] += " " + self._amostra(tipo)
            self.assertFails(f, "VIOLAÇÃO NOVA FIT-015")

    def test_52_parametro_do_caso_real_nao_e_dado_pessoal(self):
        # zona, areas e indices podem — sao o que o LICEU precisa e nao identificam ninguem
        f = base()
        node(f, "CASO-P001")["source"]["note"] += " taxa de ocupacao 55,54% em 175 m2"
        j, _ = judge(f)
        self.assertEqual(j.errors, [], j.errors)

    # H6 — PFC com teste real, e o freio
    def test_43_pfc_apontando_teste_inexistente_e_recusado(self):
        f = base()
        node(f, "FC-001")["regression_tests"] = [{"file": "tools/test_genome_check.py",
                                                  "name": "test_que_nao_existe"}]
        self.assertFails(f, "VIOLAÇÃO NOVA FIT-014: FC-001 aponta test_que_nao_existe")

    def test_44_pfc_apontando_arquivo_inexistente_e_recusado(self):
        f = base()
        node(f, "FC-001")["regression_tests"] = [{"file": "tools/nao_existe.py", "name": "test_x"}]
        self.assertFails(f, "VIOLAÇÃO NOVA FIT-014: FC-001 aponta teste em tools/nao_existe.py")

    # H3 — campo relatado declara a origem; asserted não sustenta certeza
    def test_37_campo_relatado_sem_origem_e_violacao(self):
        f = base()
        del node(f, "liceu.anchor")["field_provenance"]["teto_interno"]
        self.assertFails(f, "VIOLAÇÃO NOVA FIT-013: liceu.anchor.teto_interno não declara origem")

    def test_38_derived_que_nao_confere_com_a_fonte_e_violacao(self):
        f = base()
        node(f, "liceu.archimedes")["teto_interno"] = "LOCAL"     # o kit diz CONTINENTAL
        self.assertFails(f, "VIOLAÇÃO NOVA FIT-013: liceu.archimedes.teto_interno diz derived mas não confere")

    def test_39_prova_apoiada_em_campo_asserted_nao_prova(self):
        f = base()
        add(f, "07-proofs.yaml", {"id": "PRF-0088", "kind": "proof", "title": "elo 1 pelo campo relatado",
                                  "proves": ["CLM-L1"], "basis": "external_observation",
                                  "external_observation": {"instrument": "i", "observed": "o"},
                                  "evidence_artifact": {"repo": "r", "path": "p"},
                                  "environment": "ephemeral", "scale": "LOCAL", "date": "2026-09-22",
                                  "derived_from": ["liceu.archimedes.planning-state@2.0.0.emitters_observed"]})
        self.assertFails(f, "VIOLAÇÃO NOVA FIT-013: PRF-0088 PROVA apoiada em")

    def test_40_refutacao_pode_se_apoiar_em_campo_asserted(self):
        # relato levanta suspeita; e refutar e levantar suspeita com consequencia
        f = base()
        add(f, "07-proofs.yaml", {"id": "PRF-0087", "kind": "proof", "title": "relato refuta",
                                  "refutes": ["CLM-L1"], "basis": "code_reading",
                                  "location": {"repo": "r", "path": "p"}, "date": "2026-09-22",
                                  "derived_from": ["liceu.archimedes.planning-state@2.0.0.emitters_observed"]})
        j, m = judge(f)
        self.assertEqual(j.errors, [], j.errors)
        self.assertEqual(m["claims"]["CLM-L1"]["status"], "REFUTED")

    def test_41_derived_from_para_campo_inexistente_e_aresta_quebrada(self):
        f = base()
        add(f, "07-proofs.yaml", {"id": "PRF-0086", "kind": "proof", "title": "x", "refutes": ["CLM-L1"],
                                  "basis": "code_reading", "location": {"repo": "r", "path": "p"},
                                  "date": "2026-09-22", "derived_from": ["liceu.opera.teto_interno"]})
        self.assertFails(f, "derived_from -> liceu.opera.teto_interno não existe no nó")

    # H2 — o genoma aprende a esquecer: STALE, superfície, expiração
    def test_32_evidencia_vencida_vira_STALE_nao_REFUTED(self):
        f = base()
        node(f, "PRF-0002")["expires_at"] = "2026-09-01"          # venceu antes de hoje
        j, m = judge(f)
        self.assertEqual(j.errors, [], j.errors)
        self.assertEqual(m["claims"]["CLM-0002"]["status"], "STALE")
        self.assertNotEqual(m["claims"]["CLM-0002"]["status"], "REFUTED")
        self.assertIn("PRF-0002", m["proofs_expired"])
        # a ENTRADA e posicao 0: vencer nao muda a contagem dos elos 1..5
        self.assertEqual(cadeia(m)[1], linha_de_base()[1])

    def test_33_prova_nova_com_o_hash_atual_volta_a_PROVEN(self):
        f = base()
        node(f, "PRF-0002")["expires_at"] = "2026-09-01"
        add(f, "07-proofs.yaml", {"id": "PRF-0089", "kind": "proof", "title": "entrada reobservada",
                                  "proves": ["CLM-0002"], "basis": "external_observation",
                                  "external_observation": {"instrument": "psql + NATS", "observed": "fato gravado"},
                                  "evidence_artifact": {"repo": "r", "path": "docs/evidence/x.md"},
                                  "environment": "ephemeral", "scale": "LOCAL", "date": "2026-09-22"})
        j, m = judge(f)
        self.assertEqual(j.errors, [], j.errors)
        self.assertEqual(m["claims"]["CLM-0002"]["status"], "PROVEN")

    def test_34_remover_a_observacao_externa_derruba_o_PROVEN(self):
        f = base()
        f["07-proofs.yaml"] = [p for p in f["07-proofs.yaml"] if p["id"] != "PRF-0002"]
        j, m = judge(f)
        self.assertNotEqual(m["claims"]["CLM-0002"]["status"], "PROVEN")
        # de novo: a entrada e posicao 0, entao perder a prova dela nao mexe nos elos
        self.assertEqual(cadeia(m)[1], linha_de_base()[1])

    def test_35_prova_por_teste_sem_superficie_e_violacao(self):
        f = base()
        del node(f, "PRF-0009")["mechanism"]
        self.assertFails(f, "VIOLAÇÃO NOVA FIT-012: PRF-0009 prova por teste sem declarar a superfície")

    def test_36_superficie_de_repositorio_inteiro_e_recusada(self):
        # "." e "src" morrem antes, no schema (minLength); "tests/" e curinga,
        # na FIT-012. O que importa e que NENHUMA delas passa.
        for ruim, marca in ((".", "is too short"), ("src", "VIOLAÇÃO NOVA FIT-012: PRF-0009 declara superfície"),
                            ("tests/", "VIOLAÇÃO NOVA FIT-012: PRF-0009 declara superfície"),
                            ("runtime/*.py", "VIOLAÇÃO NOVA FIT-012: PRF-0009 declara superfície"),
                            ("cv-backend-core/", "VIOLAÇÃO NOVA FIT-012: PRF-0009 declara superfície")):
            f = base()
            node(f, "PRF-0009")["mechanism"]["paths"] = [ruim]
            self.assertFails(f, marca)

    # FIT-011 — a contagem é por escala; escala bloqueada não conta
    def test_28_elo_provado_em_escala_bloqueada_nao_conta_naquela_escala(self):
        f = base()
        add(f, "07-proofs.yaml", {"id": "PRF-0090", "kind": "proof", "title": "elo 1 em REGIONAL",
                                  "proves": ["CLM-L1"], "basis": "external_observation",
                                  "external_observation": {"instrument": "psql + NATS", "observed": "fato gravado"},
                                  "evidence_artifact": {"repo": "r", "path": "docs/evidence/x.md"},
                                  "environment": "ephemeral", "scale": "REGIONAL", "date": "2026-09-22"})
        j, m = judge(f)
        self.assertEqual(j.errors, [], j.errors)
        self.assertEqual(m["claims"]["CLM-L1"]["status"], "PROVEN")          # a afirmação foi provada
        reg = m["chain_by_scale"]["REGIONAL"]
        self.assertTrue(reg["blocked_by"])                                    # mas REGIONAL está bloqueada
        self.assertEqual(reg["structural"], 0)                                # e a contagem REGIONAL fica 0
        self.assertEqual(reg["structural_if_unblocked"], 1)                   # o juiz diz o que HAVERIA

    def test_29_elo_provado_em_escala_livre_conta_naquela_escala(self):
        f = base()
        f["07-proofs.yaml"] = [p for p in f["07-proofs.yaml"] if "CLM-L1" not in (p.get("proves") or [])]
        antes_agregado, antes_local = cadeia(judge(f)[1])
        antes_regional = judge(f)[1]["chain_by_scale"].get("REGIONAL", {}).get("structural", 0)
        add(f, "07-proofs.yaml", {"id": "PRF-0091", "kind": "proof", "title": "elo 1 em LOCAL",
                                  "proves": ["CLM-L1"], "basis": "external_observation",
                                  "external_observation": {"instrument": "psql + NATS", "observed": "fato gravado"},
                                  "evidence_artifact": {"repo": "r", "path": "docs/evidence/x.md"},
                                  "environment": "ephemeral", "scale": "LOCAL", "date": "2026-09-22"})
        j, m = judge(f)
        self.assertEqual(j.errors, [], j.errors)
        # o elo 1 volta a contar em LOCAL, e só lá: a entrada é posição 0
        self.assertEqual(cadeia(m)[1], antes_local + 1)
        self.assertEqual(m["chain_by_scale"]["LOCAL"]["substantive"], 0)
        self.assertEqual(m["chain_by_scale"].get("REGIONAL", {}).get("structural", 0), antes_regional)

    def test_30_prova_de_elo_sem_escala_e_violacao(self):
        f = base()
        add(f, "07-proofs.yaml", {"id": "PRF-0092", "kind": "proof", "title": "elo 1 sem escala",
                                  "proves": ["CLM-L1"], "basis": "external_observation",
                                  "external_observation": {"instrument": "i", "observed": "o"},
                                  "evidence_artifact": {"repo": "r", "path": "p"},
                                  "environment": "ephemeral", "date": "2026-09-22"})
        self.assertFails(f, "VIOLAÇÃO NOVA FIT-011: PRF-0092 prova elo da cadeia sem declarar a escala")

    def test_31_escala_fora_do_enum_da_constituicao_e_violacao(self):
        f = base()
        node(f, "PRF-0002")["scale"] = "MUNICIPAL"
        self.assertFails(f, "VIOLAÇÃO NOVA FIT-011: PRF-0002 declara scale 'MUNICIPAL', fora do enum federativo")

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
                                  "mechanism": {"repo": "ANCHOR.OS", "paths": ["tests/test_x.py"],
                                                "content_hash": "b" * 64, "commit": "abc1234"},
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
        # Dívida no código (FIT-009 -> CLM-0011) só se sustenta com refutação
        # VIGENTE. Cenário: a dívida está no livro e alguém apaga a refutação
        # (e as provas que a supersediam) em vez de superseder: CLM-0011 vira
        # UNPROVEN e a catraca acusa a dívida obsoleta.
        f = base()
        add(f, "10-violations.yaml", {"id": "VIO-0098", "kind": "violation", "fitness": "FIT-009",
                                      "detection": "code", "observed": "x", "tracked_in": {"repo": "r"}})
        f["07-proofs.yaml"] = [p for p in f["07-proofs.yaml"] if p["id"] not in ("PRF-0007", "PRF-0012", "PRF-0013")]
        j, m = judge(f)
        self.assertEqual(m["claims"]["CLM-0011"]["status"], "UNPROVEN")
        self.assertFails(f, "DÍVIDA OBSOLETA VIO-0098")
        # e com a refutação superseded (o estado real pós-G5), a dívida também é obsoleta
        g = base()
        add(g, "10-violations.yaml", {"id": "VIO-0098", "kind": "violation", "fitness": "FIT-009",
                                      "detection": "code", "observed": "x", "tracked_in": {"repo": "r"}})
        self.assertFails(g, "DÍVIDA OBSOLETA VIO-0098")

    def test_27_o_genoma_real_registra_a_primeira_refutacao_desfeita(self):
        # G5: CLM-0011 foi REFUTED por PRF-0007 e é TESTED por PRF-0012, que a
        # supersede. A PRF-0007 continua no grafo. Nenhuma dívida no livro.
        j, m = judge(base())
        self.assertEqual(j.errors, [])
        self.assertEqual(m["claims"]["CLM-0011"]["status"], "TESTED")
        self.assertIn(("PRF-0007", "PRF-0012"), [tuple(x) for x in m["proofs_superseded"]])
        # A divida do livro que importa AQUI e a ligada a FIT-009/CLM-0011 —
        # nenhuma. Exigir o livro INTEIRO vazio afirmaria o estado do genoma, e
        # apodreceu assim que a FIT-018 registrou a divida das condicionais em
        # prosa. (O `and` entre os dois assertEqual era bug: assertEqual devolve
        # None, entao o segundo nunca rodava.)
        self.assertEqual([d for d in m["debt_known"] if d[0] == "FIT-009"], [])
        self.assertEqual([d for d in m["debt_code"] if d[1] == "FIT-009"], [])

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

    # O genoma real não tem dívida desde o G5: as mutações da catraca CRIAM a dívida.
    def test_03_valor_fora_da_dimensao_sem_divida_no_livro_e_violacao_nova(self):
        f = base()
        node(f, "liceu.anchor.authorization@1.1.0")["implementation_observed"] = {"legal_coverage": ["REFERENCED"]}
        self.assertFails(f, "VIOLAÇÃO NOVA FIT-006")

    def test_04_proposta_nao_e_usada_como_autoritativa(self):
        f = base()
        node(f, "SCR-05")["used_by"][0]["used_as"] = "authoritative_decision"
        self.assertFails(f, "VIOLAÇÃO NOVA FIT-004")

    def test_05_teste_sozinho_nao_prova_elo(self):
        f = base()
        # tira as provas que JA sustentam o elo 1: o que se mede aqui e o que um
        # teste, SOZINHO, faz — e nao o que o genoma ja tem
        f["07-proofs.yaml"] = [p for p in f["07-proofs.yaml"] if "CLM-L1" not in (p.get("proves") or [])]
        antes, _ = cadeia(judge(f)[1])
        add(f, "07-proofs.yaml", {"id": "PRF-0099", "kind": "proof", "title": "teste do elo 1",
            "proves": ["CLM-L1"], "basis": "test",
            "test": {"repo": "x", "path": "t.py"}, "scale": "LOCAL", "date": "2026-09-22",
            "mechanism": {"repo": "x", "paths": ["app/t.py"], "content_hash": "a" * 64, "commit": "abc1234"}})
        j, m = judge(f)
        self.assertEqual(j.errors, [])
        self.assertEqual(m["claims"]["CLM-L1"]["status"], "TESTED")
        self.assertEqual(cadeia(m)[0], antes, "teste sem observação externa não conta elo")

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
        add(f, "10-violations.yaml", {"id": "VIO-0099", "kind": "violation", "fitness": "FIT-006",
                                      "detection": "genome",
                                      "subject": "liceu.anchor.authorization@1.1.0/legal_coverage/REFERENCED",
                                      "observed": "x", "tracked_in": {"repo": "r"}})
        self.assertFails(f, "DÍVIDA OBSOLETA VIO-0099")

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


class Freio(unittest.TestCase):
    """O freio da H6: a maquinaria crescendo sem a cadeia andar."""

    def test_45_tres_crescimentos_sem_numerador_disparam_o_aviso(self):
        serie = [("c0", 20, 0), ("c1", 21, 0), ("c2", 23, 0), ("c3", 26, 0)]
        aviso = gc.growth_verdict(serie)
        self.assertIsNotNone(aviso)
        self.assertEqual(aviso["denominador"], [20, 21, 23, 26])
        self.assertEqual(aviso["de"], "c0")

    def test_46_numerador_andando_nao_dispara(self):
        self.assertIsNone(gc.growth_verdict([("c0", 20, 0), ("c1", 21, 0), ("c2", 23, 1), ("c3", 26, 1)]))

    def test_47_denominador_parado_nao_dispara(self):
        self.assertIsNone(gc.growth_verdict([("c0", 20, 0), ("c1", 21, 0), ("c2", 21, 0), ("c3", 26, 0)]))

    def test_48_serie_curta_nao_dispara(self):
        self.assertIsNone(gc.growth_verdict([("c0", 20, 0), ("c1", 21, 0), ("c2", 23, 0)]))

    def test_49_denominador_e_maquinaria_nao_registro(self):
        # fitness + tipos de no; claim/proof/unknown/violation NAO contam —
        # contar registro puniria o pre-registro honesto (a CLM-0015 foi um)
        fit = yaml.safe_dump([{"id": "FIT-001", "kind": "fitness"}, {"id": "FIT-002", "kind": "fitness"}])
        sch = json.dumps({"$defs": {"claim": {"properties": {"kind": {}}},
                                    "proof": {"properties": {"kind": {}}},
                                    "source": {"properties": {"repo": {}}}}})
        self.assertEqual(gc.machinery_of(fit, sch), (2, 2))


class ControlePositivo(unittest.TestCase):
    def test_15_prova_real_faz_a_contagem_subir(self):
        f = base()
        f["07-proofs.yaml"] = [p for p in f["07-proofs.yaml"] if "CLM-L1" not in (p.get("proves") or [])]
        antes_agregado, antes_local = cadeia(judge(f)[1])
        add(f, "07-proofs.yaml", {"id": "PRF-0097", "kind": "proof",
            "title": "elo 1 observado", "proves": ["CLM-L1"], "basis": "external_observation",
            "external_observation": {"instrument": "connz + subscriber",
                                     "observed": "archimedes.planning-state na tabela events"},
            "evidence_artifact": {"repo": "x", "path": "docs/evidence/e.md"},
            "environment": "durable", "scale": "LOCAL", "date": "2026-09-22"})
        j, m = judge(f)
        self.assertEqual(j.errors, [])
        self.assertEqual(m["claims"]["CLM-L1"]["status"], "PROVEN")
        self.assertEqual(cadeia(m)[0], antes_agregado + 1,
                         "com prova externa real, a cadeia tem de SUBIR um elo")
        self.assertEqual(cadeia(m)[1], antes_local + 1,
                         "e a contagem POR ESCALA tem de subir em LOCAL (FIT-011)")


class CondicionalEmProsa(unittest.TestCase):
    """FIT-018 — a prosa do contrato nao alcanca maquina nenhuma.

    A B3 pagou para aprender isto: `confidence obrigatorio quando kind =
    FORECAST` so existia em `domain_invariants`, e o gerador de vetores, que le
    o payload_schema, acusava o CEFEIDA por obedecer o contrato.
    """

    def assertFails(self, files, contains, registry=None):
        j, _ = judge(files, registry)
        self.assertTrue(any(contains in e for e in j.errors),
                        f"esperava erro com {contains!r}; veio {j.errors}")

    @staticmethod
    def _contrato(invariantes, esquema):
        reg = copy.deepcopy(KIT_REGISTRY)
        reg["contracts"]["liceu.teste.condicional"] = {"1.0.0": {
            "owner": "liceu.cefeida", "status": "ACTIVE",
            "domain_invariants": invariantes, "payload_schema": esquema}}
        return reg

    ESQUEMA_SEM = {"type": "object", "required": ["kind"],
                   "properties": {"kind": {"type": "string"},
                                  "confidence": {"type": "number"}}}

    def test_65_condicional_so_na_prosa_e_violacao_nova(self):
        reg = self._contrato(["confidence obrigatorio quando kind = FORECAST"],
                             self.ESQUEMA_SEM)
        self.assertFails(base(), "VIOLAÇÃO NOVA FIT-018: liceu.teste.condicional@1.0.0: "
                                 "'confidence' é exigido condicionalmente só na prosa",
                         registry=reg)

    def test_66_condicional_no_esquema_nao_e_violacao(self):
        """O outro lado: com `if`/`then` nomeando o campo, o juiz cala."""
        esquema = dict(self.ESQUEMA_SEM)
        esquema["allOf"] = [{"if": {"properties": {"kind": {"const": "FORECAST"}}},
                             "then": {"required": ["confidence"]}}]
        reg = self._contrato(["confidence obrigatorio quando kind = FORECAST"], esquema)
        j, _ = judge(base(), reg)
        self.assertEqual([e for e in j.errors if "FIT-018" in e], [], j.errors)

    def test_67_condicional_de_OUTRO_campo_no_esquema_nao_cobre(self):
        """O caso real da planning-proposal: ela TEM um `allOf`, para study_basis,
        e mesmo assim deixa `crs` so na prosa. A pergunta e por CAMPO."""
        esquema = dict(self.ESQUEMA_SEM)
        esquema["properties"] = dict(esquema["properties"], crs={"type": "string"})
        esquema["allOf"] = [{"if": {"properties": {"kind": {"const": "FORECAST"}}},
                             "then": {"required": ["confidence"]}}]
        reg = self._contrato(["confidence obrigatorio quando kind = FORECAST",
                              "crs obrigatorio quando ha geometria"], esquema)
        self.assertFails(base(), "VIOLAÇÃO NOVA FIT-018: liceu.teste.condicional@1.0.0: "
                                 "'crs' é exigido condicionalmente só na prosa", registry=reg)

    def test_68_prosa_que_nomeia_campo_inexistente_e_acusada(self):
        reg = self._contrato(["certeza obrigatorio quando kind = FORECAST"], self.ESQUEMA_SEM)
        self.assertFails(base(), "o invariante condicional começa por 'certeza', que não é "
                                 "campo do payload_schema", registry=reg)

    def test_69_vocabulario_estreito_nao_acusa_quem_fez_certo(self):
        """A liceu.legal.admissibility diz, na propria prosa, "codificado no
        schema (if/then), nao em prosa", e o esquema tem o `allOf`. Um detector
        que acusasse quem fez certo ensinaria a ignora-lo."""
        j, _ = judge(base())
        self.assertEqual(
            [e for e in j.errors if "FIT-018" in e and "admissibility" in e], [], j.errors)

    # A excecao do RETIRED (decisao do titular, 2026-09-23). Ela e uma FRESTA
    # na fitness, e fresta sem teste vira buraco: estes quatro fixam o tamanho
    # exato dela.
    def test_71_versao_RETIRED_com_condicional_so_na_prosa_nao_e_divida(self):
        reg = self._contrato(["confidence obrigatorio quando kind = FORECAST"],
                             self.ESQUEMA_SEM)
        reg["contracts"]["liceu.teste.condicional"]["1.0.0"]["status"] = "RETIRED"
        j, _ = judge(base(), reg)
        self.assertEqual([e for e in j.errors if "FIT-018" in e and "teste.condicional" in e],
                         [], j.errors)

    def test_72_o_que_a_fitness_deixa_de_cobrar_vira_AVISO(self):
        """Parar de contar nao pode virar parar de olhar."""
        reg = self._contrato(["confidence obrigatorio quando kind = FORECAST"],
                             self.ESQUEMA_SEM)
        reg["contracts"]["liceu.teste.condicional"]["1.0.0"]["status"] = "RETIRED"
        j, _ = judge(base(), reg)
        self.assertTrue(
            any("FIT-018 nao cobra liceu.teste.condicional@1.0.0 (RETIRED)" in w
                for w in j.warnings),
            f"a condicional de uma versao RETIRED tem de aparecer nos avisos; veio {j.warnings}")

    def test_73_DEPRECATED_nao_entra_na_excecao(self):
        """Contrato depreciado ainda pode ser usado: prosa que ninguem executa
        continua sendo o defeito. A excecao e so para o que ja morreu."""
        reg = self._contrato(["confidence obrigatorio quando kind = FORECAST"],
                             self.ESQUEMA_SEM)
        reg["contracts"]["liceu.teste.condicional"]["1.0.0"]["status"] = "DEPRECATED"
        self.assertFails(base(), "VIOLAÇÃO NOVA FIT-018: liceu.teste.condicional@1.0.0",
                         registry=reg)

    def test_74_versao_que_volta_de_RETIRED_volta_a_ser_cobrada(self):
        """A excecao e do ESTADO, e nao do contrato: se a versao reviver, a
        divida revive com ela."""
        reg = self._contrato(["confidence obrigatorio quando kind = FORECAST"],
                             self.ESQUEMA_SEM)
        reg["contracts"]["liceu.teste.condicional"]["1.0.0"]["status"] = "ACTIVE"
        self.assertFails(base(), "VIOLAÇÃO NOVA FIT-018: liceu.teste.condicional@1.0.0",
                         registry=reg)

    def test_70_divida_paga_e_nao_removida_do_livro_falha(self):
        """A catraca no outro sentido: pagar a divida no contrato e deixar a
        linha no livro faz o juiz acusar DIVIDA OBSOLETA — o livro nao vira
        ficcao de um defeito ja corrigido.

        O teste monta a PROPRIA divida, e nao depende do livro real. Ja mudou
        duas vezes por isso: citava a VIO-0009 e apodreceu quando ela foi paga;
        passou a usar a primeira do livro e apodreceu quando o livro zerou.
        Teste que depende do estado do genoma mede o estado, nao a regra.
        """
        esquema_pago = dict(self.ESQUEMA_SEM)
        esquema_pago["allOf"] = [{"if": {"properties": {"kind": {"const": "FORECAST"}},
                                         "required": ["kind"]},
                                  "then": {"required": ["confidence"]}}]
        # o contrato JA esta pago...
        reg = self._contrato(["confidence obrigatorio quando kind = FORECAST"], esquema_pago)
        # ...e a divida continua no livro
        f = base()
        add(f, "10-violations.yaml", {
            "id": "VIO-0099", "kind": "violation", "fitness": "FIT-018",
            "detection": "genome", "subject": "liceu.teste.condicional@1.0.0/confidence",
            "observed": "condicional so na prosa", "tracked_in": {"repo": "liceu-protocol"}})
        j, _ = judge(f, reg)
        self.assertTrue(any("DÍVIDA OBSOLETA VIO-0099" in e for e in j.errors),
                        f"esperava DIVIDA OBSOLETA; veio {j.errors}")

    def test_75_o_livro_da_FIT_018_vazio_nao_desarma_a_catraca(self):
        """O livro zerou em 2026-09-23. Livro vazio nao pode virar fitness
        dormindo: uma condicional nova, so na prosa, tem de FALHAR."""
        reg = self._contrato(["confidence obrigatorio quando kind = FORECAST"],
                             self.ESQUEMA_SEM)
        self.assertFails(base(), "VIOLAÇÃO NOVA FIT-018: liceu.teste.condicional@1.0.0",
                         registry=reg)


class YamlQuePerdeEmSilencio(unittest.TestCase):
    """O `lint` guarda os dois defeitos que o YAML comete CALADO e que o schema
    nunca ve. Aqui o grafo E o arquivo: um no perdido em silencio faria o juiz
    julgar um genoma que nao e o que esta escrito.

    O leitor estrito vem do KIT (ADR-001), e nao de uma copia local: duas
    implementacoes do que conta como YAML valido seriam duas verdades.
    """

    def escrever(self, texto):
        d = Path(tempfile.mkdtemp())
        (d / "00-meta.yaml").write_text(texto, encoding="utf-8")
        return d

    def test_chave_duplicada_e_recusada_antes_de_qualquer_regra(self):
        d = self.escrever("- id: X\n  kind: claim\n  statement: primeiro\n  statement: segundo\n")
        try:
            problemas = gc.lint(d)
            self.assertTrue(any("chave duplicada 'statement'" in p for p in problemas), problemas)
            self.assertTrue(any(":4:" in p for p in problemas),
                            f"tem de apontar a LINHA da segunda ocorrencia; veio {problemas}")
        finally:
            shutil.rmtree(d)

    def test_o_safe_load_perderia_o_primeiro_em_silencio(self):
        """Sem este caso, o de cima provaria que o lint novo funciona — mas nao
        que havia o que consertar."""
        frouxo = yaml.safe_load("- id: X\n  statement: primeiro\n  statement: segundo\n")
        self.assertEqual(frouxo[0]["statement"], "segundo")

    def test_ancora_de_fusao_nao_e_duplicata(self):
        """O grafo usa `<<: *ancora`. Um lint que a recusasse pararia o juiz —
        foi o que a v0.22.0 do kit fazia."""
        d = self.escrever("- &b\n  id: A\n  kind: claim\n- <<: *b\n  id: B\n")
        try:
            self.assertEqual([p for p in gc.lint(d) if "duplicada" in p], [])
        finally:
            shutil.rmtree(d)

    def test_o_genoma_real_carrega_limpo(self):
        self.assertEqual([p for p in gc.lint(ROOT / "genome") if "duplicada" in p], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
