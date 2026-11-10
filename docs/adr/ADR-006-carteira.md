# ADR-006 · Regras da carteira de R$ 1.000

**Status:** aceito · **Atenção:** a regra da carteira `propria` precisa ser **commitada antes do primeiro cálculo da carteira** (exigência da disciplina). Revise e faça esse commit antes de rodar `portfolio` pela primeira vez com dados reais.

| Carteira | Regra |
|---|---|
| `selado` | Booster box da coleção (nome sem "case"), unidades inteiras; sem booster box com preço no 1º dia, o selado de maior preço com preço |
| `cesta_raras` | R$ 100 em cada uma das 10 cartas de maior `market_price` no 1º dia (sem Code Card), unidades inteiras |
| `propria` | **Hipótese do autor, editável:** 20 cartas de raridade acima de Rare com `market_price` entre US$ 3 e US$ 50 no 1º dia, orçamento igual (R$ 50 cada). Racional: evitar o teto de preço (em que uma unidade já passa do orçamento) e o chão sem liquidez |
| `dolar` | R$ 1.000 pela PTAX de venda do 1º dia; avaliado pela PTAX de compra |
| `cdi` | R$ 1.000 corrigidos pelo CDI de cada dia útil, juros compostos; o dia da compra não rende |

**Avaliação diária (liquidação):** `Σ unidades × preço × (1 − taxa_venda) × PTAX_compra + caixa × fator CDI`. Taxa de venda: **15%**, hipótese declarada, parâmetro `TAXA_VENDA`. O dashboard mostra com e sem taxa.

**Consequência a conhecer:** com R$ 100 por carta, cartas mais caras que R$ 100 compram **0 unidades** (o valor fica em caixa). A cesta das dez mais caras tende, portanto, a ficar em boa parte em caixa rendendo CDI; isso decorre da regra da disciplina e merece análise no ATAM, não correção.

**Armadilhas tratadas:** informação do futuro (composição usa só o 1º dia; testado), preço ausente (último preço observado, dia marcado em `itens_preco_carregado`), calendário do CDI (só rende com taxa publicada).
