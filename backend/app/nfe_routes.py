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
from app.produtos_models import Produto, EstoqueMovimentacao
from app.services.bling_sync_service import BlingSyncService
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
    """Lista todas as NF-e/NFC-e emitidas — busca direto do Bling (inclui marketplace)"""
    current_user, tenant_id = user_and_tenant

    _STATUS_MAP = {
        0: "Pendente",
        1: "Autorizada",
        2: "Cancelada",
        3: "Erro",
        4: "Denegada",
        5: "Inutilizada",
        6: "Rejeitada",
    }

    def _situacao_num(val):
        """Extrai inteiro da situação — Bling pode retornar int ou {'id': X}"""
        if isinstance(val, dict):
            val = val.get("id", 0)
        try:
            return int(val)
        except (TypeError, ValueError):
            return 0

    def _normalizar_nota_bling(item: dict, modelo: int) -> dict:
        sit_num = _situacao_num(item.get("situacao"))
        status_txt = _STATUS_MAP.get(sit_num, "Pendente")
        contato = item.get("contato") or {}
        return {
            "id": str(item.get("id", "")),
            "venda_id": None,
            "numero": str(item.get("numero", "")),
            "serie": str(item.get("serie", "")),
            "tipo": 1 if modelo == 65 else 0,
            "modelo": modelo,
            "chave": item.get("chaveAcesso") or "",
            "status": status_txt,
            "data_emissao": item.get("dataEmissao") or item.get("data_emissao"),
            "valor": float(item.get("valorTotal") or item.get("total") or 0),
            "cliente": {
                "id": contato.get("id"),
                "nome": contato.get("nome") or contato.get("descricao"),
                "cpf_cnpj": contato.get("cpf") or contato.get("cnpj") or contato.get("cpfCnpj"),
            },
            "origem": "bling",
        }

    notas: list[dict] = []
    bling_ok = False

    # ── 1. Buscar do Bling (NF-e modelo 55) ──────────────────────────────────
    try:
        bling = BlingAPI()
        resp_nfe = bling.listar_nfes(
            data_inicial=data_inicial,
            data_final=data_final,
        )
        for item in (resp_nfe.get("data") or []):
            nota = _normalizar_nota_bling(item, modelo=55)
            if situacao and nota["status"].lower() != situacao.lower():
                continue
            notas.append(nota)
        bling_ok = True
    except Exception as e:
        logger.warning("listar_nfes", f"Bling NF-e não disponível: {e}")

    # ── 2. Buscar do Bling (NFC-e modelo 65) ─────────────────────────────────
    try:
        if not bling_ok:
            bling = BlingAPI()
            bling_ok = True
        resp_nfce = bling.listar_nfces(
            data_inicial=data_inicial,
            data_final=data_final,
        )
        ids_ja_adicionados = {n["id"] for n in notas}
        for item in (resp_nfce.get("data") or []):
            nota = _normalizar_nota_bling(item, modelo=65)
            if str(nota["id"]) in ids_ja_adicionados:
                continue
            if situacao and nota["status"].lower() != situacao.lower():
                continue
            notas.append(nota)
    except Exception as e:
        logger.warning("listar_nfes", f"Bling NFC-e não disponível: {e}")

    # ── 3. Fallback / complemento: NFs emitidas via PDV local ────────────────
    # Só incluídas se Bling não respondeu OU se têm ID que não veio do Bling
    try:
        query = db.query(Venda).filter(
            Venda.tenant_id == tenant_id,
            Venda.nfe_bling_id.isnot(None),
        )
        if situacao:
            query = query.filter(Venda.nfe_status == situacao)
        if data_inicial:
            query = query.filter(Venda.nfe_data_emissao >= data_inicial)
        if data_final:
            query = query.filter(Venda.nfe_data_emissao <= data_final)

        ids_bling = {n["id"] for n in notas}
        for venda in query.order_by(Venda.nfe_data_emissao.desc()).all():
            if str(venda.nfe_bling_id) in ids_bling:
                continue  # já veio do Bling
            notas.append({
                "id": str(venda.nfe_bling_id),
                "venda_id": venda.id,
                "numero": venda.nfe_numero,
                "serie": venda.nfe_serie,
                "tipo": venda.nfe_tipo,
                "modelo": venda.nfe_modelo,
                "chave": venda.nfe_chave,
                "status": venda.nfe_status or "Pendente",
                "data_emissao": venda.nfe_data_emissao.isoformat() if venda.nfe_data_emissao else None,
                "valor": float(venda.total or 0),
                "cliente": {
                    "id": venda.cliente.id if venda.cliente else None,
                    "nome": venda.cliente.nome if venda.cliente else None,
                    "cpf_cnpj": (venda.cliente.cpf or venda.cliente.cnpj) if venda.cliente else None,
                },
                "origem": "local",
            })
    except Exception as e:
        logger.warning("listar_nfes", f"Erro ao consultar NFs locais: {e}")

    # Ordenar por data (mais recente primeiro)
    def _key_data(n):
        return n.get("data_emissao") or ""

    notas.sort(key=_key_data, reverse=True)

    return {
        "success": True,
        "total": len(notas),
        "notas": notas,
        "fonte": "bling" if bling_ok else "local",
    }


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
        # Formato esperado: { "topic": "nfe_notafiscal", "id": 123456, "status": "autorizada" }
        # Ou: { "topic": "notas_fiscais", "data": { "id": 123456, "situacao": 1 } }
        topic = dados.get("topic")
        nfe_id = dados.get("id") or (dados.get("data", {}).get("id") if dados.get("data") else None)
        
        if topic not in ["nfe", "nfce", "nfe_notafiscal", "notas_fiscais"] or not nfe_id:
            logger.warning("webhook_bling", f"Webhook ignorado: topic={topic}, nfe_id={nfe_id}")
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
        
        if topic in ["nfce", "notas_fiscais"]:
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
        
        # ✅ Se NF foi AUTORIZADA, confirmar o estoque reservado e sincronizar o saldo final.
        if valor_situacao == 1:
            logger.info("webhook_bling", f"✅ NF AUTORIZADA - Confirmando estoque da Venda #{venda.id}")

            movimentacoes = db.query(EstoqueMovimentacao).filter(
                EstoqueMovimentacao.referencia_id == venda.id,
                EstoqueMovimentacao.referencia_tipo == 'venda_bling',
                EstoqueMovimentacao.status == 'reservado'
            ).all()

            for mov in movimentacoes:
                mov.status = 'confirmado'
                logger.info("webhook_bling", f"  📦 Movimentação #{mov.id} (Produto {mov.produto_id}) confirmada")

                try:
                    BlingSyncService.queue_product_sync(
                        db,
                        produto_id=mov.produto_id,
                        motivo="nf_autorizada",
                        origem="webhook_nf",
                        force=True,
                    )
                except Exception as e:
                    logger.warning("webhook_bling", f"  ⚠️ Erro ao enfileirar sync do produto {mov.produto_id}: {e}")

        # Se NF foi CANCELADA, revert estoque
        elif valor_situacao == 2:
            logger.warning("webhook_bling", f"⚠️ NF CANCELADA - Revertendo estoque da Venda #{venda.id}")

            movimentacoes = db.query(EstoqueMovimentacao).filter(
                EstoqueMovimentacao.referencia_id == venda.id,
                EstoqueMovimentacao.referencia_tipo == 'venda_bling'
            ).all()

            for mov in movimentacoes:
                if mov.status != 'cancelado':
                    produto = db.query(Produto).filter(Produto.id == mov.produto_id).first()
                    if produto:
                        produto.estoque_atual = (produto.estoque_atual or 0) + mov.quantidade
                        mov.status = 'cancelado'
                        logger.info("webhook_bling", f"  ↩️ Estoque revertido: {produto.codigo}")
                        try:
                            BlingSyncService.queue_product_sync(
                                db,
                                produto_id=produto.id,
                                motivo="nf_cancelada",
                                origem="webhook_nf",
                                force=True,
                            )
                        except Exception as e:
                            logger.warning("webhook_bling", f"  ⚠️ Erro ao enfileirar estorno do produto {produto.id}: {e}")
        
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
        import traceback
        logger.error("webhook_error", traceback.format_exc())
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
