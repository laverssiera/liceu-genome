# 2026-10-02 — o valor colado que nenhuma varredura vê

Um segredo foi encontrado em claro num arquivo versionado do monólito. Este
documento registra a MEDIÇÃO, feita antes de qualquer conserto, por instrução
expressa do titular: "MEÇA primeiro, e não conserte antes de medir".

**O valor não aparece aqui, nem em lugar nenhum do genoma.** Só a forma e a
impressão. A regra é a mesma da prova de revogação: só fingerprint e evidência,
nunca valor.

## O que é

| | |
|---|---|
| Nome pelo qual é consumido | `CANONICAL_EVENT_STORE_API_SECRET` |
| Nome pelo qual viaja | cabeçalho HTTP `X-Canonical-Service-Secret` |
| Forma | 11 caracteres: maiúscula + minúscula + dígito + símbolo |
| Impressão | sha256 `402f633e52d80787…` |
| Gerado por máquina? | **Não.** Não é hex, não é base64. É senha escolhida por pessoa. |

A forma é o achado mais importante, e é o que a aritmética do incidente não
alcança: um token gerado por máquina só vale no sistema que o emitiu, e
rotacionar fecha o assunto. Uma senha de onze caracteres escolhida por pessoa
pode estar em uso em outro lugar, e nenhuma medição feita neste repositório
consegue responder onde. **Quem sabe isso é o titular, e a pergunta é dele.**

## Onde está, e desde quando

Medido com `git log --all -S <valor>` e varredura de conteúdo sobre a árvore de
trabalho dos 19 repositórios, 18 extensões de texto, 0 arquivos não lidos.

- `CANONICAL_FEDERATION_RESTORATION_REPORT.md`, linhas **87 e 247**
- **2 ocorrências, 1 arquivo, 1 repositório, 1 commit**
- entrou em `e0a0f19`, **2026-08-24**, e nunca saiu
- é ancestral de `origin/main`: está no remoto
- janela de exposição: **39 dias** (24/08 a 02/10)
- **nenhum dos 4 repositórios públicos** contém o valor, em nenhum commit

Na linha 247 ele está dentro de um `curl -H "X-Canonical-Service-Secret: …"`.
Na linha 87, dentro de uma célula de tabela markdown: `| **API Secret
Configured** | YES (…) |`. Guardem-se estas duas formas: elas são a razão pela
qual nenhuma guarda o viu.

### Uma correção, porque ela importa para o tamanho do incidente

A primeira medição desta sessão relatou **81 ocorrências em 11 repositórios, de
2026-08-22**. Estava errada, e o modo de errar é o próprio assunto deste
documento: o script procurou "o token com cara de segredo" na linha, e
`X-Canonical-Service-Secret` tem **exatamente 26 caracteres** e casa com
alfanumérico-mais-hífen. Ele travou no **nome do cabeçalho** e passou ao lado do
**valor**, que estava na mesma linha, depois dos dois pontos. As 81 ocorrências
em 11 repositórios são do nome — e nome não é segredo.

O instrumento que caçava segredo achou nome. É o mesmo erro que a guarda abaixo
precisa cobrir, cometido pela medição do incidente, no dia do incidente.

## Onde é consumido hoje

- `runtime/identity/canonical_federation_client.py:34` — `os.getenv("CANONICAL_EVENT_STORE_API_SECRET", "").strip()`
- `cv-backend-core/app/core/market_duality.py:322` — `settings.CANONICAL_EVENT_STORE_API_SECRET.strip()`, comparado com `hmac.compare_digest` na linha 323
- `execute_w90_real_alignment.py` — passa adiante como `service_secret=`

**Nenhum arquivo de ambiente, em nenhum dos 19 repositórios, atribui valor a
esse nome.** As duas únicas atribuições são
`LICEU_6.0_CONSTRUTORA_VIRTUAL/.env.example:24` e
`HUB-BACKOFICE-LICEU-6.0/.env.example:18`, ambas **vazias** (sha256 do vazio,
`e3b0c44298fc…`). Com a CLM-0062 REFUTED — não há ambiente implantado —, a
consequência é a mesma que o titular tirou da rotação da OpenAI: **não há onde
revogar, porque não há serviço que aceite.** Rotacionar, aqui, é trocar o valor
onde ele vier a ser posto, e não revogar num provedor: não existe provedor.

Isso **não** diminui a regra que o titular enunciou — "segredo commitado é
segredo comprometido". Diminui o que a rotação consegue provar: não há par
aceita/recusa a medir, logo a prova de revogação devolveria `NAO_MENSURAVEL`, e
isso é o resultado certo, não um resultado baixo.

## Quem teve acesso de leitura em 39 dias

