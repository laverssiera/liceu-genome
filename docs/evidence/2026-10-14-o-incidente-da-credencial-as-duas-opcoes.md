# 2026-10-14 — o incidente da credencial: as duas opções, prontas

**O valor não aparece aqui, nem em lugar nenhum do genoma.** Só a impressão, a
forma e o alcance. A medição abaixo foi feita **sem passar o valor por argv** —
nem `git log -S<valor>`, nem `git grep <valor>` —, porque argumento aparece na
lista de processos e no histórico do shell. Ela percorre o grafo de objetos com
`git cat-file --batch` alimentado por stdin e testa pertinência em memória.

```
impressão   402f633e52d80787…           (sha256 do valor; confere com a PRF-0113)
nome        CANONICAL_EVENT_STORE_API_SECRET
forma       11 caracteres · maiúscula, minúscula, dígito e símbolo · não gerado por máquina
provedor    NENHUM — não há onde revogar, porque não há serviço que aceite
```

---

## 1. O que está medido, definitivamente

### Onde o valor está

| | |
|---|---|
| arquivo | `CANONICAL_FEDERATION_RESTORATION_REPORT.md`, linhas **87** e **247** |
| ocorrências | **2**, em **1** arquivo, **1** repositório, **1** commit |
| commit | `e0a0f19`, **2026-08-24**, ancestral de `origin/main` |
| repositório | `LICEU_6.0_CONSTRUTORA_VIRTUAL` — **privado** |
| **ainda no HEAD** | **SIM** |
| janela de exposição | **51 dias** (24/08 → 14/10). Eram 39 em 02/10. |

### Não está em nenhum repositório público

Varredura do **grafo de objetos inteiro** de cada público — todos os refs, todos
os commits, todas as tags:

| repositório | objetos | refs | ocorrências |
|---|---|---|---|
| `liceu-design-tokens` | 26 | 5 | **0** |
| `liceu-genome` | 1019 | 130 | **0** |
| `liceu-protocol` | 382 | 73 | **0** |
| `liceu-shell` | 20 | 5 | **0** |
| `LICEU_6.0_CONSTRUTORA_VIRTUAL` *(controle positivo)* | 2926 | 95 | **2** |

**O controle positivo é o que dá valor aos zeros.** Varredura que não acha onde
se sabe que está não prova ausência em lugar nenhum.

> **Correção da premissa do item:** ele lista **cinco** repositórios públicos, e
> `liceu-core-schemas` **não existe** sob a conta. São **quatro**.

### Não está em log de CI, artefato de build ou pacote publicado

| | |
|---|---|
| releases nos quatro públicos | **0** em todos |
| passos `upload-artifact` no CONSTRUTORA | **0** — não há caminho para a árvore sair como artefato |
| `set -x`, `printenv`, despejo de ambiente | **0** |
| workflows que nomeiam o arquivo | **0** |
| arquivos de build versionados nos públicos | 2, em `liceu-design-tokens` — e os dois estavam no grafo varrido, com 0 acertos |

O pacote publicado do kit é instalado **por tag de git** do `liceu-protocol`, e
as tags entraram na varredura (73 refs).

### Não existe fork de nada

`forkCount = 0` em **todos os 21** repositórios da conta.

> **Segunda correção, e ela é maior:** a conta tem **21** repositórios, não 19.
> `Nateli-` e `Tation-Engenharia-Solu-o-02-` são privados e **nunca estiveram no
> universo "os 19 repositórios rastreados"** que toda prova deste ecossistema
> declara. **Foram varridos agora, pela primeira vez:** 692 e 4903 objetos,
> **zero ocorrências do valor e zero do nome**. O achado que sobra não é sobre
> esta credencial — é que o universo declarado em toda prova do genoma cobre
> **19 de 21**, e os dois de fora nunca entraram em medição alguma.

---

## 2. O que é NÃO-MENSURÁVEL, nomeado em vez de estimado

- **Se a senha de 11 caracteres é reutilizada fora dos repositórios.** Não há
  como saber, e não se estima. É o item que o próprio pedido já declarava.
