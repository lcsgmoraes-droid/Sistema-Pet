"""Utilitarios compartilhados do importador SimplesVet."""

from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


SIMPLESVET_PATH = Path(
    r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\simplesvet\banco"
)


def ler_csv(arquivo: str, limite: Optional[int] = None) -> List[Dict]:
    """Le arquivo CSV e retorna lista de dicionarios."""
    caminho = SIMPLESVET_PATH / arquivo

    if not caminho.exists():
        print(f"[ERRO] Arquivo nao encontrado: {caminho}")
        return []

    registros = []
    with open(caminho, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if limite and i >= limite:
                break
            registros.append(row)

    print(f"[INFO] Lidos {len(registros)} registros de {arquivo}")
    return registros


def limpar_cpf(cpf: Optional[str]) -> Optional[str]:
    """Remove formatacao do CPF."""
    if not cpf or cpf == "NULL" or cpf == "":
        return None
    return re.sub(r"[^0-9]", "", cpf)


def limpar_telefone(tel: Optional[str]) -> Optional[str]:
    """Remove formatacao do telefone."""
    if not tel or tel == "NULL" or tel == "":
        return None
    return re.sub(r"[^0-9]", "", tel)


def carregar_contatos() -> Dict[str, Dict[str, Optional[str]]]:
    """Carrega contatos (telefone/celular) do SimplesVet."""
    contatos = {}
    registros = ler_csv("glo_contato.csv", limite=None)

    for row in registros:
        pes_id = row.get("pes_int_codigo")
        if not pes_id:
            continue

        tipo = (row.get("tco_var_nome") or "").strip().lower()
        contato = limpar_telefone(row.get("con_var_contato"))
        if not contato:
            continue

        if pes_id not in contatos:
            contatos[pes_id] = {"telefone": None, "celular": None}

        if "cel" in tipo:
            contatos[pes_id]["celular"] = contatos[pes_id]["celular"] or contato
        elif "tel" in tipo or "fone" in tipo:
            contatos[pes_id]["telefone"] = contatos[pes_id]["telefone"] or contato

    return contatos


def parse_decimal(valor: Optional[str]) -> float:
    """Converte string decimal para float."""
    if not valor or valor == "NULL" or valor == "":
        return 0.0
    try:
        return float(valor.replace(",", "."))
    except Exception:
        return 0.0


def parse_bool(valor: Optional[str], verdadeiro: str = "Sim") -> bool:
    """Converte string para boolean."""
    if not valor or valor == "NULL":
        return False
    return valor.strip() == verdadeiro


def parse_date(data: Optional[str]) -> Optional[datetime]:
    """Converte string de data para datetime."""
    if not data or data == "NULL" or data == "":
        return None

    formatos = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M:%S"]

    for fmt in formatos:
        try:
            return datetime.strptime(data.strip(), fmt)
        except Exception:
            continue

    return None


def log(msg: str, nivel: str = "INFO"):
    """Log com timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    icones = {"INFO": "[INFO]", "SUCESSO": "[OK]", "ERRO": "[ERR]", "AVISO": "[WARN]"}
    icone = icones.get(nivel, "[INFO]")
    try:
        print(f"[{timestamp}] {icone} {msg}")
    except UnicodeEncodeError:
        print(f"[{timestamp}] {nivel} {msg.encode('ascii', 'ignore').decode()}")
