# 2026-10-15 — o contrato da Testemunha: duas proibições aplicadas, uma muda

O `ADR-005 §5.1` nomeia esta como pendente, e a `PRF-0173` do dia 14 estabeleceu
que ela é **a montante** do mecanismo de consenso: se *"votar no log"* nunca
autoriza atos, a camada de consenso é um log e o ônus de correção sob partição
cai muito; se votar autoriza, o consenso entra no caminho de confiança.

**Existe um rascunho pronto desde 2026-10-09** —
`liceu-protocol/docs/2026-10-09-rascunho-contratos-do-plano-de-autoridade.md`,
398 linhas — e ele diz, na própria abertura, que mexer no Producer Registry, no
Contract Registry e no Event Registry **espera a palavra do titular**. Este
documento não o reescreve. Ele mede o que faltava medir para a palavra ser
informada.

---

## 1. O rascunho não envelheceu

| | |
|---|---|
| bloco de `liceu.authority#mother-witness` | ainda nas linhas **560-566** |
| as três proibições | **inalteradas** |

Conferido porque este ecossistema já perdeu um `:617` por envelhecimento de
número de linha, e porque o kit andou de `v0.26.0` a `v0.29.0` entre o rascunho
e hoje.

---

## 2. Das três proibições, **duas são aplicadas por código e uma não é**

| proibição | aplicada? | onde |
|---|---|---|
| **nunca autoriza** | **SIM** | `authority_control_plane.py:273-276` — `if role == "WITNESS" and not event_type.startswith(WITNESS_ALLOWED_PREFIXES)` → recusa `witness_cannot_authorize` |
| **nunca assume o papel da ativa** | **SIM, por consequência** | o papel vem da **identidade autenticada** (`:11`), e `promote()` recusa `promotion_target_not_successor` |
| **nunca estabelece teto** | **NÃO** | zero ocorrências de `teto`, `ceiling`, `scale_cap` ou `max_scale` no control plane inteiro |

A terceira não é violada — ela simplesmente **não é tocada por nada**. É texto
que ninguém lê e ninguém contraria.

---

## 3. E `PROIBICOES`, como chave, **é lida por nada**

Busca nos 19 repositórios, em `.py`, `.sh`, `.yml` e `.yaml`, fora do arquivo que
a declara: **duas** ocorrências, e as duas são a mesma linha de docstring —
`liceu_federation_sdk.py:138`, *"Ver PROIBICOES em publish()"*, mais sua cópia em
`build/`. Prosa que **menciona** o conceito; não código que leia a chave.

Para comparar: `authority_role`, no mesmo bloco, **é lido** por quatro arquivos —
`liceu_conformance.py`, `liceu_registry_check.py`, `app/main.py` e o próprio
control plane.

**Então a aplicação de "nunca autoriza" não deriva do registry: ela vive numa
constante Python.**

```python
# authority_control_plane.py:55
WITNESS_ALLOWED_PREFIXES = ("authority.witness.", "authority.human.decision.")
```

O registry e o código concordam **por coincidência de autoria**, não por
derivação. Se um dia divergirem, nada percebe — e isso é exatamente a classe que
o C25-06 passou um ciclo eliminando, com a `FIT-020` armada para guardá-la.

> **Uma atribuição que eu desconfiei e está CERTA.** O comentário do código diz
> *"(Constituição: 'so autoriza apos promocao valida')"*, e eu fui conferir porque
> o §0 do rascunho pegou a outra atribuição errada — a frase *"só informa, nunca
> autoriza"* é atribuída pelo `ADR-003` à Constituição e **não está lá**, está no
> Producer Registry. Esta, sim, está: `liceu_constitution.yaml:1008`, e fala do
> SUCCESSOR. Desconfiar custou um grep; não desconfiar custaria a emenda no
> arquivo errado.

---

## 4. O voto de Raft **nunca passa pelo portão**

O portão de "nunca autoriza" é sobre o `event_type` de um **publish**: ele roda
dentro de `enforce()`, no caminho de publicação de fato. **Um voto de Raft não é
um fato publicado** — é tráfego do protocolo de consenso.

