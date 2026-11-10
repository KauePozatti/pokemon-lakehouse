"""Modelos Pydantic da silver — o contrato comum da turma.

Nulo não é zero: preço ausente fica None e nunca entra em média ou variação.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

import pyarrow as pa
from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ColecaoSilver(_Base):
    group_id: int
    nome: str = Field(min_length=1)
    sigla: str = Field(min_length=1)
    data_lancamento: date
    responsavel: str


class ProdutoSilver(_Base):
    product_id: int
    group_id: int
    nome: str = Field(min_length=1)
    tipo_produto: Literal["carta", "selado"]
    raridade: Optional[str] = None
    numero: Optional[str] = None
    image_url: Optional[str] = None
    url: Optional[str] = None


class PrecoDiarioSilver(_Base):
    data: date
    product_id: int
    group_id: int
    acabamento: str = Field(min_length=1)
    market_price: Optional[float] = Field(default=None, ge=0)
    low_price: Optional[float] = Field(default=None, ge=0)
    mid_price: Optional[float] = Field(default=None, ge=0)
    high_price: Optional[float] = Field(default=None, ge=0)
    moeda: Literal["USD"] = "USD"
    fonte: str
    chave_raw: str


class CambioDiarioSilver(_Base):
    data: date
    cotacao_compra: float = Field(gt=0)
    cotacao_venda: float = Field(gt=0)
    data_hora_cotacao: datetime
    boletim: Literal["Fechamento"] = "Fechamento"
    chave_raw: str


class CdiDiarioSilver(_Base):
    data: date
    taxa_dia: float = Field(ge=0)  # % ao dia, como publicada
    chave_raw: str


# Esquemas Arrow: nomes e tipos exatamente como no contrato (INTEGER = int32).
SCHEMAS: dict[str, pa.Schema] = {
    "colecao": pa.schema(
        [
            ("group_id", pa.int32()),
            ("nome", pa.string()),
            ("sigla", pa.string()),
            ("data_lancamento", pa.date32()),
            ("responsavel", pa.string()),
        ]
    ),
    "produto": pa.schema(
        [
            ("product_id", pa.int32()),
            ("group_id", pa.int32()),
            ("nome", pa.string()),
            ("tipo_produto", pa.string()),
            ("raridade", pa.string()),
            ("numero", pa.string()),
            ("image_url", pa.string()),
            ("url", pa.string()),
        ]
    ),
    "preco_diario": pa.schema(
        [
            ("data", pa.date32()),
            ("product_id", pa.int32()),
            ("group_id", pa.int32()),
            ("acabamento", pa.string()),
            ("market_price", pa.float64()),
            ("low_price", pa.float64()),
            ("mid_price", pa.float64()),
            ("high_price", pa.float64()),
            ("moeda", pa.string()),
            ("fonte", pa.string()),
            ("chave_raw", pa.string()),
        ]
    ),
    "cambio_diario": pa.schema(
        [
            ("data", pa.date32()),
            ("cotacao_compra", pa.float64()),
            ("cotacao_venda", pa.float64()),
            ("data_hora_cotacao", pa.timestamp("us")),
            ("boletim", pa.string()),
            ("chave_raw", pa.string()),
        ]
    ),
    "cdi_diario": pa.schema(
        [
            ("data", pa.date32()),
            ("taxa_dia", pa.float64()),
            ("chave_raw", pa.string()),
        ]
    ),
}

CARTEIRA_SCHEMA = pa.schema(
    [
        ("data", pa.date32()),
        ("group_id", pa.int32()),
        ("carteira", pa.string()),
        ("valor_brl", pa.float64()),
        ("retorno_acumulado", pa.float64()),
        ("taxa_venda", pa.float64()),
    ]
)
