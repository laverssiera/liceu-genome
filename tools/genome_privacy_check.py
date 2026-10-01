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
Saida 0: nada encontrado, E a varredura mediu — a frase traz o numero de
arquivos conferidos. 1: encontrou (imprime arquivo, linha e o TIPO — nunca o
valor inteiro). 2: NAO MENSURAVEL — algum arquivo nao se deixou ler, e o que
nao foi lido nao foi aprovado.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import varredura

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


def alvos(root: Path) -> list[Path]:
    """Os arquivos que esta varredura se propoe a conferir — o DENOMINADOR."""
    return [f for f in sorted(root.rglob("*"))
            if f.is_file() and f.suffix.lower() in EXTENSOES
            and not any(parte in IGNORAR for parte in f.parts)]


def scan(root: Path, allow: list[re.Pattern] | None = None) -> varredura.Resultado:
    """Um arquivo, uma resposta. Arquivo que nao se deixa ler NAO conta limpo.

    Antes de 2026-10-01 isto era `except OSError: continue`: o arquivo sumia da
    conta, e o silencio dele era lido como limpeza — num guarda que protege
    repositorio PUBLICO de dado pessoal. Agora a varredura inteira vira
    NAO_MENSURAVEL, com o nome do arquivo e o motivo.
    """
    allow = allow or []

    def conferir(f: Path) -> list[str]:
        rel = f.relative_to(root).as_posix()
        # Sem try: a excecao E a resposta "nao consegui ler", e quem a trata e
        # a regra de varredura, nao este laco.
        linhas = f.read_text(encoding="utf-8", errors="replace").splitlines()
        achados = []
        for i, linha in enumerate(linhas, 1):
            if any(a.search(linha) for a in allow):
                continue
            for tipo, rx in PADROES.items():
                if rx.search(linha):
                    # NUNCA imprimir o valor: o log da CI tambem e publico.
                    achados.append(f"{rel}:{i}: possivel {tipo}")
        return achados

    return varredura.responder_por_item(
        alvos(root), conferir, nome=lambda f: f.relative_to(root).as_posix())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--root", default=".")
    ap.add_argument("--allow", action="append", default=[],
                    help="regex de linha isenta; use para falso positivo conhecido, com comentario")
    a = ap.parse_args(argv)
    r = scan(Path(a.root), [re.compile(x) for x in a.allow])
    achados = [x for lista in r.respostas for x in lista]
    if achados:
        print("DADO PESSOAL EM REPOSITORIO PUBLICO\n")
        for x in achados:
            print("  x", x)
        print("\nO tipo e dito; o valor NAO e impresso (o log da CI tambem e publico).")
        print("Remova o dado. Parametro (zona, area, indice) pode; identificacao, nao.")
        return 1
    # Achado nenhum so vira aprovacao quando a varredura MEDIU, e o numero de
    # arquivos vai SEMPRE na frase: sem ele, quem le nao distingue um
    # repositorio limpo de uma varredura que nao leu nada.
    if not r.mediu:
        print(r.resumo())
        return 0 if r.estado == varredura.NADA_A_CONFERIR else 2
    print(f"nenhum padrao de dado pessoal encontrado em {r.itens} arquivo(s) conferido(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
