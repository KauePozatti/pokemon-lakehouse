"""Acesso ao object storage (RustFS/MinIO via S3) e backend local para desenvolvimento."""
from __future__ import annotations

from pathlib import Path

from pokelake.config import Settings


class BaseLake:
    kind = "base"

    def exists(self, key: str) -> bool:  # pragma: no cover - interface
        raise NotImplementedError

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:  # pragma: no cover
        raise NotImplementedError

    def get(self, key: str) -> bytes:  # pragma: no cover
        raise NotImplementedError

    def list_keys(self, prefix: str) -> list[str]:  # pragma: no cover
        raise NotImplementedError

    def list_prefixes(self, prefix: str) -> list[str]:  # pragma: no cover
        raise NotImplementedError

    def uri(self, key: str) -> str:  # pragma: no cover
        raise NotImplementedError

    def put_if_absent(self, key: str, data: bytes, content_type: str = "application/json") -> bool:
        """Grava só se a chave não existir. Garante a imutabilidade do bruto (`raw/`).

        Retorna True se gravou, False se a chave já existia (nada foi alterado).
        """
        if self.exists(key):
            return False
        self.put(key, data, content_type)
        return True


class S3Lake(BaseLake):
    kind = "s3"

    def __init__(self, s: Settings):
        import boto3
        from botocore.config import Config

        self.bucket = s.bucket
        self.endpoint_url = s.endpoint_url
        self.settings = s
        self.client = boto3.client(
            "s3",
            endpoint_url=s.endpoint_url,
            aws_access_key_id=s.access_key,
            aws_secret_access_key=s.secret_key,
            region_name=s.region,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                retries={"max_attempts": 5, "mode": "standard"},
            ),
        )

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return False
            raise

    def put(self, key, data, content_type="application/octet-stream"):
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def get(self, key):
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def list_keys(self, prefix):
        out: list[str] = []
        for page in self.client.get_paginator("list_objects_v2").paginate(Bucket=self.bucket, Prefix=prefix):
            out.extend(o["Key"] for o in page.get("Contents", []))
        return sorted(out)

    def list_prefixes(self, prefix):
        out: list[str] = []
        pages = self.client.get_paginator("list_objects_v2").paginate(
            Bucket=self.bucket, Prefix=prefix, Delimiter="/"
        )
        for page in pages:
            out.extend(p["Prefix"] for p in page.get("CommonPrefixes", []))
        return sorted(out)

    def uri(self, key):
        return f"s3://{self.bucket}/{key}"


class LocalLake(BaseLake):
    kind = "local"

    def __init__(self, s: Settings):
        self.root = (Path(s.local_root) / s.bucket).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _p(self, key: str) -> Path:
        return self.root / key

    def exists(self, key):
        return self._p(key).is_file()

    def put(self, key, data, content_type="application/octet-stream"):
        p = self._p(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def get(self, key):
        return self._p(key).read_bytes()

    def list_keys(self, prefix):
        base = self._p(prefix)
        if base.is_file():
            return [prefix]
        if not base.exists():
            return []
        return sorted(str(p.relative_to(self.root)).replace("\\", "/") for p in base.rglob("*") if p.is_file())

    def list_prefixes(self, prefix):
        base = self._p(prefix)
        if not base.exists():
            return []
        return sorted(f"{prefix}{p.name}/" for p in base.iterdir() if p.is_dir())

    def uri(self, key):
        return self._p(key).as_posix()


def make_lake(s: Settings) -> BaseLake:
    if s.backend == "local":
        return LocalLake(s)
    if s.backend == "s3":
        if not (s.access_key and s.secret_key):
            raise RuntimeError(
                "S3_ACCESS_KEY / S3_SECRET_KEY não configurados. Preencha o .env com a chave enviada pelo canal da turma."
            )
        return S3Lake(s)
    raise ValueError(f"POKELAKE_BACKEND inválido: {s.backend}")
