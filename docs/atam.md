# ATAM — validação da arquitetura

> Rascunho com o raciocínio arquitetural. As seções marcadas **[preencher]** dependem da série real: complete-as antes da entrega.

## Atributos de qualidade e cenários

| ID | Atributo | Cenário | Resposta da arquitetura | Evidência |
|---|---|---|---|---|
| Q1 | Integridade | Coleta roda duas vezes no mesmo dia | Segunda execução não chama a API nem grava | `test_idempotencia_...` |
| Q2 | Integridade | TCGCSV ainda não publicou o dia | Coleta aborta (exit 2); nada é gravado na chave de hoje | `test_dado_defasado_...` |
| Q3 | Auditabilidade | Verificar um valor em reais | `market_price_brl`, cotação e `data_ptax` no fato; `chave_raw` na silver | `test_gold_ptax.py` |
| Q4 | Recuperabilidade | Silver/gold corrompidos | `rebuild` reconstrói tudo do bruto | `test_silver_e_reconstruivel_do_bruto` |
| Q5 | Interoperabilidade | Colega grava um tipo diferente | `TRY_CAST` no staging + `union_by_name` | `gold.py` |
| Q6 | Correção financeira | Fim de semana/feriado sem PTAX | `ASOF JOIN`, nunca cotação futura | `test_nunca_usa_cotacao_posterior` |
| Q7 | Correção financeira | Futuro vazando na carteira | Composição só com o 1º dia | `test_composicao_nao_usa_informacao_do_futuro` |

## Pontos de sensibilidade

- **Taxa de venda (15%).** Muda o resultado das carteiras de cartas e selado, mas não o do dólar nem do CDI. O dashboard mostra o retorno com e sem taxa e a diferença. **[preencher: diferença observada, por carteira]**
- **Spread PTAX compra/venda.** Entra no `dolar` e nas carteiras de cartas: em período curto pesa proporcionalmente mais.
- **Janela comum (P3/P5).** Uma coleção de lançamento recente encurta a janela de todas.
- **Heurísticas de classificação** (`tipo_produto`, `categoria_selado`, "Double Rare em diante"): alteram os índices da P2 e a escolha do selado.

## Trade-offs

| Decisão | Ganho | Custo |
|---|---|---|
| Bruto imutável + guarda de frescor | Nunca grava preço defasado como atual | Exige rodar depois das 17h BRT; um dia perdido é permanente |
| Reconstruir silver/gold inteiros a cada dia | Simples, determinístico, sem estado | Custo cresce com o histórico (irrelevante em ~7 semanas) |
| Estrela sobre silver de todos | Perguntas da turma sem ETL extra | Depende de os colegas respeitarem o contrato |
| Último preço conhecido na carteira | Evita buracos | Pode mascarar iliquidez (por isso o dia é marcado) |

## Riscos

| ID | Risco | Mitigação |
|---|---|---|
| R1 | Dia sem coleta | Lacuna declarada no README; nada é inventado |
| R2 | Formato real da fonte diverge dos parsers | Quarentena + log; validar na primeira coleta real |
| R3 | `market_price` nulo para produtos ilíquidos | Nulo preservado; fora de médias/variações |
| R4 | Série curta (~7 semanas) | Linguagem descritiva, sem previsão |
| R5 | Cartas caras compram 0 unidades na `cesta_raras` | Documentado no ADR-006 |

## Resultados observados **[preencher com a série real]**

- Dias coletados / lacunas:
- Contagem de quarentena por tabela:
- Coleção que mais valorizou na turma:
- Selado × cartas na minha coleção:
- Placar da carteira (selado × CDI; cesta × dólar):
- Limitações encontradas na prática:
