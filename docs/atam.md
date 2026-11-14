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
| Q8 | Disponibilidade | Agendador do GitHub atrasa horas | Duas janelas e coleta idempotente (ADR-008) | Aba Actions: execuções de 12/11 e 13/11 concluídas |

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
| R6 | Atraso do agendador empurra a coleta para depois da meia-noite | ADR-008 (duas janelas; a trava de frescor impede gravar dado do dia errado) |

## Resultados observados

**Já verificado (dados reais, 12/11 a 14/11/2026)**

- **Coleção e série.** ASC (group_id 24541). Primeira coleta em 12/11/2026. Execuções agendadas de 12/11 e 13/11 concluídas com sucesso (aba Actions). A execução agendada de 11/11 falhou, provavelmente porque os secrets ainda não estavam configurados (inferência: o log não foi analisado); a coleta da ASC só começou em 12/11, então não há lacuna na série.
- **Qualidade.** Primeira carga da ASC: 620 produtos, 658 linhas de preço, **0 registros na quarentena**; câmbio com 4 dias úteis e CDI com 7 dias.
- **R2 (formato real da fonte).** O parser do TCGCSV leu a resposta real sem ajustes. O parser da PTAX tinha um defeito: o BCB publica `Fechamento PTAX`, não `Fechamento`, e nenhum dia de câmbio entrava. Corrigido (ADR-003, nota) e coberto por teste.
- **Idempotência.** Segunda execução no mesmo dia: 0 objetos gravados em todas as fontes, com silver e gold idênticas.
- **Carteira no primeiro dia (ASC).** `cesta_raras` terminou 100% em caixa (nenhuma das dez cartas mais caras cabe em R$ 100), com retorno 0,0%. `selado` e `propria`, após a revisão 1 do ADR-006, investem parte do capital; seu retorno do primeiro dia (−13,5% e −11,8%) reflete apenas a taxa de venda de 15% aplicada sobre a parte investida na liquidação, não variação de preço.
- **Agendamento.** As execuções agendadas começaram com cerca de 4h30 de atraso (23:01 e 22:37 BRT para um cron de 18:30 BRT), o que motivou o ADR-008.
- **Série curta.** Cerca de quatro semanas de coleta até a entrega: descreve o período, não sustenta previsão.

**A completar até 12/12 com a série final**

- Dias coletados e lacunas (se houver):
- Coleção que mais valorizou na turma (P3):
- Selado × cartas na minha coleção (P2):
- Cartas com melhor retorno por risco (P5):
- Placar da carteira (selado × CDI; cesta × dólar):
- Diferença com e sem taxa de venda, por carteira:
- Limitações encontradas na prática:
