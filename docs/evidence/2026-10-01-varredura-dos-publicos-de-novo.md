# Varredura de dado pessoal nos repositórios PÚBLICOS — 2026-10-01

Evidência da **PRF-0076** (prova a CLM-0017, supersede a PRF-0052) e da
**PRF-0077** (refuta a CLM-0054, supersede a PRF-0053).

## Por que de novo

Porque a superfície mudou, e **a prova não foi transcrita — foi rodada de
novo.** O PR que trouxe a regra "N itens, N respostas" alterou os três arquivos
que a PRF-0052 e a PRF-0053 cobrem:

```
tools/genome_privacy_check.py     scan() devolve Resultado; arquivo que não se
                                  deixa ler vira NAO_MENSURAVEL
tools/varredura_publica.py        varrer_arvore leva o não-mensurável para a
                                  saída; o relatório volta a dizer QUAL repo
tools/test_varredura_publica.py   inalterado, e é o controle
```

O detector de superfície acusou corretamente — é o que ele existe para fazer.
O comportamento provado, porém, não mudou: o que mudou foi o que acontece
quando um arquivo **não se deixa ler**, caso que não ocorre nos quatro.

## Visibilidade, medida de novo e não suposta

`gh repo view --json visibility`, 2026-10-01:

| repositório | visibilidade |
|---|---|
| liceu-genome | PUBLIC |
| liceu-protocol | PUBLIC |
| liceu-design-tokens | PUBLIC |
| liceu-shell | PUBLIC |

## O que a varredura devolveu

Árvore de trabalho **e** histórico, sete padrões, nos quatro:

```
liceu-genome         0 na árvore,  5 no histórico
liceu-protocol       0 na árvore,  0 no histórico
liceu-design-tokens  0 na árvore,  0 no histórico
liceu-shell          0 na árvore,  0 no histórico
```

Os cinco do histórico são **os mesmos de 2026-09-28**, no mesmo blob antigo:

```
c09ff07:tools/test_genome_check.py:84  CPF
c09ff07:tools/test_genome_check.py:88  e-mail
c09ff07:tools/test_genome_check.py:88  telefone BR
c09ff07:tools/test_genome_check.py:89  CEP
c09ff07:tools/test_genome_check.py:89  matrícula/inscrição imobiliária
```

São as **iscas** dos testes de mutação da FIT-015, e que são iscas está medido,
não suposto: o CPF tem dígitos verificadores inválidos e começa em 123456789, o
marcador canônico; os vizinhos são um domínio de exemplo, um telefone de
cinco-mais-quatro dígitos sequenciais descendentes, a palavra "matrícula"
seguida de seis dígitos em sequência e um CEP com três zeros no sufixo —
**descritos e não reproduzidos**, porque reproduzir a forma num repositório
público é o que a FIT-015 recusa.

Nenhum dos três identificadores do caso real — CPF do proprietário, matrícula
do imóvel, inscrição cadastral — aparece em qualquer commit de qualquer um dos
quatro.

## O que esta evidência NÃO alcança

Os 15 repositórios `PRIVATE` não são objeto da CLM-0017 e não foram varridos.
E a varredura mede a **árvore e o histórico git**; o que já foi clonado por
alguém está fora do alcance de qualquer medição daqui.
