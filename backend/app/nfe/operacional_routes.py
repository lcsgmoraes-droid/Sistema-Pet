import traceback

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.auth.dependencies import get_current_user_and_tenant
from app.bling_integration import BlingAPI
from app.db import get_session
from app.models import User
from app.nfe_cache_models import BlingNotaFiscalCache
from app.produtos_models import EstoqueMovimentacao, Produto
from app.services.bling_sync_service import BlingSyncService
from app.services.nfe_authorized_reconciliation_service import (
    reconciliar_nf_autorizada_cache,
)
from app.utils.logger import logger
from app.vendas_models import Venda

router = APIRouter()


class CancelarNFeRequest(BaseModel):
    justificativa: str


class CartaCorrecaoRequest(BaseModel):
    correcao: str


def _nfe_routes():
    from app import nfe_routes

    return nfe_routes


@router.post("/{nfe_id}/reconciliar-fluxo")
async def reconciliar_fluxo_nfe(
    nfe_id: str,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant

    registro = (
        db.query(BlingNotaFiscalCache)
        .filter(
            BlingNotaFiscalCache.tenant_id == tenant_id,
            BlingNotaFiscalCache.bling_id == str(nfe_id).strip(),
        )
        .order_by(BlingNotaFiscalCache.id.desc())
        .first()
    )
    if not registro and str(nfe_id).strip().isdigit():
        registro = (
            db.query(BlingNotaFiscalCache)
            .filter(
                BlingNotaFiscalCache.tenant_id == tenant_id,
                BlingNotaFiscalCache.id == int(str(nfe_id).strip()),
            )
            .first()
        )

    if not registro:
        raise HTTPException(status_code=404, detail="NF nao encontrada no cache local")

    try:
        resultado = reconciliar_nf_autorizada_cache(
            db,
            tenant_id=tenant_id,
            registro=registro,
        )
        if resultado.get("success"):
            return {"success": True, **resultado}
        raise HTTPException(status_code=409, detail=resultado)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(
            "reconciliar_fluxo_nfe", f"Falha ao reconciliar NF {nfe_id}: {exc}"
        )
        raise HTTPException(
            status_code=500, detail=f"Erro ao reconciliar fluxo da NF: {exc}"
        )


@router.get("/{nfe_id}")
async def consultar_nfe(
    nfe_id: int,
    modelo: int | None = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Consulta dados completos de uma NF-e/NFC-e"""
    try:
        _current_user, tenant_id = user_and_tenant
        nfe_routes = _nfe_routes()
        bling = BlingAPI()
        detalhe, modelo_resolvido, venda = nfe_routes._consultar_detalhe_nota_bling(
            bling,
            db,
            tenant_id,
            nfe_id,
            modelo=modelo,
        )
        detalhe_normalizado = nfe_routes._normalizar_detalhe_nota_bling(
            detalhe, modelo_resolvido, venda=venda
        )
        nfe_routes._enriquecer_detalhe_com_xml_link(detalhe, detalhe_normalizado)
        nfe_routes._enriquecer_notas_com_pedidos_integrados(
            db, tenant_id, [detalhe_normalizado]
        )
        return detalhe_normalizado
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao consultar nota fiscal: {str(e)}"
        )


@router.get("/{nfe_id}/xml")
async def baixar_xml(
    nfe_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Baixa XML da NF-e"""
    try:
        bling = BlingAPI()
        xml = bling.baixar_xml(nfe_id)
        return {"xml": xml}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao baixar XML: {str(e)}")


@router.post("/{nfe_id}/cancelar")
async def cancelar_nfe(
    nfe_id: int,
    request: CancelarNFeRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cancela uma NF-e"""
    try:
        bling = BlingAPI()
        resultado = bling.cancelar_nfe(nfe_id, request.justificativa)

        # Atualizar status na venda
        venda = db.query(Venda).filter(Venda.nfe_bling_id == nfe_id).first()
        if venda:
            venda.nfe_status = "cancelada"
            venda.nfe_motivo_rejeicao = request.justificativa
            # Voltar status para 'finalizada' quando NF for cancelada
            venda.status = "finalizada"
            db.commit()

        return {
            "success": True,
            "message": "NF-e cancelada com sucesso",
            "data": resultado,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao cancelar NF-e: {str(e)}")


@router.post("/{nfe_id}/carta-correcao")
async def carta_correcao(
    nfe_id: int,
    request: CartaCorrecaoRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Emite Carta de Correção Eletrônica (CC-e)"""
    try:
        bling = BlingAPI()
        resultado = bling.carta_correcao(nfe_id, request.correcao)

        return {
            "success": True,
            "message": "Carta de Correção emitida com sucesso",
            "data": resultado,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao emitir CC-e: {str(e)}")


@router.delete("/{venda_id}")
async def excluir_nota(
    venda_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Remove os dados da nota fiscal da venda (apenas para notas não autorizadas)"""
    current_user, tenant_id = user_and_tenant
    try:
        # Buscar venda
        venda = (
            db.query(Venda)
            .filter(Venda.id == venda_id, Venda.tenant_id == tenant_id)
            .first()
        )

        if not venda:
            raise HTTPException(status_code=404, detail="Venda não encontrada")

        if not venda.nfe_bling_id:
            raise HTTPException(status_code=400, detail="Venda não possui nota fiscal")

        # Validar status - só permite excluir notas que não foram autorizadas
        status_permitidos = ["Pendente", "Erro", "Rejeitada", None]
        if venda.nfe_status not in status_permitidos:
            raise HTTPException(
                status_code=400,
                detail=f"Não é possível excluir nota com status '{venda.nfe_status}'. Apenas notas Pendentes, com Erro ou Rejeitadas podem ser excluídas.",
            )

        # Limpar dados da NF (mantém a venda)
        venda.nfe_tipo = None
        venda.nfe_modelo = None
        venda.nfe_numero = None
        venda.nfe_serie = None
        venda.nfe_chave = None
        venda.nfe_status = None
        venda.nfe_bling_id = None
        venda.nfe_data_emissao = None
        venda.nfe_motivo_rejeicao = None

        # Voltar status para finalizada
        venda.status = "finalizada"

        db.commit()

        return {
            "success": True,
            "message": "Dados da nota fiscal removidos com sucesso",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("excluir_nota_error", f"Erro ao excluir nota: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao excluir nota: {str(e)}")


@router.post("/webhook/bling")
async def webhook_bling(request: Request, db: Session = Depends(get_session)):
    """Recebe notificações do Bling sobre mudanças de status das notas"""
    try:
        # Pegar dados do webhook
        dados = await request.json()

        logger.info("webhook_bling", "\n=== WEBHOOK BLING RECEBIDO ===")
        logger.info("webhook_bling", f"Dados: {dados}")

        # Extrair informações do webhook
        # Formato esperado: { "topic": "nfe_notafiscal", "id": 123456, "status": "autorizada" }
        # Ou: { "topic": "notas_fiscais", "data": { "id": 123456, "situacao": 1 } }
        topic = dados.get("topic")
        nfe_id = dados.get("id") or (
            dados.get("data", {}).get("id") if dados.get("data") else None
        )

        if (
            topic not in ["nfe", "nfce", "nfe_notafiscal", "notas_fiscais"]
            or not nfe_id
        ):
            logger.warning(
                "webhook_bling", f"Webhook ignorado: topic={topic}, nfe_id={nfe_id}"
            )
            return {"success": True, "message": "Webhook ignorado"}

        # Buscar venda com essa nota
        venda = db.query(Venda).filter(Venda.nfe_bling_id == nfe_id).first()

        if not venda:
            logger.warning(
                "webhook_bling", f"Venda não encontrada para nfe_bling_id={nfe_id}"
            )
            return {"success": True, "message": "Venda não encontrada"}

        # Consultar status atualizado no Bling
        bling = BlingAPI()

        if topic in ["nfce", "notas_fiscais"]:
            resultado = bling.consultar_nfce(nfe_id)
        else:
            resultado = bling.consultar_nfe(nfe_id)

        dados_nota = (
            resultado.get("data", resultado) if isinstance(resultado, dict) else {}
        )
        nfe_routes = _nfe_routes()
        novo_status = nfe_routes._status_nota_bling(dados_nota)

        # Atualizar venda
        venda.nfe_status = novo_status
        venda.nfe_chave = dados_nota.get("chaveAcesso") or venda.nfe_chave

        # ✅ Se NF foi AUTORIZADA, confirmar o estoque reservado e sincronizar o saldo final.
        if nfe_routes._nota_autorizada_bling(dados_nota):
            logger.info(
                "webhook_bling",
                f"✅ NF AUTORIZADA - Confirmando estoque da Venda #{venda.id}",
            )

            movimentacoes = (
                db.query(EstoqueMovimentacao)
                .filter(
                    EstoqueMovimentacao.referencia_id == venda.id,
                    EstoqueMovimentacao.referencia_tipo == "venda_bling",
                    EstoqueMovimentacao.status == "reservado",
                )
                .all()
            )

            for mov in movimentacoes:
                mov.status = "confirmado"
                logger.info(
                    "webhook_bling",
                    f"  📦 Movimentação #{mov.id} (Produto {mov.produto_id}) confirmada",
                )

                try:
                    BlingSyncService.queue_product_sync(
                        db,
                        produto_id=mov.produto_id,
                        motivo="nf_autorizada",
                        origem="webhook_nf",
                        force=True,
                    )
                except Exception as e:
                    logger.warning(
                        "webhook_bling",
                        f"  ⚠️ Erro ao enfileirar sync do produto {mov.produto_id}: {e}",
                    )

        # Se NF foi CANCELADA, revert estoque
        elif nfe_routes._nota_cancelada_bling(dados_nota):
            logger.warning(
                "webhook_bling",
                f"⚠️ NF CANCELADA - Revertendo estoque da Venda #{venda.id}",
            )

            movimentacoes = (
                db.query(EstoqueMovimentacao)
                .filter(
                    EstoqueMovimentacao.referencia_id == venda.id,
                    EstoqueMovimentacao.referencia_tipo == "venda_bling",
                )
                .all()
            )

            for mov in movimentacoes:
                if mov.status != "cancelado":
                    produto = (
                        db.query(Produto).filter(Produto.id == mov.produto_id).first()
                    )
                    if produto:
                        produto.estoque_atual = (
                            produto.estoque_atual or 0
                        ) + mov.quantidade
                        mov.status = "cancelado"
                        logger.info(
                            "webhook_bling", f"  ↩️ Estoque revertido: {produto.codigo}"
                        )
                        try:
                            BlingSyncService.queue_product_sync(
                                db,
                                produto_id=produto.id,
                                motivo="nf_cancelada",
                                origem="webhook_nf",
                                force=True,
                            )
                        except Exception as e:
                            logger.warning(
                                "webhook_bling",
                                f"  ⚠️ Erro ao enfileirar estorno do produto {produto.id}: {e}",
                            )

        db.commit()

        logger.info(
            "webhook_bling", f"✅ Status atualizado: Venda #{venda.id} -> {novo_status}"
        )

        return {
            "success": True,
            "message": "Webhook processado com sucesso",
            "venda_id": venda.id,
            "novo_status": novo_status,
        }

    except Exception as e:
        logger.error("webhook_error", f"Erro ao processar webhook: {str(e)}")
        logger.error("webhook_error", traceback.format_exc())
        # Retornar 200 mesmo com erro para não ficar reenviando
        return {"success": False, "error": str(e)}


@router.post("/{venda_id}/sincronizar-status")
async def sincronizar_status_nota(
    venda_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Sincroniza o status da nota fiscal com o Bling"""
    current_user, tenant_id = user_and_tenant
    try:
        # Buscar venda
        venda = (
            db.query(Venda)
            .filter(Venda.id == venda_id, Venda.tenant_id == tenant_id)
            .first()
        )

        if not venda:
            raise HTTPException(status_code=404, detail="Venda não encontrada")

        if not venda.nfe_bling_id:
            raise HTTPException(
                status_code=400, detail="Venda não possui nota fiscal emitida"
            )

        # Consultar nota no Bling
        bling = BlingAPI()
        nfe_routes = _nfe_routes()

        # Verificar se é NFC-e ou NF-e
        if nfe_routes._venda_usa_nfce(venda):
            resultado = bling.consultar_nfce(venda.nfe_bling_id)
        else:
            resultado = bling.consultar_nfe(venda.nfe_bling_id)

        dados_nota = (
            resultado.get("data", resultado) if isinstance(resultado, dict) else {}
        )
        novo_status = nfe_routes._status_nota_bling(dados_nota)

        # Atualizar venda
        venda.nfe_status = novo_status
        venda.nfe_chave = dados_nota.get("chaveAcesso") or venda.nfe_chave

        db.commit()
        db.refresh(venda)

        return {
            "success": True,
            "message": f"Status atualizado para: {novo_status}",
            "status": novo_status,
            "dados_bling": dados_nota,
        }

    except Exception as e:
        logger.error(
            "sincronizar_status_error", f"Erro ao sincronizar status: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Erro ao sincronizar status: {str(e)}"
        )


@router.post("/sincronizar-todos")
async def sincronizar_todos_status(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Sincroniza o status de todas as notas fiscais com o Bling"""
    current_user, tenant_id = user_and_tenant
    try:
        # Buscar vendas com NF emitida
        vendas = (
            db.query(Venda)
            .filter(Venda.tenant_id == tenant_id, Venda.nfe_bling_id.isnot(None))
            .all()
        )

        bling = BlingAPI()
        atualizados = 0
        erros = 0
        nfe_routes = _nfe_routes()

        for venda in vendas:
            try:
                # Consultar nota no Bling
                if nfe_routes._venda_usa_nfce(venda):
                    resultado = bling.consultar_nfce(venda.nfe_bling_id)
                else:
                    resultado = bling.consultar_nfe(venda.nfe_bling_id)

                dados_nota = (
                    resultado.get("data", resultado)
                    if isinstance(resultado, dict)
                    else {}
                )
                novo_status = nfe_routes._status_nota_bling(dados_nota)

                # Atualizar apenas se mudou
                if venda.nfe_status != novo_status:
                    venda.nfe_status = novo_status
                    venda.nfe_chave = dados_nota.get("chaveAcesso") or venda.nfe_chave
                    atualizados += 1

            except Exception as e:
                logger.error(
                    "sincronizar_todos_error",
                    f"Erro ao sincronizar venda {venda.id}: {str(e)}",
                )
                erros += 1

        db.commit()

        return {
            "success": True,
            "message": "Sincronização concluída",
            "total": len(vendas),
            "atualizados": atualizados,
            "erros": erros,
        }

    except Exception as e:
        logger.error("sincronizar_todos_error", f"Erro ao sincronizar todos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar: {str(e)}")


@router.get("/{nfe_id}/danfe")
async def baixar_danfe(
    nfe_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Baixa PDF da DANFE"""
    try:
        bling = BlingAPI()
        pdf_content = bling.baixar_danfe(nfe_id)

        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=danfe_{nfe_id}.pdf"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao baixar DANFE: {str(e)}")


@router.get("/config/testar-conexao")
async def testar_conexao(current_user: User = Depends(get_current_user)):
    """Testa conexão com Bling"""
    try:
        bling = BlingAPI()
        if bling.validar_conexao():
            return {"success": True, "message": "Conexão com Bling OK"}
        else:
            return {"success": False, "message": "Falha na conexão com Bling"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")
