# Histórico de prompts (método CREATE)

> A disciplina exige o histórico dos seus prompts. Este arquivo registra o do início do projeto; **acrescente os seus próprios prompts e ajustes** a partir daqui.

## 1 · Persona → objetivos → especificação (resumo do pedido inicial)

**Persona:** colecionador que compra cartas e selados para guardar e quer saber onde o dinheiro rende mais.
**Pedido:** construir o pipeline completo do projeto "Cartas Pokémon como ativo de coleção" conforme a página da disciplina: coleta diária (TCGCSV, PTAX, CDI) para o RustFS da turma, silver Pydantic/Parquet no contrato comum, gold dimensional no DuckDB, dashboard Streamlit com as cinco perguntas em reais e o desafio da carteira de R$ 1.000, com SDD, ADRs, ATAM, testes e agendamento.

## 2 · Plano e tarefas
Ver `specs/04_plano.md` e `specs/05_tarefas.md`.

## 3 · Implementação e validação
Implementação em módulos independentes (coleta → silver → gold → perguntas → carteira → dashboard), testada com dados sintéticos locais. A validação contra a fonte real fica para a primeira coleta (tarefa T15).

## 4 · Decisões e ajustes ao longo da execução

| Data | Prompt ou decisão do aluno | Efeito |
|---|---|---|
| 08/11/2026 | Descrição do projeto e links da página da disciplina e do console do RustFS: "me ajude a fazer esse projeto completo" | Pipeline completo: coleta, silver, gold, perguntas, carteira, dashboard, testes, SDD |
| 10/11/2026 | Perguntas sobre o que faltava para entregar e se um agente com acesso poderia executar os passos | Roteiro de execução passo a passo no Mac; GitHub e chaves do S3 ficaram sob controle do aluno |
| 10/11/2026 | Regra da carteira `propria`: "prefiro A" (manter a regra proposta) | ADR-006 original commitado antes de qualquer cálculo no lake |
| 10/11/2026 | Primeira coleta local (coleção SSP) para testar as fontes reais | Descobertas: boletim `Fechamento PTAX`; booster box e cartas caras não cabem no orçamento |
| 12/11/2026 | "Pode ser" para as revisões A (selado que cabe) e B (própria que cabe) | ADR-006, revisão 1, commitada antes da primeira gravação da carteira no lake |
| 12/11/2026 | Troca de coleção: "escolha uma aleatória" (sorteio: ASC); `check-colecao` confirmou a ASC livre | Série da ASC começa em 12/11/2026 |
| 12/11/2026 | Secrets e variables no GitHub; execução manual do workflow | Agendamento validado |
| 14/11/2026 | Conferência da aba Actions e do dashboard com dados reais; pedido para concluir o restante | ADR-008 (duas janelas), testes de regressão do formato real da PTAX, ATAM com resultados observados |

> Complemente esta tabela com qualquer outro prompt ou ajuste seu até a entrega.
