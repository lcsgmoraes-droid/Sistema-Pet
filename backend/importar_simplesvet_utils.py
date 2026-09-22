"""Utilitarios compartilhados do importador SimplesVet."""

from __future__ import annotations

import csv
import re
from datetime import datetime
from typing import Dict, List, Optional

from importar_simplesvet_state import RUNTIME


def ler_csv(arquivo: str, limite: Optional[int] = None) -> List[Dict]:
    """Le arquivo CSV e retorna lista de dicionarios."""
    caminho = RUNTIME.require_configured().source_dir / arquivo

    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo obrigatorio nao encontrado: {caminho}")

    registros = []
    with open(caminho, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row or not any(valor not in (None, "") for valor in row.values()):
                continue
            if limite and len(registros) >= limite:
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


def normalizar_unidade(valor: Optional[str]) -> str:
    """Converte descricoes do SimplesVet em siglas usadas no cadastro fiscal."""

    unidade = (valor or "").strip().casefold()
    if not unidade or unidade == "null":
        return "UN"
    if unidade.startswith(("uni", "uid", "uno", "unu", "umi")) or unidade == "un":
        return "UN"
    return {
        "kg": "KG",
        "granel": "KG",
        "saco": "SC",
        "caixa": "CX",
        "frasco": "FR",
        "cartela": "CT",
        "kit": "KIT",
    }.get(unidade, unidade.upper()[:10])


def gtin_valido(valor: Optional[str]) -> bool:
    """Aceita somente GTIN-8, -12, -13 ou -14 com digito correto."""

    gtin = (valor or "").strip()
    if not gtin.isdigit() or len(gtin) not in (8, 12, 13, 14):
        return False
    digitos = [int(char) for char in gtin]
    soma = sum(
        digito * (3 if indice % 2 == 0 else 1)
        for indice, digito in enumerate(reversed(digitos[:-1]))
    )
    return digitos[-1] == (10 - soma % 10) % 10


def carregar_contatos() -> Dict[str, Dict[str, Optional[str]]]:
    """Carrega telefone, celular e e-mail vinculados a cada pessoa."""
    contatos = {}
    registros = ler_csv("glo_contato.csv", limite=None)

    for row in registros:
        pes_id = row.get("pes_int_codigo")
        if not pes_id:
            continue

        tipo = (row.get("tco_var_nome") or "").strip().lower()
        valor = (row.get("con_var_contato") or "").strip()
        if not valor or valor == "NULL":
            continue

        if pes_id not in contatos:
            contatos[pes_id] = {"telefone": None, "celular": None, "email": None}

        if "email" in tipo or "e-mail" in tipo:
            if "@" in valor:
                contatos[pes_id]["email"] = contatos[pes_id]["email"] or valor
            continue

        contato = limpar_telefone(valor)
        if not contato:
            continue
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
    if nivel == "SUCESSO" and RUNTIME.quiet_rows:
        return
    timestamp = datetime.now().strftime("%H:%M:%S")
    icones = {"INFO": "[INFO]", "SUCESSO": "[OK]", "ERRO": "[ERR]", "AVISO": "[WARN]"}
    icone = icones.get(nivel, "[INFO]")
    try:
        print(f"[{timestamp}] {icone} {msg}")
    except UnicodeEncodeError:
        print(f"[{timestamp}] {nivel} {msg.encode('ascii', 'ignore').decode()}")
