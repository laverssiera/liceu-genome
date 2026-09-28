# Varredura de dado pessoal nos repositórios PÚBLICOS — 2026-09-28

Evidência da PRF-0052 (prova a CLM-0017) e da PRF-0053.

## O que foi varrido, e por que estes quatro

A visibilidade foi **medida**, não suposta, com `gh repo view --json visibility`
nos 19 repositórios do ecossistema. Quatro são `PUBLIC`; os outros quinze são
`PRIVATE` e não são objeto da CLM-0017.

| repositório | visibilidade |
|---|---|
| liceu-genome | PUBLIC |
| liceu-protocol | PUBLIC |
| liceu-design-tokens | PUBLIC |
| liceu-shell | PUBLIC |

Os dois últimos **nunca tinham sido varridos**: o `genome_privacy_check` dizia no
próprio cabeçalho que servia "ao liceu-genome e ao liceu-protocol (os dois
públicos)".

## Método

- sete padrões, os mesmos do `genome_privacy_check`, **importados** e não
  reescritos — dois vocabulários de "o que é dado pessoal" seriam duas verdades;
- **árvore de trabalho e histórico**. O histórico de um repositório público
  também é público: apagar não é remover, e o blob segue entregue a quem clonar;
- o valor encontrado **nunca** é impresso: só o tipo, o arquivo e o commit. Log
  de CI de repositório público também é público.

## Saída

```
liceu-genome: 2 na arvore, 5 no historico
   arvore     genome/07-proofs.yaml:930: possivel matricula/inscricao imobiliaria
   arvore     genome/07-proofs.yaml:930: possivel CEP
   historico  c09ff07:tools/test_genome_check.py:84: CPF
   historico  c09ff07:tools/test_genome_check.py:88: e-mail
   historico  c09ff07:tools/test_genome_check.py:88: telefone BR
   historico  c09ff07:tools/test_genome_check.py:89: CEP
   historico  c09ff07:tools/test_genome_check.py:89: matricula/inscricao imobiliaria
liceu-protocol: 0 na arvore, 0 no historico
liceu-design-tokens: 0 na arvore, 0 no historico
liceu-shell: 0 na arvore, 0 no historico

7 achado(s) em 4 repositorio(s). O valor nao aparece aqui de proposito: va no arquivo.
```

## Os cinco achados são iscas, e isso foi medido

Todos no **mesmo blob antigo** (`c09ff07`) de `tools/test_genome_check.py`,
linhas 84 a 89 — as amostras dos testes de mutação da própria FIT-015.

Que são iscas e não dado real não é suposição:

- o CPF tem **dígitos verificadores inválidos** e começa em `123456789`, o
  marcador canônico;
- os vizinhos são descritos e **não reproduzidos**, porque reproduzir a forma
  num repositório público é o que a FIT-015 recusa — e ela recusou este próprio
  arquivo na primeira escrita: exemplo.com.br, um telefone de cinco-mais-quatro digitos sequenciais descendentes, a palavra matricula seguida de seis digitos em sequencia, e um CEP do proprio municipio com tres zeros no sufixo.

E o arquivo de hoje já monta essas amostras por **concatenação**, justamente
para não casar com o próprio padrão — por isso a árvore está limpa e só o blob
antigo acusa.

Nenhum dos três identificadores que o caso real carrega — CPF do proprietário,
matrícula do imóvel, inscrição cadastral — aparece em qualquer um dos quatro, em
qualquer commit.

## A primeira versão desta varredura mentia

Ela usava `git grep -E`. O grep do git fala ERE POSIX e não conhece as classes
de dígito e de fronteira de palavra do Python, e os padrões estão em sintaxe
Python: CPF, CEP e telefone casavam **nada**, em silêncio. Só o padrão de e-mail,
que usa classes literais, funcionava — e foi ele que deu o único acerto da
primeira rodada, escondendo que os outros seis estavam cegos.

Trocada por ler cada blob e aplicar o **mesmo** `re` da árvore. A prova de que
enxerga é isca plantada em repositório temporário, e a prova por mutação
(voltando ao `git grep`) derruba três testes.

**Zero achados não se distingue de varredura quebrada sem uma isca que se saiba
estar lá.**
