"""Mapeamentos de cadastros usados pelo importador SimplesVet."""

from __future__ import annotations

from app.produtos_models import Categoria
from importar_simplesvet_state import ID_MAP, RUNTIME, STATS
from importar_simplesvet_utils import parse_date


def _preenchido(valor: str | None) -> str | None:
    return valor if valor not in (None, "", "NULL") else None


def dados_cliente(row: dict, contato: dict, cpf: str | None) -> dict:
    juridica = row.get("pes_var_tipo") == "Pessoa jurídica"
    return {
        "user_id": RUNTIME.user_id,
        "tenant_id": RUNTIME.tenant_id,
        "codigo": row.get("pes_var_chave"),
        "nome": row["pes_var_nome"].strip(),
        "tipo_pessoa": "PJ" if juridica else "PF",
        "cpf": None if juridica else cpf,
        "cnpj": cpf if juridica else None,
        "inscricao_estadual": _preenchido(row.get("pes_var_inscricaoestadual"))
        if juridica
        else None,
        "telefone": contato.get("telefone"),
        "celular": contato.get("celular"),
        "email": contato.get("email"),
        "cep": _preenchido(row.get("end_var_cep")),
        "endereco": _preenchido(row.get("end_var_endereco")),
        "numero": _preenchido(row.get("end_var_numero")),
        "complemento": _preenchido(row.get("end_var_complemento")),
        "bairro": _preenchido(row.get("end_var_bairro")),
        "cidade": _preenchido(row.get("end_var_municipio")),
        "estado": _preenchido(row.get("end_var_uf")),
        "observacoes": _preenchido(row.get("pes_txt_observacao")),
        "ativo": row.get("pes_var_status") != "Arquivado",
        "created_at": parse_date(row.get("pes_dti_inclusao")),
    }


def importar_categorias_produtos(db, registros: list[dict]) -> None:
    categorias_por_nome: dict[str, int] = {}
    for row in registros:
        nome_categoria = (row.get("tpr_var_nome") or "").strip()
        if not nome_categoria or nome_categoria == "NULL":
            continue
        chave = nome_categoria.casefold()
        if chave not in categorias_por_nome:
            existente = (
                db.query(Categoria).filter(Categoria.nome == nome_categoria).first()
            )
            if existente is None:
                existente = Categoria(
                    tenant_id=RUNTIME.tenant_id,
                    user_id=RUNTIME.user_id,
                    nome=nome_categoria,
                    ativo=True,
                )
                db.add(existente)
                db.flush()
                STATS["categorias"]["sucesso"] += 1
            else:
                STATS["categorias"]["duplicado"] += 1
            categorias_por_nome[chave] = existente.id
        if row.get("tpr_int_codigo"):
            ID_MAP["categorias"][row["tpr_int_codigo"]] = categorias_por_nome[chave]
    STATS["categorias"]["total"] = len(categorias_por_nome)