- ~~**Os dois repositórios fora do universo**~~ — **medidos em 2026-10-14, e
  saíram desta lista.** Eu os havia classificado como "mensuráveis com
  trabalho", e o trabalho era clonar e varrer. Feito, pelo mesmo percurso de
  grafo de objetos: `Nateli-` com 692 objetos e `tation.git` com 4903, **zero
  ocorrências do valor e zero do nome** em ambos. Os clones foram apagados
  depois da medição.
- **O conteúdo das 245 execuções de CI.** Medi que nenhum passo nomeia o
  arquivo, que não há `upload-artifact` e que não há rastro de shell — mas não
  li 245 logs. O que está medido é a **ausência de caminho**, não a ausência de
  ocorrência.
- **Instalações de GitHub App com acesso de leitura.** Já declarado
  não-mensurável no documento de 02/10.
- **O Codespace parado** criado em 2026-03-11 contém o arquivo. Quem leu o disco
  dele não é enumerável.
- **Os checkouts apagados.** Cada uma das 245 execuções escreveu o arquivo no
  disco de um runner.

---

## 3. Opção A — reescrita de histórico

### O raio, medido

| | |
|---|---|
| ramos remotos a reescrever | **69** |
| tags | **0** |
| commits depois do `e0a0f19` em `main` | **169** |
| PRs abertos | **0** |
| submódulos apontando para o repo | **0** |
| **consumidores que pinam este repositório** | **0** |

> **Terceira correção da premissa:** o item diz que a opção A tem *"a
> consequência para os 8 repos que consomem o pacote pinado (re-pin
> obrigatório)"*. **Não tem.** Os oito pinam `liceu-protocol`, e o valor está no
> `LICEU_6.0_CONSTRUTORA_VIRTUAL`. **Re-pin não é necessário**, e isso torna a
> opção A muito mais barata do que o item supunha.

### O roteiro

```bash
# 0. ANTES DE QUALQUER COISA: espelho completo, fora da máquina de trabalho.
git clone --mirror https://github.com/laverssiera/LICEU_6.0_CONSTRUTORA_VIRTUAL.git \
    backup-construtora-2026-10-14.git

# 1. instalar a ferramenta (git-filter-branch é obsoleto e lento com 69 ramos)
pipx install git-filter-repo

# 2. trabalhar sobre um clone-espelho NOVO, nunca sobre a árvore de trabalho
git clone --mirror https://github.com/laverssiera/LICEU_6.0_CONSTRUTORA_VIRTUAL.git rewrite.git
cd rewrite.git

# 3. o valor vai num ARQUIVO, nunca em argv — argumento aparece em `ps` e no
#    histórico do shell. O arquivo é criado fora do repositório e apagado depois.
#    Formato de --replace-text: uma linha `literal:<valor>==><substituto>`
#    Escreva-o com um editor; não use `echo`, que também vai para o histórico.
git filter-repo --replace-text ../substituicao.txt

# 4. conferir que saiu — pelo mesmo método da medição, sem argv
#    (o script da medição, apontado para rewrite.git, tem de devolver 0)

# 5. empurrar os 69 ramos reescritos
git push --force --mirror

# 6. apagar o arquivo de substituição e o clone de trabalho
shred -u ../substituicao.txt && rm -rf ../rewrite.git
```

### O que a opção A custa

- **Todo clone local existente fica inválido.** Quem tiver clone precisa
  re-clonar; `git pull` vai divergir em 69 ramos.
- **As 245 execuções de CI passam a referenciar SHAs que não existem mais.**
  Logs e anotações ficam órfãos. Não é perda de dado, é perda de rastreabilidade.
- **O commit `e0a0f19` e os 169 depois dele mudam de SHA.** Qualquer prova do
  genoma que cite SHA deste repositório precisa ser reconferida — e há provas
  que citam, inclusive `mechanism.commit` de superfícies provadas.
