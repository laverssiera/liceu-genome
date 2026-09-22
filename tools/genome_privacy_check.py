#!/usr/bin/env python3
"""
genome_privacy_check — o genoma e PUBLICO; dado pessoal que entrar fica na internet.

A P-001 e uma casa real, de uma pessoa real. O que o LICEU registra sobre ela
sao PARAMETROS — municipio, zona, area do terreno, area construida, taxa de
ocupacao, coeficiente de aproveitamento, permeabilidade. Nunca identificacao.

Esta varredura recusa, em qualquer arquivo de texto do diretorio:

    CPF              pontuado, e 11 digitos junto da palavra "cpf"
    CNPJ             pontuado
    e-mail           qualquer endereco de correio eletronico
    telefone BR      com ou sem DDI/DDD e nono digito
    matricula ou inscricao imobiliaria/cadastral seguida de numero
    CEP              cinco digitos, hifen, tres digitos

    (os padroes estao em PADROES; aqui nao vai exemplo literal — este
    arquivo tambem e varrido, e exemplo de CPF num repositorio publico
    continua sendo um CPF num repositorio publico)

Serve ao liceu-genome e ao liceu-protocol (os dois publicos) e a qualquer
diretorio que se queira manter limpo. Falso positivo se resolve com o
allowlist explicito (--allow), nunca afrouxando o padrao.

Uso:
    genome_privacy_check.py [--root DIR] [--allow REGEX ...]
Saida 0: nada encontrado. 1: encontrou (imprime arquivo, linha e o TIPO —
nunca o valor inteiro).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PADROES = {
    "CPF": re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),
    "CPF sem pontuacao": re.compile(r"(?i)\bcpf\D{0,10}\d{11}\b"),
    "CNPJ": re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"),
    "e-mail": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "telefone BR": re.compile(r"(?:\+55[\s-]?)?\(?\b\d{2}\)?[\s-]?9?\d{4}[\s-]?\d{4}\b"),
    "matricula/inscricao imobiliaria": re.compile(r"(?i)\b(matr[ií]cula|inscri[çc][ãa]o\s+(?:imobili[áa]ria|cadastral))\D{0,10}\d"),
    "CEP": re.compile(r"\b\d{5}-\d{3}\b"),
}

# Extensoes de texto que valem varrer. Binario nao entra.
EXTENSOES = {".yaml", ".yml", ".json", ".md", ".py", ".txt", ".cfg", ".toml", ".html", ".csv"}
IGNORAR = {".git", "__pycache__", "node_modules", ".venv", "build", "dist"}


def scan(root: Path, allow: list[re.Pattern] | None = None) -> list[str]:
    allow = allow or []
    achados = []
    for f in sorted(root.rglob("*")):
        if not f.is_file() or f.suffix.lower() not in EXTENSOES:
            continue
        if any(parte in IGNORAR for parte in f.parts):
            continue
        rel = f.relative_to(root).as_posix()
        try:
            linhas = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for i, linha in enumerate(linhas, 1):
            if any(a.search(linha) for a in allow):
                continue
            for tipo, rx in PADROES.items():
                if rx.search(linha):
                    # NUNCA imprimir o valor: o log da CI tambem e publico.
                    achados.append(f"{rel}:{i}: possivel {tipo}")
    return achados


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--root", default=".")
    ap.add_argument("--allow", action="append", default=[],
                    help="regex de linha isenta; use para falso positivo conhecido, com comentario")
    a = ap.parse_args(argv)
    achados = scan(Path(a.root), [re.compile(x) for x in a.allow])
    if achados:
        print("DADO PESSOAL EM REPOSITORIO PUBLICO\n")
        for x in achados:
            print("  x", x)
        print("\nO tipo e dito; o valor NAO e impresso (o log da CI tambem e publico).")
        print("Remova o dado. Parametro (zona, area, indice) pode; identificacao, nao.")
        return 1
    print("nenhum padrao de dado pessoal encontrado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
