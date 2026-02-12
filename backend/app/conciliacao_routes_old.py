"""
Rotas para conciliação de pagamentos via upload de planilhas
Suporta qualquer adquirente: Stone, Cielo, Rede, PagSeguro, etc
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import io
import uuid
import logging

from .db import get_session
from .auth.dependencies import get_current_user_and_tenant
from .financeiro_models import ContaReceber
from .vendas_models import Venda

router = APIRouter(prefix="/api/conciliacao", tags=["Conciliação de Pagamentos"])
logger = logging.getLogger(__name__)


@router.post("/upload-planilha")
async def upload_planilha_conciliacao(
    file: UploadFile = File(...),
    auth = Depends(get_current_user_and_tenant)
):
    """
    📤 Upload de planilha para conciliação de pagamentos
    
    Suporta:
    - Excel (.xlsx, .xls)
    - CSV (.csv)
    
    Retorna preview dos dados para mapeamento de colunas
    """
    user, tenant_id = auth
    
    try:
        # Lê arquivo
        contents = await file.read()
        
        # Detecta formato
        if file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(contents))
        elif file.filename.endswith('.csv'):
            # Tenta diferentes encodings
            try:
                df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
            except:
                try:
                    df = pd.read_csv(io.BytesIO(contents), encoding='latin-1')
                except:
                    df = pd.read_csv(io.BytesIO(contents), encoding='iso-8859-1')
        else:
            raise HTTPException(400, "Formato não suportado. Use .xlsx, .xls ou .csv")
        
        # Converte para JSON-safe
        df = df.fillna('')
        
        # Gera ID temporário para a sessão
        upload_id = str(uuid.uuid4())
        
        # Salva preview (primeiras 10 linhas)
        preview = df.head(10).to_dict('records')
        
        return {
            "success": True,
            "upload_id": upload_id,
            "filename": file.filename,
            "total_rows": len(df),
            "columns": list(df.columns),
            "preview": preview,
            "message": f"✅ {len(df)} linhas carregadas. Configure os mapeamentos."
        }
        
    except Exception as e:
        logger.error(f"Erro ao processar planilha: {str(e)}")
        raise HTTPException(400, f"Erro ao processar planilha: {str(e)}")


@router.post("/mapear-colunas")
async def mapear_colunas_conciliacao(
    file: UploadFile = File(...),
    coluna_identificador: str = Form(...),
    coluna_valor: str = Form(...),
    coluna_data: str = Form(...),
    coluna_status: Optional[str] = Form(None),
    coluna_adquirente: Optional[str] = Form(None),
    formato_data: str = Form("DD/MM/YYYY"),
    auth = Depends(get_current_user_and_tenant)
):
    """
    🔗 Processa planilha com mapeamento de colunas e faz match com vendas
    
    Args:
        coluna_identificador: Nome da coluna com identificador único (NSU, STONEID, RRN, etc)
        coluna_valor: Nome da coluna com o valor da transação
        coluna_data: Nome da coluna com a data/hora
        coluna_status: (Opcional) Nome da coluna com status da transação
        coluna_adquirente: (Opcional) Nome da coluna com nome da adquirente
        formato_data: Formato da data (DD/MM/YYYY, YYYY-MM-DD, etc)
    """
    user, tenant_id = auth
    session = next(get_session())
    
    try:
        # Lê arquivo
        contents = await file.read()
        
        if file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(contents))
        elif file.filename.endswith('.csv'):
            try:
                df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
            except:
                try:
                    df = pd.read_csv(io.BytesIO(contents), encoding='latin-1')
                except:
                    df = pd.read_csv(io.BytesIO(contents), encoding='iso-8859-1')
        
        # Valida colunas
        if coluna_identificador not in df.columns:
            raise HTTPException(400, f"Coluna '{coluna_identificador}' não encontrada")
        if coluna_valor not in df.columns:
            raise HTTPException(400, f"Coluna '{coluna_valor}' não encontrada")
        if coluna_data not in df.columns:
            raise HTTPException(400, f"Coluna '{coluna_data}' não encontrada")
        
        resultados = {
            "total_linhas": len(df),
            "matches_automaticos": 0,
            "matches_manuais": 0,
            "sem_match": 0,
            "detalhes": []
        }
        
        # Processa cada linha
        for idx, row in df.iterrows():
            try:
                identificador = str(row[coluna_identificador]).strip()
                
                # Parse valor
                valor_str = str(row[coluna_valor]).replace('R$', '').replace(',', '.').strip()
                valor = Decimal(valor_str)
                
                # Parse data
                data_str = str(row[coluna_data])
                if formato_data == "DD/MM/YYYY HH:MM":
                    data_transacao = datetime.strptime(data_str, "%d/%m/%Y %H:%M")
                elif formato_data == "DD/MM/YYYY":
                    data_transacao = datetime.strptime(data_str, "%d/%m/%Y")
                elif formato_data == "YYYY-MM-DD":
                    data_transacao = datetime.strptime(data_str, "%Y-%m-%d")
                else:
                    data_transacao = pd.to_datetime(data_str)
                
                # Busca match por:
                # 1. NSU exato
                # 2. Valor + data próxima (±1 dia)
                
                # Tenta NSU primeiro
                conta = session.query(ContaReceber).filter(
                    and_(
                        ContaReceber.tenant_id == tenant_id,
                        ContaReceber.nsu == identificador,
                        ContaReceber.conciliado == False
                    )
                ).first()
                
                match_type = None
                venda_numero = None
                
                if conta:
                    # Match por NSU
                    match_type = "nsu"
                    
                    # Atualiza
                    conta.conciliado = True
                    conta.data_conciliacao = datetime.now()
                    conta.nsu = identificador
                    if coluna_adquirente and coluna_adquirente in df.columns:
                        conta.adquirente = str(row[coluna_adquirente])
                    
                    if conta.venda_id:
                        venda = session.query(Venda).get(conta.venda_id)
                        if venda:
                            venda_numero = venda.numero_venda
                    
                    resultados["matches_automaticos"] += 1
                    
                else:
                    # Tenta match por valor + data
                    data_inicio = data_transacao - timedelta(days=1)
                    data_fim = data_transacao + timedelta(days=1)
                    
                    conta = session.query(ContaReceber).filter(
                        and_(
                            ContaReceber.tenant_id == tenant_id,
                            ContaReceber.valor == valor,
                            ContaReceber.data_vencimento >= data_inicio,
                            ContaReceber.data_vencimento <= data_fim,
                            ContaReceber.conciliado == False
                        )
                    ).first()
                    
                    if conta:
                        match_type = "valor_data"
                        
                        # Atualiza
                        conta.conciliado = True
                        conta.data_conciliacao = datetime.now()
                        conta.nsu = identificador
                        if coluna_adquirente and coluna_adquirente in df.columns:
                            conta.adquirente = str(row[coluna_adquirente])
                        
                        if conta.venda_id:
                            venda = session.query(Venda).get(conta.venda_id)
                            if venda:
                                venda_numero = venda.numero_venda
                        
                        resultados["matches_manuais"] += 1
                
                # Registra resultado
                detalhe = {
                    "linha": idx + 2,  # +2 porque começa em 1 e tem header
                    "identificador": identificador,
                    "valor": float(valor),
                    "data": data_transacao.strftime("%d/%m/%Y %H:%M"),
                    "match": match_type is not None,
                    "match_type": match_type,
                    "venda_numero": venda_numero
                }
                
                if match_type is None:
                    resultados["sem_match"] += 1
                    detalhe["motivo"] = "Nenhuma venda encontrada com NSU, valor ou data correspondente"
                
                resultados["detalhes"].append(detalhe)
                
            except Exception as e:
                logger.error(f"Erro ao processar linha {idx}: {str(e)}")
                resultados["sem_match"] += 1
                resultados["detalhes"].append({
                    "linha": idx + 2,
                    "match": False,
                    "erro": str(e)
                })
        
        # Salva alterações
        session.commit()
        
        return {
            "success": True,
            "message": f"✅ Processadas {resultados['total_linhas']} transações",
            "resumo": {
                "total": resultados["total_linhas"],
                "conciliados_automatico": resultados["matches_automaticos"],
                "conciliados_manual": resultados["matches_manuais"],
                "pendentes": resultados["sem_match"]
            },
            "detalhes": resultados["detalhes"]
        }
        
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao processar conciliação: {str(e)}")
        raise HTTPException(400, f"Erro ao processar conciliação: {str(e)}")
    finally:
        session.close()


@router.get("/pendentes")
async def listar_pendentes_conciliacao(
    auth = Depends(get_current_user_and_tenant)
):
    """
    📋 Lista vendas pendentes de conciliação
    
    Retorna vendas com NSU que ainda não foram conciliadas
    """
    user, tenant_id = auth
    session = next(get_session())
    
    try:
        pendentes = session.query(ContaReceber).filter(
            and_(
                ContaReceber.tenant_id == tenant_id,
                ContaReceber.conciliado == False,
                ContaReceber.nsu.isnot(None)
            )
        ).order_by(ContaReceber.data_vencimento.desc()).all()
        
        resultado = []
        for conta in pendentes:
            venda_info = None
            if conta.venda_id:
                venda = session.query(Venda).get(conta.venda_id)
                if venda:
                    venda_info = {
                        "numero_venda": venda.numero_venda,
                        "cliente": venda.cliente.nome if venda.cliente else None
                    }
            
            resultado.append({
                "id": conta.id,
                "nsu": conta.nsu,
                "valor": float(conta.valor),
                "data_vencimento": conta.data_vencimento.isoformat() if conta.data_vencimento else None,
                "adquirente": conta.adquirente,
                "venda": venda_info
            })
        
        return {
            "success": True,
            "total": len(resultado),
            "pendentes": resultado
        }
        
    finally:
        session.close()
