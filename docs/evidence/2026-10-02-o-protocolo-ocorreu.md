# O protocolo ocorreu — 2026-10-02

Evidência da **PRF-0091** (prova a CLM-0072), da **PRF-0092** (a janela de
pré-registro) e da **PRF-0093** (encerra a UNK-0016).

**Nenhum dado pessoal entra aqui, e número de ART conta como identificador.** O
`test_50` do JURIDICO-TECH proíbe sequência de 13 dígitos nos dados do protocolo,
e o `test_51` prova que a regra não custou informação: as duas ARTs se distinguem
por **data e área**. Esta evidência segue a mesma regra — a primeira versão dela
trazia os dois números dentro de nomes de arquivo, e eles passariam pela guarda
porque `\d{13}` não encontra fronteira antes de `_`.

Os documentos lidos contêm nome, CPF, matrícula, inscrição e endereço; o que
este registro guarda é o **fato**, a **data** e o **parâmetro** — nada mais. É a
mesma regra do `projeto_p001.json`: *"o projeto é P-001, e só"*.

## O que foi medido, e onde

Pasta `CASA_01` no Drive do titular, lida pelo conector em 2026-10-02 às 17h40.

### Medido por leitura do próprio documento

| documento | o que ele diz |
|---|---|
| comprovante de pagamento (PDF, 11 KB) | **R$ 38,55**, pago em **02/10/2026**, para `PM VARGEM GDE PTA TRIBUTOS DIVERSOS`, boleto com vencimento 04/10/2026 |
| ART retificadora (PDF) | *"Substituição retificadora"* da anterior; atividade técnica **97,20000 m²** na elaboração **e** na execução; registrada em **15/09/2026**; *"devidamente quitada"*; campo de assinaturas **em branco neste PDF** |
| procuração (PDF) | **Cotia, 24 de setembro de 2026**; confere ao RT poderes para *"preencher e assinar requerimentos para montagem de processos"*, *"protocolar documentos em geral"*, *"atender exigências"* e *"solicitar reconsideração de despacho"* |

### Medido por metadado, e NÃO lido

Nove imagens JPEG, todas com o **mesmo título** (`Foto de l Messias`), subidas
entre 17h16 e 17h22 de 02/10/2026. O conector não extrai texto de JPEG: o
`read_file_content` devolveu conteúdo vazio. **Então o que elas contêm não está
medido** — presença sim, conteúdo não.

É nelas que devem estar a caderneta, o número oficial protocolado, o
comprovante da taxa de R$ 315,00 e a via assinada da ART. Enquanto não forem
nomeadas ou lidas, o Navigator não pode derivar estado delas sem inventar.

## O risco de acervo que foi fechado

Havia **três** ARTs na mesma pasta, e a única com `assinado` no nome era a
**substituída**:

```
antes
  dois arquivos com o MESMO nome genérico          a retificadora, 97,20 m²
  um deles é cópia de 23/09                        idêntica em tamanho
  um terceiro, com "assinado" no nome              SUBSTITUÍDA, 94,50 m²

depois, renomeadas sem apagar nada, usando DATA e ÁREA
  VIGENTE_...97,20m2_retificadora.pdf              registrada em 15/09
  DUPLICATA_...97,20m2_retificadora_copia_de_23-09.pdf
  SUBSTITUIDA_NAO_USAR_...94,50m2_assinado.pdf     registrada em 24/08
```

Duas ARTs assinadas convivendo é como se chega à errada; e a que carregava a
palavra `assinado` era justamente a que não vale mais.

## A janela de pré-registro

```
as quatro previsões, registered_at ....... 2026-09-22
o protocolo .............................. 2026-10-02
```

**Dez dias.** As quatro previsões antecederam o fato, e a FIT-016 já exigia que
antecedessem: *"previsão registrada depois do fato não é previsão"*. A janela
fechou a tempo sem ninguém ter coordenado o momento — e isso é sorte, não
método. O que o método garantiu foi que a data estivesse gravada e conferível
antes, para que esta frase possa ser escrita agora sem depender de memória.

## O que esta evidência NÃO afirma

- **Não afirma que o protocolo foi aceito.** Protocolar é entregar; a análise é
  outro ato, e não existe ainda.
- **Não afirma o número do protocolo**, porque ele não aparece em documento
  legível — só, possivelmente, nas nove fotos.
- **Não afirma que a caderneta existe no acervo.** Nenhum arquivo legível a
  identifica. O titular afirma que existe, e a afirmação dele não é medição: é
  por isso que o item 5 fica `EM_ESPERA` até o documento ser nomeado.
- **Não diz nada sobre o mérito.** As quatro previsões seguem `UNPROVEN` até a
  Prefeitura responder, e o genoma não deve dizer nada sobre a análise antes de
  ela existir.
