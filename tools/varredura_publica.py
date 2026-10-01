#!/usr/bin/env python3
"""varredura_publica — dado pessoal nos repositorios PUBLICOS, arvore E historico.

A FIT-015 ja recusa dado pessoal, e o genome_privacy_check ja tem os padroes
certos. Faltava ALCANCE, e a falta tinha tres formas:

  so o diretorio genome/   a FIT-015 chama scan(self.genome_dir). O resto do
                           liceu-genome — tools, schema, docs — nunca foi olhado,
                           e os outros repositorios publicos tampouco.

  so a arvore de trabalho  o historico de um repositorio publico TAMBEM e
                           publico. Arquivo apagado continua la, e `git log -p`
                           o entrega a quem clonar. Apagar nao e remover.

  so algumas extensoes     .sh, .css e .TAG existem nos repositorios publicos e
                           ficavam de fora da lista de EXTENSOES. Estavam limpos
                           quando isto foi escrito — mas nao estavam sendo
                           olhados, que e outra coisa.

Esta ferramenta nao inventa padrao nenhum: importa PADROES do
genome_privacy_check. Dois vocabularios de "o que e dado pessoal" seriam duas
verdades, e a segunda envelheceria calada.

E ela NUNCA imprime o valor encontrado — so o TIPO, o arquivo e o commit. Um
varredor que vaza no log o que foi procurar nao serve num repositorio publico, e
por isso `mascarar` e funcao pura com teste proprio.

Uso:
    varredura_publica.py --root DIR [--root DIR ...] [--sem-historico]

Saida 0: nada encontrado. 1: encontrou.
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from genome_privacy_check import EXTENSOES, PADROES, scan  # noqa: E402

# .sh, .css e .TAG existem nos repositorios publicos e nao estavam na lista.
EXTENSOES_EXTRA = {".sh", ".css", ".tag", ".cjs", ".mjs", ".js", ".ts", ".tsx", ".env"}


def mascarar(texto: str) -> str:
    """Troca todo acerto pelo NOME do padrao. O valor nunca sai daqui.

    Isto nao e cosmetico: a saida vai para log de CI, que num repositorio
    publico tambem e publico. Imprimir o CPF que se foi procurar publicaria o
    CPF.
    """
    fora = texto
    for nome, padrao in PADROES.items():
        fora = padrao.sub(f"<{nome}>", fora)
    return fora


def extensoes_varridas() -> set[str]:
    return {e.lower() for e in EXTENSOES} | EXTENSOES_EXTRA


def _git(root: pathlib.Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(root), *args],
                       capture_output=True, text=True, errors="replace")
    return r.stdout


def varrer_arvore(root: pathlib.Path) -> list[str]:
    """A arvore inteira do repositorio, nao so um subdiretorio.

    O scan devolve um Resultado desde 2026-10-01: arquivo que nao se deixa ler
    nao conta limpo. Aqui o nao-mensuravel entra na lista de achados, porque
    quem le esta saida decide sobre repositorio PUBLICO e nao pode receber
    "nada encontrado" quando a verdade e "nao consegui conferir".
    """
    varrido = scan(root)
    achados = [x for lista in varrido.respostas for x in lista]
    if not varrido.mediu:
        achados += [f"NAO MENSURAVEL: {item} ({motivo})"
                    for item, motivo in varrido.sem_resposta]
    # As extensoes que o scan nao cobre, com os mesmos padroes.
    for f in sorted(root.rglob("*")):
        if not f.is_file() or f.suffix.lower() in {e.lower() for e in EXTENSOES}:
            continue
        if f.suffix.lower() not in EXTENSOES_EXTRA:
            continue
        if any(p in {".git", "node_modules", "__pycache__", ".venv", "build", "dist"}
               for p in f.parts):
            continue
        try:
            texto = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for numero, linha in enumerate(texto.splitlines(), 1):
            for nome, padrao in PADROES.items():
                if padrao.search(linha):
                    achados.append(f"{f.relative_to(root)}:{numero}: {nome}")
    return achados


def varrer_historico(root: pathlib.Path) -> list[str]:
    r"""Todo blob que ja esteve em qualquer ref. Apagar nao e remover.

    Le os blobs e aplica o MESMO motor de regex da arvore, de proposito.
    A primeira versao disto usava `git grep -E` e foi um falso verde: o grep do
    git fala ERE POSIX, que NAO entende `\d` nem ``. Os padroes de CPF, CEP e
    telefone estao escritos em sintaxe Python, entao casavam nada — em silencio,
    sem erro, sem aviso. So o de e-mail, que usa classes literais, funcionava.
    Traduzir padrao entre dois dialetos e criar uma segunda verdade; ler o blob
    e aplicar o mesmo `re` nao tem esse risco.
    """
    saida = _git(root, "rev-list", "--objects", "--all")
    vistos: set[str] = set()
    alvos: list[tuple[str, str]] = []
    for linha in saida.splitlines():
        partes = linha.split(" ", 1)
        if len(partes) != 2:
            continue
        sha, caminho = partes[0], partes[1].strip()
        if not caminho or sha in vistos:
            continue
        if pathlib.PurePosixPath(caminho).suffix.lower() not in extensoes_varridas():
            continue
        vistos.add(sha)
        alvos.append((sha, caminho))

    achados = []
    for sha, caminho in alvos:
        conteudo = _git(root, "cat-file", "-p", sha)
        for numero, linha in enumerate(conteudo.splitlines(), 1):
            for nome, padrao in PADROES.items():
                if padrao.search(linha):
                    achados.append(f"{sha[:7]}:{caminho}:{numero}: {nome}")
    return sorted(set(achados))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", action="append", required=True, type=pathlib.Path)
    ap.add_argument("--sem-historico", action="store_true",
                    help="so a arvore de trabalho (mais rapido, e incompleto)")
    args = ap.parse_args()

    total = 0
    for root in args.root:
        if not root.is_dir():
            print(f"x {root}: nao e diretorio — nada foi conferido")
            return 2
        arvore = varrer_arvore(root)
        historico = [] if args.sem_historico else varrer_historico(root)
        # resolve() antes do name: com --root . o nome vem VAZIO, e o relatorio
        # sai sem dizer QUE repositorio ele mediu.
        print(f"{root.resolve().name}: {len(arvore)} na arvore, {len(historico)} no historico")
        for a in arvore:
            print(f"   arvore     {mascarar(a)}")
        for h in historico:
            print(f"   historico  {mascarar(h)}")
        total += len(arvore) + len(historico)

    print()
    quantos = len(args.root)
    if total == 0:
        print(f"NADA ENCONTRADO em {quantos} repositorio(s), arvore e historico, "
              f"contra {len(PADROES)} padrao(oes).")
        return 0
    print(f"{total} achado(s) em {quantos} repositorio(s). "
          f"O valor nao aparece aqui de proposito: va no arquivo.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
