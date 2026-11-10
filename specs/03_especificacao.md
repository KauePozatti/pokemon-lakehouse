# 03 · Especificação (CREATE: Specification)

## Requisitos funcionais

| ID | Requisito |
|---|---|
| RF-01 | Coletar 1x/dia produtos e preços da coleção (TCGCSV `products` e `prices`), PTAX (USD, Olinda) e CDI (SGS 12) |
| RF-02 | Gravar a resposta original em `raw/<fonte>/group_id=X/data=D/`, sem sobrescrever; repetir no mesmo dia não duplica |
| RF-03 | Produzir silver nos cinco contratos (`colecao`, `produto`, `preco_diario`, `cambio_diario`, `cdi_diario`) validados por Pydantic; rejeitados vão para `quarentena/` com o motivo e a contagem aparece no log |
| RF-04 | Nulo não é zero: `market_price` ausente permanece nulo |
| RF-05 | Construir o esquema estrela no DuckDB sobre a silver de todas as coleções (`s3://tcg/silver/.../*.parquet`) |
| RF-06 | Converter preços para reais pela última PTAX de fechamento conhecida (nunca posterior ao dia do preço); guardar `market_price_brl`, a cotação e `data_ptax` |
| RF-07 | Pergunta 1: variação por carta/acabamento (preço inicial ≥ US$ 1), decomposta em carta, câmbio e cruzado; dois rankings de dez com imagem |
| RF-08 | Pergunta 2: índice base 100 de selados (média) contra cartas Double Rare+ (soma) |
| RF-09 | Pergunta 3: valor por coleção em base 100 numa janela comum, com a PTAX base 100 |
| RF-10 | Pergunta 4: participação de cada raridade no valor e nº de cartas que somam 80% |
| RF-11 | Pergunta 5: retorno × volatilidade para cartas ≥ US$ 5; hover/tabela com imagem |
| RF-12 | Chave BRL/USD; filtros de preço mínimo sempre em US$; `Code Card` fora das perguntas 1, 3, 4 (e 2, 5 por consistência) |
| RF-13 | Cinco carteiras (`selado`, `cesta_raras`, `propria`, `dolar`, `cdi`) avaliadas diariamente por valor de liquidação; gravar no contrato comum |
| RF-14 | Métricas: retorno acumulado, excesso sobre o CDI, perda máxima, dias com preço carregado; resultado com e sem taxa de venda |
| RF-15 | Placar da turma a partir de `gold_turma/carteira/` |

## Requisitos não funcionais

| ID | Requisito |
|---|---|
| RNF-01 | Idempotência e imutabilidade do bruto |
| RNF-02 | Respeito ao TCGCSV: `User-Agent` próprio, pausa ≥ 100 ms, 3 chamadas de preço/dia |
| RNF-03 | Credenciais fora do repositório (`.env`, secrets) |
| RNF-04 | Silver e gold reconstruíveis com um único comando |
| RNF-05 | Contrato de tipos idêntico ao da turma (INTEGER = int32, DATE, DOUBLE, TIMESTAMP) |
| RNF-06 | Testes de unidade e de integração; CI no GitHub Actions |

## Critérios de aceite (resumo)

- Semana 09/10–13/10/2026: preços de 10, 11 e 12/10 usam a PTAX de 09/10 (`tests/test_gold_ptax.py`).
- Segunda execução do dia não faz requisições nem grava (`tests/test_collect.py`).
- Composição das carteiras não muda ao acrescentar dias posteriores (`tests/test_portfolio.py`).
- CDI não rende em sábado, domingo e feriado; o dia da compra não rende.
