import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
"""C28-01b: retencao do GIL por handler, no app que ja existe.

O QUE SE MEDE, e por que este instrumento e o certo para a pergunta:
  uma thread CANARIO acorda a cada 5 ms e cronometra o proprio atraso. O
  atraso dela E o tempo em que ela nao conseguiu o GIL -- que e exatamente
  o que faz um heartbeat ser perdido. Nao se mede "quanto o handler
  trabalha": mede-se QUANTO TEMPO O RESTO DO PROCESSO FICA PARADO, que e a
  grandeza que a eleicao espuria enxerga.

LIMIARES, lidos da fonte do pysyncobj 0.3.17 nesta sessao:
    100 ms  appendEntriesPeriod  -> primeiro heartbeat perdido
    400 ms  raftMinTimeout       -> eleicao possivel

CARGA DECLARADA: os GET sem parametro de caminho, um a um, em processo,
pelo TestClient do FastAPI -- o handler roda no MESMO interpretador que o
canario, que e a condicao para a medicao valer.

O QUE ESTA MEDICAO NAO E: nao e carga de producao, nao e concorrente, e
nao cobre POST/PATCH/DELETE nem rotas com parametro. O escopo vai junto.
"""
import os
import pathlib
import statistics
import sys as _s
import threading
import time

os.environ.setdefault("EVENT_BUS_PROVIDER", "memory")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
# O CORE vem do AMBIENTE, nao do disco de quem escreveu: este arquivo vive
# num repositorio PUBLICO, e caminho absoluto ali e caminho quebrado para
# todo mundo alem de uma maquina -- e carrega o nome de usuario junto.
# Aponte CORE_RAIZ para o checkout do LICEU_6.0_CONSTRUTORA_VIRTUAL.
RAIZ = pathlib.Path(os.environ.get("CORE_RAIZ", ".")).resolve()
_s.path.insert(0, str(RAIZ / "cv-backend-core"))

TIQUE = 0.005
TETO = 420.0

parar = threading.Event()
atrasos = []          # (t_absoluto, atraso_ms)


def canario():
    prox = time.perf_counter() + TIQUE
    while not parar.is_set():
        agora = time.perf_counter()
        if agora < prox:
            time.sleep(max(0.0, prox - agora))
        depois = time.perf_counter()
        atrasos.append((depois, (depois - prox) * 1000.0))
        prox = depois + TIQUE


from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

rotas = [r for r in app.routes if getattr(r, "methods", None)]
alvos = sorted({r.path for r in rotas
                if "GET" in r.methods and "{" not in r.path})
print(f"  carga: {len(alvos)} rotas GET sem parametro, uma a uma, em processo")
print(f"  canario: tique de {TIQUE*1000:.0f} ms\n")

cliente = TestClient(app, raise_server_exceptions=False)
th = threading.Thread(target=canario, daemon=True)
th.start()
time.sleep(0.3)
base_n = len(atrasos)

por_rota = []
inicio = time.perf_counter()
for caminho in alvos:
    i0 = len(atrasos)
    t0 = time.perf_counter()
    c0 = time.process_time()
    try:
        resp = cliente.get(caminho)
        codigo = resp.status_code
    except Exception as e:
        codigo = f"EXC:{type(e).__name__}"
    parede = (time.perf_counter() - t0) * 1000.0
    cpu = (time.process_time() - c0) * 1000.0
    janela = [d for _, d in atrasos[i0:]]
    por_rota.append((caminho, codigo, parede, cpu,
                     max(janela) if janela else 0.0))
    if time.perf_counter() - inicio > TETO:
        print(f"  PAROU no teto de {TETO:.0f}s apos {len(por_rota)} de "
              f"{len(alvos)} rotas — amostra com escopo, nao varredura abandonada")
        break

parar.set()
th.join(timeout=2)

serie = [d for _, d in atrasos[base_n:]]


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100.0 * (len(xs) - 1))))]


print(f"  rotas exercitadas: {len(por_rota)}")
cods = {}
for _, c, *_ in por_rota:
    cods[c] = cods.get(c, 0) + 1
print(f"  codigos: {dict(sorted(cods.items(), key=lambda x: -x[1])[:6])}")
print()
print(f"  ATRASO DO CANARIO — a retencao observada, n={len(serie)}")
print(f"    p50 ... {statistics.median(serie):8.3f} ms")
print(f"    p95 ... {pct(serie,95):8.3f} ms")
print(f"    p99 ... {pct(serie,99):8.3f} ms")
print(f"    p999 .. {pct(serie,99.9):8.3f} ms")
print(f"    max ... {max(serie):8.3f} ms")
print()
acima100 = [d for d in serie if d > 100]
acima400 = [d for d in serie if d > 400]
print(f"    acima de 100 ms (heartbeat perdido): {len(acima100)} de {len(serie)}"
      f"  = {100*len(acima100)/len(serie):.3f}%")
print(f"    acima de 400 ms (eleicao possivel) : {len(acima400)} de {len(serie)}"
      f"  = {100*len(acima400)/len(serie):.3f}%")
print()
print("  ROTAS CUJO PIOR ATRASO DE CANARIO PASSOU DE 100 ms:")
ruins = sorted([x for x in por_rota if x[4] > 100], key=lambda x: -x[4])
if not ruins:
    print("    nenhuma")
for caminho, codigo, parede, cpu, pior in ruins[:14]:
    marca = "  <-- ACIMA DE 400" if pior > 400 else ""
    print(f"    {pior:8.1f} ms  parede={parede:7.1f}  cpu={cpu:7.1f}  "
          f"[{codigo}] {caminho}{marca}")
print()
print("  AS 8 ROTAS DE MAIOR TEMPO DE CPU:")
for caminho, codigo, parede, cpu, pior in sorted(por_rota, key=lambda x: -x[3])[:8]:
    print(f"    cpu={cpu:8.1f} ms  parede={parede:8.1f}  canario={pior:7.1f}  "
          f"[{codigo}] {caminho}")
