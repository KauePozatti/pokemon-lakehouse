# Rastreabilidade

| Requisito | Decisão | Código | Teste |
|---|---|---|---|
| RF-01 coleta | ADR-001/002 | `collect.py`, `http.py` | `test_collect.py` |
| RF-02 bruto imutável | ADR-002 | `storage.put_if_absent` | `test_bruto_nunca_e_sobrescrito`, `test_idempotencia_...` |
| RF-03/04 silver, quarentena, nulo | ADR-007 | `models.py`, `silver.py` | `test_silver.py` |
| RF-05/06 gold e PTAX | ADR-003/004 | `gold.py` | `test_gold_ptax.py`, `test_integration.py` |
| RF-07 P1 + decomposição | ADR-005 | `analytics.q1_variacao`, `decompor` | `test_pergunta_1`, `test_decomposicao_...` |
| RF-08 P2 | ADR-005 | `analytics.q2_indices` | `test_pergunta_2_...` |
| RF-09 P3 | ADR-005 | `analytics.q3_colecoes` | `test_pergunta_3_...` |
| RF-10 P4 | ADR-005 | `analytics.q4_concentracao` | `test_pergunta_4_...` |
| RF-11 P5 | ADR-005 | `analytics.q5_risco_retorno` | `test_pergunta_5_...` |
| RF-13/14 carteiras | ADR-006 | `portfolio.py`, `pipeline.build_portfolio` | `test_portfolio.py`, `test_carteiras_no_contrato_comum` |
| RF-15 placar | ADR-006 | `portfolio.placar_turma`, `dashboard/app.py` | `test_carteiras_no_contrato_comum` |
| RNF-04 reconstrução | ADR-007 | `pipeline.rebuild` | `test_silver_e_reconstruivel_do_bruto` |
