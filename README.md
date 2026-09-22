# Genoma LICEU 6.0

**Uma lei, um grafo, um juiz.**

```
schema/genome.schema.json   a lei — 11 tipos de nó
genome/*.yaml               o grafo — o estado do LICEU, só com fatos verificados
tools/genome_check.py       o juiz — valida, deriva, avalia e responde
tools/test_genome_check.py  o juiz sendo julgado — mutações e 1 controle positivo
requirements.txt            o kit liceu-protocol, na tag vigente — a FIT-010 julga contra ele
```

## O genoma não é a segunda fonte da verdade sobre contratos (FIT-010)

Produtor, versão e lifecycle de cada contrato vivem no Contract Registry do kit
(`liceu-protocol`), instalado na tag fixada em `requirements.txt`. O `03-contracts.yaml`
guarda **só o que o kit não tem**: `emitters_observed`, `implementation_observed`,
`chain_position`, `carries`. Para todo contrato com `in_registry: true`, o juiz confere
`producer` e `lifecycle` contra o kit instalado — divergência é violação nova (FIT-010) e
a CI falha. Contrato que o kit tem e o genoma declara `in_registry: false` também falha:
é o genoma atrás do kit. No bump do kit, o genoma é obrigado a acompanhar.

Sem o kit instalado o juiz não julga. Vendorizar uma cópia do registry aqui seria
exatamente a duplicação que a FIT-010 existe para impedir.

## Por que um grafo, e não 50 motores

O documento do genoma propõe 50 construções. Doze delas cabem aqui como **tipos de nó ou
regras do mesmo grafo**, e não como sistemas separados:

| Proposta do documento | No genoma |
|---|---|
| Knowledge Genome | `knowledge`, com validade, usos permitidos e proibidos |
| Proof Registry | `claim` + `proof`, com status **derivado** |
| Architecture Fitness Functions | `fitness`, avaliada pelo juiz ou ligada a uma afirmação |
| Architecture Debt Ledger | `violation`, com catraca |
| Unknowns Registry, Uncertainty Ledger | `unknown` |
| Contradiction Engine | afirmação `REFUTED` por uma prova |
| Provenance Graph | `location` e `evidence_artifact` de cada prova |
| Constitution-as-Code | invariantes no schema — uma regra, várias superfícies |
| Knowledge / Capability Gap | `unknown` + `ips_gap` nas telas |
| Self-Model | o relatório do juiz |

Os outros 38 continuam como horizonte, e entram quando a vertical precisar deles.

## As quatro regras que viraram estrutura

**1. O status de uma afirmação é derivado, nunca declarado.** O nó `claim` não tem campo de
status: declarar um é erro de schema. O juiz calcula:

```
alguma prova refuta               → REFUTED
alguma prova com observação externa e artefato de evidência → PROVEN
alguma prova por teste            → TESTED
nenhuma                           → UNPROVEN
```

Ler código ou registro pode **refutar**, mas nunca **provar** comportamento. A contagem da
cadeia é a soma dos elos `PROVEN`. É isso que impede outro "1/5" contado pelo que o processo
afirmou.

## O genoma esquece: STALE, superfície e expiração

Uma prova cobre **o código de um commit**. Quando esse código muda, a prova precisa ser
feita de novo — e quem sabe disso primeiro é o repositório que mudou.

- **`mechanism: {repo, paths, content_hash, commit}`** — a superfície provada, com precisão
  de arquivo. Repositório inteiro, diretório ou curinga é recusado (FIT-012): ficaria obsoleto
  a cada commit, o genoma viraria ruído e as pessoas passariam a ignorá-lo.
- **A invalidação acontece onde a mudança acontece.** `tools/genome_surface_check.py` roda na
  CI de **cada monólito**: lê este genoma (que é público), filtra as provas que cobrem
  arquivos daquele repo, recalcula o hash e falha ali — *"este PR altera uma superfície provada
  por PRF-XXXX"*. Ninguém precisa de token, ninguém lê repositório privado alheio e ninguém
  escreve no repositório de ninguém. Foi o genoma ser público que tornou isso possível.
