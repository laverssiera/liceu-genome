import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
"""C28-01a: a cauda de fsync DESTA maquina. O instrumento NAO e o fio.

O QUE A RECEITA DO ETCD PEDE:
    fio --rw=write --ioengine=sync --fdatasync=1 --size=22m --bs=2300

O QUE ESTE SCRIPT FAZ, e a diferenca importa:
    escrita sequencial, blocos de 2300 bytes, 22 MiB no total, e um
    os.fsync() APOS CADA BLOCO, cronometrado isoladamente.

POR QUE NAO E A MESMA COISA, e isto vai no escopo:
  - `fio` nao esta instalado nesta maquina, e baixar e executar binario
    de fora nao e ato meu.
  - no Windows, os.fsync() chama FlushFileBuffers, que e MAIS FORTE que
    fdatasync: ele desce metadados tambem. Entao esta medicao e um
    LIMITE SUPERIOR da cauda de fdatasync, nao a cauda de fdatasync.
  - um limite superior serve para a decisao: se o p99 daqui ja estiver
    DENTRO dos 10 ms, a cauda real tambem esta. Se estiver fora, nao se
    conclui nada sobre fdatasync -- e dizer isso e parte do resultado.

TRES EXECUCOES, porque a cauda e o objeto e uma execucao nao tem cauda.
"""
import os
import pathlib
import statistics
import time

BLOCO = 2300
TOTAL = 22 * 1024 * 1024
N = TOTAL // BLOCO
TETO_SEGUNDOS = 240  # regra de parada propria: nao prender a sessao

destino = pathlib.Path(__file__).resolve().parent / "fsync_alvo.bin"
dados = os.urandom(BLOCO)

livre_antes = os.statvfs(destino.parent) if hasattr(os, "statvfs") else None
import shutil
total_d, usado_d, livre_d = shutil.disk_usage(str(destino.parent))
print(f"  disco: {total_d/2**30:.1f} GiB total, {livre_d/2**30:.2f} GiB livre "
      f"({100*usado_d/total_d:.1f}% ocupado)")
print(f"  blocos: {N} de {BLOCO} bytes = {N*BLOCO/2**20:.1f} MiB por execucao")
print(f"  instrumento: os.fsync por bloco (NAO e fio; no Windows e "
      f"FlushFileBuffers)\n")


def uma_execucao(rotulo):
    amostras = []
    inicio = time.perf_counter()
    fd = os.open(str(destino), os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
    try:
        for i in range(N):
            os.write(fd, dados)
            t0 = time.perf_counter()
            os.fsync(fd)
            amostras.append((time.perf_counter() - t0) * 1000.0)
            if time.perf_counter() - inicio > TETO_SEGUNDOS:
                print(f"  {rotulo}: PAROU no teto de {TETO_SEGUNDOS}s "
                      f"apos {i+1} de {N} blocos — e isso e resultado")
                break
    finally:
        os.close(fd)
    return amostras


def pct(xs, p):
    xs = sorted(xs)
    k = min(len(xs) - 1, int(round(p / 100.0 * (len(xs) - 1))))
    return xs[k]


resultados = []
for r in range(1, 4):
    a = uma_execucao(f"execucao {r}")
    resultados.append(a)
    print(f"  execucao {r}: n={len(a)}  mediana={statistics.median(a):.3f} ms  "
          f"p95={pct(a,95):.3f}  p99={pct(a,99):.3f}  p999={pct(a,99.9):.3f}  "
          f"max={max(a):.3f}")

if destino.exists():
    destino.unlink()

print()
p99s = [pct(a, 99) for a in resultados]
print(f"  OS TRES p99 (ms): {', '.join(f'{x:.3f}' for x in p99s)}")
print(f"  pior p99: {max(p99s):.3f} ms   |   referencia do etcd: 10 ms")
dentro = max(p99s) < 10.0
print(f"  VEREDITO: p99 {'DENTRO' if dentro else 'FORA'} do envelope de 10 ms")
if dentro:
    print("    e como este instrumento e um LIMITE SUPERIOR de fdatasync,")
    print("    a cauda real de fdatasync tambem esta dentro.")
else:
    print("    e como este instrumento e MAIS FORTE que fdatasync, NAO se")
    print("    conclui que fdatasync esteja fora. Fica NAO-MENSURAVEL por")
    print("    esta rota, e o fio e que responderia.")
print(f"  todos os maximos (ms): "
      f"{', '.join(f'{max(a):.1f}' for a in resultados)}")
