# ADR-004 · Modelo dimensional (esquema estrela)

**Status:** aceito · **Perguntas atendidas:** 1 a 5

| Tabela | Grão |
|---|---|
| `fato_preco_diario` | produto × acabamento × dia (preços em USD e em BRL, cotação e `data_ptax`) |
| `fato_cambio_diario` | dia de calendário (PTAX aplicada, `data_ptax`, CDI do dia; 0 sem taxa) |
| `dim_produto` | produto (tipo, categoria do selado, raridade, número, imagem, URL, `is_code_card`) |
| `dim_colecao` | coleção (sigla, série, lançamento, responsável) |
| `dim_data` | dia (ano, mês, semana, dia da semana, fim de semana) |
| `dim_acabamento` | acabamento |

**Por que estrela e não tabela larga.** Cada pergunta é uma agregação do mesmo fato por uma dimensão diferente (coleção, raridade, tipo, data). Dias desde o lançamento **não** são guardados: calculam-se na consulta com a data do fato e `dim_colecao.data_lancamento`.

**Leitura da turma.** A gold é construída sobre `silver/*/*/...parquet` de todos os alunos, com `TRY_CAST` aos tipos do contrato e `union_by_name` para tolerar colunas extras. PTAX e CDI são deduplicados por dia entre as cópias de cada aluno.

**Qualificações.** `categoria_selado` é derivada do nome do produto (heurística por palavra-chave) e `tipo_produto` é "carta" quando há `Number` em `extendedData`; ambas são hipóteses a validar com dados reais (ver ATAM, risco R2).