Isso tem duas consequências, e elas apontam em direções opostas:

- **a favor de escrever a separação:** ela não exige tocar `enforce()`. A tensão
  que o `ADR-003` descreve é **normativa**, não mecânica — o portão nunca veria o
  voto de qualquer forma. Escrever a distinção é redação, como o `ADR-005` já
  dizia, e custa o que custa uma emenda de registry.
- **contra escrevê-la sozinha:** justamente porque o portão não vê o voto,
  **nada verificaria** que o voto não autorizou. A separação existiria só como
  texto, ao lado de um bloco que ninguém lê.

---

## 5. A proposta que torna isto contrato em vez de declaração nº 50

**Mover a lista de prefixos para o Producer Registry, e fazer o CORE derivá-la
de lá.** Não é especulação: o mecanismo já existe.

```
app/services/protocol_kit.py:90   producer_registry=_yaml(directory, "liceu_producer_registry.yaml")
app/services/protocol_kit.py:55   from liceu_protocol import KIT_DIR
app/services/protocol_kit.py:40   return self.producer_registry.get("producers") or {}
```

O CORE **já carrega** o Producer Registry do kit instalado. Trocar
`WITNESS_ALLOWED_PREFIXES` por leitura dessa fonte faz três coisas de uma vez:

1. **"nunca autoriza" deixa de ser texto não lido e passa a ser a FONTE do
   portão.** A proibição governa o comportamento em vez de descrevê-lo.
2. **Satisfaz a regra de classe** que o titular fixou em 2026-10-09:
   *"derivável de outro artefato → não se escreve, se deriva"*. Hoje a lista está
   escrita duas vezes — uma como prosa no registry, outra como tupla no código.
3. **`VOTO_NO_LOG_DE_CONSENSO` passa a ser acrescentado a um bloco que É lido**,
   e não ao lado de um que ninguém abre.

**E a `FIT-020` é o argumento, não o obstáculo:** ela está com gatilho armado e
classe viva em zero. Escrever uma declaração nova agora, sem leitor, repõe um
membro na classe que acabou de ser zerada.

---

## 6. O custo de aplicar, medido

O Producer Registry é **artefato governado** (R13A-D): declara
`constitution_version: 1.18.0` e `constitution_sha256: 29b95fb1…`, com
`registry_version: 1.4.0`.

| | |
|---|---|
| a Constituição | **não** muda — a emenda é no Producer Registry |
| `registry_version` | 1.4.0 → 1.5.0 |
| kit | versão nova + **tag** |
| consumidores | **8 PRs de pino + 8 merges** |

Medido quatro vezes nesta semana: é o custo real, não estimativa. E se a troca da
lista de prefixos entrar no mesmo movimento, o CORE ganha um PR a mais — e o
`test_boundary_conformance.py:165`, que é o estopim do pino, move a mão de novo.

---

## 7. O que este documento **não** decide, e segue do titular

1. **Aplicar ou não.** O rascunho de 09/10 diz que esses arquivos esperam a sua
   palavra, e eu não os toquei.
2. **Se a emenda vem com o leitor ou sem ele.** Escrever a separação sozinha é
   mais barato por um PR e repõe um membro na classe zerada. Eu recomendaria
   **com o leitor**, no mesmo kit.
3. **"Nunca estabelece teto".** Ela não é aplicada por nada. Ou ganha leitor, ou
   sai do registry por não ser norma — é a mesma decisão de classe da `UNK-0018`,
   e ela não foi tomada para este campo.
4. **O nome do quarto evento e o rótulo do `implementation_status`**, que o §6 do
   rascunho já listava como seus.
5. **O portão `P1_07B`**, que o rascunho nomeia: ele foi **fechado em 2026-10-14**
   (`CUMPRIDO — ADR-001 decidida em 2026-09-18`), então essa pendência do §5 do
   rascunho **caiu** — e é a única coisa que mudou nele desde 09/10.
