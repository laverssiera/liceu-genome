#!/usr/bin/env python3
"""
genome_check — o juiz do Genoma LICEU 6.0.

Um grafo, uma lei, um juiz:
  1. valida cada nó contra o schema, pelo seu 'kind'
  2. resolve cada aresta (referência a outro nó)
  3. DERIVA o status de cada afirmação a partir das provas VIGENTES — nunca o lê.
     Vigente = nenhuma outra a supersede E não venceu (`expires_at`). Quando a
     única sustentação venceu, o status é STALE: "precisa ser provado de novo",
     nunca "é falso" — uma refatoração pode mudar o arquivo e manter o
     comportamento. STALE não conta na cadeia.
     A contagem da cadeia é POR ESCALA (FIT-011): cada prova de elo declara a
     escala do fato observado, e um elo provado numa escala BLOQUEADA não conta
     naquela escala. Sem isso, uma cadeia poderia "atravessar" em REGIONAL
     enquanto o próprio genoma declara REGIONAL bloqueada.
     Uma prova refuta ou prova o código de um commit; quando o código muda,
     uma prova nova a SUPERSEDE. Só as vigentes (as que nenhuma outra
     supersede) derivam; as superseded ficam como história. Prova nunca é
     apagada — apagar é reescrever a história.
  4. avalia as fitness functions de genoma — inclusive a origem de cada campo
     relatado (FIT-013): `derived` e conferido contra a fonte; `asserted` nao
     sustenta certeza, so divida e alerta
  5. aplica a catraca do livro de dívida
  6. responde às perguntas do Self-Model
  7. imprime o que o genoma deve a si mesmo: numerador (elos provados) contra
     denominador (MAQUINARIA — fitness + tipos de nó), e avisa quando a
     maquinaria cresce três merges seguidos sem a cadeia andar. Avisa; não
     falha. A decisão de parar é humana.

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
import datetime
import subprocess
from pathlib import Path

import genome_privacy_check
import genome_producer_hosting

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
KIT_REGISTRY_FILE = "liceu_contract_registry.yaml"
KIT_CONSTITUTION_FILE = "liceu_constitution.yaml"
SCALE_BLOCK = re.compile(r"^scale:([A-Z]+)$")
# Campos RELATADOS: foram digitados a partir de relato, nao observados. Cada um
# declara a origem (FIT-013). O nome "observed" era o primeiro erro.
REPORTED_FIELDS = {
    "contract": ("emitters_observed", "implementation_observed"),
    "monolith": ("teto_interno", "may_authorize", "may_decide"),
}
# Superficie de repositorio inteiro, ou curinga: proibida (FIT-012).
WHOLE_REPO = re.compile(r"^[./]*$|[*?]|^[^/]+/$|^(src|app|tests?|lib)$")
AUTHORITATIVE_USES = {"authoritative_decision", "authoritative_budget",
                      "procurement_commitment", "physical_execution_authorization"}
EVIDENCE_FIELD = re.compile(r"(_refs|content_hash)$")
SCALE_REF = re.compile(r"^scale:[A-Z]+$")
# O repositório do próprio genoma. Teste de regressão daqui o juiz abre; de
# outro repositório, quem confere é a CI de lá (tools/genome_pfc_check.py).
GENOME_REPO = "liceu-genome"

# FIT-018 — invariante CONDICIONAL que vive só na prosa do contrato.
# O vocabulário é ESTREITO de propósito, e o limite é declarado: só "quando" e
# "somente se", a forma que diz "o campo X é exigido SE tal coisa". Alargá-lo
# para "exige"/"proíbe" acusaria a liceu.legal.admissibility, cujos invariantes
# dizem eles mesmos "codificado no schema (if/then), nao em prosa" e cujo
# payload_schema tem o `allOf` — um detector que acusa quem fez certo ensina a
# ignorá-lo. Invariante escrito fora deste vocabulário escapa; isso é limite
# nomeado, não cobertura silenciosa.
COND_PROSA = re.compile(r"\bquando\b|\bsomente se\b", re.I)
COND_ESQUEMA = ("if", "then", "else", "allOf", "anyOf", "oneOf", "not",
                "dependentRequired")


def campos_sob_condicional(no, dentro: bool = False) -> set:
    """Nomes de campo que aparecem SOB construto condicional do payload_schema.

    Não basta o esquema ter um `if`: a planning-proposal tem `allOf` para
    study_basis e mesmo assim deixa `crs obrigatorio quando ha geometria` só na
    prosa. A pergunta é por CAMPO, não por contrato.
    """
    achados: set = set()
    if isinstance(no, dict):
        for k, v in no.items():
            if k in COND_ESQUEMA:
                achados |= campos_sob_condicional(v, True)
            elif dentro:
                if k == "required" and isinstance(v, list):
                    achados |= {str(x) for x in v}
                elif k == "properties" and isinstance(v, dict):
                    achados |= set(v)
                    for sub in v.values():
                        achados |= campos_sob_condicional(sub, True)
                else:
                    achados |= campos_sob_condicional(v, True)
    elif isinstance(no, list):
        for x in no:
            achados |= campos_sob_condicional(x, dentro)
    return achados


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


def load_scale_order(path: Path | None = None) -> dict[str, int]:
    """Enum federativo da escala, lido da CONSTITUIÇÃO do kit instalado.

    Uma definição: o genoma não reescreve o enum (mesma regra da FIT-010).
    Sem o kit não há veredito.
    """
    if path is None:
        try:
            from liceu_protocol import KIT_DIR
        except ImportError as exc:
            raise SystemExit(
                "kit ausente: instale liceu-protocol na tag vigente (requirements.txt). "
                "O enum de escala vive na Constituição do kit.") from exc
        path = Path(KIT_DIR) / KIT_CONSTITUTION_FILE
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    niveis = (((data.get("global") or {}).get("federation_scale") or {}).get("niveis")) or []
    order = {str(n["valor"]).upper(): int(n["ordem"]) for n in niveis if "valor" in n and "ordem" in n}
    if not order:
        raise SystemExit(f"{path}: Constituição sem global.federation_scale.niveis")
    return order


def growth_verdict(serie: list[tuple[str, int, int]]) -> dict | None:
    """`serie` vai do mais ANTIGO ao mais recente: (commit, denominador, numerador).

    Aviso quando a maquinaria cresceu em TRES passos seguidos e a cadeia nao
    andou em nenhum. Nao falha a CI: a decisao de parar e humana.
    """
    if len(serie) < 4:
        return None
    ultimos = serie[-4:]
    passos = list(zip(ultimos, ultimos[1:]))
    cresceu = all(b[1] > a[1] for a, b in passos)
    parado = all(b[2] <= a[2] for a, b in passos)
    if not (cresceu and parado):
        return None
    return {"de": ultimos[0][0], "ate": ultimos[-1][0],
            "denominador": [d for _, d, _ in ultimos], "numerador": [n for _, _, n in ultimos]}


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def machinery_of(fitness_yaml: str, schema_json: str) -> tuple[int, int]:
    """Denominador: fitness functions + tipos de no do schema. Maquinaria — regra
    e mecanismo —, nunca registro da realidade (claim, proof, unknown, violation
    ficam de fora: contar registro puniria o pre-registro honesto)."""
    fit = yaml.safe_load(fitness_yaml) or []
    defs = (json.loads(schema_json).get("$defs") or {})
    kinds = [k for k, v in defs.items() if "kind" in (v.get("properties") or {})]
    return len(fit), len(kinds)


def history_series(repo: Path, schema: dict, registry: dict, scale_order: dict,
                   producers: dict, n: int = 4) -> list[tuple[str, int, int]]:
    """Serie derivada do GIT — nada e gravado no repositorio: o git ja tem.

    Denominador de cada merge: parse de YAML/JSON via `git show`. Numerador: os
    NOS daquele commit passam pelo juiz ATUAL (uma implementacao da contagem, a
    daqui), sem validacao de schema — dado velho pode nao satisfazer a lei nova,
    e a contagem de entao continua sendo a contagem de entao.
    """
    linha = _git(repo, "log", "--first-parent", "-n", str(n), "--format=%H", "main").split()
    serie = []
    for commit in reversed(linha):
        try:
            fit = _git(repo, "show", f"{commit}:genome/08-fitness.yaml")
            sch = _git(repo, "show", f"{commit}:schema/genome.schema.json")
            if not fit or not sch:
                continue
            n_fit, n_kinds = machinery_of(fit, sch)
            nodes = []
            for nome in _git(repo, "ls-tree", "--name-only", f"{commit}:genome").split():
                if not nome.endswith(".yaml"):
                    continue
                for no in yaml.safe_load(_git(repo, "show", f"{commit}:genome/{nome}")) or []:
                    no = dict(no)
                    no["__file"] = nome
                    nodes.append(no)
            j = Judge(nodes, schema, registry, scale_order, producers)
            for no in nodes:
                j.by_id[no.get("id")] = no
                j.kind[no.get("kind")].append(no)
            j.derive()
            claims = {c["id"]: c for c in j.kind["claim"]}
            meta = j.kind["meta"][0] if j.kind["meta"] else {"chain_positions": 5}
            por_escala = j.chain_by_scale(meta["chain_positions"], claims)
            provados = max((v["structural"] for v in por_escala.values()), default=0)
            serie.append((commit[:7], n_fit + n_kinds, provados))
        except Exception:
            continue
    return serie


def load_kit_producers(path: Path | None = None) -> dict:
    """Producer Registry do kit instalado — fonte de teto e capacidades (FIT-013)."""
    if path is None:
        try:
            from liceu_protocol import KIT_DIR
        except ImportError as exc:
            raise SystemExit("kit ausente: instale liceu-protocol (requirements.txt).") from exc
        path = Path(KIT_DIR) / "liceu_producer_registry.yaml"
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if "producers" not in data:
        raise SystemExit(f"{path}: nao e um Producer Registry do kit (sem `producers`)")
    return data


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
    def __init__(self, nodes: list[dict], schema: dict, registry: dict | None = None,
                 scale_order: dict[str, int] | None = None, producer_registry: dict | None = None,
                 genome_dir: Path | None = None):
        self.nodes = nodes
        # O que o juiz VARRE e o que ele julga, nunca "o diretorio de sempre".
        self.genome_dir = Path(genome_dir) if genome_dir else ROOT / "genome"
        self.schema = schema
        # Contract Registry do kit: a fonte de produtor/versão/lifecycle (FIT-010).
        self.registry = registry if registry is not None else load_kit_registry()
        # Producer Registry: fonte de teto/capacidades para a FIT-013.
        self.producer_registry = producer_registry if producer_registry is not None else load_kit_producers()
        # Enum de escala: da Constituição do kit (FIT-011).
        self.scale_order = scale_order if scale_order is not None else load_scale_order()
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
    @staticmethod
    def _expired(p: dict, today: str) -> bool:
        exp = p.get("expires_at")
        return bool(exp) and str(exp) < today

    def derive(self, today: str | None = None):
        today = today or datetime.date.today().isoformat()
        self.today = today
        # Vigente = nenhuma outra prova a supersede E não venceu.
        self.superseded_by: dict[str, str] = {}
        self.expired = {p["id"] for p in self.kind["proof"] if self._expired(p, today)}
        for p in self.kind["proof"]:
            for s in p.get("supersedes", []):
                self.superseded_by[s] = p["id"]
        proving, refuting = defaultdict(list), defaultdict(list)
        self.history: dict[str, list[dict]] = defaultdict(list)   # claim -> provas, vigentes ou não
        had_any: dict[str, bool] = defaultdict(bool)
        for p in self.kind["proof"]:
            current = p["id"] not in self.superseded_by and p["id"] not in self.expired
            for c in p.get("proves", []) + p.get("refutes", []):
                had_any[c] = True
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
            elif had_any[cid]:
                # houve prova; nenhuma vige (vencida, ou superseded por uma que
                # venceu). Nao e UNPROVEN — e "prove de novo".
                self.status[cid] = "STALE"
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
            elif p["id"] in getattr(self, "expired", set()):
                out.append(f"{self.verdict_of(p)} por {p['id']} até {p['expires_at']} (evidência vencida — STALE)")
            else:
                out.append(f"{self.verdict_of(p)} por {p['id']} desde {p.get('date')}")
        return out

    # ─────────────────────────────────────────── 4. fitness de genoma
    def find(self, fit: str, subject: str, msg: str):
        self.findings.append((fit, subject, msg))

    @property
    def registry_producers(self) -> dict:
        """Producer Registry do kit — a fonte de teto e capacidades."""
        return (self.producer_registry or {}).get("producers") or {}

    @staticmethod
    def derived_value(kind: str, node: dict, campo: str, kit_producers: dict):
        """O valor que a FONTE dá para este campo, ou None quando o juiz não
        consegue conferir aqui (ex.: emitters, que dependem da tabela events)."""
        if kind != "monolith":
            return None
        entry = kit_producers.get(node["id"]) or {}
        if campo == "teto_interno":
            return (entry.get("teto") or {}).get("teto_interno")
        if campo in ("may_authorize", "may_decide"):
            valor = (entry.get("capabilities") or {}).get(campo)
            return valor if isinstance(valor, list) else None
        return None

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

        # FIT-015 — o genoma é PÚBLICO. Dado pessoal que entrar fica na internet,
        # e a P-001 é a casa de uma pessoa real. Parâmetro pode; identificação, não.
        for achado in genome_privacy_check.scan(self.genome_dir):
            arquivo = achado.split(":", 1)[0]
            self.find("FIT-015", f"privacidade/{arquivo}",
                      f"dado pessoal em repositório público: {achado}")

        # FIT-017 — produtor sem repositório declara ONDE está, para o juiz.
        # A regra e os testes dela vivem em tools/genome_producer_hosting.py, e
        # não aqui: o `mechanism` da PRF-0031 cobria este arquivo inteiro, então
        # toda fitness nova invalidava uma prova que não tinha mudado. A FIT-012
        # proíbe superfície de repositório inteiro pelo mesmo motivo; 1500 linhas
        # que crescem a cada ciclo são o mesmo defeito em escala menor.
        for subject, msg in genome_producer_hosting.achados(self.registry_producers):
            self.find("FIT-017", subject, msg)

        # FIT-018 — prosa não é executável. Um invariante CONDICIONAL escrito
        # em `domain_invariants` e ausente do `payload_schema` não alcança
        # ninguém: o gerador de vetores lê o esquema e produz payload que o
        # contrato proíbe; o boundary valida o esquema e deixa passar o que o
        # contrato proíbe; o produtor implementa a prosa e fica sozinho. Foi
        # exatamente isso na B3 — "confidence obrigatorio quando kind =
        # FORECAST" acusava o CEFEIDA, que estava certo (PRF-0036).
        #
        # A pergunta é por CAMPO. Ter `allOf` no esquema não basta: a
        # planning-proposal tem um, para study_basis, e mesmo assim deixa `crs`
        # só na prosa.
        for cid, versoes in (self.registry.get("contracts") or {}).items():
            for versao, entrada in (versoes or {}).items():
                if not isinstance(entrada, dict):
                    continue
                # Versao RETIRED nao alcanca produtor nenhum: ninguem pode
                # publicar nela, e reescrever o payload_schema de uma versao
                # aposentada seria mudar o que ja foi publicado. Cobrar dela e
                # divida que nao tem conserto — e divida sem conserto ensina a
                # ignorar o livro.
                #
                # DEPRECATED NAO entra nesta excecao: contrato depreciado ainda
                # pode ser usado, e prosa que ninguem executa continua sendo o
                # defeito. A excecao e so para o que ja morreu.
                #
                # E nao e pular calado: o que se deixa de cobrar vira AVISO, com
                # a linha inteira. Parar de contar nao pode virar parar de olhar.
                if str(entrada.get("status") or "").upper() == "RETIRED":
                    for inv in (entrada.get("domain_invariants") or []):
                        if COND_PROSA.search(str(inv)):
                            self.warnings.append(
                                f"FIT-018 nao cobra {cid}@{versao} (RETIRED), e a condicional "
                                f"continua so na prosa: {str(inv)!r}")
                    continue
                esquema = entrada.get("payload_schema") or {}
                campos = set(esquema.get("properties") or {})
                cobertos = campos_sob_condicional(esquema)
                for inv in (entrada.get("domain_invariants") or []):
                    texto = str(inv)
                    if not COND_PROSA.search(texto):
                        continue
                    # O invariante nomeia o campo exigido primeiro: "confidence
                    # obrigatorio quando ...", "crs obrigatorio quando ...".
                    alvo = (texto.split() or [""])[0].strip(":,.")
                    if alvo not in campos:
                        self.find("FIT-018", f"{cid}@{versao}/{alvo}",
                                  f"{cid}@{versao}: o invariante condicional começa por "
                                  f"{alvo!r}, que não é campo do payload_schema — a prosa "
                                  f"exige algo que o esquema não nomeia: {texto!r}")
                    elif alvo not in cobertos:
                        self.find("FIT-018", f"{cid}@{versao}/{alvo}",
                                  f"{cid}@{versao}: {alvo!r} é exigido condicionalmente só "
                                  f"na prosa ({texto!r}) — nenhum `if`/`then`/"
                                  f"`dependentRequired` do payload_schema o alcança")

        # FIT-016 — previsão registrada depois do fato não é previsão.
        # É o coração do modo sombra: uma saída conferida DEPOIS não mede nada,
        # porque sempre dá para explicar o que já aconteceu. Três regras, e
        # nenhuma delas admite exceção:
        #   1. o mundo real é o oráculo — só observação externa resolve
        #   2. a prova tem de ser POSTERIOR ao registro
        #   3. sem ato declarado que a resolva, a previsão não se refuta
        for c in self.kind["claim"]:
            pred = c.get("prediction")
            if pred is None:
                continue
            for p in self.kind["proof"]:
                if c["id"] not in (p.get("proves") or []) + (p.get("refutes") or []):
                    continue
                if p["basis"] != "external_observation":
                    self.find("FIT-016", f"{c['id']}/{p['id']}/basis",
                              f"{p['id']} resolve a previsão {c['id']} por {p['basis']}: "
                              f"previsão sobre o mundo real só se resolve por observação "
                              f"externa — teste não é oráculo")
                if p["date"] < pred["registered_at"]:
                    self.find("FIT-016", f"{c['id']}/{p['id']}/data",
                              f"{p['id']} é de {p['date']} e a previsão {c['id']} foi registrada "
                              f"em {pred['registered_at']}: o fato veio antes do registro, "
                              f"então isto não é previsão — é explicação depois do ocorrido")

        # FIT-014 — PFC só conta com teste de regressão que EXISTE.
        # "Erro evitado" sem prova é o defeito que o genoma combate.
        #
        # A partir do momento em que um PFC nasce de um PROCESSO REAL, o teste
        # que o sustenta mora no monolito que implementa a regra, e o juiz não
        # tem esse arquivo. A conferência então acontece ONDE O ARQUIVO ESTÁ —
        # na CI daquele repositório, por tools/genome_pfc_check.py, do mesmo
        # jeito que a invalidação de superfície. Para que `repo` não vire porta
        # de fuga, ele só vale se for um repositório cuja superfície o genoma
        # já prova: é lá que os detectores rodam.
        repos_com_superficie = {(p.get("mechanism") or {}).get("repo")
                                for p in self.kind["proof"]} - {None}
        for fc in self.kind["pfc"]:
            for t in fc["regression_tests"]:
                repo = t.get("repo")
                if repo is not None and repo != GENOME_REPO:
                    if repo not in repos_com_superficie:
                        self.find("FIT-014", f"{fc['id']}/{repo}",
                                  f"{fc['id']} aponta teste em {repo!r}, onde o genoma não prova "
                                  f"superfície alguma: ninguém confere se esse teste existe")
                    continue
                arquivo = ROOT / t["file"]
                if not arquivo.is_file():
                    self.find("FIT-014", f"{fc['id']}/{t['file']}",
                              f"{fc['id']} aponta teste em {t['file']}, que não existe")
                elif f"def {t['name']}" not in arquivo.read_text(encoding="utf-8", errors="replace"):
                    self.find("FIT-014", f"{fc['id']}/{t['name']}",
                              f"{fc['id']} aponta {t['name']} em {t['file']}, e esse teste não está lá")

        # FIT-013 — campo relatado declara a origem; derived é CONFERIDO.
        # Parte do genoma foi digitada a partir de relatos e se chamava "observed".
        # `derived` significa "extraído de fonte verificável e conferível aqui";
        # `asserted` significa "alguém escreveu" — e não sustenta certeza.
        kit_producers = (self.registry_producers or {})
        for kind, campos in REPORTED_FIELDS.items():
            for n in self.kind[kind]:
                origem = n.get("field_provenance") or {}
                for campo in campos:
                    if campo not in n:
                        continue
                    if campo not in origem:
                        self.find("FIT-013", f"{n['id']}/{campo}",
                                  f"{n['id']}.{campo} não declara origem (derived ou asserted): "
                                  f"um campo relatado sem origem é lido como observação")
                    elif origem[campo] == "derived":
                        esperado = self.derived_value(kind, n, campo, kit_producers)
                        if esperado is not None and esperado != n[campo]:
                            self.find("FIT-013", f"{n['id']}/{campo}/derived",
                                      f"{n['id']}.{campo} diz derived mas não confere com a fonte: "
                                      f"genoma {n[campo]!r}, fonte {esperado!r}")
                for campo in origem:
                    if campo not in campos:
                        self.find("FIT-013", f"{n['id']}/{campo}/desconhecido",
                                  f"{n['id']}.field_provenance declara {campo!r}, que não é campo "
                                  f"relatado de {kind}")
        # Prova que PROVA não se apoia em campo asserted. Relato levanta suspeita
        # (refutação, dívida, alerta); nunca dá certeza.
        for p in self.kind["proof"]:
            for ref in p.get("derived_from", []):
                node_id, _, campo = ref.rpartition(".")
                n = self.by_id.get(node_id)
                if n is None:
                    self.errors.append(f"{p['id']}: derived_from -> {node_id!r} não existe")
                    continue
                origem = (n.get("field_provenance") or {}).get(campo)
                if campo not in n:
                    self.errors.append(f"{p['id']}: derived_from -> {node_id}.{campo} não existe no nó")
                elif p.get("proves") and origem != "derived":
                    self.find("FIT-013", f"{p['id']}/{ref}",
                              f"{p['id']} PROVA apoiada em {ref} ({origem or 'sem origem'}): campo "
                              f"asserted não sustenta certeza — só dívida e alerta")

        # FIT-012 — a prova declara a superfície que cobre, com precisão de arquivo.
        # Prova por TESTE sem `mechanism` não sabe dizer quando deixou de valer;
        # superfície de repositório inteiro ficaria obsoleta a cada commit e o
        # genoma viraria ruído.
        for p in self.kind["proof"]:
            m = p.get("mechanism")
            if p["basis"] == "test" and m is None:
                self.find("FIT-012", f"{p['id']}/mechanism",
                          f"{p['id']} prova por teste sem declarar a superfície que cobre "
                          f"(mechanism: repo, paths, content_hash, commit)")
            for rel in (m or {}).get("paths", []):
                if WHOLE_REPO.search(rel):
                    self.find("FIT-012", f"{p['id']}/paths",
                              f"{p['id']} declara superfície {rel!r}: repositório inteiro, diretório "
                              f"ou curinga não é superfície — use arquivos")

        # FIT-011 — a contagem é por escala, e a escala do fato é declarada.
        # Prova que sustenta um elo (claim com chain_link) sem `scale`, ou com
        # escala fora do enum da Constituição, não pode entrar em contagem
        # alguma: a cadeia não sabe em que escala atravessou.
        chain_claims = {c["id"] for c in self.kind["claim"] if c.get("chain_link")}
        for p in self.kind["proof"]:
            if not (set(p.get("proves", [])) & chain_claims):
                continue
            scale = p.get("scale")
            if scale is None:
                self.find("FIT-011", f"{p['id']}/scale",
                          f"{p['id']} prova elo da cadeia sem declarar a escala do fato observado")
            elif scale not in self.scale_order:
                self.find("FIT-011", f"{p['id']}/scale",
                          f"{p['id']} declara scale {scale!r}, fora do enum federativo "
                          f"{sorted(self.scale_order, key=self.scale_order.get)}")

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
    def blocked_scales(self) -> dict[str, list]:
        """Escalas bloqueadas e por quem: afirmação não PROVEN ou incógnita que
        declara `blocks: [scale:X]`. Mesma fonte que já respondia "o que impede
        REGIONAL" — agora ela também decide a contagem (FIT-011)."""
        out: dict[str, list] = {}
        for c in self.kind["claim"]:
            for b in c.get("blocks", []):
                m = SCALE_BLOCK.match(b)
                if m and self.status[c["id"]] != "PROVEN":
                    out.setdefault(m.group(1), []).append((c["id"], self.status[c["id"]]))
        for u in self.kind["unknown"]:
            for b in u["blocks"]:
                m = SCALE_BLOCK.match(b)
                if m:
                    out.setdefault(m.group(1), []).append((u["id"], "UNKNOWN"))
        return out

    def chain_by_scale(self, n: int, claims: dict) -> dict:
        """Contagem POR ESCALA. Um elo conta numa escala quando há prova VIGENTE
        de observação externa daquele elo COM aquela escala; escala bloqueada
        conta zero, e o relatório diz por quê."""
        proving = defaultdict(list)
        for p in self.kind["proof"]:
            if p["id"] in self.superseded_by or p["basis"] != "external_observation":
                continue
            for c in p.get("proves", []):
                proving[c].append(p)
        blocked = self.blocked_scales()
        scales = sorted({p.get("scale") for ps in proving.values() for p in ps
                         if p.get("scale") in self.scale_order} | set(blocked),
                        key=lambda s: self.scale_order.get(s, 99))
        out = {}
        for scale in scales:
            def counted(measure):
                total = 0
                for c in claims.values():
                    cl = c.get("chain_link")
                    if not cl or cl["measure"] != measure or not (1 <= cl["position"] <= n):
                        continue
                    if any(p.get("scale") == scale for p in proving.get(c["id"], [])):
                        total += 1
                return total
            b = blocked.get(scale, [])
            out[scale] = {
                "blocked_by": b,
                "structural": 0 if b else counted("structural"),
                "substantive": 0 if b else counted("substantive"),
                # o que HAVERIA se a escala não estivesse bloqueada — nunca é a contagem
                "structural_if_unblocked": counted("structural"),
            }
        return out

    def self_model(self) -> dict:
        meta = self.kind["meta"][0]
        claims = {c["id"]: c for c in self.kind["claim"]}
        n = meta["chain_positions"]
        links = {}
        for c in claims.values():
            cl = c.get("chain_link")
            if cl and cl["measure"] == "structural":
                links[cl["position"]] = c["id"]
        by_scale = self.chain_by_scale(n, claims)
        # A contagem AGREGADA continua existindo (um elo PROVEN em qualquer
        # escala não bloqueada), mas o número que se anuncia é o por escala.
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
            "chain_by_scale": by_scale,
            "chain": {"structural": structural, "substantive": substantive, "positions": n,
                      "shadow_ceiling": meta.get("shadow_mode_ceiling"),
                      "shadow_note": meta.get("shadow_mode_note"),
                      "entry": {"claim": entry, "status": self.status.get(entry),
                                "ephemeral": entry in self.ephemeral}},
            "claims": {c: {"status": self.status[c], "statement": claims[c]["statement"],
                           "ephemeral": c in self.ephemeral,
                           "history": self.claim_history(c)} for c in claims},
            "proofs_superseded": sorted(self.superseded_by.items()),
            "proofs_expired": sorted(self.expired),
            "q_multi_emitter": emitters,
            "q_screens_on_proposta": proposta_screens,
            "q_blocks_regional": regional,
            "q_runtime_fitness_without_proof": runtime_no_proof,
            "pfc": [{"id": f["id"], "title": f["title"], "false_claim": f["false_claim"],
                      "tests": [f"{t['file']}::{t['name']}"
                                + ("" if t.get("repo") in (None, GENOME_REPO)
                                   else f"  (em {t['repo']}, conferido na CI de lá)")
                                for t in f["regression_tests"]]}
                     for f in self.kind["pfc"]],
            "machinery": {"fitness": len(self.kind["fitness"]),
                          "node_kinds": len([k for k, v in (self.schema.get("$defs") or {}).items()
                                             if "kind" in (v.get("properties") or {})])},
            "predictions": [
                {"id": c["id"], "statement": c["statement"],
                 "registered_at": c["prediction"]["registered_at"],
                 "method": f"{c['prediction']['method']}/{c['prediction']['method_version']}",
                 "settled_by": c["prediction"]["settled_by"],
                 "status": self.status[c["id"]]}
                for c in self.kind["claim"] if c.get("prediction")],
            "proofs": [
                {"id": p["id"], "title": p["title"], "basis": p["basis"],
                 "date": p["date"], "scale": p.get("scale"),
                 "environment": p.get("environment"),
                 "proves": p.get("proves") or [], "refutes": p.get("refutes") or [],
                 "superseded": p["id"] in self.superseded_by,
                 "expired": p["id"] in self.expired,
                 "repo": ((p.get("mechanism") or p.get("location") or
                           p.get("evidence_artifact") or p.get("test") or {}).get("repo"))}
                for p in sorted(self.kind["proof"], key=lambda x: x["id"])],
            "producers": sorted(
                ({"id": pid,
                  "repo": (entry or {}).get("repository"),
                  "hosted_in": (entry or {}).get("hosted_in"),
                  "hosted_in_reason": (entry or {}).get("hosted_in_reason"),
                  "teto": ((entry or {}).get("teto") or {}).get("teto_interno"),
                  "instancias": len((entry or {}).get("instances") or [])}
                 for pid, entry in (self.registry_producers or {}).items()),
                key=lambda x: x["id"]),
            "q_asserted_fields": sorted(
                f"{n['id']}.{campo}"
                for kind, campos in REPORTED_FIELDS.items() for n in self.kind[kind]
                for campo in campos
                if campo in n and (n.get("field_provenance") or {}).get(campo) == "asserted"),
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
    L.append("CADEIA — derivada das provas, nunca declarada; POR ESCALA (FIT-011)")
    if not m["chain_by_scale"]:
        L.append("  nenhuma escala com prova de elo nem bloqueio declarado")
    for scale, v in m["chain_by_scale"].items():
        if v["blocked_by"]:
            quem = ", ".join(f"{i} {st}" for i, st in v["blocked_by"])
            extra = (f"; haveria {v['structural_if_unblocked']}/{c['positions']} se nao estivesse"
                     if v["structural_if_unblocked"] else "")
            L.append(f"  {scale:12} bloqueada por {len(v['blocked_by'])} item(ns) — 0 elos contam  "
                     f"[{quem}]{extra}")
        else:
            L.append(f"  {scale:12} estrutural {v['structural']}/{c['positions']}   "
                     f"substantiva {v['substantive']}/{c['positions']}")
    L.append(f"  (agregado, sem escala: estrutural {c['structural']}/{c['positions']}, "
             f"substantiva {c['substantive']}/{c['positions']})")
    if c.get("shadow_ceiling"):
        L.append(f"  TETO EM MODO SOMBRA: {c['shadow_ceiling']}/{c['positions']} POR DESENHO — "
                 f"os elos acima de {c['shadow_ceiling']} nao sao atos do LICEU.")
        if c.get("shadow_note"):
            for linha in str(c["shadow_note"]).strip().splitlines():
                L.append(f"    {linha.strip()}")
    e = c["entry"]
    L.append(f"  entrada      {e['claim']} {e['status']}" + ("  (ambiente efêmero)" if e["ephemeral"] else ""))
    L.append("")
    if m["proofs_expired"]:
        L.append(f"PROVAS VENCIDAS: {', '.join(m['proofs_expired'])}  "
                 f"(a afirmação vira STALE — prove de novo, não é falsa)")
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
    L.append(f"  campos relatados (asserted) ............ {len(m['q_asserted_fields'])}")
    for x in m["q_asserted_fields"]:
        L.append(f"    {x}")
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
    mach = m["machinery"]
    den = mach["fitness"] + mach["node_kinds"]
    num = max((v["structural"] for v in m["chain_by_scale"].values()), default=0)
    L.append("O QUE O GENOMA DEVE A SI MESMO")
    L.append(f"  elos provados (numerador) .............. {num}")
    L.append(f"  maquinaria (denominador) ............... {den}  "
             f"({mach['fitness']} fitness + {mach['node_kinds']} tipos de nó)")
    L.append(f"  falsas afirmações evitadas (PFC) ....... {len(m['pfc'])}")
    for f in m["pfc"]:
        L.append(f"    {f['id']}  {f['title']}")
        L.append(f"          teria afirmado: {f['false_claim']}")
        for t in f["tests"]:
            L.append(f"          prova: {t}")
    if m["predictions"]:
        conf = [p for p in m["predictions"] if p["status"] == "PROVEN"]
        refu = [p for p in m["predictions"] if p["status"] == "REFUTED"]
        aberto = [p for p in m["predictions"] if p["status"] not in ("PROVEN", "REFUTED")]
        L.append("")
        L.append("MODO SOMBRA — previsões pré-registradas e o que o mundo respondeu")
        L.append(f"  previsões pré-registradas .............. {len(m['predictions'])}")
        L.append(f"  confirmadas pelo mundo real ............ {len(conf)}")
        L.append(f"  refutadas pelo mundo real .............. {len(refu)}")
        L.append(f"  ainda sem resposta ..................... {len(aberto)}")
        for p in m["predictions"]:
            L.append(f"    [{p['status']:<9}] {p['id']}  ({p['registered_at']}, {p['method']})")
            L.append(f"                  {p['statement']}")
            L.append(f"                  resolve: {p['settled_by']}")
        if not conf and not refu:
            L.append("  O mundo real ainda não respondeu nenhuma. Enquanto este histórico não")
            L.append("  existir, o LICEU não deve conduzir processo algum.")
    if m.get("growth_warning"):
        g = m["growth_warning"]
        L.append(f"  AVISO: a maquinaria cresceu em três merges seguidos "
                 f"({' -> '.join(str(d) for d in g['denominador'])}) e a cadeia não andou "
                 f"({' -> '.join(str(x) for x in g['numerador'])}), de {g['de']} a {g['ate']}.")
        for linha in g.get("o_que_cresceu", []):
            L.append(f"         {linha}")
        L.append("         Não falha a CI. A decisão de parar é humana.")
    L.append("")
    L.append("RESULTADO: " + ("FALHOU" if j.errors else "ÍNTEGRO — nenhuma violação nova"))
    for e_ in j.errors:
        L.append(f"  ✗ {e_}")
    return "\n".join(L)


