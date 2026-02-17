"""
Rotas para gerenciamento de Notas Fiscais Eletrônicas
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from app.db import get_session
from app.auth import get_current_user
from app.auth.dependencies import get_current_user_and_tenant
from app.models import User
from app.vendas_models import Venda
from app.bling_integration import BlingAPI
from app.utils.logger import logger

router = APIRouter(prefix="/nfe", tags=["NF-e"])


class EmitirNFeRequest(BaseModel):
    venda_id: int
    tipo_nota: str = "nfce"  # 'nfe' ou 'nfce'


class CancelarNFeRequest(BaseModel):
    justificativa: str


class CartaCorrecaoRequest(BaseModel):
    correcao: str


@router.post("/emitir")
async def emitir_nfe(
    request: EmitirNFeRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Emite NF-e ou NFC-e para uma venda"""
    import traceback
    try:
        venda = db.query(Venda).filter(Venda.id == request.venda_id).first()
        if not venda:
            raise HTTPException(status_code=404, detail="Venda não encontrada")
        
        # Verificar se venda já tem NF emitida
        if venda.nfe_bling_id:
            raise HTTPException(
                status_code=400, 
                detail=f"Esta venda já possui nota fiscal emitida (NF #{venda.nfe_numero}). Cancele a nota existente antes de emitir uma nova."
            )
        
        logger.info("emitir_nfe", f"\n=== EMITINDO NF-e ===")
        logger.info("emitir_nfe", f"Venda ID: {venda.id}")
        logger.info("emitir_nfe", f"Tipo: {request.tipo_nota}")
        
        bling = BlingAPI()
        resultado = bling.emitir_nota_fiscal(venda, request.tipo_nota, db)
        
        logger.info("emitir_nfe", f"DEBUG: Resultado Bling: {resultado}")
        
        # Extrair dados da resposta (Bling retorna em 'data')
        dados_nota = resultado.get('data', {})
        
        # Atualizar venda com dados da nota
        # IMPORTANTE: tipo deve ser INTEGER (0=NF-e, 1=NFC-e) para consultas funcionarem
        venda.nfe_tipo = 0 if request.tipo_nota == "nfe" else 1
        venda.nfe_modelo = 55 if request.tipo_nota == "nfe" else 65
        venda.nfe_numero = dados_nota.get("numero")
        venda.nfe_serie = dados_nota.get("serie")
        venda.nfe_chave = dados_nota.get("chaveAcesso")
        
        # Mapear situacao (número) para texto
        situacao_map = {0: "Pendente", 1: "Autorizada", 2: "Cancelada", 3: "Erro", 4: "Denegada", 5: "Inutilizada", 6: "Rejeitada"}
        situacao_num = dados_nota.get("situacao", 0)
        venda.nfe_status = situacao_map.get(situacao_num, "Pendente")
        
        venda.nfe_bling_id = dados_nota.get("id")
        venda.nfe_data_emissao = datetime.now()
        
        logger.info("emitir_nfe", f"✅ Rastreamento: Venda #{venda.id} → Bling #{venda.nfe_bling_id} (Tipo {venda.nfe_tipo}, Modelo {venda.nfe_modelo})")
        
        logger.info("emitir_nfe", f"DEBUG: Salvando - nfe_bling_id={venda.nfe_bling_id}, numero={venda.nfe_numero}, status={venda.nfe_status}")
        
        # Mudar status para 'pago_nf' quando a nota for emitida
        venda.status = 'pago_nf'
        
        db.commit()
        db.refresh(venda)
        
        logger.info("emitir_nfe", f"DEBUG: Após commit - nfe_bling_id={venda.nfe_bling_id}, venda_id={venda.id}")
        
        return {
            "success": True,
            "message": f"{'NF-e' if request.tipo_nota == 'nfe' else 'NFC-e'} emitida com sucesso",
            "nfe_id": dados_nota.get("id"),
            "numero": dados_nota.get("numero"),
            "serie": dados_nota.get("serie"),
            "chave_acesso": dados_nota.get("chaveAcesso"),
            "situacao": dados_nota.get("situacao", "Pendente")
        }
        
    except ValueError as e:
        logger.error("emitir_nfe_error", f"❌ ValueError: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("emitir_nfe_error", f"❌ ERRO AO EMITIR NF-e:")
        logger.error("emitir_nfe_error", f"Erro: {str(e)}")
        logger.error("emitir_nfe_error", f"Traceback completo:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro ao emitir NF-e: {str(e)}")


@router.get("/")
async def listar_nfes(
    data_inicial: Optional[str] = None,
    data_final: Optional[str] = None,
    situacao: Optional[str] = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Lista todas as NF-e/NFC-e emitidas"""
    current_user, tenant_id = user_and_tenant
    try:
        logger.info("listar_nfes", f"\n=== LISTANDO NF-es ===")
        logger.info("listar_nfes", f"User ID: {current_user.id}, Tenant ID: {tenant_id}")
        
        # Buscar vendas com NF emitida do tenant
        query = db.query(Venda).filter(
            Venda.tenant_id == tenant_id,
            Venda.nfe_bling_id.isnot(None)
        )
        
        # Aplicar filtros
        if situacao:
            query = query.filter(Venda.nfe_status == situacao)
        
        if data_inicial:
            query = query.filter(Venda.nfe_data_emissao >= data_inicial)
        
        if data_final:
            query = query.filter(Venda.nfe_data_emissao <= data_final)
        
        vendas = query.order_by(Venda.nfe_data_emissao.desc()).all()
        
        logger.info("listar_nfes", f"Vendas encontradas: {len(vendas)}")
        
        # Sincronizar status com Bling para manter atualizado (somente se houver vendas)
        if vendas:
            try:
                bling = BlingAPI()
                for venda in vendas:
                    try:
                        # ✅ Usar tipo correto: 1=NFC-e, 0=NF-e (INTEGER)
                        if venda.nfe_tipo == 1:  # NFC-e
                            nota = bling.consultar_nfce(venda.nfe_bling_id)
                        elif venda.nfe_tipo == 0:  # NF-e
                            nota = bling.consultar_nfe(venda.nfe_bling_id)
                        else:
                            # Tipo inválido (string antiga), tentar deduzir pelo modelo
                            if venda.nfe_modelo == 65:
                                nota = bling.consultar_nfce(venda.nfe_bling_id)
                                venda.nfe_tipo = 1  # Corrigir
                            else:
                                nota = bling.consultar_nfe(venda.nfe_bling_id)
                                venda.nfe_tipo = 0  # Corrigir
                        
                        # Mapear situacao do Bling para status
                        situacao = nota.get("situacao", 0)
                        status_map = {
                            0: "Pendente",
                            1: "Autorizada",
                            2: "Cancelada",
                            3: "Erro",
                            4: "Denegada",
                            5: "Inutilizada",
                            6: "Rejeitada"
                        }
                        novo_status = status_map.get(situacao, "Pendente")
                        
                        # Atualizar se mudou
                        if venda.nfe_status != novo_status:
                            logger.info("sincronizar_status", f"🔄 Atualizando NF {venda.nfe_numero}: {venda.nfe_status} → {novo_status}")
                            venda.nfe_status = novo_status
                            db.commit()
                            
                    except Exception as e:
                        logger.warning("sincronizar_status", f"⚠️ Erro ao sincronizar NF {venda.nfe_numero}: {e}")
                        continue
            except Exception as e:
                # Se Bling não estiver configurado, apenas ignora a sincronização
                logger.warning("listar_nfes", f"Bling não configurado ou erro ao conectar: {e}")
        
        # Formatar resposta
        notas = []
        for venda in vendas:
            notas.append({
                "id": venda.nfe_bling_id,
                "venda_id": venda.id,
                "numero": venda.nfe_numero,
                "serie": venda.nfe_serie,
                "tipo": venda.nfe_tipo,
                "modelo": venda.nfe_modelo,
                "chave": venda.nfe_chave,
                "status": venda.nfe_status,
                "data_emissao": venda.nfe_data_emissao.isoformat() if venda.nfe_data_emissao else None,
                "valor": float(venda.total),
                "cliente": {
                    "id": venda.cliente.id if venda.cliente else None,
                    "nome": venda.cliente.nome if venda.cliente else None,
                    "cpf_cnpj": venda.cliente.cpf or venda.cliente.cnpj if venda.cliente else None
                }
            })
        
        return {
            "success": True,
            "total": len(notas),
            "notas": notas
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar NF-es: {str(e)}")


@router.get("/{nfe_id}")
async def consultar_nfe(
    nfe_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Consulta dados de uma NF-e"""
    try:
        bling = BlingAPI()
        return bling.consultar_nfe(nfe_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar NF-e: {str(e)}")


@router.get("/{nfe_id}/xml")
async def baixar_xml(
    nfe_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
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
    user_and_tenant = Depends(get_current_user_and_tenant)
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
            venda.status = 'finalizada'
            db.commit()
        
        return {
            "success": True,
            "message": "NF-e cancelada com sucesso",
            "data": resultado
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
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Emite Carta de Correção Eletrônica (CC-e)"""
    try:
        bling = BlingAPI()
        resultado = bling.carta_correcao(nfe_id, request.correcao)
        
        return {
            "success": True,
            "message": "Carta de Correção emitida com sucesso",
            "data": resultado
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao emitir CC-e: {str(e)}")


@router.delete("/{venda_id}")
async def excluir_nota(
    venda_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Remove os dados da nota fiscal da venda (apenas para notas não autorizadas)"""
    current_user, tenant_id = user_and_tenant
    try:
        # Buscar venda
        venda = db.query(Venda).filter(
            Venda.id == venda_id,
            Venda.tenant_id == tenant_id
        ).first()
        
        if not venda:
            raise HTTPException(status_code=404, detail="Venda não encontrada")
        
        if not venda.nfe_bling_id:
            raise HTTPException(status_code=400, detail="Venda não possui nota fiscal")
        
        # Validar status - só permite excluir notas que não foram autorizadas
        status_permitidos = ["Pendente", "Erro", "Rejeitada", None]
        if venda.nfe_status not in status_permitidos:
            raise HTTPException(
                status_code=400, 
                detail=f"Não é possível excluir nota com status '{venda.nfe_status}'. Apenas notas Pendentes, com Erro ou Rejeitadas podem ser excluídas."
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
        venda.status = 'finalizada'
        
        db.commit()
        
        return {
            "success": True,
            "message": "Dados da nota fiscal removidos com sucesso"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("excluir_nota_error", f"Erro ao excluir nota: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao excluir nota: {str(e)}")


@router.post("/webhook/bling")
async def webhook_bling(
    request: Request,
    db: Session = Depends(get_session)
):
    """Recebe notificações do Bling sobre mudanças de status das notas"""
    try:
        # Pegar dados do webhook
        dados = await request.json()
        
        logger.info("webhook_bling", f"\n=== WEBHOOK BLING RECEBIDO ===")
        logger.info("webhook_bling", f"Dados: {dados}")
        
        # Extrair informações do webhook
        # Formato esperado: { "topic": "nfe", "id": 123456, "status": "autorizada" }
        topic = dados.get("topic")
        nfe_id = dados.get("id")
        
        if topic not in ["nfe", "nfce"] or not nfe_id:
            return {"success": True, "message": "Webhook ignorado"}
        
        # Buscar venda com essa nota
        venda = db.query(Venda).filter(
            Venda.nfe_bling_id == nfe_id
        ).first()
        
        if not venda:
            logger.warning("webhook_bling", f"Venda não encontrada para nfe_bling_id={nfe_id}")
            return {"success": True, "message": "Venda não encontrada"}
        
        # Consultar status atualizado no Bling
        bling = BlingAPI()
        
        if topic == "nfce":
            resultado = bling.consultar_nfce(nfe_id)
        else:
            resultado = bling.consultar_nfe(nfe_id)
        
        dados_nota = resultado.get('data', {})
        
        # Mapear situação
        situacao_bling = dados_nota.get("situacao", {})
        if isinstance(situacao_bling, dict):
            valor_situacao = situacao_bling.get("valor")
        else:
            valor_situacao = situacao_bling
        
        mapa_status = {
            0: "Pendente",
            1: "Autorizada",
            2: "Cancelada",
            3: "Erro",
            4: "Denegada",
            5: "Inutilizada",
            6: "Rejeitada"
        }
        
        novo_status = mapa_status.get(valor_situacao, "Pendente")
        
        # Atualizar venda
        venda.nfe_status = novo_status
        venda.nfe_chave = dados_nota.get("chaveAcesso") or venda.nfe_chave
        
        db.commit()
        
        logger.info("webhook_bling", f"✅ Status atualizado: Venda #{venda.id} -> {novo_status}")
        
        return {
            "success": True,
            "message": "Webhook processado com sucesso",
            "venda_id": venda.id,
            "novo_status": novo_status
        }
        
    except Exception as e:
        logger.error("webhook_error", f"Erro ao processar webhook: {str(e)}")
        # Retornar 200 mesmo com erro para não ficar reenviando
        return {"success": False, "error": str(e)}


@router.post("/{venda_id}/sincronizar-status")
async def sincronizar_status_nota(
    venda_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Sincroniza o status da nota fiscal com o Bling"""
    current_user, tenant_id = user_and_tenant
    try:
        # Buscar venda
        venda = db.query(Venda).filter(
            Venda.id == venda_id,
            Venda.tenant_id == tenant_id
        ).first()
        
        if not venda:
            raise HTTPException(status_code=404, detail="Venda não encontrada")
        
        if not venda.nfe_bling_id:
            raise HTTPException(status_code=400, detail="Venda não possui nota fiscal emitida")
        
        # Consultar nota no Bling
        bling = BlingAPI()
        
        # Verificar se é NFC-e ou NF-e
        if venda.nfe_tipo == "nfce":
            resultado = bling.consultar_nfce(venda.nfe_bling_id)
        else:
            resultado = bling.consultar_nfe(venda.nfe_bling_id)
        
        dados_nota = resultado.get('data', {})
        
        # Mapear situação do Bling para status do sistema
        situacao_bling = dados_nota.get("situacao", {})
        if isinstance(situacao_bling, dict):
            valor_situacao = situacao_bling.get("valor")
        else:
            valor_situacao = situacao_bling
        
        # Mapeamento de status
        mapa_status = {
            0: "Pendente",
            1: "Autorizada",
            2: "Cancelada",
            3: "Erro",
            4: "Denegada",
            5: "Inutilizada",
            6: "Rejeitada"
        }
        
        novo_status = mapa_status.get(valor_situacao, "Pendente")
        
        # Atualizar venda
        venda.nfe_status = novo_status
        venda.nfe_chave = dados_nota.get("chaveAcesso") or venda.nfe_chave
        
        db.commit()
        db.refresh(venda)
        
        return {
            "success": True,
            "message": f"Status atualizado para: {novo_status}",
            "status": novo_status,
            "dados_bling": dados_nota
        }
        
    except Exception as e:
        logger.error("sincronizar_status_error", f"Erro ao sincronizar status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar status: {str(e)}")


@router.post("/sincronizar-todos")
async def sincronizar_todos_status(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Sincroniza o status de todas as notas fiscais com o Bling"""
    current_user, tenant_id = user_and_tenant
    try:
        # Buscar vendas com NF emitida
        vendas = db.query(Venda).filter(
            Venda.tenant_id == tenant_id,
            Venda.nfe_bling_id.isnot(None)
        ).all()
        
        bling = BlingAPI()
        atualizados = 0
        erros = 0
        
        for venda in vendas:
            try:
                # Consultar nota no Bling
                if venda.nfe_tipo == "nfce":
                    resultado = bling.consultar_nfce(venda.nfe_bling_id)
                else:
                    resultado = bling.consultar_nfe(venda.nfe_bling_id)
                
                dados_nota = resultado.get('data', {})
                
                # Mapear situação
                situacao_bling = dados_nota.get("situacao", {})
                if isinstance(situacao_bling, dict):
                    valor_situacao = situacao_bling.get("valor")
                else:
                    valor_situacao = situacao_bling
                
                mapa_status = {
                    0: "Pendente",
                    1: "Autorizada",
                    2: "Cancelada",
                    3: "Erro",
                    4: "Denegada",
                    5: "Inutilizada",
                    6: "Rejeitada"
                }
                
                novo_status = mapa_status.get(valor_situacao, "Pendente")
                
                # Atualizar apenas se mudou
                if venda.nfe_status != novo_status:
                    venda.nfe_status = novo_status
                    venda.nfe_chave = dados_nota.get("chaveAcesso") or venda.nfe_chave
                    atualizados += 1
                    
            except Exception as e:
                logger.error("sincronizar_todos_error", f"Erro ao sincronizar venda {venda.id}: {str(e)}")
                erros += 1
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Sincronização concluída",
            "total": len(vendas),
            "atualizados": atualizados,
            "erros": erros
        }
        
    except Exception as e:
        logger.error("sincronizar_todos_error", f"Erro ao sincronizar todos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar: {str(e)}")


@router.get("/{nfe_id}/danfe")
async def baixar_danfe(
    nfe_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Baixa PDF da DANFE"""
    from fastapi.responses import Response
    
    try:
        bling = BlingAPI()
        pdf_content = bling.baixar_danfe(nfe_id)
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=danfe_{nfe_id}.pdf"
            }
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