- **`expires_at`** — evidência com prazo. Vencida, a afirmação vira **STALE**.
- **STALE não é REFUTED.** Uma refatoração pode mudar o arquivo e manter o comportamento.
  STALE quer dizer "precisa ser provado de novo", não "é falso" — e **não conta na cadeia**.

## A contagem é por escala (FIT-011)

Um elo provado em REGIONAL não conta enquanto o próprio genoma declara REGIONAL
bloqueada — senão a cadeia "atravessaria" numa escala que o grafo diz não estar
disponível. Cada prova de elo declara a `scale` do fato observado (enum federativo da
**Constituição do kit**, não reescrito aqui); escala sem prova de elo mas com bloqueio
aparece com o bloqueio; escala bloqueada imprime `0 elos contam` e, entre colchetes, quem
a bloqueia — e quanto **haveria** se não estivesse. Prova de elo sem `scale`, ou com escala
fora do enum, é violação nova.

**2. Uma dimensão, uma definição.** Cada valor de estado pertence a um nó `dimension` só,
como decidiu o C6-SM-01. Valor produzido pelo código fora da dimensão é violação.

**3. A tela só exibe o que declara.** `displays` é uma lista de permissão. A tela não pode
exibir uma dimensão que nenhum contrato lido transporta, nem `decision_result` sem ler o
contrato de quem tem `may_authorize`. O papel do JOHN numa tela não aceita `AUTHORIZES`: o
valor não existe no schema.

**4. A validade mora no conhecimento, e não no link.** O link declara o **uso**
(`used_as`); o juiz junta com a validade do nó. Se a validade estivesse no link, cada mudança
de `PROPOSTA` para `VIGENTE` deixaria dezenas de cópias desatualizadas.

## Provas têm tempo

Uma prova refuta ou prova o código de **um commit**. Quando o código muda, a refutação não
pode continuar valendo sobre um código que não existe mais — e apagá-la destruiria a
história. Por isso a prova tem `supersedes: [PRF-…]`: a prova nova encerra a validade da
antiga sem apagá-la. O juiz deriva **só das provas vigentes** (as que nenhuma outra
supersede) e mostra a história: `REFUTED por PRF-0007 até 2026-09-22; TESTED por PRF-0012
desde então`. Supersedes para prova inexistente é aresta quebrada; ciclo de supersessão é
recusado; apagar a prova refutada em vez de superseder deixa a dívida no código obsoleta, e
a catraca acusa. **Nenhuma prova é apagada, nunca.**

## A catraca

```
violação detectada que não está no livro   → a CI falha
dívida no livro que não é mais detectada   → a CI falha: remova-a
```

O genoma não piora sem que alguém registre, e não guarda dívida já paga.

## O que o juiz também pega: o YAML que trunca em silêncio

`asserted_by: CORE #50` é lido pelo YAML como `asserted_by: CORE`. O `#50` vira comentário,
e o schema não vê nada, porque o valor truncado continua sendo uma string válida. O juiz
recusa qualquer valor sem aspas que contenha ` #`. Isso foi encontrado construindo este
genoma: três afirmações perdiam a origem em silêncio.

## Como promover uma afirmação

Não se edita o status. Registra-se uma prova:

```yaml
- id: PRF-0010
  kind: proof
  title: elo 1 observado num CORE real
  proves: [CLM-L1]
  basis: external_observation
  external_observation: {instrument: connz + subscriber, observed: "..."}
  evidence_artifact: {repo: LICEU_6.0_CONSTRUTORA_VIRTUAL, path: docs/evidence/....md}
  environment: durable
  date: "2026-09-22"
```

Na próxima execução, o `CLM-L1` passa a `PROVEN` e a cadeia sobe para `1/5`.

## Rodar

```
pip install pyyaml jsonschema
python tools/test_genome_check.py
python tools/genome_check.py --html self-model.html
```
