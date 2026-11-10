# ADR-002 · Coleta idempotente com bruto imutável

**Status:** aceito

**Decisão.** Chave `raw/<fonte>/group_id=X/data=AAAA-MM-DD/<arquivo>`; antes de gravar, o coletor confere se a chave existe (`put_if_absent`). Uma segunda execução no mesmo dia não faz requisição nem grava. O corpo é gravado exatamente como veio.

**Guarda de frescor.** O TCGCSV atualiza por volta de 20h UTC. Antes disso, gravar na chave do dia colocaria o preço de ontem como se fosse de hoje e, como o bruto é imutável, o erro seria permanente. O coletor lê `last-updated.txt` e aborta com código 2 se a atualização é anterior ao dia. Se o carimbo não puder ser lido ou interpretado, a coleta segue com aviso no log (falha aberta, para não perder um dia por causa de um arquivo auxiliar). `--allow-stale` existe para exceções conscientes.

**PTAX com retroação.** Como a PTAX é histórica, o coletor também busca os 5 dias anteriores que faltem. Isso recupera lacunas de câmbio; **não existe equivalente para o preço do TCGplayer**, então um dia sem coleta é lacuna permanente e deve ser declarado no README.

**Horário.** 21:30 UTC (18:30 BRT): depois da atualização do TCGCSV e da PTAX de fechamento. O CDI de um dia útil só aparece na manhã seguinte; a janela de 10 dias consultada a cada coleta o recupera, e a silver usa a janela mais recente.
