# Cartas Pokémon como ativo de coleção

Projeto individual do módulo **Data Collection and Storage** (MBA em Engenharia de Dados, Mackenzie).
Pipeline diário que coleta preços de cartas e produtos selados do TCGplayer (via TCGCSV), grava no data lake
da turma (RustFS/MinIO, bucket `tcg`), monta um lakehouse com **DuckDB + Parquet**, um **modelo dimensional**
e um **dashboard em Streamlit** que responde a cinco perguntas de investimento em reais (PTAX do dia) e ao
desafio da carteira de R$ 1.000 contra dólar e CDI.

- **Aluno:** Kauê Douglas
- **Coleção escolhida:** ASC — ME: Ascended Heroes (group_id 24541)
- **Primeiro dia de coleta (no lake atual):** 14/11/2026 (a coleta começou em 12/11/2026 no endpoint antigo do lake; ver lacunas)
- **Dias sem coleta (lacunas):** 12/11/2026, 13/11/2026 e 16/11/2026. O dia 16/11 foi perdido porque o agendador do GitHub atrasou as duas execuções em 6h a 6h30 e elas começaram já em 17/11; a trava de frescor abortou sem gravar (ADR-008, revisão 1). Os dias 12/11 e 13/11: A coleta desses dias foi gravada no endpoint antigo do data lake (`s3.afonsolelis.tech`), que o professor substituiu em 14/11/2026; as credenciais antigas foram revogadas e os objetos não foram migrados. A série da ASC no lake atual começa em 14/11/2026. Nada foi inventado nem reconstruído para preencher o intervalo.

## Arquitetura

```
TCGCSV (products, prices) ─┐
PTAX (BCB Olinda)         ─┼─► collect ─► raw/ (imutável) ─► silver/ (Parquet + Pydantic) ─► gold/ (DuckDB, estrela)
CDI  (BCB SGS 12)         ─┘                                      │                               │
                                                      quarentena/ ┘                               ├─► dashboard Streamlit
                                                                                                   └─► gold_turma/carteira
```

| Camada | Onde | Conteúdo |
|---|---|---|
| Bruto | `tcg/raw/{tcgplayer,bcb_ptax,bcb_cdi}/group_id=X/data=AAAA-MM-DD/` | Resposta original, nunca sobrescrita |
| Silver | `tcg/silver/{colecao,produto,preco_diario,cambio_diario,cdi_diario}/group_id=X/` | Contrato comum da turma, validado por Pydantic |
| Quarentena | `tcg/quarentena/<tabela>/group_id=X/data=.../` | Registros rejeitados, com o motivo |
| Gold | `tcg/gold/group_id=X/*.parquet` | Esquema estrela sobre a silver de **todas** as coleções |
| Turma | `tcg/gold_turma/carteira/group_id=X/carteira.parquet` | Resultado diário das cinco carteiras |

Modelo dimensional: `fato_preco_diario`, `fato_cambio_diario`, `dim_produto`, `dim_colecao`, `dim_data`, `dim_acabamento`
(ver [ADR-004](docs/adr/ADR-004-modelo-dimensional.md)).

