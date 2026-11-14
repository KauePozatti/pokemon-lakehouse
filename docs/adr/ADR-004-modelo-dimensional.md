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


**Nota (14/11/2026, dado real da ASC).** Validação das heurísticas: as raridades reais são Common, Uncommon, Rare, Double Rare, Illustration Rare, Special Illustration Rare, Ultra Rare, Mega Attack Rare, Mega Hyper Rare e Code Card (a ASC tem 575 cartas e 45 produtos sem número). A regra "sem `Number` = selado" classificava as 5 Code Cards como selado; corrigido: `Rarity = Code Card` é **carta** (`tipo_produto = carta`) e fica fora das perguntas por `is_code_card`. As consultas de selado também excluem Code Card por segurança, para o caso de a silver de um colega ainda trazer a classificação antiga.
