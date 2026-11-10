# ADR-007 · Lakehouse: DuckDB + Parquet sobre S3

**Status:** aceito

DuckDB lê Parquet no RustFS/MinIO pela extensão `httpfs` (path-style, secret S3). Silver e gold são Parquet com compressão zstd; nenhum banco precisa ficar de pé. `read_parquet(..., hive_partitioning=false, union_by_name=true)` evita colunas duplicadas (`group_id`/`data` já existem nos arquivos) e tolera colunas extras dos colegas.

**Escrita.** Cada aluno escreve só nos próprios prefixos (`group_id=` da sua coleção) e lê todos os demais.