def proveniencia(genome_dir: Path) -> dict:
    """De onde esta pagina saiu. Sem isto, ela envelhece em silencio.

    O commit e o do repositorio do genoma; a data e a da geracao; o kit e o
    INSTALADO, o mesmo que a FIT-010 usa para julgar. Uma pagina que nao diz
    isso e indistinguivel de uma copia escrita a mao.
    """
    def git(*args):
        try:
            out = subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True,
                                 text=True, timeout=10)
            return out.stdout.strip() if out.returncode == 0 else ""
        except Exception:                                    # noqa: BLE001
            return ""

    try:
        from liceu_protocol import KIT_DIR
        kit = dict(l.split("=", 1) for l in
                   (Path(KIT_DIR) / "VERSION").read_text(encoding="utf-8").splitlines()
                   if "=" in l)
    except Exception:                                        # noqa: BLE001
        kit = {}
    return {
        "commit": git("rev-parse", "--short", "HEAD"),
        "commit_date": git("log", "-1", "--format=%cI"),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "sujo": bool(git("status", "--porcelain")),
        "gerado_em": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "genome_dir": str(genome_dir),
        "kit": kit.get("conformance_kit", "?"),
        "constitution": kit.get("constitution", "?"),
    }


FONTES = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
          '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
          '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
          'family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">')


