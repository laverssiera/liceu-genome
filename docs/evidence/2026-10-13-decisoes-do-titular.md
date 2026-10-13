# 2026-10-13 — decisões do titular, e o que elas não são

Pela regra final de 2026-10-09: **decisão, execução e comprovação são estados
distintos.** Nada neste documento é prova, e nada aqui autoriza contar nada como
feito.

---

## D-CLM-0006 — a leitura é (b), e o motivo é mais forte que o ADR-003 §4

A pergunta era se "a Testemunha observa a Ativa de forma independente" se
mede pelo **ato de observar** (a) ou por um **caminho que não termine no mesmo
armazenamento** (b).

A decisão é **(b)**, e a razão dada não é a redação do ADR-003 — é o achado do
C25-03:

> toda concordância que este sistema já aceitou veio de literal escrito à mão.
> Sob a leitura (a), a Testemunha seria "provada observadora" enquanto o que
> ela observa é uma string que alguém digitou. Os bloqueadores cairiam de 3
> para 2 e nada no sistema teria mudado — que é a definição exata de
> declaração melhorando um número. É o que o PFC existe para impedir.

**Sob (b) o número fica 3 e a descrição fica verdadeira.** A `CLM-0006`
continua aberta.

---

## D-PRIMITIVA — a rota de auto-identificação, e ela é pré-requisito do C25-05

O C25-03 nomeou o que falta: **nenhuma rota `/authority` tem
auto-identificação.** `/authority/state` responde quem está **ativa**, nunca
quem **respondeu**.

A leitura do titular vai além do que a medição disse, e é o item mais
importante do ciclo:

> Isso está a montante dos **dois** bloqueadores, não de um. Com uma rota pela
> qual a instância diga quem ela é — **assinada, e com a resposta atribuível a
> quem a produziu** — a Testemunha pode observar quem respondeu em vez de quem
> foi declarada ativa, e a promoção da Sucessora pode ser provada pela própria
> instância se identificando sob a época nova.

**Consequência de ordem:** o C25-05 não é só difícil — ele tem um pré-requisito
que **não existia até esta medição**. Antes do C25-05, a rota de
auto-identificação.

Isto é **tarefa, não incógnita**, pelo mesmo critério da PRF-0108: nada falta de
informação para fazê-la. Por isso não se abre `unknown` para ela.

E vale o registro de procedência: foi descoberta **medindo, não revisando
desenho**.

---

## D-FREIO — a FIT-020 só como exceção decidida, nunca presumida

A FIT-019 levou a maquinaria de 30 para 31. A FIT-020 do C25-06 seria o
**terceiro merge seguido** de denominador, que é onde o freio da H6 acende.

> O freio existe para impedir que se infle a maquinaria, e "o meu caso é
> legítimo" é precisamente o argumento que o freio tem de resistir. Se a
> FIT-020 for necessária, que seja **exceção decidida e registrada**, não
> presumida.

Então o C25-06 **não** nasce autorizado a criar a FIT-020. A derrubada dos 40
campos declarativos continua; o instrumento novo depende de decisão própria.

---

## D-REFRESH — as quatro `db.refresh` ficam

> removê-las trocaria redundância visível por acoplamento invisível a "nenhum
> chamador desanexa".

O portão as mantém declaradas `NÃO-CARACTERIZÁVEL` e confirmadas pela própria
mutação, e a declaração é conferida nos dois sentidos.

---

## D-KIT-NO-TEMPO — a versão do kit é parte do instrumento

Observação do titular que o relatório de hoje não tinha:

> há três versões em jogo — lei em 0.26.0, tag publicada em 0.25.0, máquina em
> 0.24.0. [...] A versão do kit é parte do instrumento. O FIT-019 exige
> instrumento declarado no escopo, e prova produzida nesta máquina foi
> produzida contra um kit duas versões atrás da lei. [...] É a mesma classe do
> escopo, aplicada ao **tempo** em vez do espaço.

A regra está correta e foi **aceita**. A consequência foi **medida** (`PRF-0136`)
e é mais estreita do que a regra: nenhuma ferramenta do kit mudou entre 0.24.0 e
0.26.0, e o veredito do juiz é idêntico nas três versões. **Nenhuma prova
precisa ser refeita**; o que resta é declarar a versão do kit no escopo.

A classe é real e a instância está vazia hoje — e isso só se sabia medindo.

---

## O que estas decisões NÃO movem

- a cadeia substantiva continua **0/5**;
- os bloqueadores da REGIONAL continuam **três**, e a decisão D-CLM-0006 é
  justamente o que os mantém em três;
- nenhuma delas é execução, e nenhuma é prova.