Medido via `gh api` em 2026-10-02.

**MEDIDO**

| | |
|---|---|
| visibilidade | `private` |
| forks | **0** |
| watchers | **0** |
| colaboradores | **1** — `laverssiera`, admin |
| deploy keys | **0** |
| ações de terceiro nos workflows | **nenhuma** (todo `uses:` é `actions/*` ou local) |
| execuções de workflow desde 24/08 | **180** (122 CI, 45 Main Guard, 10 Dependency Graph, 3 diag) |
| Codespaces neste repositório | **1**, criado 2026-03-11, estado `Shutdown` |

Cada uma das 180 execuções fez checkout, e checkout escreve o arquivo no disco
do runner. Nenhum passo nomeia o arquivo nem varre `.md` — medido por grep nos
workflows —, então o valor não foi para log de CI por um passo deste
repositório. O Codespace parado contém o arquivo.

**NÃO MENSURÁVEL, e nomeado em vez de suposto**

- **Codespaces apagados na janela.** A API lista 9 Codespaces da conta e os
  apagados não aparecem nela. Não há como enumerar o que foi destruído.
- **Instalações de GitHub App com acesso de leitura.** `repos/.../installation`
  exige JWT de app, que eu não tenho: devolveu 401.

Não escrevo "ninguém mais leu". Escrevo o que medi: a superfície administrativa
é de um titular só, e os dois caminhos que poderiam desmentir isso não são
enumeráveis por mim.

## Por que nenhuma guarda viu

Duas varreduras existem. Nenhuma das duas olharia para ali, e isto está lido na
linha, não lembrado.

**1. O inventário procura NOME, e o vazamento é VALOR.**
`infra/security/inventario_segredos.py:40` define o que conta como segredo:
limite de palavra, seguido de `[A-Z][A-Z0-9_]*` com SECRET, PASSWORD, TOKEN,
API_KEY, CREDENTIAL ou _KEY dentro. **Só nome, e só nome em maiúsculas.** E a
linha 108, `ATRIBUICAO`, só extrai um valor quando existe um nome assim à
esquerda de `=` ou `:`.

O comentário logo acima da linha 40, que eu mesmo escrevi, diz: "Deliberadamente
largo: e melhor listar um nome que nao e segredo do que deixar um de fora." A
largura é no eixo errado. `X-Canonical-Service-Secret` é cabeçalho HTTP —
minúsculas e hífens —, logo não casa com `[A-Z][A-Z0-9_]*`. E a linha 87 não é
atribuição nenhuma: é célula de tabela. **Nenhuma das duas formas é alcançável
pelo padrão**, por construção e não por descuido de configuração.

**2. A varredura de privacidade só olha repositório público.**
A CLM-0017 afirma, na sua própria letra: "O genoma e os repositorios publicos do
LICEU nao contem dado pessoal do caso real". E a PRF que a prova diz, no fim da
nota: "A afirmacao vale para os PUBLICOS: os 15 privados nao sao objeto da
CLM-0017 e nao foram varridos por esta prova." O monólito é privado. Está fora
do escopo declarado, e sempre esteve.

Juntas: uma guarda certa no alvo errado, e outra certa no escopo errado. O
vazamento caiu exatamente na interseção dos dois buracos, e ficou lá 39 dias.

## O que a guarda precisa ter, quando vier

Por instrução do titular: "A guarda vem depois — e quando vier, com controle
positivo cuja amostra contenha um valor colado, e não só um nome de variável."

1. Amostra do controle positivo com um **valor colado em prosa**, sem nome de
   variável à esquerda: numa célula de tabela markdown e dentro de um `curl -H`.
   As duas formas deste incidente.
2. Escopo que inclui **repositório privado** — a varredura de privacidade não o
   faz, e o diagnóstico está em que ninguém olhava.
3. A amostra montada por **concatenação**, como a FIT-015 já exige, para a
   própria amostra não acusar o arquivo da guarda.
4. Decisão explícita sobre o eixo: casar por **forma e entropia** do valor é o
   que pega senha curta escolhida por pessoa, e é também o que produz falso
   positivo em prosa comum. A guarda não existe sem essa decisão tomada, e ela
   não está tomada.

## O que este documento não resolve

Duas decisões do titular, e nenhuma delas é minha:

- **Reescrever o histórico ou aceitar a exposição por escrito.** A reescrita é
  um commit só (`e0a0f19`), ancestral de `origin/main`; ela invalida todo hash
  posterior e, com a guarda de superfície do genoma ativa, derruba a CI de toda
  prova cujo `mechanism` aponte para o monólito.
- **Se essa senha de onze caracteres vive em outro lugar.** A medição não
  alcança, e a pergunta é do titular.
