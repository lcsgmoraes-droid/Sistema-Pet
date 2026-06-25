"""Rotas de confronto entre pedidos de compra e NF-e."""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import Cliente
from app.produtos_models import (
    PedidoCompra,
    PedidoCompraItem,
    PedidoCompraNotaEntrada,
)

from .confronto_calculo import (
    _formatar_numeros_notas,
    _realizar_confronto,
    _resumir_notas_confronto,
)
from .confronto_exportacao import (
    _carregar_confronto_exportacao,
    criar_confronto_csv_response,
    criar_confronto_pdf_response,
    gerar_texto_email_confronto,
)
from .confronto_vinculos import (
    _buscar_pedido_finalizado_da_nota,
    _garantir_vinculo_legado,
    _ids_notas_vinculadas,
    _obter_notas_vinculadas,
    _salvar_confronto_pedido,
)

router = APIRouter()


@router.get("/{pedido_id}/notas-candidatas")
def listar_notas_candidatas(
    pedido_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista NF-e importadas do mesmo fornecedor do pedido, ordenadas pela mais recente."""
    from app.produtos_models import NotaEntrada

    _, tenant_id = current_user_and_tenant
    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    fornecedor = (
        db.query(Cliente)
        .filter(Cliente.id == pedido.fornecedor_id, Cliente.tenant_id == tenant_id)
        .first()
    )

    query = db.query(NotaEntrada).filter(NotaEntrada.tenant_id == tenant_id)
    if fornecedor and fornecedor.cnpj:
        cnpj_limpo = (
            fornecedor.cnpj.replace(".", "").replace("/", "").replace("-", "").strip()
        )
        query = query.filter(
            or_(
                NotaEntrada.fornecedor_id == pedido.fornecedor_id,
                func.replace(
                    func.replace(
                        func.replace(NotaEntrada.fornecedor_cnpj, ".", ""), "/", ""
                    ),
                    "-",
                    "",
                )
                == cnpj_limpo,
            )
        )
    elif fornecedor:
        query = query.filter(NotaEntrada.fornecedor_id == pedido.fornecedor_id)

    notas = query.order_by(desc(NotaEntrada.data_emissao)).limit(20).all()
    nota_ids_vinculadas = set(_ids_notas_vinculadas(db, pedido, tenant_id))

    return {
        "notas": [
            {
                "id": nota.id,
                "numero_nota": nota.numero_nota,
                "serie": nota.serie,
                "chave_acesso": nota.chave_acesso,
                "fornecedor_nome": nota.fornecedor_nome,
                "data_emissao": nota.data_emissao,
                "valor_total": nota.valor_total,
                "status": nota.status,
                "ja_vinculada": nota.id in nota_ids_vinculadas,
            }
            for nota in notas
        ],
        "nota_vinculada_id": pedido.nota_entrada_id,
        "nota_vinculada_ids": list(nota_ids_vinculadas),
    }


@router.post("/{pedido_id}/vincular-nota/{nota_id}")
def vincular_nota_e_confrontar(
    pedido_id: int,
    nota_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Vincula NF-e ao pedido e realiza o confronto completo."""
    from app.produtos_models import NotaEntrada

    current_user, tenant_id = current_user_and_tenant
    pedido = (
        db.query(PedidoCompra)
        .options(joinedload(PedidoCompra.itens))
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    nota = (
        db.query(NotaEntrada)
        .options(joinedload(NotaEntrada.itens))
        .filter(NotaEntrada.id == nota_id, NotaEntrada.tenant_id == tenant_id)
        .first()
    )
    if not nota:
        raise HTTPException(status_code=404, detail="Nota fiscal não encontrada")
    if pedido.confronto_finalizado:
        raise HTTPException(status_code=400, detail="Confronto ja foi finalizado")

    outro_finalizado = _buscar_pedido_finalizado_da_nota(
        db, nota_id, pedido_id, tenant_id
    )
    if outro_finalizado:
        raise HTTPException(
            status_code=400,
            detail=f"Esta NF já está vinculada em definitivo ao pedido {outro_finalizado.numero_pedido}. Não é possível revinculá-la.",
        )

    _garantir_vinculo_legado(db, pedido, tenant_id, current_user.id)
    vinculo = (
        db.query(PedidoCompraNotaEntrada)
        .filter(
            PedidoCompraNotaEntrada.pedido_compra_id == pedido.id,
            PedidoCompraNotaEntrada.nota_entrada_id == nota_id,
            PedidoCompraNotaEntrada.tenant_id == tenant_id,
        )
        .first()
    )
    if not vinculo:
        db.add(
            PedidoCompraNotaEntrada(
                pedido_compra_id=pedido.id,
                nota_entrada_id=nota_id,
                user_id=current_user.id,
                tenant_id=tenant_id,
            )
        )
        db.flush()

    notas = _obter_notas_vinculadas(db, pedido, tenant_id, com_itens=True)
    confronto = _realizar_confronto(pedido, notas, db, tenant_id)
    _salvar_confronto_pedido(pedido, notas, confronto)
    db.commit()

    return {
        "message": "Confronto realizado com sucesso",
        "pedido_id": pedido_id,
        "nota_id": nota_id,
        "nota_ids": [n.id for n in notas],
        "notas_entrada": _resumir_notas_confronto(notas),
        "confronto": confronto,
    }


@router.delete("/{pedido_id}/vincular-nota/{nota_id}")
def desvincular_nota_e_recalcular_confronto(
    pedido_id: int,
    nota_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Remove uma NF do confronto do pedido e recalcula com as restantes."""
    current_user, tenant_id = current_user_and_tenant
    pedido = (
        db.query(PedidoCompra)
        .options(joinedload(PedidoCompra.itens))
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido nao encontrado")
    if pedido.confronto_finalizado:
        raise HTTPException(status_code=400, detail="Confronto ja foi finalizado")

    _garantir_vinculo_legado(db, pedido, tenant_id, current_user.id)
    vinculo = (
        db.query(PedidoCompraNotaEntrada)
        .filter(
            PedidoCompraNotaEntrada.pedido_compra_id == pedido.id,
            PedidoCompraNotaEntrada.nota_entrada_id == nota_id,
            PedidoCompraNotaEntrada.tenant_id == tenant_id,
        )
        .first()
    )
    if vinculo:
        db.delete(vinculo)
        db.flush()
    if pedido.nota_entrada_id == nota_id:
        pedido.nota_entrada_id = None

    notas = _obter_notas_vinculadas(db, pedido, tenant_id, com_itens=True)
    if not notas:
        pedido.nota_entrada_id = None
        pedido.data_confronto = None
        pedido.status_confronto = None
        pedido.resumo_confronto = None
        pedido.updated_at = datetime.utcnow()
        db.commit()
        return {
            "message": "NF removida. Pedido sem NF vinculada.",
            "pedido_id": pedido_id,
            "nota_ids": [],
            "notas_entrada": [],
            "confronto": None,
        }

    confronto = _realizar_confronto(pedido, notas, db, tenant_id)
    _salvar_confronto_pedido(pedido, notas, confronto)
    db.commit()
    return {
        "message": "NF removida e confronto recalculado",
        "pedido_id": pedido_id,
        "nota_ids": [n.id for n in notas],
        "notas_entrada": _resumir_notas_confronto(notas),
        "confronto": confronto,
    }


@router.get("/{pedido_id}/confronto")
def obter_confronto_salvo(
    pedido_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Retorna o confronto salvo do pedido."""
    _, tenant_id = current_user_and_tenant
    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    notas = _obter_notas_vinculadas(db, pedido, tenant_id)
    if not notas:
        raise HTTPException(status_code=404, detail="Pedido não possui NF vinculada")

    return {
        "pedido_id": pedido_id,
        "nota_entrada_id": pedido.nota_entrada_id,
        "nota_entrada_ids": [n.id for n in notas],
        "numero_nota": _formatar_numeros_notas(notas),
        "notas_entrada": _resumir_notas_confronto(notas),
        "data_confronto": pedido.data_confronto,
        "status_confronto": pedido.status_confronto,
        "confronto_finalizado": pedido.confronto_finalizado or False,
        "confronto": json.loads(pedido.resumo_confronto)
        if pedido.resumo_confronto
        else None,
    }


@router.get("/{pedido_id}/confronto/csv")
def exportar_confronto_csv(
    pedido_id: int,
    filtros: Optional[str] = Query(
        None,
        description="Filtrar status separados por vírgula: ok,divergencia_quantidade,divergencia_preco,divergencia_mista,nao_encontrado,nao_pedido",
    ),
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Exporta o confronto do pedido em CSV."""
    _, tenant_id = current_user_and_tenant
    pedido, itens, resumo, numero_nota = _carregar_confronto_exportacao(
        db, pedido_id, tenant_id, filtros
    )
    return criar_confronto_csv_response(pedido, itens, resumo, numero_nota)


@router.get("/{pedido_id}/confronto/pdf")
def exportar_confronto_pdf(
    pedido_id: int,
    filtros: Optional[str] = Query(
        None, description="Filtrar status separados por vírgula"
    ),
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Exporta o confronto do pedido em PDF."""
    _, tenant_id = current_user_and_tenant
    pedido, itens, resumo, numero_nota = _carregar_confronto_exportacao(
        db, pedido_id, tenant_id, filtros
    )
    return criar_confronto_pdf_response(
        db, tenant_id, pedido, itens, resumo, numero_nota
    )


@router.get("/{pedido_id}/confronto/email-texto")
def gerar_email_confronto(
    pedido_id: int,
    filtros: Optional[str] = Query(
        None, description="Filtrar status separados por vírgula"
    ),
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Gera texto de e-mail para enviar ao fornecedor com as divergências."""
    _, tenant_id = current_user_and_tenant
    pedido, itens, resumo, numero_nota = _carregar_confronto_exportacao(
        db, pedido_id, tenant_id, filtros, None
    )
    return gerar_texto_email_confronto(
        db, tenant_id, pedido, itens, resumo, numero_nota
    )


@router.post("/{pedido_id}/finalizar-confronto")
def finalizar_confronto(
    pedido_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Finaliza o confronto, criando vínculo permanente entre pedido e NF."""
    current_user, tenant_id = current_user_and_tenant
    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    _garantir_vinculo_legado(db, pedido, tenant_id, current_user.id)
    notas = _obter_notas_vinculadas(db, pedido, tenant_id)
    if not notas or not pedido.resumo_confronto:
        raise HTTPException(
            status_code=400, detail="Pedido não possui confronto realizado"
        )
    if pedido.confronto_finalizado:
        raise HTTPException(status_code=400, detail="Confronto já foi finalizado")

    for nota in notas:
        outro_finalizado = _buscar_pedido_finalizado_da_nota(
            db, nota.id, pedido_id, tenant_id
        )
        if outro_finalizado:
            raise HTTPException(
                status_code=400,
                detail=f"Esta NF ja esta vinculada ao pedido {outro_finalizado.numero_pedido}. Uma NF so pode ser finalizada em um pedido.",
            )

    outro = (
        db.query(PedidoCompra)
        .filter(
            PedidoCompra.nota_entrada_id == pedido.nota_entrada_id,
            PedidoCompra.confronto_finalizado,
            PedidoCompra.id != pedido_id,
            PedidoCompra.tenant_id == tenant_id,
        )
        .first()
    )
    if outro:
        raise HTTPException(
            status_code=400,
            detail=f"Esta NF já está vinculada ao pedido {outro.numero_pedido}. Uma NF só pode ser confrontada com um pedido.",
        )
    pedido.confronto_finalizado = True
    pedido.updated_at = datetime.utcnow()
    db.commit()
    return {
        "message": "Confronto finalizado com sucesso",
        "pedido_id": pedido_id,
        "numero_pedido": pedido.numero_pedido,
        "nota_entrada_id": pedido.nota_entrada_id,
        "nota_entrada_ids": [n.id for n in notas],
        "notas_entrada": _resumir_notas_confronto(notas),
    }


@router.post("/{pedido_id}/sugerir-pedido-complementar")
def sugerir_pedido_complementar(
    pedido_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria pedido rascunho com os itens faltantes após o confronto."""
    current_user, tenant_id = current_user_and_tenant
    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )
    if not pedido or not pedido.resumo_confronto:
        raise HTTPException(status_code=404, detail="Confronto não encontrado")

    confronto = json.loads(pedido.resumo_confronto)
    itens_faltantes = [
        item
        for item in confronto.get("itens", [])
        if item.get("status") in ("nao_encontrado", "divergencia_quantidade")
        and item.get("dif_qtd", 0) < 0
    ]

    if not itens_faltantes:
        raise HTTPException(
            status_code=400,
            detail="Não há itens faltantes para criar pedido complementar",
        )

    ultimo = db.query(PedidoCompra).order_by(desc(PedidoCompra.id)).first()
    numero = (ultimo.id + 1) if ultimo else 1
    numero_pedido = f"PC{datetime.now().year}{numero:05d}-C"

    valor_total = 0.0
    itens_novos = []
    for item in itens_faltantes:
        qtd_faltante = abs(item.get("dif_qtd", 0))
        preco = item.get("preco_pedido", 0)
        valor_item = qtd_faltante * preco
        valor_total += valor_item
        itens_novos.append(
            {
                "produto_id": item["produto_id"],
                "qtd": qtd_faltante,
                "preco": preco,
                "valor": valor_item,
            }
        )

    novo_pedido = PedidoCompra(
        numero_pedido=numero_pedido,
        fornecedor_id=pedido.fornecedor_id,
        status="rascunho",
        valor_total=valor_total,
        valor_frete=0,
        valor_desconto=0,
        valor_final=valor_total,
        data_pedido=datetime.utcnow(),
        observacoes=f"Pedido complementar gerado automaticamente após confronto com NF. Pedido original: {pedido.numero_pedido}",
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    db.add(novo_pedido)
    db.flush()

    for item in itens_novos:
        db.add(
            PedidoCompraItem(
                pedido_compra_id=novo_pedido.id,
                produto_id=item["produto_id"],
                quantidade_pedida=item["qtd"],
                quantidade_recebida=0,
                preco_unitario=item["preco"],
                desconto_item=0,
                valor_total=item["valor"],
                status="pendente",
                tenant_id=tenant_id,
            )
        )

    db.commit()

    return {
        "message": "Pedido complementar criado em rascunho",
        "pedido_complementar_id": novo_pedido.id,
        "numero_pedido": numero_pedido,
        "itens_faltantes": len(itens_novos),
        "valor_total": valor_total,
    }
