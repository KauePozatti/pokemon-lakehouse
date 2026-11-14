# Histórico de prompts (método CREATE)

> Histórico dos prompts do aluno (Kauê Douglas) e das decisões tomadas a partir deles. Credenciais e chaves informadas durante o trabalho foram omitidas de propósito.

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
| 14/11/2026 | Troca do endpoint do lake pelo professor; chave antiga revogada | Coleta reiniciada no lake novo em 14/11; lacuna de 12/11 e 13/11 declarada |
| 14/11/2026 | Conferência da aba Actions e do dashboard com dados reais; pedido para concluir o restante | ADR-008 (duas janelas), testes de regressão do formato real da PTAX, ATAM com resultados observados |


## 5 · Prompts do aluno, em ordem

| # | Prompt (resumo fiel) | O que mudou no projeto |
|---|---|---|
| 1 | "me ajude a fazer esse projeto completo" | Construção do pipeline e da documentação |
| 2 | "oque falta ser feito?" / "mais como entrega, posso enviar para o professor? o que falta?" | Lista do que faltava: chaves do S3, coleta real, repositório, README |
| 3 | "se eu te der acesso full, consegue fazer pra mim?" | Definido que GitHub e chaves ficam sob controle do aluno; execução guiada |
| 4 | "estou fazendo isso no Mac, como assim abrir um terminal na pasta?" | Roteiro adaptado ao macOS |
| 5 | "onde encontro essas informações?" (sigla da coleção e chaves) | Orientação sobre `COLECAO_SIGLA` e credenciais do canal da turma |
| 6 | "consigo dar andamento sem preencher essa parte e depois voltar?" | Coleta local primeiro, S3 depois |
| 7 | "quando falar para eu executar uma coisa, mande uma de cada vez e deixe isso claro" | Roteiro passou a ter um comando por vez |
| 8 | "pode ser" (revisões A e B da carteira) | ADR-006, revisão 1 |
| 9 | "quero fazer com outra coleção, escolha uma aleatória pra mim" | Sorteio da ASC |
| 10 | "tenho que ficar rodando todos os dias para ter o registro?" | Agendamento no GitHub Actions |
| 11 | "com base em tudo que foi passado, meu projeto falta alguma coisa para entregar?" | Auditoria final; correção das Code Cards; ADR-008 |
| 12 | "me ajude a mudar o visual do Streamlit, quero algo mais visual" | Dashboard redesenhado (tema escuro, cartões, galeria de cartas) |
| 13 | "meu professor trocou o endpoint do RustFS, me ajude a fazer os ajustes" | Secrets e `.env` atualizados; lacuna de 12/11 e 13/11 declarada |

## 6 · Observação sobre autoria
O código foi gerado com assistência de IA a partir dos prompts acima; a execução, a configuração de contas e chaves, os testes no ambiente real e as decisões de regra (itens 8 e 9) foram feitas pelo aluno.
