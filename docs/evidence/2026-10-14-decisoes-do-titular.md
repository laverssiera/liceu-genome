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
