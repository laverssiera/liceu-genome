import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
"""C28-01b, segunda metade: a MESMA medicao sob CONCORRENCIA.

A primeira passagem foi sequencial e nao achou retencao acima de 100 ms. Mas
contencao de GIL e por definicao um fenomeno de concorrencia: uma rota sozinha
que solta o GIL com frequencia pode, com dez iguais em paralelo, manter o
interpretador ocupado o tempo todo. Medir so a sequencial e medir a condicao em
que o fenomeno nao ocorre.

CARGA DECLARADA: as 12 rotas de maior tempo de CPU da primeira passagem,
disparadas por 12 threads em paralelo, em rodadas, durante uma janela fixa.
O canario continua com tique de 5 ms e continua sendo a medida.

O QUE SEGUE FORA DO ESCOPO: POST/PATCH/DELETE, rotas com parametro de caminho,
e carga de producao real. 128 das 317 rotas foram exercitadas na primeira
passagem; esta segunda olha as 12 piores dela.
"""
import os
import pathlib
import statistics
import sys as _s
import threading
import time
from concurrent.futures import ThreadPoolExecutor

os.environ.setdefault("EVENT_BUS_PROVIDER", "memory")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
# O CORE vem do AMBIENTE, nao do disco de quem escreveu: este arquivo vive
# num repositorio PUBLICO, e caminho absoluto ali e caminho quebrado para
# todo mundo alem de uma maquina -- e carrega o nome de usuario junto.
# Aponte CORE_RAIZ para o checkout do LICEU_6.0_CONSTRUTORA_VIRTUAL.
RAIZ = pathlib.Path(os.environ.get("CORE_RAIZ", ".")).resolve()
_s.path.insert(0, str(RAIZ / "cv-backend-core"))

TIQUE = 0.005
JANELA = 60.0
PARALELO = 12

QUENTES = [
    "/civilization/dashboard",
    "/gateway/trust-layer/audit",
    "/gateway/decision-intelligence/events/published",
    "/gateway/decision-intelligence/health",
    "/gateway/execution-engine/health",
    "/gateway/quant-engine/events/published",
    "/gateway/capital-engine/events/published",
    "/gateway/decision-intelligence/system-state",
]

parar = threading.Event()
atrasos = []


def canario():
    prox = time.perf_counter() + TIQUE
    while not parar.is_set():
        agora = time.perf_counter()
        if agora < prox:
            time.sleep(max(0.0, prox - agora))
        depois = time.perf_counter()
        atrasos.append((depois - prox) * 1000.0)
        prox = depois + TIQUE


from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

cliente = TestClient(app, raise_server_exceptions=False)
print(f"  carga: {len(QUENTES)} rotas quentes x {PARALELO} threads, "
      f"janela de {JANELA:.0f}s")
print(f"  canario: tique de {TIQUE*1000:.0f} ms\n")

th = threading.Thread(target=canario, daemon=True)
th.start()
time.sleep(0.3)
base = len(atrasos)

feitas = [0]
trava = threading.Lock()
fim = time.perf_counter() + JANELA


def trabalhador(k):
    i = k
    while time.perf_counter() < fim:
        try:
            cliente.get(QUENTES[i % len(QUENTES)])
        except Exception:
            pass
        with trava:
            feitas[0] += 1
        i += 1


with ThreadPoolExecutor(max_workers=PARALELO) as ex:
    list(ex.map(trabalhador, range(PARALELO)))

parar.set()
th.join(timeout=2)
serie = atrasos[base:]


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100.0 * (len(xs) - 1))))]


print(f"  requisicoes concluidas: {feitas[0]}")
print(f"  amostras do canario: {len(serie)}\n")
print(f"  ATRASO DO CANARIO SOB CONCORRENCIA")
for rot, p in (("p50", 50), ("p95", 95), ("p99", 99), ("p999", 99.9)):
    print(f"    {rot:5s} ... {pct(serie, p):9.3f} ms")
print(f"    max   ... {max(serie):9.3f} ms")
print()
for limiar, nome in ((100, "heartbeat perdido"), (400, "eleicao possivel")):
    acima = [d for d in serie if d > limiar]
    print(f"    acima de {limiar} ms ({nome}): {len(acima)} de {len(serie)} "
          f"= {100*len(acima)/len(serie):.4f}%")
    if acima:
        print(f"      maiores: {', '.join(f'{x:.0f}' for x in sorted(acima)[-6:])}")
