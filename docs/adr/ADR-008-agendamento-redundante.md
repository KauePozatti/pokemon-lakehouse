# ADR-008 · Agendamento redundante (duas janelas)

**Status:** aceito · **Data:** 14/11/2026

**Contexto.** O workflow foi programado para 21:30 UTC (18:30 em Brasília). Na aba Actions, as execuções agendadas de 12/11 e 13/11 começaram às 23:01 e 22:37 (horário de Brasília), ou seja, com cerca de 4h30 de atraso. O preço do TCGplayer só existe no dia e o bruto é imutável: se a execução atrasar a ponto de cruzar a meia-noite de Brasília, `hoje_brt()` passa a ser o dia seguinte, a trava de frescor aborta (nada é gravado) e o dia anterior vira lacuna permanente.

**Decisão.** Duas janelas de agendamento: 20:45 UTC (17:45 BRT, logo após a atualização do TCGCSV, por volta de 17h05 BRT) e 22:00 UTC (19:00 BRT, reserva). Como a coleta é idempotente, a segunda execução não grava nada quando a primeira deu certo; o grupo de `concurrency` impede execuções simultâneas.

**Consequências.** (+) Tolera atrasos e uma falha isolada. (−) Em dias de atraso longo, uma das execuções pode terminar em vermelho pela trava de frescor, sem prejuízo para os dados. O GitHub também pode pular execuções agendadas em horários de pico: acompanhar a aba Actions e declarar no README qualquer dia sem coleta.
