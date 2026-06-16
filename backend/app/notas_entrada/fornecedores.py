"""Helpers de fornecedores para importacao de notas de entrada."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.clientes_routes import gerar_codigo_cliente
from app.models import Cliente

logger = logging.getLogger(__name__)


def gerar_prefixo_fornecedor(nome: str) -> str:
    """
    Gera um prefixo baseado no nome do fornecedor.

    Ex: Megazoo -> MGZ, Reino das Aves -> RA
    """
    palavras_ignorar = {
        "ltda",
        "sa",
        "me",
        "epp",
        "eireli",
        "comercio",
        "industria",
        "distribuidora",
        "de",
        "da",
        "do",
        "das",
        "dos",
        "e",
    }
    palavras = [p for p in nome.lower().split() if p not in palavras_ignorar]

    if not palavras:
        return nome[:3].upper()

    if len(palavras) == 1:
        return palavras[0][:3].upper()

    if len(palavras) <= 3:
        return "".join([p[0] for p in palavras]).upper()

    palavras_ordenadas = sorted(palavras, key=len, reverse=True)[:3]
    return "".join([p[0] for p in palavras_ordenadas]).upper()


def criar_fornecedor_automatico(
    dados_xml: dict, db: Session, current_user, tenant_id: int
) -> tuple:
    """
    Cria um fornecedor automaticamente a partir dos dados do XML.

    Se ja existir um fornecedor inativo com o mesmo CNPJ, reativa ele.
    Retorna (fornecedor, foi_criado_agora).
    """
    cnpj = dados_xml["fornecedor_cnpj"]

    fornecedor = (
        db.query(Cliente)
        .filter(
            Cliente.cnpj == cnpj,
            Cliente.tenant_id == tenant_id,
        )
        .first()
    )

    if fornecedor:
        if not fornecedor.ativo:
            logger.info("Reativando fornecedor inativo: %s", fornecedor.nome)
            fornecedor.ativo = True
            fornecedor.nome = dados_xml["fornecedor_nome"]
            fornecedor.razao_social = dados_xml["fornecedor_nome"]
            fornecedor.nome_fantasia = dados_xml.get("fornecedor_fantasia", "")
            fornecedor.inscricao_estadual = dados_xml.get("fornecedor_ie", "")
            fornecedor.endereco = dados_xml.get("fornecedor_endereco", "")
            fornecedor.numero = dados_xml.get("fornecedor_numero", "")
            fornecedor.bairro = dados_xml.get("fornecedor_bairro", "")
            fornecedor.cidade = dados_xml.get("fornecedor_cidade", "")
            fornecedor.estado = dados_xml.get("fornecedor_uf", "")
            fornecedor.cep = dados_xml.get("fornecedor_cep", "")
            fornecedor.telefone = dados_xml.get("fornecedor_telefone", "")

            if not fornecedor.codigo:
                fornecedor.codigo = gerar_codigo_cliente(
                    db, "fornecedor", "PJ", tenant_id
                )

            db.commit()
            db.refresh(fornecedor)
            logger.info(
                "Fornecedor reativado: %s (Codigo: %s)",
                fornecedor.nome,
                fornecedor.codigo,
            )
            return (fornecedor, True)

        if not fornecedor.codigo:
            fornecedor.codigo = gerar_codigo_cliente(db, "fornecedor", "PJ", tenant_id)
            db.commit()
            db.refresh(fornecedor)
            logger.info(
                "Codigo gerado para fornecedor existente: %s (Codigo: %s)",
                fornecedor.nome,
                fornecedor.codigo,
            )

        return (fornecedor, False)

    codigo = gerar_codigo_cliente(db, "fornecedor", "PJ", tenant_id)

    fornecedor = Cliente(
        tipo_cadastro="fornecedor",
        tipo_pessoa="PJ",
        nome=dados_xml["fornecedor_nome"],
        razao_social=dados_xml["fornecedor_nome"],
        nome_fantasia=dados_xml.get("fornecedor_fantasia", ""),
        cnpj=cnpj,
        inscricao_estadual=dados_xml.get("fornecedor_ie", ""),
        endereco=dados_xml.get("fornecedor_endereco", ""),
        numero=dados_xml.get("fornecedor_numero", ""),
        bairro=dados_xml.get("fornecedor_bairro", ""),
        cidade=dados_xml.get("fornecedor_cidade", ""),
        estado=dados_xml.get("fornecedor_uf", ""),
        cep=dados_xml.get("fornecedor_cep", ""),
        telefone=dados_xml.get("fornecedor_telefone", ""),
        codigo=codigo,
        ativo=True,
        user_id=current_user.id,
        tenant_id=tenant_id,
    )

    db.add(fornecedor)
    db.commit()
    db.refresh(fornecedor)

    logger.info("Fornecedor criado automaticamente: %s", fornecedor.nome)

    return (fornecedor, True)
