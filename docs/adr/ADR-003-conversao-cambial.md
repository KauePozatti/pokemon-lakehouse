# ADR-003 · Conversão para reais: última cotação conhecida

**Status:** aceito · **Perguntas atendidas:** 1, 2, 3, carteira

**Decisão.** O preço do dia D usa a PTAX de **fechamento** do dia D ou, se não existir, a do dia útil anterior mais próximo. Nunca uma cotação posterior (o colecionador não a conhecia). Implementação: `ASOF JOIN` sobre `cambio_diario` (`p.data >= c.data`). O fato guarda `market_price_brl`, a cotação aplicada e `data_ptax`.

**Venda x compra.** Compra de carta/dólar usa a cotação de **venda**; liquidação usa a de **compra** (o spread entra no resultado das carteiras).

**Decomposição.** `(1 + r_brl) = (1 + r_usd)(1 + r_cambio)`; efeito cruzado = `r_usd · r_cambio`.

**Teste.** `tests/test_gold_ptax.py`: sexta 09/10, fim de semana 10–11/10 e feriado 12/10 usam a PTAX de 09/10; 13/10 usa a própria; nenhuma linha com `data_ptax > data`.
