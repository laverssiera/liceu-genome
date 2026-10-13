# 2026-10-12 — a cobertura declarada de busca (FIT-019)

O primeiro item do ciclo 25, e primeiro por uma razão declarada pelo titular: ele
**rebaixa provas já aceitas**, e fazer isso depois de empilhar trabalho em cima
delas seria descobrir tarde que o chão não estava lá.

---

## 1. O defeito, medido duas vezes no mesmo dia

A `PRF-0124` registra que eu afirmei *"nada fixa a versão 0.24.0"* apoiado numa
busca que não cobria o arquivo que fixava — a CI achou o portão em
`test_boundary_conformance.py:165`. Horas depois, a `PRF-0128` registra o mesmo
defeito outra vez: afirmei *"nada lê esses campos"* com uma busca mais estreita
que a própria frase, e tive de reescrever o corpo do PR explicando por quê.

As duas vezes o erro não foi a medição: foi **não ter escrito onde procurei**.
Afirmação negativa — "nada lê", "não existe tal chamada" — só vale com o escopo
que **acharia o contrário**. E quem lê a prova depois não tem como saber se ela
foi feita, se o escopo não está lá.

---

## 2. As duas medições que precederam o desenho

### a. A catraca existe, e tem dois braços

`def ratchet()` em `tools/genome_check.py`, com dois braços que leem de lugares
diferentes:

| braço | lê | dispara |
|---|---|---|
| 1 | `self.findings` contra o livro de dívida | `VIOLAÇÃO NOVA` · `DÍVIDA OBSOLETA` |
| 2 | `self.status[claim]` das dívidas `detection: code` | `DÍVIDA OBSOLETA` se a afirmação não está `REFUTED` |

Três fatos decidiram o desenho:

- **`self.findings` tem uma única porta**, `def find()`. Então se uma fitness
  trava a catraca ou não é escolha de desenho, não consequência inevitável.
- **O livro está vazio**: `genome/10-violations.yaml` não tem nenhuma entrada.
  Com zero entradas, `self.stale` do braço 1 é vazio e o laço do braço 2 nunca
  executa.
- **Uma FIT-019 que chamasse `find()` 40 vezes** produziria 40 `VIOLAÇÃO NOVA` e
  sairia com código 4 na primeira execução.

### b. O raio: 40 provas, 37 afirmações

```
provas no grafo: 128      vigentes: 94
por basis (vigentes): test 39 · record_reading 20 · code_reading 20 · external_observation 15
ALVO: 40      que já tinham scope: 0      que caem: 40
AFIRMAÇÕES QUE PERDEM TODA A SUSTENTAÇÃO: 37      com sustentação parcial: 0
```

O zero da coluna "já tinham scope" é **tautológico** e fica dito: o campo não
existia no schema antes deste commit.

**Zero com sustentação parcial** é o que torna o efeito binário: as 37 são
sustentadas exclusivamente por `refutes` dessas 40, então todas vão de `REFUTED`
para `STALE` — "prove de novo", nunca "é falsa".

---

## 3. O desenho: veredito, não achado

A FIT-019 **não emite achado**. Marca a prova como indeterminada e reusa o mesmo
mecanismo de `expired`: a prova deixa de viger, e o `had_any` do juiz faz a
afirmação cair em `STALE` em vez de `UNPROVEN`. O comentário que já estava no
juiz descreve exatamente o estado certo para insuficiência declarada:

> Não é UNPROVEN — é "prove de novo".

Como `findings` não é tocado, **o braço 1 não dispara e nenhuma isenção precisa
existir para ele**. Era a brecha que o titular temia, e ela foi evitada por não
ser necessária, não por ser bem calibrada.

---

## 4. Por que lista fechada de ids, e não predicado de data

O plano do ciclo pedia `instrument_introduced` com **id da FIT + data**. Essa
forma tem furo, e o furo é preciso:

> um rebaixamento causado por instrumento e um rebaixamento causado por
> regressão têm **a mesma forma**. Se o critério de isenção é "prova anterior a
> tal data", então (i) qualquer prova retrodatada ganha isenção, e (ii) uma
> regressão real que caia na mesma fitness no mesmo dia é indistinguível.

O teste de mutação que o titular exigiu é justamente o que denunciaria isso — e
eu não conseguiria fazê-lo passar honestamente.

A **lista fechada de ids** não tem esse furo:

- prova **nova** nasce fora da lista;
- prova **editada** não ganha isenção de conteúdo — o lacre confere o conjunto de
  ids, e uma prova da lista continua sem viger, logo não sustenta nada;
- a lista **só encurta**: um id sai dela quando a prova ganha escopo completo.

**O lacre é um teste.** O `sha256` da lista ordenada está congelado em
`tools/test_genome_check.py::ListaFechada`:

```
299f4bed433112f7790659f0ab90b813469eac1115cee963de7c06cc18cdffa0
```

Acrescentar um id reprova a CI antes de isentar coisa alguma. E há a mutação do
próprio lacre — `test_acrescentar_um_id_quebra_o_lacre` —, sem a qual o sha
congelado seria enfeite.

### A direção da isenção

Vale registrar o que a isenção faz quando acerta e quando erra. Ela suprime a
mensagem *"remova do livro"*. Ou seja: **mantém dívida registrada**. Se um dia
ela errar, erra **guardando** dívida, nunca perdoando-a. Há teste para a direção:
`test_a_isencao_so_MANTEM_divida_nunca_apaga`.

---

## 5. O resultado, pelo instrumento

```
COBERTURA DECLARADA DE BUSCA (FIT-019) — insuficiência declarada, não violação
  provas de leitura vigentes ............. 40
  com `scope` completo ................... 0
  INDETERMINADAS ........................ 40
    na introdução do instrumento (FIT-019 em 2026-10-12), lista fechada: 40
    DEPOIS da introdução, sem isenção nenhuma: 0
  afirmações que perderam toda a sustentação: 37
```

`RESULTADO: ÍNTEGRO — nenhuma violação nova`, código de saída 0. A catraca não
disparou, que é o desenho funcionando e não a catraca falhando: há 15 testes
novos, e um deles (`test_perda_MISTA_dispara_a_catraca`) prova que ela dispara
quando deve.

**A cadeia não se moveu**: `LOCAL` segue estrutural 3/5 e substantiva 0/5, e a
`REGIONAL` segue bloqueada pelos mesmos 3 itens. `blocked_scales` testa
`!= "PROVEN"`, e `REFUTED` e `STALE` bloqueiam igual.

### A `CLM-0006` está entre as 37

É um dos três itens continentais do ciclo, e suas duas refutações — `PRF-0006` e
`PRF-0058` — são de leitura e sem escopo. A consequência para o portão é
**nenhuma**, pelo motivo do parágrafo acima; a consequência para o ciclo é que a
`CLM-0006` agora diz a verdade mais fraca e mais exata: *não se sabe*.

### E a FIT-019 rebaixa as provas que a justificam

`PRF-0124`, `PRF-0127`, `PRF-0128` e `PRF-0129` estão nas 40. A base de
evidência da própria regra está, desde hoje, em insuficiência declarada. Não é
argumento contra o instrumento — é a medida de que o retrofit é o trabalho, e
não um detalhe.

---

## 6. As 40 ficam em INDETERMINADO — decisão do titular, 2026-10-12

Para as provas recentes eu mesmo rodei os comandos e poderia reconstruir o
escopo. Para `PRF-0001`, `PRF-0006` e `PRF-0014` eu não rodei, e **escrever
escopo que eu não executei seria inventar a medição** — exatamente o que esta
fitness combate.

A decisão foi: **lista fechada, e as antigas aceitas em INDETERMINADO**. Não é
dívida com prazo nem incógnita aberta: é o registro de que 40 provas medem o que
alguém olhou, e não se sabe o que existe.

---

## 7. O que a FIT-019 **não** faz

- **Não julga se o escopo é bom.** `universo: "o repositório"` passa. Ela cobra
  que o escopo exista e esteja completo. Isso move a pergunta de *"o autor
  buscou direito?"* para *"o autor disse onde buscou?"* — e só a segunda é
  verificável por quem lê.
- **Não cobra prova por teste nem por observação externa.** Essas têm
  `mechanism`, `evidence_artifact` e `environment`, que são outra conversa.
- **Não exige `scope` no schema.** Ausência é veredito, não má-formação. Exigir
  no schema mataria o juiz na validação, antes de qualquer veredito; e a lista de
  isenção teria de ser escrita **duas vezes**, no schema e na fitness, que é a
  objeção do ADR-002 e a regra de classe de 2026-10-09. O schema exige a
  **forma**: `scope` escrito pela metade é erro duro, porque meio escopo engana
  mais que escopo nenhum.

---

## 8. Uma consequência que contraria regra vigente, e fica dita

**O denominador da maquinaria sobe: 30 → 31.**

`machinery_of()` é derivado — `len(fitness) + len(kinds do schema)` —, e eram 18
+ 12. A FIT-019 faz 19 + 12. A regra em vigor era *"o denominador do genoma não
sobe"*, e quem a move é a própria ordem do ciclo 25, que manda construir a
FIT-019 primeiro e a FIT-020 depois (que levaria a 32).

Isto não está sendo decidido aqui. Está sendo **medido e exposto**, porque o
número que o juiz imprime é o único que vale, e ele vai imprimir 31.