def html_report(m: dict, j: Judge, *, fragment: bool = False) -> str:
    """O Self-Model, em pagina. Nada aqui e escrito a mao.

    Toda secao sai de `m`, que o juiz deriva do genoma e do kit instalado. Um
    relatorio escrito a mao seria copia declarada do que o juiz ja deriva, e
    ficaria desatualizado em silencio — o defeito que a FIT-010 existe para
    impedir. Por isso a pagina carrega PROCEDENCIA: commit do genoma, data da
    geracao e versao do kit. Uma pagina velha diz que esta velha.

    fragment=True omite doctype/html/head/body — e o formato que um Artifact
    espera, porque a plataforma poe o proprio esqueleto em volta.
    """
    esc = html.escape
    c = m["chain"]
    prov = proveniencia(Path(getattr(j, "genome_dir", ROOT / "genome")))
    tone = {"PROVEN": "ok", "TESTED": "at", "UNPROVEN": "no", "REFUTED": "bad", "STALE": "at"}

    def pill(st, extra=""):
        return f'<span class="pill {tone.get(st, "no")}{extra}">{esc(str(st))}</span>'

    def secao(titulo, corpo, nota=""):
        n = f'<p class="nota">{nota}</p>' if nota else ""
        return f"<section><h2>{esc(titulo)}</h2>{n}{corpo}</section>"

    # ---------------------------------------------------------------- cadeia
    escalas = ""
    for nome, v in m["chain_by_scale"].items():
        if v["blocked_by"]:
            quem = ", ".join(f"{i} {st}" for i, st in v["blocked_by"])
            haveria = (f' <span class="dim">· haveria {v["structural_if_unblocked"]}/{c["positions"]}'
                       f" se nao estivesse</span>" if v["structural_if_unblocked"] else "")
            escalas += (f'<tr><td class="m">{esc(nome)}</td>'
                        f'<td colspan="2">{pill("REFUTED")} bloqueada por {len(v["blocked_by"])}'
                        f' item(ns){haveria}<div class="dim m">{esc(quem)}</div></td></tr>')
        else:
            escalas += (f'<tr><td class="m">{esc(nome)}</td>'
                        f'<td><b class="num">{v["structural"]}</b><span class="dim">/{c["positions"]}'
                        f' estrutural</span></td>'
                        f'<td><b class="num">{v["substantive"]}</b><span class="dim">/{c["positions"]}'
                        f' substantiva</span></td></tr>')
    teto = ""
    if c.get("shadow_ceiling"):
        teto = (f'<p class="teto"><b>Teto em modo sombra: {c["shadow_ceiling"]}/{c["positions"]}'
                f' por desenho.</b> {esc(str(c.get("shadow_note") or "").strip())}</p>')

    # ---------------------------------------------------------------- previsoes
    prev = ""
    if m.get("predictions"):
        conf = sum(1 for x in m["predictions"] if x["status"] == "PROVEN")
        refu = sum(1 for x in m["predictions"] if x["status"] == "REFUTED")
        linhas = "".join(
            f'<tr><td>{pill(x["status"])}</td><td><div>{esc(x["statement"])}</div>'
            f'<div class="dim m">registrada {esc(x["registered_at"])} · {esc(x["method"])}</div>'
            f'<div class="dim">resolve: {esc(x["settled_by"])}</div></td></tr>'
            for x in m["predictions"])
        aviso = ("" if conf or refu else
                 '<p class="aviso">O mundo real ainda nao respondeu nenhuma. Enquanto este '
                 'historico nao existir, o LICEU nao deve conduzir processo algum.</p>')
        prev = secao(
            "Modo sombra — o que foi previsto antes de o mundo responder",
            f'<div class="chain"><div class="stat"><b>{len(m["predictions"])}</b>'
            f'<span>pre-registradas</span></div>'
            f'<div class="stat"><b>{conf}</b><span>confirmadas</span></div>'
            f'<div class="stat"><b>{refu}</b><span>refutadas</span></div></div>'
            f'{aviso}<div class="tbl"><table>{linhas}</table></div>',
            "Previsao registrada depois do fato nao e previsao. A FIT-016 compara a data da "
            "prova com a do registro, e so observacao externa resolve — teste nao e oraculo.")

    # ---------------------------------------------------------------- PFC
    pfc = ""
    if m.get("pfc"):
        itens = "".join(
            f'<article class="card"><header><span class="m">{esc(f["id"])}</span>'
            f'<h3>{esc(f["title"])}</h3></header>'
            f'<p class="falsa">teria afirmado: <q>{esc(f["false_claim"])}</q></p>'
            + "".join(f'<div class="m dim">{esc(t)}</div>' for t in f["tests"])
            + "</article>" for f in m["pfc"])
        pfc = secao("Falsas afirmacoes evitadas", f'<div class="grid">{itens}</div>',
                    "So conta com teste de regressao que EXISTE — o juiz confere arquivo e nome. "
                    "Sem teste executavel, <q>erro evitado</q> e so mais uma afirmacao.")

    # ---------------------------------------------------------------- provas
    provas = "".join(
        f'<tr><td class="m">{esc(pr["id"])}</td>'
        f'<td>{pill("PROVEN" if pr["proves"] else "REFUTED")}'
        f'{" " + pill("STALE") if pr["expired"] else ""}'
        f'{chr(32) + chr(60)}span class="dim m"{chr(62)}{esc(pr["basis"])}'
        f'{" · " + esc(pr["scale"]) if pr["scale"] else ""}'
        f'{" · " + esc(pr["environment"]) if pr["environment"] else ""}</span></td>'
        f'<td>{esc(pr["title"])}'
        f'<div class="dim m">{esc(", ".join(pr["proves"] + pr["refutes"]))}'
        f'{" · " + esc(pr["repo"]) if pr["repo"] else ""} · {esc(pr["date"])}</div></td></tr>'
        for pr in m.get("proofs", []) if not pr["superseded"])
    n_sup = sum(1 for pr in m.get("proofs", []) if pr["superseded"])

    # ---------------------------------------------------------------- produtores
    def onde(x):
        if x["repo"]:
            return esc(x["repo"])
        if x["hosted_in"]:
            return (f'{pill("TESTED")} hospedado em <b>{esc(x["hosted_in"])}</b>'
                    f'<div class="dim">{esc((x["hosted_in_reason"] or "")[:160])}</div>')
        return pill("REFUTED") + " sem repositorio e sem hosted_in"

    prods = "".join(
        f'<tr><td class="m">{esc(x["id"])}</td><td class="m">{onde(x)}</td>'
        f'<td class="m dim">{esc(str(x["teto"] or "—"))}</td>'
        f'<td class="m dim">{x["instancias"]}</td></tr>' for x in m.get("producers", []))
    sem_repo = [x["id"] for x in m.get("producers", [])
                if not x["repo"] and not x["hosted_in"]]
    hospedados = [x for x in m.get("producers", []) if not x["repo"] and x["hosted_in"]]

    # ---------------------------------------------------------------- resto
    claims = "".join(
        f'<tr><td class="m">{esc(cid)}</td><td>{pill(v["status"])}'
        f'{"<span class=eph>efemero</span>" if v["ephemeral"] else ""}</td>'
        f'<td>{esc(v["statement"])}</td></tr>' for cid, v in m["claims"].items())
    unknowns = "".join(f'<li><span class="m">{esc(u[0])}</span> {esc(u[1])}</li>' for u in m["unknowns"])
    regional = "".join(f'<li><span class="m">{esc(x[0])}</span> {pill(x[1])} {esc(x[2])}</li>'
                       for x in m["q_blocks_regional"])
    debt = "".join(f'<li>{pill("REFUTED")} <span class="m">{esc(f)}</span> {esc(msg)}</li>'
                   for f, st, msg in m["debt_known"])
    debt += "".join(f'<li>{pill("REFUTED")} <span class="m">{esc(f)}</span> {esc(o)} '
                    f'<span class="dim">[{esc(v)}]</span></li>' for v, f, o in m["debt_code"])
    debt = debt or '<li class="dim">nenhuma divida registrada</li>'

    mach = m["machinery"]
    den = mach["fitness"] + mach["node_kinds"]
    freio = ""
    if m.get("growth_warning"):
        g = m["growth_warning"]
        freio = (f'<p class="aviso">A maquinaria cresceu em tres merges seguidos '
                 f'({" → ".join(str(d) for d in g["denominador"])}) e a cadeia nao andou '
                 f'({" → ".join(str(x) for x in g["numerador"])}), de {esc(g["de"])} a {esc(g["ate"])}.</p>')

    verdict = "FALHOU" if j.errors else "INTEGRO"
    sujo = ' <span class="pill bad">arvore suja</span>' if prov["sujo"] else ""

    ESTILO = """<style>
:root{
  color-scheme:dark;
  --bg:#0B0F14; --sf:#151B23; --sf2:#1B232E; --ln:#263241; --mu:#7A8899; --tx:#F8FAFC;
  --ok:#16A34A; --at:#F59E0B; --bad:#DC2626; --ev:#7C3AED;
  --sans:'Inter',system-ui,-apple-system,sans-serif;
  --mono:'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,monospace;
}
@media (prefers-color-scheme:light){:root:not([data-theme="dark"]){
  color-scheme:light;
  --bg:#F7F8FA; --sf:#FFFFFF; --sf2:#F1F4F8; --ln:#DDE3EA; --mu:#5B6876; --tx:#0B0F14;
}}
:root[data-theme="light"]{
  color-scheme:light;
  --bg:#F7F8FA; --sf:#FFFFFF; --sf2:#F1F4F8; --ln:#DDE3EA; --mu:#5B6876; --tx:#0B0F14;
}
*{box-sizing:border-box;margin:0}
body{background:var(--bg);color:var(--tx);font:14px/1.6 var(--sans);
  -webkit-font-smoothing:antialiased}
main{max-width:1060px;margin:0 auto;padding-block:34px 72px;padding-left:20px;padding-right:20px;
  display:flex;flex-direction:column;gap:38px}
section{display:flex;flex-direction:column;gap:12px}
.eyebrow{font:11px/1.4 var(--mono);color:var(--mu);letter-spacing:.06em;text-transform:uppercase}
h1{font-size:clamp(22px,4.4vw,30px);line-height:1.18;letter-spacing:-.022em;text-wrap:balance;
  margin-top:8px}
h2{font-size:13px;font-weight:600;letter-spacing:.02em;color:var(--tx);
  padding-bottom:9px;border-bottom:1px solid var(--ln)}
h3{font-size:13.5px;font-weight:600;text-wrap:balance}
.lede{color:var(--mu);max-width:66ch}
.nota{color:var(--mu);font-size:12.5px;max-width:78ch;margin-top:-4px}
.m{font-family:var(--mono);font-size:12px}
.dim{color:var(--mu)}
.num{font:600 15px/1 var(--mono);font-variant-numeric:tabular-nums}
q{quotes:'\201C' '\201D'}
.prov{display:flex;flex-wrap:wrap;gap:6px 18px;font:11.5px/1.5 var(--mono);color:var(--mu);
  background:var(--sf2);border:1px solid var(--ln);border-radius:3px;padding:10px 13px}
.prov b{color:var(--tx);font-weight:500}
.verdict{font:600 12px var(--mono);padding:4px 11px;border-radius:2px;display:inline-block;
  border:1px solid;align-self:flex-start}
.chain{display:grid;grid-template-columns:repeat(auto-fit,minmax(138px,1fr));gap:10px}
.stat{background:var(--sf);border:1px solid var(--ln);border-radius:4px;padding:15px 14px}
.stat b{display:block;font:600 32px/1 var(--mono);letter-spacing:-.035em;
  font-variant-numeric:tabular-nums}
.stat span{color:var(--mu);font-size:11.5px}
.stat.zero b{color:var(--bad)}
.stat.hero{border-left:2px solid var(--ev)}
.tbl{overflow-x:auto;background:var(--sf);border:1px solid var(--ln);border-radius:4px}
table{width:100%;border-collapse:collapse;min-width:min(100%,520px)}
td{padding:8px 10px;border-bottom:1px solid var(--ln);vertical-align:top}
tr:last-child td{border-bottom:0}
.pill{font:10px var(--mono);padding:2px 7px;border-radius:2px;border:1px solid;white-space:nowrap;
  display:inline-block}
.pill.ok{color:var(--ok);border-color:color-mix(in srgb,var(--ok) 45%,transparent)}
.pill.at{color:var(--at);border-color:color-mix(in srgb,var(--at) 45%,transparent)}
.pill.no{color:var(--mu);border-color:var(--ln)}
.pill.bad{color:var(--bad);border-color:color-mix(in srgb,var(--bad) 45%,transparent)}
.eph{font:10px var(--mono);color:var(--at);margin-left:6px}
.chip{font:10.5px var(--mono);padding:1px 6px;border:1px solid var(--ln);border-radius:2px;
  display:inline-block;margin:1px}
.chip.bad{color:var(--bad)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}
.card{background:var(--sf);border:1px solid var(--ln);border-radius:4px;padding:14px;
  display:flex;flex-direction:column;gap:7px}
.card header{display:flex;gap:9px;align-items:baseline;flex-wrap:wrap}
.falsa{font-size:12.5px;color:var(--mu)}
.falsa q{color:var(--bad)}
.teto{background:var(--sf2);border-left:2px solid var(--ev);border-radius:0 3px 3px 0;
  padding:11px 14px;font-size:12.5px;color:var(--mu);max-width:82ch}
.teto b{color:var(--tx)}
.aviso{background:var(--sf2);border-left:2px solid var(--at);border-radius:0 3px 3px 0;
  padding:11px 14px;font-size:12.5px;max-width:82ch}
.scr{background:var(--sf);border:1px solid var(--ln);border-top:2px solid var(--ev);
  border-radius:4px;padding:14px}
.scr header{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;margin-bottom:10px}
.scr header h3{flex:1;min-width:150px}
dl{display:grid;grid-template-columns:88px 1fr;gap:6px 10px;font-size:12.5px}
dt{color:var(--mu)}
ul{padding-left:19px;display:flex;flex-direction:column;gap:5px}
footer{padding-top:18px;border-top:1px solid var(--ln);color:var(--mu);font-size:12.5px;
  max-width:74ch}
@media (max-width:520px){dl{grid-template-columns:1fr;gap:2px 0}dt{margin-top:6px}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>"""

    screens = ""
    for sc in m["screens"]:
        disp = "".join(f'<div><span class="m">{esc(d)}</span> '
                       + " ".join(f'<span class="chip">{esc(x)}</span>' for x in v) + "</div>"
                       for d, v in sc["displays"].items()) or '<span class="dim">nenhuma dimensao</span>'
        users = "".join(f'<div><span class="m">{esc(r)}</span> {esc(t or "")} '
                        f'{pill(v or "")} <span class="dim">· {esc(u)}</span></div>'
                        for r, t, v, u in sc["used_by"])
        john = ", ".join(f"{a} · {b}" for a, b in sc["john"]) or "nenhum"
        screens += f"""
<article class="scr">
  <header><span class="m">{esc(sc['id'])}</span><h3>{esc(sc['title'])}</h3>
    {pill(sc['implementation'])}</header>
  <dl>
    <dt>dono</dt><dd class="m">{esc(sc['owner'])}</dd>
    <dt>le</dt><dd class="m">{esc(', '.join(sc['reads']))}</dd>
    <dt>jornada</dt><dd><span class="m">{esc(sc['journey'][0])}</span> {pill(sc['journey'][1] or '')}</dd>
    <dt>usada por</dt><dd>{users}</dd>
    <dt>JOHN</dt><dd>{esc(john)}</dd>
    <dt>exibe</dt><dd>{disp}</dd>
    <dt>nunca exibe</dt><dd>{' '.join(f'<span class="chip bad">{esc(x)}</span>' for x in sc['must_not'])}</dd>
    <dt>obrigatorio</dt><dd class="m">{esc(', '.join(sc['required']) or '—')}</dd>
    <dt>evidencia</dt><dd>{'exigida' if sc['evidence_required'] else 'nao se aplica'} · confidence {esc(sc['confidence'])}</dd>
    <dt>autoridade</dt><dd>{'pode exibir resultado' if sc['authority'] else 'nao pode exibir resultado de autoridade'}</dd>
    <dt>IPS/CQP/CQM</dt><dd>{esc(', '.join(f'{r} ({v})' for r, v in sc['ips'])) or 'sem mapeamento'}</dd>
  </dl>
</article>"""

    CORPO = f"""<main>
<header>
  <p class="eyebrow">Genoma LICEU 6.0 · Self-Model · grafo {esc(m['graph_version'])}</p>
  <h1>O que o LICEU consegue provar sobre si mesmo.</h1>
  <p class="lede">Gerado pelo juiz a partir do genoma e do kit instalado. Nada aqui e escrito
  a mao: o status de cada afirmacao e derivado das provas, e a contagem da cadeia nao pode
  ser declarada por arquivo nenhum.</p>
</header>

<div class="prov">
  <span>genoma <b>{esc(prov['commit'] or '?')}</b>{sujo}</span>
  <span>branch <b>{esc(prov['branch'] or '?')}</b></span>
  <span>ultimo commit <b>{esc((prov['commit_date'] or '?')[:10])}</b></span>
  <span>kit <b>{esc(prov['kit'])}</b> · constituicao <b>{esc(prov['constitution'])}</b></span>
  <span>gerado em <b>{esc(prov['gerado_em'])}</b></span>
</div>

<span class="verdict" style="color:{'var(--bad)' if j.errors else 'var(--ok)'}">{verdict} ·
  {len(j.errors)} erro(s) · {len(m['debt_known']) + len(m['debt_code'])} divida(s) conhecida(s)</span>

<section>
  <div class="chain">
    <div class="stat hero {'zero' if c['structural'] == 0 else ''}">
      <b>{c['structural']}/{c['positions']}</b><span>cadeia estrutural</span></div>
    <div class="stat {'zero' if c['substantive'] == 0 else ''}">
      <b>{c['substantive']}/{c['positions']}</b><span>cadeia substantiva</span></div>
    <div class="stat"><b>{sum(1 for v in m['claims'].values() if v['status'] == 'PROVEN')}</b>
      <span>afirmacoes provadas</span></div>
    <div class="stat"><b>{len(m['pfc'])}</b><span>falsas afirmacoes evitadas</span></div>
    <div class="stat"><b>{len(m['unknowns'])}</b><span>incognitas declaradas</span></div>
  </div>
</section>

{secao("A cadeia, por escala",
       f'<div class="tbl"><table>{escalas}</table></div>{teto}',
       "Estrutural: o fato atravessou o boundary real com o contrato real. Substantiva: o "
       "conteudo vale. Sao dois numeros porque sao duas perguntas, e a segunda e a dificil.")}

{prev}

{secao("Afirmacoes, e o status que as provas permitem",
       f'<div class="tbl"><table>{claims}</table></div>')}

{secao("As provas vigentes",
       f'<div class="tbl"><table>{provas}</table></div>',
       f"{n_sup} prova(s) supersedida(s) nao aparecem aqui, e continuam no genoma: uma prova "
       "substituida nao e apagada, e a historia de cada afirmacao fica legivel.")}

{secao("O que impede a escala REGIONAL", f"<ul>{regional}</ul>")}

{secao("O que o LICEU sabe que nao sabe", f"<ul>{unknowns}</ul>")}

{secao("Divida registrada", f"<ul>{debt}</ul>",
       "Violacao nova falha a CI; divida registrada que deixou de ser detectada tambem falha.")}

{pfc}

{secao("Produtores declarados no kit",
       f'<div class="tbl"><table>{prods}</table></div>',
       ((f'<span class="pill bad">{len(sem_repo)}</span> produtor(es) sem repositorio e sem '
         f'hosted_in: <span class="m">{esc(", ".join(sem_repo))}</span>. A FIT-017 recusa isso.')
        if sem_repo else
        (f"Lido do Producer Registry instalado, a mesma fonte que a FIT-010 usa para julgar. "
         f"{len(hospedados)} produtor(es) sem repositorio proprio declaram onde estao "
         f"(hosted_in), e a FIT-017 confere que o anfitriao existe, tem repositorio e que a "
         f"razao esta escrita.")))}

{secao("O que o genoma deve a si mesmo",
       f'<div class="chain">'
       f'<div class="stat"><b>{c["structural"]}</b><span>elos provados (numerador)</span></div>'
       f'<div class="stat"><b>{den}</b><span>maquinaria (denominador)</span></div>'
       f'<div class="stat"><b>{mach["fitness"]}</b><span>fitness functions</span></div>'
       f'<div class="stat"><b>{mach["node_kinds"]}</b><span>tipos de no</span></div>'
       f'</div>{freio}',
       "Maquinaria nova so se justifica quando a cadeia se move. O freio compara as duas "
       "series ao longo dos merges e avisa — nunca falha — quando uma cresce e a outra nao.")}

{secao("Genealogia das cinco telas da vertical", f'<div class="grid">{screens}</div>')}

<footer>Uma lei (schema), um grafo (genoma), um juiz (genome_check). Para mudar esta pagina e
preciso mudar o genoma, e para promover uma afirmacao e preciso registrar uma prova. Esta
pagina foi gerada do commit <span class="m">{esc(prov['commit'] or '?')}</span> — se o genoma
andou depois disso, ela esta velha, e e por isso que a data esta no topo.</footer>
</main>"""

    if fragment:
        return f"<title>Genoma LICEU 6.0</title>\n{FONTES}\n{ESTILO}\n{CORPO}"
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1, '
            f'viewport-fit=cover"><title>Genoma LICEU 6.0</title>{FONTES}{ESTILO}'
            f"</head><body>{CORPO}</body></html>")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--genome", default=str(ROOT / "genome"))
    ap.add_argument("--schema", default=str(ROOT / "schema" / "genome.schema.json"))
    ap.add_argument("--json")
    ap.add_argument("--html")
    ap.add_argument("--html-fragment")
    ap.add_argument("--kit-registry", help="Contract Registry do kit; default: o do pacote liceu-protocol instalado")
    ap.add_argument("--history", action="store_true",
                    help="deriva a série do git (--first-parent main) para o freio da H6; "
                         "exige checkout com histórico (fetch-depth: 0)")
    a = ap.parse_args(argv)
    schema = json.loads(Path(a.schema).read_text(encoding="utf-8"))
    registry = load_kit_registry(Path(a.kit_registry) if a.kit_registry else None)
    problems = lint(Path(a.genome))
    if problems:
        print("TRUNCAMENTO SILENCIOSO")
        for p in problems:
            print("  ✗", p)
        return 1
    j = Judge(load(Path(a.genome)), schema, registry, genome_dir=Path(a.genome))
    m = j.run()
    if m is None:
        print("GENOMA INVÁLIDO — schema ou arestas; o Self-Model não é calculado sobre grafo partido")
        for e in j.errors:
            print("  ✗", e)
        return 1
    if a.history:
        serie = history_series(ROOT, schema, registry, load_scale_order(), load_kit_producers())
        aviso = growth_verdict(serie)
        if aviso:
            atual = serie[-1]
            anterior = serie[-4]
            mach = m["machinery"]
            aviso["o_que_cresceu"] = [
                f"denominador {anterior[1]} -> {atual[1]} "
                f"(hoje: {mach['fitness']} fitness + {mach['node_kinds']} tipos de nó)"]
            m["growth_warning"] = aviso
        m["history"] = serie
    print(text_report(m, j))
    if a.json:
        Path(a.json).write_text(json.dumps({"self_model": m, "errors": j.errors,
                                            "warnings": j.warnings}, ensure_ascii=False, indent=2))
    if a.html:
        Path(a.html).write_text(html_report(m, j), encoding="utf-8")
    if a.html_fragment:
        Path(a.html_fragment).write_text(html_report(m, j, fragment=True), encoding="utf-8")
    return 1 if j.errors else 0


if __name__ == "__main__":
    sys.exit(main())
