# ADR-008 · Agendamento redundante (duas janelas)

**Status:** aceito · **Data:** 14/11/2026

**Contexto.** O workflow foi programado para 21:30 UTC (18:30 em Brasília). Na aba Actions, as execuções agendadas de 12/11 e 13/11 começaram às 23:01 e 22:37 (horário de Brasília), ou seja, com cerca de 4h30 de atraso. O preço do TCGplayer só existe no dia e o bruto é imutável: se a execução atrasar a ponto de cruzar a meia-noite de Brasília, `hoje_brt()` passa a ser o dia seguinte, a trava de frescor aborta (nada é gravado) e o dia anterior vira lacuna permanente.

**Decisão.** Duas janelas de agendamento: 20:45 UTC (17:45 BRT, logo após a atualização do TCGCSV, por volta de 17h05 BRT) e 22:00 UTC (19:00 BRT, reserva). Como a coleta é idempotente, a segunda execução não grava nada quando a primeira deu certo; o grupo de `concurrency` impede execuções simultâneas.

**Consequências.** (+) Tolera atrasos e uma falha isolada. (−) Em dias de atraso longo, uma das execuções pode terminar em vermelho pela trava de frescor, sem prejuízo para os dados. O GitHub também pode pular execuções agendadas em horários de pico: acompanhar a aba Actions e declarar no README qualquer dia sem coleta.

## Revisão 1 (18/11/2026)

**Fato observado.** As janelas de 20:45 e 22:00 UTC não foram suficientes. Em 16/11 as duas execuções agendadas só começaram às 00:09 e 01:15 de 17/11 (BRT), ou seja, com atraso de 6h a 6h30. Já com `hoje_brt()` no dia seguinte, a trava de frescor abortou as duas (nada foi gravado), e **16/11/2026 virou lacuna permanente** no lake. Em 17/11 a primeira execução rodou às 23:35 e coletou; a seguinte (00:14 de 18/11) abortou pela mesma trava, sem prejuízo.

**Decisão.** Seis janelas, de 20:10 a 22:10 UTC (17:10 a 19:10 BRT), com a primeira logo depois da publicação do TCGCSV. Como o atraso do GitHub é independente por execução, mais janelas aumentam a chance de uma cair antes da meia-noite. A coleta continua idempotente e o `concurrency` evita execuções simultâneas. Como reserva final, o aluno pode disparar o workflow manualmente (Run workflow, sem `allow_stale`) a partir das 17h05 BRT.

**Consequências.** (+) Maior tolerância a atrasos do agendador. (−) Mais execuções vermelhas "por segurança" quando o dia já foi coletado e a execução atrasada passa da meia-noite; elas não alteram dados. Não existe recuperação do preço de um dia perdido: a lacuna é declarada no README.