- **Não remove o valor dos lugares fora do git:** o Codespace parado, os discos
  dos runners já apagados, e qualquer cópia que alguém tenha feito.

---

## 4. Opção B — aceitação por escrito

### O texto, pronto para assinar

> **Aceitação de risco residual — incidente de credencial, 2026-10-14**
>
> Eu, titular do ecossistema LICEU 6.0, aceito por escrito o risco residual do
> incidente da credencial de impressão `402f633e52d80787…`, nome
> `CANONICAL_EVENT_STORE_API_SECRET`, e **decido não reescrever o histórico** do
> repositório `LICEU_6.0_CONSTRUTORA_VIRTUAL`.
>
> **Aceito com base no que está medido:** 2 ocorrências em 1 arquivo, 1 commit
> (`e0a0f19`, 2026-08-24), exclusivamente num repositório **privado**; **zero**
> ocorrências nos quatro repositórios públicos, varridos no grafo de objetos
> inteiro com controle positivo; **zero** forks em todos os 21 repositórios da
> conta; **zero** releases publicadas; nenhum passo de CI que nomeie o arquivo,
> suba a árvore como artefato ou ligue rastro de shell; e **provedor nenhum** —
> não há serviço que aceite este valor, logo não há sessão a revogar.
>
> **Aceito sabendo o que não está medido**, e o aceito como risco: se a senha de
> 11 caracteres é reutilizada fora dos repositórios; o conteúdo das 245
> execuções de CI; as instalações de GitHub App com acesso de leitura; o
> Codespace parado de 2026-03-11, que contém o arquivo; os discos de runner já
> apagados; e qualquer cópia feita por quem teve acesso de
> leitura. *(Os dois repositórios privados fora do universo — `Nateli-` e
> `Tation-Engenharia-Solu-o-02-` — foram varridos em 2026-10-14 e estão limpos:
> zero do valor e zero do nome.)*
>
> **Condição desta aceitação:** o valor sai do `HEAD` por commit normal, e esta
> credencial **nunca** é usada em ambiente algum. Se um dia vier a ser usada, a
> aceitação caduca e a reescrita volta à mesa.
>
> Data: __________   Assinatura: __________

### O que a opção B custa

- **O valor permanece recuperável** por quem tiver, hoje ou amanhã, acesso de
  leitura ao repositório privado — inclusive por qualquer GitHub App já
  instalada.
- **A janela não fecha, ela congela.** Hoje são 51 dias; sob a opção B o número
  para de crescer só quanto a *novos* checkouts, e não quanto a acesso ao
  histórico.

---

## 5. O passo que as duas opções compartilham

**O arquivo ainda está no `HEAD`.** Enquanto estiver, cada novo checkout
reescreve o valor no disco de um runner — foram **65 execuções** só entre 02/10
e hoje.

Então, nas duas opções, o primeiro ato é o mesmo: **remover o valor do `HEAD` por
commit normal.** Sob a opção A isso é redundante (a reescrita o remove de toda
parte), mas é o que impede a exposição de crescer enquanto a reescrita é
preparada. Sob a opção B é **condição**: sem ele, não é aceitação de exposição
passada — é exposição em curso.

---

## 6. O que eu recomendaria, em uma linha

**B**, porque as três coisas que a reescrita compraria — ausência nos públicos,
ausência de fork e ausência de provedor onde revogar — já estão medidas como
verdadeiras, e o que ela **não** compra (Codespace, runners, reuso fora) é
justamente o risco que sobra nas duas.

**A condição que mudaria isso para A foi medida, e é falsa.** Eu havia escrito
que recomendaria A se os dois repositórios fora do universo contivessem o valor.
Clonei os dois e varri: **zero do valor e zero do nome**, em 692 e 4903 objetos.
A recomendação fica **B**, sem condição pendente.

**O que ainda reabriria a mesa:** a credencial ser usada em algum ambiente. Hoje
o provedor é nenhum e nenhum arquivo de ambiente lhe atribui valor — se isso
mudar, a aceitação caduca por cláusula própria.
