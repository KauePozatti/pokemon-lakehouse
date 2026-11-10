# Histórico de prompts (método CREATE)

> A disciplina exige o histórico dos seus prompts. Este arquivo registra o do início do projeto; **acrescente os seus próprios prompts e ajustes** a partir daqui.

## 1 · Persona → objetivos → especificação (resumo do pedido inicial)

**Persona:** colecionador que compra cartas e selados para guardar e quer saber onde o dinheiro rende mais.
**Pedido:** construir o pipeline completo do projeto "Cartas Pokémon como ativo de coleção" conforme a página da disciplina: coleta diária (TCGCSV, PTAX, CDI) para o RustFS da turma, silver Pydantic/Parquet no contrato comum, gold dimensional no DuckDB, dashboard Streamlit com as cinco perguntas em reais e o desafio da carteira de R$ 1.000, com SDD, ADRs, ATAM, testes e agendamento.

## 2 · Plano e tarefas
Ver `specs/04_plano.md` e `specs/05_tarefas.md`.

## 3 · Implementação e validação
Implementação em módulos independentes (coleta → silver → gold → perguntas → carteira → dashboard), testada com dados sintéticos locais. A validação contra a fonte real fica para a primeira coleta (tarefa T15).

## 4 · Seus ajustes
- _[data] prompt/decisão:_
