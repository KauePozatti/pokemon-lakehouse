# ADR-006 · Regras da carteira de R$ 1.000

**Status:** aceito · **Atenção:** a regra da carteira `propria` precisa ser **commitada antes do primeiro cálculo da carteira** (exigência da disciplina). Revise e faça esse commit antes de rodar `portfolio` pela primeira vez com dados reais.

| Carteira | Regra |
|---|---|
| `selado` | Booster box da coleção (nome sem "case"), unidades inteiras; sem booster box com preço no 1º dia, o selado de maior preço com preço. **Revisão 1:** se uma unidade da escolha custar mais que R$ 1.000, usa-se o selado de maior preço cuja unidade caiba; se nenhum couber, mantém-se a escolha original (0 unidades, tudo em caixa) |
| `cesta_raras` | R$ 100 em cada uma das 10 cartas de maior `market_price` no 1º dia (sem Code Card), unidades inteiras |
| `propria` | **Hipótese do autor:** 20 cartas de raridade acima de Rare com `market_price` entre US$ 3 e US$ 50 no 1º dia, R$ 50 por carta. **Revisão 1:** só entram cartas cuja unidade caiba em R$ 50 (preço × PTAX de venda ≤ R$ 50), das mais caras para as mais baratas; sobra vai para caixa |
| `dolar` | R$ 1.000 pela PTAX de venda do 1º dia; avaliado pela PTAX de compra |
| `cdi` | R$ 1.000 corrigidos pelo CDI de cada dia útil, juros compostos; o dia da compra não rende |

**Avaliação diária (liquidação):** `Σ unidades × preço × (1 − taxa_venda) × PTAX_compra + caixa × fator CDI`. Taxa de venda: **15%**, hipótese declarada, parâmetro `TAXA_VENDA`. O dashboard mostra com e sem taxa.

**Consequência a conhecer:** com R$ 100 por carta, cartas mais caras que R$ 100 compram **0 unidades** (o valor fica em caixa). A cesta das dez mais caras tende, portanto, a ficar em boa parte em caixa rendendo CDI; isso decorre da regra da disciplina e merece análise no ATAM, não correção.

**Armadilhas tratadas:** informação do futuro (composição usa só o 1º dia; testado), preço ausente (último preço observado, dia marcado em `itens_preco_carregado`), calendário do CDI (só rende com taxa publicada).

## Revisão 1 (10/11/2026): regras que compravam zero unidades

**Motivo (defeito funcional, não desempenho).** Num teste local, com 1 dia de dados da coleção SSP (Surging Sparks), a booster box (US$ 302,69, cerca de R$ 1.670) e as dez cartas mais caras da `cesta_raras` (a décima, US$ 20,80, cerca de R$ 115, já passa de R$ 100) não cabiam no orçamento: as carteiras `selado` e `cesta_raras` terminaram 100% em caixa, e a `propria` incluía cartas que não cabiam em R$ 50 (0 unidades). Nenhum resultado foi gravado no data lake antes desta revisão; o teste foi apenas local.

**Mudanças:** `selado` e `propria`, conforme a tabela acima. **A `cesta_raras` não foi alterada**: segue o enunciado e, na SSP, fica em caixa. Isso é tratado como limitação a analisar no ATAM, não como erro a corrigir.
