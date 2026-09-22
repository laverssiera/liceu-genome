#!/usr/bin/env python3
"""
genome_check — o juiz do Genoma LICEU 6.0.

Um grafo, uma lei, um juiz:
  1. valida cada nó contra o schema, pelo seu 'kind'
  2. resolve cada aresta (referência a outro nó)
  3. DERIVA o status de cada afirmação a partir das provas VIGENTES — nunca o lê.
     Uma prova refuta ou prova o código de um commit; quando o código muda,
     uma prova nova a SUPERSEDE. Só as vigentes (as que nenhuma outra
     supersede) derivam; as superseded ficam como história. Prova nunca é
     apagada — apagar é reescrever a história.
  4. avalia as fitness functions de genoma
  5. aplica a catraca do livro de dívida
  6. responde às perguntas do Self-Model

Saída 0: genoma íntegro e nenhuma violação nova.
Saída 1: erro de schema, aresta quebrada, violação nova ou dívida obsoleta.

Uso:
  genome_check.py [--genome DIR] [--schema FILE] [--json FILE] [--html FILE]
                  [--kit-registry FILE]

O Contract Registry do kit (pacote liceu-protocol, instalado na tag vigente)
é a fonte de produtor, versão e lifecycle de cada contrato. O genoma NÃO os
copia como verdade própria: a FIT-010 confere o que o genoma diz contra o
que o kit instalado diz, e divergência é violação. Sem o kit instalado o
juiz não julga (fail-closed) — um genoma julgado sem o kit não pode dizer
que está alinhado a ele.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
KIT_REGISTRY_FILE = "liceu_contract_registry.yaml"
AUTHORITATIVE_USES = {"authoritative_decision", "authoritative_budget",
                      "procurement_commitment", "physical_execution_authorization"}
EVIDENCE_FIELD = re.compile(r"(_refs|content_hash)$")
SCALE_REF = re.compile(r"^scale:[A-Z]+$")


# ─────────────────────────────────────────────────────────── carga
# O YAML trata " #" como início de comentário mesmo no meio de um valor sem aspas:
# "asserted_by: CORE #50" vira "asserted_by: CORE", em silêncio. O schema não vê,
# porque o valor truncado continua sendo uma string válida. O juiz vê.
SILENT_TRUNCATION = re.compile(r"""^\s*(?:-\s+)?[A-Za-z_][\w.-]*:\s+[^\s"'#|>{\[&*].*?\s#""")


def lint(genome_dir: Path) -> list[str]:
    problems = []
    for f in sorted(genome_dir.glob("*.yaml")):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if SILENT_TRUNCATION.match(line):
                problems.append(f"{f.name}:{i}: valor sem aspas contém ' #' — o YAML trunca em "
                                f"silêncio. Ponha o valor entre aspas: {line.strip()[:70]}")
    return problems


def load_kit_registry(path: Path | None = None) -> dict:
    """Contract Registry do kit instalado (ou de `path`, nos testes).

    Fail-closed: sem o pacote liceu-protocol não há registry e não há
    veredito. Vendorizar uma cópia aqui seria a segunda fonte da verdade
    que a FIT-010 existe para impedir.
    """
    if path is None:
        try:
            from liceu_protocol import KIT_DIR
        except ImportError as exc:
            raise SystemExit(
                "kit ausente: instale liceu-protocol na tag vigente (requirements.txt). "
                "O genoma não é julgado sem o Contract Registry do kit.") from exc
        path = Path(KIT_DIR) / KIT_REGISTRY_FILE
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if "contracts" not in data:
        raise SystemExit(f"{path}: não é um Contract Registry do kit (sem `contracts`)")
    return data


