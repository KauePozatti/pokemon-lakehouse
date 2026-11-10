# ADR-001 · Fonte de preços: TCGCSV

**Status:** aceito · **Perguntas atendidas:** 1 a 5 e carteira

**Contexto.** Precisamos de produtos (imagem, URL, raridade, número) e preços (`low/mid/high/market`) por acabamento, para cartas e selados. A API oficial do TCGplayer não libera chaves novas; o PriceCharting é pago e protegido por desafio anti-robô (contornar está fora do escopo).

**Decisão.** Usar o TCGCSV (`/tcgplayer/3/{groupId}/products` e `/prices`), sem chave, com `User-Agent` próprio (`colecao-<sigla>/1.0`), pausa ≥ 100 ms e 1 coleta/dia.

**Consequências.** (+) Sem credencial, cobre cartas e selados. (−) Só o preço do dia: a série histórica nasce da própria coleta. (−) Sem preço por SKU/condição (limite declarado no dashboard).
