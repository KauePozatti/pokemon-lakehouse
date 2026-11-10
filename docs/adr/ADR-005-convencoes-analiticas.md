# ADR-005 · Convenções analíticas

**Status:** aceito

- **Um exemplar de cada carta:** um acabamento canônico por produto (Normal > Holofoil > Reverse Holofoil > demais). Evita contar a mesma carta duas vezes na soma da coleção.
- **Code Card** fora das perguntas (não é colecionável).
- **Filtros de preço mínimo em US$** (1 na P1, 5 na P5), para a lista não mudar com o câmbio.
- **Cestas fixas:** itens com preço no primeiro dia da janela; dias sem preço usam o último preço conhecido (só na análise, nada é gravado na silver).
- **"Double Rare em diante" (P2):** toda raridade fora de {Common, Uncommon, Rare, Promo, Code Card}. Hipótese: confirmar com os valores reais de `Rarity`.
- **Janela comum (P3 e P5):** a partir do primeiro dia em que **todas** as coleções têm preço, para comparar a mesma janela; coleções de lançamento mais recente reduzem a janela de todas.
- **P5:** volatilidade = desvio-padrão amostral dos retornos diários (em R$ ou US$ conforme a chave); exige ≥ 4 observações.