def load(genome_dir: Path) -> list[dict]:
    nodes = []
    for f in sorted(genome_dir.glob("*.yaml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or []
        for n in data:
            n = dict(n)
            n["__file"] = f.name
            nodes.append(n)
    return nodes


class Judge:
    def __init__(self, nodes: list[dict], schema: dict, registry: dict | None = None):
        self.nodes = nodes
        self.schema = schema
        # Contract Registry do kit: a fonte de produtor/versão/lifecycle (FIT-010).
        self.registry = registry if registry is not None else load_kit_registry()
        self.errors: list[str] = []      # falham a CI
        self.warnings: list[str] = []    # informam, não falham
        self.findings: list[tuple[str, str, str]] = []   # (fitness, subject, message)
        self.by_id: dict[str, dict] = {}
        self.kind: dict[str, list[dict]] = defaultdict(list)
        self.status: dict[str, str] = {}
        self.ephemeral: set[str] = set()

    # ─────────────────────────────────────────── 1. schema e índice
    def validate_schema(self):
        defs = self.schema["$defs"]
        for n in self.nodes:
            k = n.get("kind")
            body = {x: y for x, y in n.items() if x != "__file"}
            if k not in defs or "kind" not in defs[k].get("properties", {}):
                self.errors.append(f"{n['__file']}: kind desconhecido {k!r} em {n.get('id')}")
                continue
            sub = {"$defs": defs, **defs[k]}
            for e in sorted(Draft202012Validator(sub).iter_errors(body), key=str):
                path = "/".join(str(p) for p in e.absolute_path) or "(nó)"
                self.errors.append(f"{n['__file']}: {n.get('id')} [{k}] {path}: {e.message}")
            if n.get("id") in self.by_id:
                self.errors.append(f"id duplicado: {n.get('id')}")
            self.by_id[n.get("id")] = n
            self.kind[k].append(n)

    # ─────────────────────────────────────────── 2. arestas
    def ref(self, owner: str, target: str, kinds: tuple[str, ...]):
        t = self.by_id.get(target)
        if t is None:
            self.errors.append(f"{owner}: aresta quebrada -> {target!r} não existe")
            return None
        if t["kind"] not in kinds:
            self.errors.append(f"{owner}: {target!r} é {t['kind']}, esperado {'/'.join(kinds)}")
            return None
        return t

    def resolve_edges(self):
        dims = {d["id"]: d for d in self.kind["dimension"]}
        for d in self.kind["dimension"]:
            if d["defined_by"] != "genome":
                self.ref(d["id"], d["defined_by"], ("contract",))
        for c in self.kind["contract"]:
            self.ref(c["id"], c["producer"], ("monolith",))
            for x in c.get("carries", []):
                self.ref(c["id"], x, ("dimension",))
            for x in c.get("emitters_observed", []):
                self.ref(c["id"], x, ("monolith",))
            for x in c.get("implementation_observed", {}):
                self.ref(c["id"], x, ("dimension",))
            if "superseded_by" in c:
                self.ref(c["id"], c["superseded_by"], ("contract",))
        for s in self.kind["screen"]:
            sid = s["id"]
            self.ref(sid, s["journey"], ("knowledge",))
            self.ref(sid, s["owner_monolith"], ("monolith",))
            for l in s["used_by"] + s["ips_supported"]:
                self.ref(sid, l["ref"], ("knowledge",))
            for c in s["reads"]:
                self.ref(sid, c, ("contract",))
            for j in s["john_participation"]:
                self.ref(sid, j["john"], ("monolith",))
            if "ips_gap" in s:
                self.ref(sid, s["ips_gap"], ("unknown",))
            for dim, vals in s["displays"].items():
                d = self.ref(sid, dim, ("dimension",))
                for v in vals if d else []:
                    if v not in d["values"]:
                        self.errors.append(f"{sid}: exibe {dim}:{v}, valor fora da dimensão")
            for item in s["must_not_display"]:
                dim, _, val = item.partition(":")
                d = self.ref(sid, dim, ("dimension",))
                if d and val and val not in d["values"]:
                    self.errors.append(f"{sid}: must_not_display {item} fora da dimensão")
        for p in self.kind["proof"]:
            for c in p.get("proves", []) + p.get("refutes", []):
                self.ref(p["id"], c, ("claim",))
            for s in p.get("supersedes", []):
                if s == p["id"]:
                    self.errors.append(f"{p['id']}: supersede a si mesma")
                else:
                    self.ref(p["id"], s, ("proof",))
        # ciclo de supersessão: A supersede B, B supersede A (ou mais longo) —
        # nenhuma das duas seria vigente e nenhuma seria história. Recusado.
        succ = {p["id"]: [s for s in p.get("supersedes", []) if s in self.by_id] for p in self.kind["proof"]}
        state: dict[str, int] = {}

        def visit(n, trail):
            if state.get(n) == 2:
                return
            if state.get(n) == 1:
                cyc = trail[trail.index(n):] + [n]
                self.errors.append(f"ciclo de supersessão: {' -> '.join(cyc)}")
                return
            state[n] = 1
            for m in succ.get(n, []):
                visit(m, trail + [n])
            state[n] = 2

        for pid in succ:
            visit(pid, [])
        for f in self.kind["fitness"]:
            if f["evaluated_by"] == "runtime":
                self.ref(f["id"], f["claim"], ("claim",))
        for n in self.kind["claim"] + self.kind["unknown"]:
            for b in n.get("blocks", []):
                if not SCALE_REF.match(b):
                    self.ref(n["id"], b, tuple(self.kind))
        for v in self.kind["violation"]:
            self.ref(v["id"], v["fitness"], ("fitness",))
        if len(self.kind["meta"]) != 1:
            self.errors.append(f"o genoma precisa de exatamente um nó meta; há {len(self.kind['meta'])}")
        meta = self.kind["meta"][0] if self.kind["meta"] else None
        if meta:
            for c in self.kind["contract"]:
                pos = c.get("chain_position")
                if pos is not None and pos > meta["chain_positions"]:
                    self.errors.append(f"{c['id']}: posição {pos} além de {meta['chain_positions']}")

    # ─────────────────────────────────────────── 3. derivação
    def derive(self):
        # Vigente = nenhuma outra prova a supersede. Só vigentes derivam.
        self.superseded_by: dict[str, str] = {}
        for p in self.kind["proof"]:
            for s in p.get("supersedes", []):
                self.superseded_by[s] = p["id"]
        proving, refuting = defaultdict(list), defaultdict(list)
        self.history: dict[str, list[dict]] = defaultdict(list)   # claim -> provas, vigentes ou não
        for p in self.kind["proof"]:
            current = p["id"] not in self.superseded_by
            for c in p.get("proves", []):
                self.history[c].append(p)
                if current:
                    proving[c].append(p)
            for c in p.get("refutes", []):
                self.history[c].append(p)
                if current:
                    refuting[c].append(p)
        for c in self.kind["claim"]:
            cid = c["id"]
            if refuting[cid]:
                self.status[cid] = "REFUTED"
            elif any(p["basis"] == "external_observation" for p in proving[cid]):
                self.status[cid] = "PROVEN"
                if all(p.get("environment") == "ephemeral" for p in proving[cid]
                       if p["basis"] == "external_observation"):
                    self.ephemeral.add(cid)
            elif any(p["basis"] == "test" for p in proving[cid]):
                self.status[cid] = "TESTED"
            else:
                self.status[cid] = "UNPROVEN"

    def verdict_of(self, p: dict) -> str:
        if p.get("refutes"):
            return "REFUTED"
        return "PROVEN" if p["basis"] == "external_observation" else "TESTED"

    def claim_history(self, cid: str) -> list[str]:
        """A história de uma afirmação: 'REFUTED por PRF-0007 até 22/09; TESTED por PRF-0012 desde então'."""
        out = []
        for p in sorted(self.history.get(cid, []), key=lambda x: (str(x.get("date")), x["id"])):
            nxt = self.superseded_by.get(p["id"])
            if nxt:
                until = self.by_id[nxt].get("date")
                out.append(f"{self.verdict_of(p)} por {p['id']} até {until} (superseded por {nxt})")
            else:
                out.append(f"{self.verdict_of(p)} por {p['id']} desde {p.get('date')}")
        return out

    # ─────────────────────────────────────────── 4. fitness de genoma
    def find(self, fit: str, subject: str, msg: str):
        self.findings.append((fit, subject, msg))

    def fitness(self):
        mono = {m["id"]: m for m in self.kind["monolith"]}
        contracts = {c["id"]: c for c in self.kind["contract"]}
        dims = {d["id"]: d for d in self.kind["dimension"]}
        know = {k["id"]: k for k in self.kind["knowledge"]}

        # FIT-001 — emissor único
        for c in self.kind["contract"]:
            for e in c.get("emitters_observed", []):
                if e != c["producer"]:
                    self.find("FIT-001", f"{c['id']}/{e}",
                              f"{e} emite o evento de {c['producer']}")

        # FIT-004 — validade do conhecimento
        for k in self.kind["knowledge"]:
            if k["validity"] == "PROPOSTA":
                missing = AUTHORITATIVE_USES - set(k["prohibited_uses"])
                if missing:
                    self.find("FIT-004", f"{k['id']}/prohibited",
                              f"PROPOSTA sem proibir {sorted(missing)}")
            both = set(k["permitted_uses"]) & set(k["prohibited_uses"])
            if both:
                self.find("FIT-004", f"{k['id']}/overlap", f"uso permitido e proibido: {sorted(both)}")
        for s in self.kind["screen"]:
            for l in s["used_by"] + s["ips_supported"]:
                k = know.get(l["ref"])
                if not k:
                    continue
                if l["used_as"] not in k["permitted_uses"] or l["used_as"] in k["prohibited_uses"]:
                    self.find("FIT-004", f"{s['id']}/{l['ref']}/{l['used_as']}",
                              f"{s['id']} usa {l['ref']} ({k['validity']}) como {l['used_as']}")

        # FIT-006 — valores observados dentro da dimensão
        for c in self.kind["contract"]:
            for dim, vals in c.get("implementation_observed", {}).items():
                d = dims.get(dim)
                for v in vals if d else []:
                    if v not in d["values"]:
                        self.find("FIT-006", f"{c['id']}/{dim}/{v}",
                                  f"{c['id']} produz {dim}={v}, valor que a dimensão não tem")

        # FIT-007 — a tela só exibe o que declara
        for s in self.kind["screen"]:
            sid = s["id"]
            read = [contracts[c] for c in s["reads"] if c in contracts]
            carried = {d for c in read for d in c.get("carries", [])}
            producers = {c["producer"] for c in read}
            shown = set(s.get("shows_fields", []))
            banned = set(s["must_not_display"])
            for dim, vals in s["displays"].items():
                if dim not in carried:
                    self.find("FIT-007", f"{sid}/carries/{dim}",
                              f"{sid} exibe {dim}, que nenhum contrato lido transporta")
                if dim in banned or any(f"{dim}:{v}" in banned for v in vals):
                    self.find("FIT-007", f"{sid}/contradiction/{dim}",
                              f"{sid} exibe e proíbe {dim} ao mesmo tempo")
            if "decision_result" in s["displays"]:
                if not any(mono.get(p, {}).get("may_authorize") for p in producers):
                    self.find("FIT-007", f"{sid}/authority",
                              f"{sid} exibe resultado de autoridade sem ler contrato de quem pode autorizar")
            for r in s.get("required_display", []):
                if r not in s["displays"] and r not in shown:
                    self.find("FIT-007", f"{sid}/required/{r}", f"{sid} exige {r} e não o exibe")
            if s["evidence_required"] and not any(EVIDENCE_FIELD.search(f) for f in shown):
                self.find("FIT-007", f"{sid}/evidence", f"{sid} exige evidência e não exibe referência")
            if "confidence" in shown:
                if s["confidence_display"] == "never":
                    self.find("FIT-007", f"{sid}/confidence", f"{sid} proíbe confidence e o exibe")
                elif "method_version" not in shown:
                    self.find("FIT-007", f"{sid}/confidence",
                              f"{sid} exibe confidence sem method_version")
            if s["owner_monolith"] not in producers:
                self.find("FIT-007", f"{sid}/owner",
                          f"{sid} é de {s['owner_monolith']} e não lê contrato dele")

        # FIT-010 — o genoma não é a segunda fonte da verdade sobre contratos.
        # Para cada contrato com in_registry: true, produtor e lifecycle têm de
        # bater com o Contract Registry do kit instalado; contrato que o kit
        # tem e o genoma diz que não tem também diverge (o genoma ficou atrás).
        kit_contracts = self.registry.get("contracts") or {}
        kit_meta = self.registry.get("meta") or {}
        for c in self.kind["contract"]:
            cid, _, version = c["id"].partition("@")
            kit_versions = kit_contracts.get(cid) or {}
            kit = kit_versions.get(version)
            if c["in_registry"]:
                if kit is None:
                    self.find("FIT-010", f"{c['id']}/in_registry",
                              f"{c['id']} diz in_registry mas o kit {kit_meta.get('registry_version')} "
                              f"não tem essa versão (tem {sorted(kit_versions) or 'nenhuma'})")
                    continue
                if c["producer"] != kit.get("owner"):
                    self.find("FIT-010", f"{c['id']}/producer",
                              f"{c['id']} produtor {c['producer']} no genoma, {kit.get('owner')} no kit")
                if c.get("lifecycle") != kit.get("status"):
                    self.find("FIT-010", f"{c['id']}/lifecycle",
                              f"{c['id']} lifecycle {c.get('lifecycle')} no genoma, {kit.get('status')} no kit")
            elif kit is not None:
                self.find("FIT-010", f"{c['id']}/in_registry",
                          f"{c['id']} diz in_registry: false, mas o kit {kit_meta.get('registry_version')} "
                          f"já o tem ({kit.get('status')}) — o genoma ficou atrás do kit")

        # FIT-008 — contratos lidos existem e estão vigentes
        for s in self.kind["screen"]:
            for cid in s["reads"]:
                c = contracts.get(cid)
                if not c:
                    continue
                if c.get("lifecycle") == "RETIRED":
                    self.find("FIT-008", f"{s['id']}/{cid}", f"{s['id']} lê contrato aposentado {cid}")
                if not c["in_registry"]:
                    if s["implementation"]["status"] == "NOT_IMPLEMENTED":
                        self.warnings.append(
                            f"{s['id']} lê {cid}, que ainda não está no registry (tela não implementada)")
                    else:
                        self.find("FIT-008", f"{s['id']}/{cid}/registry",
                                  f"{s['id']} implementada lê {cid}, fora do registry")

    # ─────────────────────────────────────────── 5. catraca
    def ratchet(self):
        ledger = {(v["fitness"], v["subject"]): v for v in self.kind["violation"]
                  if v["detection"] == "genome"}
        found = {(f, s) for f, s, _ in self.findings}
        self.known, self.new = [], []
        for f, s, m in self.findings:
            (self.known if (f, s) in ledger else self.new).append((f, s, m))
        self.stale = [v for k, v in ledger.items() if k not in found]
        for f, s, m in self.new:
            self.errors.append(f"VIOLAÇÃO NOVA {f}: {m}  [{s}]")
        for v in self.stale:
            self.errors.append(f"DÍVIDA OBSOLETA {v['id']}: não é mais detectada — remova do livro")
        # Dívida detectada NO CÓDIGO liga-se a uma fitness de runtime, cuja
        # afirmação tem de estar REFUTED por prova vigente. Se a refutação foi
        # superseded (correção provada) ou apagada, a dívida está obsoleta —
        # e apagar a prova em vez de superseder não escapa da catraca.
        fitness = {f["id"]: f for f in self.kind["fitness"]}
        for v in self.kind["violation"]:
            if v["detection"] != "code":
                continue
            f = fitness.get(v["fitness"])
            claim = f.get("claim") if f else None
            if claim and self.status.get(claim) != "REFUTED":
                self.errors.append(
                    f"DÍVIDA OBSOLETA {v['id']}: {claim} está {self.status.get(claim)}, não REFUTED — "
                    f"a refutação que sustentava a dívida não vige; remova do livro (ou registre a prova)")

    # ─────────────────────────────────────────── 6. Self-Model
    def self_model(self) -> dict:
        meta = self.kind["meta"][0]
        claims = {c["id"]: c for c in self.kind["claim"]}
        n = meta["chain_positions"]
        links = {}
        for c in claims.values():
            cl = c.get("chain_link")
            if cl and cl["measure"] == "structural":
                links[cl["position"]] = c["id"]
        structural = sum(1 for p in range(1, n + 1)
                         if self.status.get(links.get(p)) == "PROVEN")
        substantive = sum(1 for c in claims.values()
                          if c.get("chain_link", {}).get("measure") == "substantive"
                          and 1 <= c["chain_link"]["position"] <= n
                          and self.status[c["id"]] == "PROVEN")
        entry = links.get(0)

        emitters = [(c["id"], c["emitters_observed"]) for c in self.kind["contract"]
                    if len(c.get("emitters_observed", [])) > 1]
        know = {k["id"]: k for k in self.kind["knowledge"]}
        proposta_screens = []
        for s in self.kind["screen"]:
            refs = [l["ref"] for l in s["used_by"] + s["ips_supported"]] + [s["journey"]]
            p = sorted({r for r in refs if know.get(r, {}).get("validity") == "PROPOSTA"})
            if p:
                proposta_screens.append((s["id"], p))
        regional = []
        for c in claims.values():
            if "scale:REGIONAL" in c.get("blocks", []) and self.status[c["id"]] != "PROVEN":
                regional.append((c["id"], self.status[c["id"]], c["statement"]))
        for u in self.kind["unknown"]:
            if "scale:REGIONAL" in u["blocks"]:
                regional.append((u["id"], "UNKNOWN", u["question"]))
        runtime_no_proof = [(f["id"], f["claim"], self.status.get(f["claim"]))
                            for f in self.kind["fitness"]
                            if f["evaluated_by"] == "runtime"
                            and self.status.get(f["claim"]) != "PROVEN"]
        return {
            "graph_version": meta["graph_version"],
            "kit_registry_version": (self.registry.get("meta") or {}).get("registry_version"),
            "chain": {"structural": structural, "substantive": substantive, "positions": n,
                      "entry": {"claim": entry, "status": self.status.get(entry),
                                "ephemeral": entry in self.ephemeral}},
            "claims": {c: {"status": self.status[c], "statement": claims[c]["statement"],
                           "ephemeral": c in self.ephemeral,
                           "history": self.claim_history(c)} for c in claims},
            "proofs_superseded": sorted(self.superseded_by.items()),
            "q_multi_emitter": emitters,
            "q_screens_on_proposta": proposta_screens,
            "q_blocks_regional": regional,
            "q_runtime_fitness_without_proof": runtime_no_proof,
            "unknowns": [(u["id"], u["question"], u["blocks"]) for u in self.kind["unknown"]],
            "debt_known": [(f, s, m) for f, s, m in self.known],
            "debt_code": [(v["id"], v["fitness"], v["observed"]) for v in self.kind["violation"]
                          if v["detection"] == "code"],
            "screens": [self.genealogy(s) for s in self.kind["screen"]],
        }

    def genealogy(self, s: dict) -> dict:
        know = {k["id"]: k for k in self.kind["knowledge"]}
        mono = {m["id"]: m for m in self.kind["monolith"]}
        return {
            "id": s["id"], "title": s["title"],
            "owner": s["owner_monolith"], "reads": s["reads"],
            "journey": (s["journey"], know.get(s["journey"], {}).get("validity")),
            "used_by": [(l["ref"], know.get(l["ref"], {}).get("title"),
                         know.get(l["ref"], {}).get("validity"), l["used_as"]) for l in s["used_by"]],
            "john": [(j["john"], j["role"]) for j in s["john_participation"]],
            "displays": s["displays"], "must_not": s["must_not_display"],
            "required": s.get("required_display", []),
            "evidence_required": s["evidence_required"],
            "confidence": s["confidence_display"],
            "ips": [(l["ref"], know.get(l["ref"], {}).get("validity")) for l in s["ips_supported"]],
            "ips_gap": s.get("ips_gap"),
            "authority": any(mono.get(self.by_id[c]["producer"], {}).get("may_authorize")
                             for c in s["reads"] if c in self.by_id),
            "implementation": s["implementation"]["status"],
        }

    def run(self):
        self.validate_schema()
        if self.errors:          # sem schema íntegro, o resto não tem chão
            return None
        self.resolve_edges()
        if self.errors:          # grafo partido: não há veredito sobre o que não existe
            return None
        self.derive()
        self.fitness()
        self.ratchet()
        return self.self_model()


# ─────────────────────────────────────────────────────────── relatório
def text_report(m: dict, j: Judge) -> str:
    L = []
    c = m["chain"]
    L.append("GENOMA LICEU 6.0 — Self-Model")
    L.append(f"grafo: {m['graph_version']}")
    L.append(f"kit:   contract registry {m['kit_registry_version']}")
    L.append("")
    L.append("CADEIA — derivada das provas, nunca declarada")
    L.append(f"  estrutural   {c['structural']}/{c['positions']}")
    L.append(f"  substantiva  {c['substantive']}/{c['positions']}")
    e = c["entry"]
    L.append(f"  entrada      {e['claim']} {e['status']}" + ("  (ambiente efêmero)" if e["ephemeral"] else ""))
    L.append("")
    L.append("AFIRMAÇÕES")
    for cid, v in m["claims"].items():
        flag = "  (efêmero)" if v["ephemeral"] else ""
        L.append(f"  {v['status']:9} {cid:9} {v['statement']}{flag}")
        if len(v["history"]) > 1 or any("superseded" in h for h in v["history"]):
            L.append(f"  {'':9} {'':9} história: " + "; ".join(v["history"]))
    L.append("")
    L.append("PERGUNTAS DO SELF-MODEL")
    L.append(f"  eventos com mais de um emissor ........ {len(m['q_multi_emitter'])}")
    for x in m["q_multi_emitter"]:
        L.append(f"    {x[0]}: {x[1]}")
    L.append(f"  fitness de runtime sem prova ........... {len(m['q_runtime_fitness_without_proof'])}")
    for f, cl, st in m["q_runtime_fitness_without_proof"]:
        L.append(f"    {f} -> {cl} {st}")
    L.append(f"  telas apoiadas só em PROPOSTA .......... {len(m['q_screens_on_proposta'])} de {len(m['screens'])}")
    L.append(f"  o que impede REGIONAL .................. {len(m['q_blocks_regional'])}")
    for x in m["q_blocks_regional"]:
        L.append(f"    {x[0]:9} {x[1]:9} {x[2]}")
    L.append("")
    L.append(f"INCÓGNITAS ({len(m['unknowns'])})")
    for u in m["unknowns"]:
        L.append(f"  {u[0]}  {u[1]}")
    L.append("")
    L.append("DÍVIDA")
    for f, s, msg in m["debt_known"]:
        L.append(f"  conhecida  {f}  {msg}")
    for vid, f, obs in m["debt_code"]:
        L.append(f"  no código  {f}  {obs}  [{vid}]")
    L.append("")
    if j.warnings:
        L.append("AVISOS")
        for w in j.warnings:
            L.append(f"  {w}")
        L.append("")
    L.append("RESULTADO: " + ("FALHOU" if j.errors else "ÍNTEGRO — nenhuma violação nova"))
    for e_ in j.errors:
        L.append(f"  ✗ {e_}")
    return "\n".join(L)


def html_report(m: dict, j: Judge) -> str:
    esc = html.escape
    c = m["chain"]
    tone = {"PROVEN": "ok", "TESTED": "at", "UNPROVEN": "no", "REFUTED": "bad"}

    def pill(st):
        return f'<span class="pill {tone.get(st, "no")}">{esc(st)}</span>'

    claims = "".join(
        f'<tr><td class="m">{esc(cid)}</td><td>{pill(v["status"])}'
        f'{"<span class=eph>efêmero</span>" if v["ephemeral"] else ""}</td>'
        f'<td>{esc(v["statement"])}</td></tr>' for cid, v in m["claims"].items())
    screens = ""
    for s in m["screens"]:
        disp = "".join(f'<div><span class="m">{esc(d)}</span> '
                       + " ".join(f'<span class="chip">{esc(x)}</span>' for x in v) + "</div>"
                       for d, v in s["displays"].items()) or '<span class="dim">nenhuma dimensão</span>'
        users = "".join(f'<div><span class="m">{esc(r)}</span> {esc(t or "")} '
                        f'<span class="pill no">{esc(v or "")}</span> '
                        f'<span class="dim">· {esc(u)}</span></div>' for r, t, v, u in s["used_by"])
        john = ", ".join(f"{a} · {b}" for a, b in s["john"]) or "nenhum"
        screens += f"""
<article class="scr">
  <header><span class="m">{esc(s['id'])}</span><h3>{esc(s['title'])}</h3>
    <span class="pill no">{esc(s['implementation'])}</span></header>
  <dl>
    <dt>dono</dt><dd class="m">{esc(s['owner'])}</dd>
    <dt>lê</dt><dd class="m">{esc(', '.join(s['reads']))}</dd>
    <dt>jornada</dt><dd><span class="m">{esc(s['journey'][0])}</span> <span class="pill no">{esc(s['journey'][1] or '')}</span></dd>
    <dt>usada por</dt><dd>{users}</dd>
    <dt>JOHN</dt><dd>{esc(john)}</dd>
    <dt>exibe</dt><dd>{disp}</dd>
    <dt>nunca exibe</dt><dd>{' '.join(f'<span class="chip bad">{esc(x)}</span>' for x in s['must_not'])}</dd>
    <dt>obrigatório</dt><dd class="m">{esc(', '.join(s['required']) or '—')}</dd>
    <dt>evidência</dt><dd>{'exigida' if s['evidence_required'] else 'não se aplica'} · confidence {esc(s['confidence'])}</dd>
    <dt>autoridade</dt><dd>{'pode exibir resultado — lê contrato de quem autoriza' if s['authority'] else 'não pode exibir resultado de autoridade'}</dd>
    <dt>IPS/CQP/CQM</dt><dd>{esc(', '.join(f'{r} ({v})' for r, v in s['ips'])) or f'sem mapeamento · <span class="m">{esc(s["ips_gap"] or "")}</span>'}</dd>
  </dl>
</article>"""
    unknowns = "".join(f'<li><span class="m">{esc(u[0])}</span> {esc(u[1])}</li>' for u in m["unknowns"])
    regional = "".join(f'<li><span class="m">{esc(x[0])}</span> {pill(x[1])} {esc(x[2])}</li>'
                       for x in m["q_blocks_regional"])
    debt = "".join(f'<li>{pill("REFUTED")} <span class="m">{esc(f)}</span> {esc(msg)}</li>'
                   for f, s, msg in m["debt_known"])
    debt += "".join(f'<li>{pill("REFUTED")} <span class="m">{esc(f)}</span> {esc(o)} '
                    f'<span class="dim">[{esc(v)}]</span></li>' for v, f, o in m["debt_code"])
    verdict = "FALHOU" if j.errors else "ÍNTEGRO"
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Genoma LICEU 6.0 — Self-Model</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{{--bg:#0B0F14;--sf:#151B23;--ln:#263241;--mu:#64748B;--tx:#F8FAFC;
--ok:#16A34A;--at:#F59E0B;--bad:#DC2626;--ev:#7C3AED;
--sans:'Inter',system-ui,sans-serif;--mono:'IBM Plex Mono',ui-monospace,monospace;
box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}
@media (prefers-color-scheme:light){{:root:not([data-theme="dark"]){{--bg:#F8FAFC;--sf:#FFFFFF;--ln:#E2E8F0;--mu:#64748B;--tx:#0B0F14}}}}
:root[data-theme="light"]{{--bg:#F8FAFC;--sf:#FFFFFF;--ln:#E2E8F0;--mu:#64748B;--tx:#0B0F14}}
*{{box-sizing:border-box;margin:0}} body{{background:var(--bg);color:var(--tx);font:14px/1.55 var(--sans)}}
main{{max-width:1080px;margin:0 auto;padding:34px 22px 64px}}
.eyebrow{{font:11px var(--mono);color:var(--mu);letter-spacing:.04em}}
h1{{font-size:26px;letter-spacing:-.02em;margin:6px 0 4px}} h2{{font-size:15px;margin:36px 0 12px}}
h3{{font-size:14px;font-weight:600}} .lede{{color:var(--mu);max-width:64ch}}
.m{{font-family:var(--mono);font-size:12px}} .dim{{color:var(--mu)}}
.chain{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-top:20px}}
.stat{{background:var(--sf);border:1px solid var(--ln);border-radius:4px;padding:14px}}
.stat b{{display:block;font:600 34px/1 var(--mono);letter-spacing:-.03em}}
.stat span{{color:var(--mu);font-size:12px}}
.stat.zero b{{color:var(--bad)}}
table{{width:100%;border-collapse:collapse}} td{{padding:7px 8px;border-bottom:1px solid var(--ln);vertical-align:top}}
.tbl{{overflow-x:auto;background:var(--sf);border:1px solid var(--ln);border-radius:4px}}
.pill{{font:10px var(--mono);padding:2px 7px;border-radius:2px;border:1px solid;white-space:nowrap}}
.pill.ok{{color:var(--ok);border-color:color-mix(in srgb,var(--ok) 40%,transparent)}}
.pill.at{{color:var(--at);border-color:color-mix(in srgb,var(--at) 40%,transparent)}}
.pill.no{{color:var(--mu);border-color:var(--ln)}}
.pill.bad{{color:var(--bad);border-color:color-mix(in srgb,var(--bad) 40%,transparent)}}
.eph{{font:10px var(--mono);color:var(--at);margin-left:6px}}
.chip{{font:10.5px var(--mono);padding:1px 6px;border:1px solid var(--ln);border-radius:2px;display:inline-block;margin:1px}}
.chip.bad{{color:var(--bad)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}}
.scr{{background:var(--sf);border:1px solid var(--ln);border-top:2px solid var(--ev);border-radius:4px;padding:14px}}
.scr header{{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;margin-bottom:10px}}
.scr header h3{{flex:1;min-width:160px}}
dl{{display:grid;grid-template-columns:92px 1fr;gap:6px 10px;font-size:12.5px}} dt{{color:var(--mu)}}
ul{{padding-left:18px}} li{{margin:5px 0}}
.verdict{{font:600 12px var(--mono);padding:4px 10px;border-radius:2px;display:inline-block;margin-top:14px;
border:1px solid;color:{'var(--bad)' if j.errors else 'var(--ok)'}}}
footer{{margin-top:44px;padding-top:16px;border-top:1px solid var(--ln);color:var(--mu);font-size:12px;max-width:70ch}}
</style></head><body><main>
<p class="eyebrow">GENOMA LICEU 6.0 · SELF-MODEL · grafo {esc(m['graph_version'])}</p>
<h1>O que o LICEU consegue provar sobre si mesmo.</h1>
<p class="lede">Gerado pelo validador a partir do genoma. Nada aqui é escrito à mão: o status de cada
afirmação é derivado das provas, e a contagem da cadeia não pode ser declarada.</p>
<span class="verdict">{verdict} · {len(j.errors)} erro(s) · {len(m['debt_known']) + len(m['debt_code'])} dívida(s) conhecida(s)</span>
<div class="chain">
  <div class="stat {'zero' if c['structural']==0 else ''}"><b>{c['structural']}/{c['positions']}</b><span>cadeia estrutural</span></div>
  <div class="stat {'zero' if c['substantive']==0 else ''}"><b>{c['substantive']}/{c['positions']}</b><span>cadeia substantiva</span></div>
  <div class="stat"><b>{sum(1 for v in m['claims'].values() if v['status']=='PROVEN')}</b><span>afirmações provadas</span></div>
  <div class="stat"><b>{len(m['unknowns'])}</b><span>incógnitas declaradas</span></div>
</div>
<h2>Afirmações e o status que as provas permitem</h2>
<div class="tbl"><table>{claims}</table></div>
<h2>O que impede a escala REGIONAL</h2><ul>{regional}</ul>
<h2>Genealogia das cinco telas da vertical</h2><div class="grid">{screens}</div>
<h2>O que o LICEU sabe que não sabe</h2><ul>{unknowns}</ul>
<h2>Dívida registrada</h2><ul>{debt}</ul>
<footer>Uma lei (schema), um grafo (genoma), um juiz (genome_check). Violação nova falha a CI;
dívida registrada que deixou de ser detectada também falha. Para mudar este relatório, é preciso
mudar o genoma, e para promover uma afirmação é preciso registrar uma prova.</footer>
</main></body></html>"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--genome", default=str(ROOT / "genome"))
    ap.add_argument("--schema", default=str(ROOT / "schema" / "genome.schema.json"))
    ap.add_argument("--json")
    ap.add_argument("--html")
    ap.add_argument("--kit-registry", help="Contract Registry do kit; default: o do pacote liceu-protocol instalado")
    a = ap.parse_args(argv)
    schema = json.loads(Path(a.schema).read_text(encoding="utf-8"))
    registry = load_kit_registry(Path(a.kit_registry) if a.kit_registry else None)
    problems = lint(Path(a.genome))
    if problems:
        print("TRUNCAMENTO SILENCIOSO")
        for p in problems:
            print("  ✗", p)
        return 1
    j = Judge(load(Path(a.genome)), schema, registry)
    m = j.run()
    if m is None:
        print("GENOMA INVÁLIDO — schema ou arestas; o Self-Model não é calculado sobre grafo partido")
        for e in j.errors:
            print("  ✗", e)
        return 1
    print(text_report(m, j))
    if a.json:
        Path(a.json).write_text(json.dumps({"self_model": m, "errors": j.errors,
                                            "warnings": j.warnings}, ensure_ascii=False, indent=2))
    if a.html:
        Path(a.html).write_text(html_report(m, j), encoding="utf-8")
    return 1 if j.errors else 0


if __name__ == "__main__":
    sys.exit(main())