## Primeiros passos

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env                                    # preencha com a chave enviada pelo canal da turma
```

1. **Escolha a coleção sem conflito.** `python -m pokelake check-colecao` lista os `group_id` que já têm pasta em
   `tcg/raw/tcgplayer/`. Se a sua já existir e você ainda não coletou, outra pessoa chegou antes: troque `COLECAO_SIGLA` no `.env`.
2. **Primeira coleta:** `python -m pokelake daily`. O TCGCSV publica a atualização do dia por volta de 20h UTC (17h em Brasília);
   antes disso o coletor se recusa a gravar (código de saída 2) para não colocar o preço de ontem na chave de hoje.
3. **Confira o resultado:** a silver deve ter `produto` e `preco_diario` não vazios e `quarentena` próxima de zero
   (a página do projeto cita, para a Destined Rivals em 21/10/2026, 281 produtos e 446 linhas de preço como ordem de grandeza).
   Se a quarentena vier cheia, abra os arquivos em `tcg/quarentena/` — o motivo de cada rejeição está lá.
4. **Agende** o job (próxima seção) e confirme que a segunda execução do dia não grava nada novo (idempotência).
5. Preencha o topo deste README e **registre o ADR-006 (carteira `propria`) com commit anterior ao primeiro cálculo da carteira**.

## Comandos

| Comando | O que faz |
|---|---|
| `python -m pokelake check-colecao` | Lista `group_id` ocupados no lake |
| `python -m pokelake collect` | Só coleta o dia (bruto) |
| `python -m pokelake silver` | Bruto → silver da sua coleção |
| `python -m pokelake gold` | Silver da turma → gold dimensional |
| `python -m pokelake portfolio` | Calcula as cinco carteiras |
| `python -m pokelake rebuild` | **Reconstrói silver + gold + carteira a partir do bruto (um único comando)** |
| `python -m pokelake daily` | Coleta + rebuild (o que o agendador roda) |
| `python -m pokelake demo` | Dados **sintéticos** locais para ver o dashboard (recusa rodar contra o S3) |
| `streamlit run dashboard/app.py` | Dashboard |
| `pytest -q` | Testes de unidade e de integração |

Para ver o dashboard antes:

```bash
python -m pokelake demo
POKELAKE_BACKEND=local LOCAL_ROOT=data_demo streamlit run dashboard/app.py
```

O modo demo grava só em `data_demo/` e o dashboard exibe um aviso de dado sintético. **Nunca** aponte dados de demonstração para o lake da turma.

## Agendamento

**GitHub Actions** (recomendado): `.github/workflows/coleta.yml` roda todo dia às 21:30 UTC (18:30 em Brasília).
Em *Settings → Secrets and variables → Actions* crie os secrets `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`
e as variables `COLECAO_SIGLA` e `RESPONSAVEL`. O botão *Run workflow* permite disparar manualmente.

**Railway** (alternativa): crie um serviço a partir deste repositório (usa o `Dockerfile`), defina as mesmas variáveis de ambiente
e configure *Cron Schedule* como `30 21 * * *`.

Como o bruto é imutável e a coleta confere a existência da chave antes de gravar, reexecutar um dia é sempre seguro.
A PTAX é recuperável retroativamente (o coletor refaz os últimos 5 dias se faltar algum), mas **o preço do TCGplayer não**:
um dia sem coleta é uma lacuna permanente e precisa ser listada no topo deste README.

## Decisões e documentação SDD

- [`specs/`](specs/): persona, objetivos de negócio, especificação, plano e tarefas (método CREATE).
- [`docs/adr/`](docs/adr/): decisões de arquitetura (fonte, coleta, câmbio, modelo, convenções analíticas, carteira, lakehouse).
- [`docs/atam.md`](docs/atam.md): validação ATAM com cenários de qualidade, pontos de sensibilidade e riscos.
- [`docs/rastreabilidade.md`](docs/rastreabilidade.md): requisito → decisão → código → teste.
- [`docs/historico_prompts.md`](docs/historico_prompts.md): histórico dos prompts (complete com os seus).

## Limites do dado (leia antes de interpretar o dashboard)

- O `market_price` do TCGplayer vem de vendas recentes nos EUA, em dólar, sem separar a condição da carta, sem frete, sem taxas e sem o preço praticado no Brasil.
- A PTAX é taxa de referência; cartão internacional paga outra cotação (spread e IOF). O CDI entra sem imposto e sem taxas de corretora.
- A série tem cerca de sete semanas. Descreve o que aconteceu; não sustenta previsão nem recomendação de compra.
- Nulo não é zero: preço ausente fica nulo na silver, nunca entra em média ou variação, e a carteira só o "carrega" na avaliação (marcado no painel).
