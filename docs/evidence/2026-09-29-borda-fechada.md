# A borda do ecossistema fecha — 2026-09-29

Evidência da PRF-0055 (prova a CLM-0038, supersede a PRF-0040).

## A medição

`infra/security/borda_compose.py` sobre a raiz dos 19 repositórios, com o `main`
mergeado de cada um:

```
borda fechada: 56 arquivo(s) de compose conferido(s),
nenhum servico de estado publica porta fora do loopback
```

**119 → 0.**

| leva | repos | portas |
|---|---|---|
| cadeia, elos 0 a 5 | 6 | 54 |
| fora da cadeia | 8 | 65 |
| **total** | **14** | **119** |

## Por que o zero é confiável

Zero achados não se distingue de varredor quebrado. **Controle positivo**, rodado
logo depois da medição: um compose temporário publicando `"5432:5432"` faz o
scanner acusar `1 exposicao(oes)`.

O scanner enxerga. O zero é do mundo, não da ferramenta.

## A forma da mudança

```diff
-      - "5432:5432"
+      - "127.0.0.1:5432:5432"
```

Aplicada **linha a linha**, recusando o que não casasse exatamente com o formato —
editar compose às cegas seria trocar um risco por outro. 36 arquivos de compose
alterados ao todo, todos reconferidos como YAML válido **por carregamento**.

Prender ao loopback **não** tira acesso do próprio host: `127.0.0.1` continua
alcançável de quem roda o compose. O que sai é o alcance de outras máquinas.

## As duas conferências prévias

1. nenhum workflow alcança porta de estado por endereço que não seja loopback;
2. nenhum teste assere a **string** de uma porta alterada.

A segunda é lição aprendida na leva da cadeia: o JOHN tinha um teste exigindo
`"8222:8222"` — a forma que publica em todas as interfaces. Ele falhou, e estava
**certo em falhar**: guardava um contrato, e o contrato mudou. A exigência foi
invertida para `assertIn "127.0.0.1:8222:8222"` mais `assertNotIn "8222:8222"`.
Na leva seguinte a busca foi feita **antes**, em `.py`, `.ts`, `.js` e `.tsx`.

## O que isto NÃO prova

**Fechar porta não é revogar credencial.** A F0-C segue bloqueada na prova de
revogação, que é outra coisa: um segredo que vazou continua válido até ser
trocado, e nenhuma mudança de `ports` altera isso.

E a medição é **estática**, sobre arquivos de compose versionados. Ela não
alcança o que um operador publique à mão, nem infraestrutura fora do compose.
