"""Exporta clientes e catalogo de um backup JN Moura restaurado em SQL Server.

Requer ``pymssql`` apenas na maquina de extracao. A senha vem de
``JNM_SQL_PASSWORD``. Os CSVs e o manifesto devem ficar fora do Git.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKUP_FILE = Path.home() / "Downloads" / "VIRALATA_21451_2026-10-02 11-45-01.jnmbak"
OUTPUT_DIR = PROJECT_ROOT / "runtime" / "viralata-migration" / "source-20261002"


CLIENT_COLUMNS = (
    "source_id",
    "nome",
    "tipo_pessoa",
    "documento",
    "telefone",
    "telefone2",
    "celular",
    "email",
    "endereco",
    "numero",
    "bairro",
    "cep",
    "cidade",
    "uf",
    "inativo",
    "data_nascimento",
    "data_cadastro",
)
PRODUCT_COLUMNS = (
    "source_id",
    "nome",
    "grupo_id",
    "grupo_nome",
    "codigo_barras",
    "preco_venda",
    "preco_custo",
    "unidade",
    "inativo",
    "servico",
    "ncm",
    "estoque_minimo",
    "estoque_maximo",
    "estoque_raw",
    "data_cadastro",
)

CLIENT_QUERY = """
SELECT p.Codigo AS source_id, p.Nome AS nome, p.Tipo AS tipo_pessoa,
       p.CPF AS documento, p.Fone_Numero AS telefone,
       p.Fone2_Numero AS telefone2, p.Numero_Celular AS celular,
       p.Email AS email, p.Endereco AS endereco, p.Numero AS numero,
       p.Bairro AS bairro, p.Cep AS cep, ci.Cidade AS cidade,
       ci.Estado AS uf, p.Inativo AS inativo,
       p.Data_Nasc AS data_nascimento,
       p.Data_Cadastro AS data_cadastro
FROM dbo.Cliente AS c
JOIN dbo.Pessoa AS p ON p.Codigo = c.Pessoa
LEFT JOIN dbo.Cidade AS ci ON ci.Codigo = p.Cidade
ORDER BY p.Codigo
"""
SUPPLIER_QUERY = """
SELECT p.Codigo AS source_id, p.Nome AS nome, p.Tipo AS tipo_pessoa,
       p.CPF AS documento, p.Fone_Numero AS telefone,
       p.Fone2_Numero AS telefone2, p.Numero_Celular AS celular,
       p.Email AS email, p.Endereco AS endereco, p.Numero AS numero,
       p.Bairro AS bairro, p.Cep AS cep, ci.Cidade AS cidade,
       ci.Estado AS uf, f.Inativo AS inativo,
       p.Data_Nasc AS data_nascimento,
       p.Data_Cadastro AS data_cadastro
FROM dbo.Fornecedor AS f
JOIN dbo.Pessoa AS p ON p.Codigo = f.Pessoa
LEFT JOIN dbo.Cidade AS ci ON ci.Codigo = p.Cidade
ORDER BY p.Codigo
"""
PRODUCT_QUERY = """
SELECT p.Codigo AS source_id, p.Nome AS nome, p.Grupo AS grupo_id,
       g.Descricao AS grupo_nome, p.Codigo_Barra AS codigo_barras,
       p.Preco_Produto AS preco_venda, p.Preco_Custo AS preco_custo,
       p.Unidade AS unidade, p.Inativo AS inativo, p.Servico AS servico,
       p.NCM AS ncm, p.Estoque_Minimo AS estoque_minimo,
       p.Estoque_Maximo AS estoque_maximo, COALESCE(e.Qtde, 0) AS estoque_raw,
       p.Data_Cadastro AS data_cadastro
FROM dbo.Produto AS p
LEFT JOIN dbo.Grupo_Produto AS g ON g.Codigo = p.Grupo
LEFT JOIN dbo.Estoque AS e ON e.Produto = p.Codigo AND e.Deposito = 1
ORDER BY p.Codigo
"""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_cnpj(value: object) -> str:
    return "".join(char for char in str(value or "") if char.isdigit())


def csv_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value).strip()


def write_csv(path: Path, columns: tuple[str, ...], cursor) -> dict:
    temporary = path.with_suffix(".csv.tmp")
    count = 0
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        for row in cursor:
            writer.writerow({column: csv_value(row[column]) for column in columns})
            count += 1
    temporary.replace(path)
    return {"rows": count, "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def export(
    connection,
    output_dir: Path,
    backup_sha256: str,
    backup_bytes: int,
    expected_cnpj: str,
) -> dict:
    with connection.cursor(as_dict=True) as cursor:
        cursor.execute("SELECT CNPJ FROM dbo.Empresa")
        companies = cursor.fetchall()
    if len(companies) != 1:
        raise ValueError("Backup precisa conter exatamente uma empresa")
    source_cnpj = normalize_cnpj(companies[0]["CNPJ"])
    if source_cnpj != normalize_cnpj(expected_cnpj):
        raise ValueError("CNPJ da empresa no backup difere do esperado")
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for filename, columns, query in (
        ("clientes.csv", CLIENT_COLUMNS, CLIENT_QUERY),
        ("fornecedores.csv", CLIENT_COLUMNS, SUPPLIER_QUERY),
        ("produtos.csv", PRODUCT_COLUMNS, PRODUCT_QUERY),
    ):
        with connection.cursor(as_dict=True) as cursor:
            cursor.execute(query)
            files[filename] = write_csv(output_dir / filename, columns, cursor)
    manifest = {
        "schema_version": 1,
        "source_system": "jn_moura",
        "source_cnpj": source_cnpj,
        "backup_sha256": backup_sha256,
        "backup_bytes": backup_bytes,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }
    manifest_path = output_dir / "manifest.json"
    temporary = manifest_path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(manifest_path)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=14339)
    parser.add_argument("--database", required=True)
    parser.add_argument("--user", default="sa")
    parser.add_argument("--expected-source-cnpj", required=True)
    parser.add_argument("--expected-backup-sha256", required=True)
    args = parser.parse_args()
    password = os.environ.get("JNM_SQL_PASSWORD")
    if not password:
        parser.error("JNM_SQL_PASSWORD nao configurada")
    backup_file = BACKUP_FILE.resolve(strict=True)
    if not backup_file.is_relative_to((Path.home() / "Downloads").resolve()):
        parser.error("Backup precisa estar no diretorio Downloads")
    backup_sha256 = sha256_file(backup_file)
    if backup_sha256.lower() != args.expected_backup_sha256.lower():
        parser.error("Hash do backup original divergente")
    import pymssql

    with pymssql.connect(
        server=args.host,
        port=args.port,
        user=args.user,
        password=password,
        database=args.database,
        charset="UTF-8",
        login_timeout=10,
        timeout=300,
    ) as connection:
        manifest = export(
            connection,
            OUTPUT_DIR,
            backup_sha256,
            backup_file.stat().st_size,
            args.expected_source_cnpj,
        )
    print(
        json.dumps(
            {
                "source_cnpj": manifest["source_cnpj"],
                "backup_sha256": manifest["backup_sha256"],
                "files": {
                    name: info["rows"] for name, info in manifest["files"].items()
                },
                "output_dir": str(OUTPUT_DIR),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
