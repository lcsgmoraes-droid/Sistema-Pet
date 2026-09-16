"""Regras de calculo e serializacao dos orcamentos do grupo."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import secrets
from typing import Callable

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models import Cliente, Tenant
from app.orcamentos_grupo_models import (
    OrcamentoGrupo,
    OrcamentoGrupoConfiguracao,
    OrcamentoGrupoCotacao,
    OrcamentoGrupoEmpresa,
    OrcamentoGrupoItem,
)


CENTAVO = Decimal("0.01")
MILHAR = Decimal("0.001")


def moeda(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def quantidade(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(MILHAR, rounding=ROUND_HALF_UP)


def texto(value) -> str | None:
    normalizado = str(value or "").strip()
    return normalizado or None


def obter_ou_criar_configuracao(db: Session, tenant_id) -> OrcamentoGrupoConfiguracao:
    configuracao = (
        db.query(OrcamentoGrupoConfiguracao)
        .filter(OrcamentoGrupoConfiguracao.tenant_id == tenant_id)
        .first()
    )
    if configuracao:
        return configuracao

    configuracao = OrcamentoGrupoConfiguracao(
        tenant_id=tenant_id,
        percentual_minimo=10,
        percentual_maximo=30,
        quantidade_empresas=2,
        validade_dias=15,
    )
    db.add(configuracao)
    db.flush()
    return configuracao


def sortear_percentual(
    minimo,
    maximo,
    *,
    randbelow: Callable[[int], int] = secrets.randbelow,
) -> Decimal:
    minimo_cent = int((Decimal(str(minimo)) * 100).to_integral_value())
    maximo_cent = int((Decimal(str(maximo)) * 100).to_integral_value())
    if maximo_cent < minimo_cent:
        raise ValueError("Faixa percentual invalida")
    return Decimal(minimo_cent + randbelow(maximo_cent - minimo_cent + 1)) / 100


def snapshot_tenant(tenant: Tenant) -> dict:
    return {
        "nome": tenant.name,
        "razao_social": tenant.razao_social,
        "cnpj": tenant.cnpj,
        "inscricao_estadual": tenant.inscricao_estadual,
        "endereco": tenant.endereco,
        "numero": tenant.numero,
        "complemento": tenant.complemento,
        "bairro": tenant.bairro,
        "cidade": tenant.cidade,
        "uf": tenant.uf,
        "cep": tenant.cep,
        "telefone": tenant.telefone,
        "email": tenant.email,
        "logo_url": tenant.logo_url,
    }


def snapshot_cliente(cliente: Cliente) -> dict:
    return {
        "nome": cliente.nome_fantasia or cliente.nome,
        "razao_social": cliente.razao_social,
        "cnpj": cliente.cnpj,
        "inscricao_estadual": cliente.inscricao_estadual,
        "endereco": cliente.endereco,
        "numero": cliente.numero,
        "complemento": cliente.complemento,
        "bairro": cliente.bairro,
        "cidade": cliente.cidade,
        "uf": cliente.estado,
        "cep": cliente.cep,
        "telefone": cliente.telefone or cliente.celular,
        "email": cliente.email,
        "responsavel": cliente.responsavel,
    }


def montar_itens_snapshot(
    itens: list[OrcamentoGrupoItem], percentual: Decimal
) -> tuple[list[dict], Decimal]:
    multiplicador = Decimal("1") + percentual / Decimal("100")
    resultado = []
    total = Decimal("0")
    for item in itens:
        preco_unitario = moeda(Decimal(item.preco_unitario_base) * multiplicador)
        preco_total = moeda(preco_unitario * Decimal(item.quantidade))
        total += preco_total
        resultado.append(
            {
                "ordem": item.ordem,
                "descricao": item.descricao,
                "quantidade": str(quantidade(item.quantidade)),
                "unidade": item.unidade,
                "preco_unitario": str(preco_unitario),
                "preco_total": str(preco_total),
            }
        )
    return resultado, moeda(total)


def obter_orcamento(db: Session, tenant_id, orcamento_id: int) -> OrcamentoGrupo:
    orcamento = (
        db.query(OrcamentoGrupo)
        .options(
            joinedload(OrcamentoGrupo.itens),
            joinedload(OrcamentoGrupo.cotacoes),
        )
        .filter(
            OrcamentoGrupo.id == orcamento_id,
            OrcamentoGrupo.tenant_id == tenant_id,
        )
        .first()
    )
    if not orcamento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orcamento nao encontrado",
        )
    return orcamento


def serializar_configuracao(configuracao: OrcamentoGrupoConfiguracao) -> dict:
    return {
        "id": configuracao.id,
        "percentual_minimo": float(configuracao.percentual_minimo),
        "percentual_maximo": float(configuracao.percentual_maximo),
        "quantidade_empresas": configuracao.quantidade_empresas,
        "validade_dias": configuracao.validade_dias,
        "observacoes_padrao": configuracao.observacoes_padrao,
    }


def serializar_empresa(empresa: OrcamentoGrupoEmpresa) -> dict:
    cliente = empresa.cliente
    return {
        "id": empresa.id,
        "cliente_id": empresa.cliente_id,
        "ativo": empresa.ativo,
        "fixada_padrao": empresa.fixada_padrao,
        "observacoes": empresa.observacoes,
        "nome": cliente.nome_fantasia or cliente.nome,
        "razao_social": cliente.razao_social,
        "cnpj": cliente.cnpj,
        "telefone": cliente.telefone or cliente.celular,
        "email": cliente.email,
        "cidade": cliente.cidade,
        "uf": cliente.estado,
    }


def serializar_orcamento(orcamento: OrcamentoGrupo, *, resumido=False) -> dict:
    base = {
        "id": orcamento.id,
        "numero": orcamento.numero,
        "titulo": orcamento.titulo,
        "destinatario": orcamento.destinatario,
        "data_emissao": orcamento.data_emissao,
        "validade_dias": orcamento.validade_dias,
        "percentual_minimo": float(orcamento.percentual_minimo),
        "percentual_maximo": float(orcamento.percentual_maximo),
        "observacoes": orcamento.observacoes,
        "status": orcamento.status,
        "total_base": float(orcamento.total_base),
        "quantidade_cotacoes": len(orcamento.cotacoes or []),
        "created_at": orcamento.created_at,
    }
    if resumido:
        return base

    base["itens"] = [
        {
            "id": item.id,
            "ordem": item.ordem,
            "descricao": item.descricao,
            "quantidade": float(item.quantidade),
            "unidade": item.unidade,
            "preco_unitario_base": float(item.preco_unitario_base),
            "total_base": float(item.total_base),
        }
        for item in sorted(orcamento.itens or [], key=lambda row: row.ordem)
    ]
    base["cotacoes"] = [
        {
            "id": cotacao.id,
            "ordem": cotacao.ordem,
            "empresa_grupo_id": cotacao.empresa_grupo_id,
            "emissor_principal": cotacao.emissor_principal,
            "fixada": cotacao.fixada,
            "percentual_acrescimo": float(cotacao.percentual_acrescimo),
            "empresa": cotacao.empresa_snapshot,
            "itens": cotacao.itens_snapshot,
            "total": float(cotacao.total),
        }
        for cotacao in sorted(orcamento.cotacoes or [], key=lambda row: row.ordem)
    ]
    return base


def criar_orcamento(
    db: Session,
    *,
    tenant_id,
    user_id: int,
    payload,
) -> OrcamentoGrupo:
    configuracao = obter_ou_criar_configuracao(db, tenant_id)
    empresas_ids = [selecao.empresa_id for selecao in payload.empresas]
    empresas = (
        db.query(OrcamentoGrupoEmpresa)
        .options(joinedload(OrcamentoGrupoEmpresa.cliente))
        .filter(
            OrcamentoGrupoEmpresa.tenant_id == tenant_id,
            OrcamentoGrupoEmpresa.id.in_(empresas_ids),
            OrcamentoGrupoEmpresa.ativo.is_(True),
        )
        .all()
    )
    empresas_por_id = {empresa.id: empresa for empresa in empresas}
    if len(empresas_por_id) != len(empresas_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uma das empresas selecionadas nao esta disponivel neste tenant",
        )

    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Empresa principal nao encontrada")

    minimo = Decimal(configuracao.percentual_minimo)
    maximo = Decimal(configuracao.percentual_maximo)
    validade = payload.validade_dias or configuracao.validade_dias
    observacoes = texto(payload.observacoes) or texto(configuracao.observacoes_padrao)
    orcamento = OrcamentoGrupo(
        tenant_id=tenant_id,
        user_id=user_id,
        titulo=payload.titulo,
        destinatario=texto(payload.destinatario),
        data_emissao=payload.data_emissao or date.today(),
        validade_dias=validade,
        percentual_minimo=minimo,
        percentual_maximo=maximo,
        observacoes=observacoes,
        status="emitido",
        total_base=0,
    )
    db.add(orcamento)
    db.flush()
    orcamento.numero = f"ORC-{orcamento.data_emissao:%Y%m%d}-{orcamento.id:06d}"

    total_base = Decimal("0")
    itens = []
    for ordem, item_payload in enumerate(payload.itens, start=1):
        qtd = quantidade(item_payload.quantidade)
        preco = moeda(item_payload.preco_unitario_base)
        total_item = moeda(qtd * preco)
        item = OrcamentoGrupoItem(
            tenant_id=tenant_id,
            orcamento_id=orcamento.id,
            ordem=ordem,
            descricao=item_payload.descricao,
            quantidade=qtd,
            unidade=texto(item_payload.unidade),
            preco_unitario_base=preco,
            total_base=total_item,
        )
        db.add(item)
        itens.append(item)
        total_base += total_item
    orcamento.total_base = moeda(total_base)
    db.flush()

    itens_principal, total_principal = montar_itens_snapshot(itens, Decimal("0"))
    db.add(
        OrcamentoGrupoCotacao(
            tenant_id=tenant_id,
            orcamento_id=orcamento.id,
            ordem=1,
            emissor_principal=True,
            fixada=True,
            percentual_acrescimo=0,
            empresa_snapshot=snapshot_tenant(tenant),
            itens_snapshot=itens_principal,
            total=total_principal,
        )
    )

    for ordem, selecao in enumerate(payload.empresas, start=2):
        empresa = empresas_por_id[selecao.empresa_id]
        percentual = sortear_percentual(minimo, maximo)
        itens_snapshot, total = montar_itens_snapshot(itens, percentual)
        db.add(
            OrcamentoGrupoCotacao(
                tenant_id=tenant_id,
                orcamento_id=orcamento.id,
                empresa_grupo_id=empresa.id,
                ordem=ordem,
                emissor_principal=False,
                fixada=selecao.fixada,
                percentual_acrescimo=percentual,
                empresa_snapshot=snapshot_cliente(empresa.cliente),
                itens_snapshot=itens_snapshot,
                total=total,
            )
        )

    db.commit()
    return obter_orcamento(db, tenant_id, orcamento.id)
