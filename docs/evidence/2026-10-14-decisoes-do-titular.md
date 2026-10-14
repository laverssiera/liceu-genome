# 2026-10-14 — decisoes do titular

## D — ligar o `--bloquear` da guarda da UNK-0017

**Decidido em 2026-10-14**, depois de a medicao que a propria incognita exigia
existir: *"a taxa de falso positivo MEDIDA sobre a arvore real dos 19
repositorios antes de a guarda virar bloqueante... Enquanto o numero nao
existir, a guarda nao existe."*

Os tres estados, e eles nao se confundem:

| estado | onde esta |
|---|---|
| **decisao** | TOMADA em 2026-10-14 |
| **execucao** | ENTROU na main em 2026-10-14, merge `0f8fa0c` (PR `LICEU_6.0_CONSTRUTORA_VIRTUAL#108`). Na CI o passo leu **1488** arquivos e disse `OK: 1 achado, todos da linha de base lacrada, nenhum novo` |
| **comprovacao** | as tres mutacoes, na `PRF-0170`; e a `PRF-0171`, por teste, com a superficie fixada — que so podia vir depois do merge |

### O que a decisao alcanca

O repositorio `LICEU_6.0_CONSTRUTORA_VIRTUAL`, **somente** — e isso e medicao e
nao preferencia. O runner tem so este checkout, e a guarda varre a partir do
diretorio que *contem* os repositorios: pedir os 19 a faz falhar fechada com
`NAO MENSURAVEL`, que e o comportamento certo e nao e o que se quer de um portao.

### O que a decisao NAO alcanca, e segue aberto

1. **Os outros 18 repositorios.** E onde estao as **13 credenciais coladas** que a
   guarda achou. Bloquear la exige a guarda rodando na CI de cada um — o que
   provavelmente significa distribui-la pelo kit, com custo de versao e oito
   pinos. **Decisao separada, nao tomada.**
2. **O que fazer com as 13 credenciais.** A guarda as ve; ninguem as removeu. As
   duas que pesam mais: uma senha que e o *default* de um `getenv` — sem a
   variavel no ambiente, ela **e** a senha — e uma chave de assinatura repetida
   como fallback em quatro arquivos do mesmo repositorio.
3. **Unificar ou manter duas guardas.** O inventario le 13 extensoes por nome;
   esta le 19 por proximidade.
4. **A UNK-0017 continua aberta.** A prova que ela exigia existe e o bloqueio foi
   decidido; a pergunta que resta — se o eixo da forma e utilizavel em geral, ou
   se a resposta certa e exigir que todo segredo chegue por nome conhecido —
   nao foi respondida por esta decisao.

### Uma coisa que a decisao mudou no instrumento

Ligar sem medir deixaria a `main` vermelha em cima de ruido: havia **4 achados**
neste repositorio e os quatro eram falsos. Havia dois caminhos — lacrar uma lista
de isencao com os quatro, ou corrigir as causas e lacrar **um**. Foi o segundo,
porque lista de isencao e a proxima brecha, e as tres causas estavam
classificadas por regra na triagem. A correcao veio de distancia medida, nao de
limiar ajustado: `19 achados, 15.8% de falso positivo, zero nao classificados`.

## D — o incidente da credencial: opção B

**Decidido em 2026-10-14.** O titular escolheu **a aceitação por escrito** e
**não reescrever o histórico** do `LICEU_6.0_CONSTRUTORA_VIRTUAL`.

| estado | onde está |
|---|---|
| **decisão** | TOMADA em 2026-10-14 |
| **execução** | o texto de aceitação está em `2026-10-14-o-incidente-da-credencial-as-duas-opcoes.md`, §4. **A assinatura não foi dada**, e ela é do titular — não deriva da decisão |
| **comprovação** | a parte mensurável da condição: o valor fora do `HEAD`, `PRF-0163` — `origin/main` devolve 0 em 1600 arquivos, com controle positivo no `e0a0f19` |

### O que a decisão fecha

O `e0a0f19` **fica**. Os 69 ramos não são reescritos, os 169 commits depois dele
mantêm os SHAs, e nenhuma prova do genoma que cite SHA deste repositório precisa
ser reconferida. Fecha também um custo que só apareceu depois do documento: a
`PRF-0167` mede que a reescrita destruiria o único controle positivo que não
depende de isca — a guarda da `UNK-0017` rodando contra o blob do `e0a0f19`. A
opção B **preserva** esse controle.

### O que a decisão NÃO fecha

1. **A assinatura.** O documento tem data e assinatura em branco. Decisão não é
   assinatura.
2. **A cláusula de caducidade.** "Esta credencial nunca é usada em ambiente
   algum." Hoje o provedor é nenhum; se isso mudar, a aceitação caduca por
   cláusula própria e a reescrita volta à mesa.
3. **As 4 ocorrências no transcript da sessão**, que eu criei no mesmo dia e
   acrescentei à lista de riscos aceitos. Reescrever o git não alcançaria esse
   arquivo — ele sobra nas duas opções. Apagar ou redigir o transcript é decisão
   do titular; eu não toco naquele arquivo.
4. **O que o provedor do modelo retém da conversa**: NÃO-MENSURÁVEL daqui.
