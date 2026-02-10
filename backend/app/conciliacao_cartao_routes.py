"""
Router de Conciliação de Cartão
================================

Endpoint para conciliar transações de cartão com contas a receber.
"""

import csv
import io
from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, status, Query, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from decimal import Decimal

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.services.conciliacao_cartao_service import conciliar_parcela_cartao, buscar_contas_nao_conciliadas

router = APIRouter(prefix="/financeiro", tags=["Financeiro - Conciliação"])


class ConciliacaoCartaoIn(BaseModel):
    """Schema de entrada para conciliação de cartão"""
    nsu: str = Field(..., min_length=1, max_length=100, description="NSU da transação")
    valor: Decimal = Field(..., gt=0, description="Valor da transação")
    data_recebimento: date = Field(..., description="Data de recebimento do valor")
    adquirente: str = Field(..., min_length=1, max_length=50, description="Nome da adquirente (Stone, Cielo, etc)")
    forma_pagamento_id: int | None = Field(None, description="ID da forma de pagamento (opcional)")


@router.post(
    "/conciliacao-cartao",
    status_code=status.HTTP_200_OK,
    summary="Conciliar transação de cartão",
    description="Concilia uma transação de cartão com base no NSU, marca como conciliado e registra o recebimento"
)
def conciliar_cartao(
    payload: ConciliacaoCartaoIn,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Concilia uma transação de cartão com contas a receber.
    
    Fluxo:
    1. Busca conta a receber pelo NSU
    2. Valida valor da transação
    3. Marca como conciliado
    4. Registra recebimento oficial (cria fluxo de caixa, atualiza DRE)
    
    Args:
        payload: Dados da conciliação
        db: Sessão do banco de dados
        user_and_tenant: Tupla (usuário, tenant_id)
    
    Returns:
        dict: Dados da conciliação realizada
    """
    current_user, tenant_id = user_and_tenant
    
    conta = conciliar_parcela_cartao(
        db=db,
        tenant_id=tenant_id,
        nsu=payload.nsu,
        valor=float(payload.valor),
        data_recebimento=payload.data_recebimento,
        adquirente=payload.adquirente,
        usuario_id=current_user.id,
        forma_pagamento_id=payload.forma_pagamento_id,
    )
    
    db.commit()

    return {
        "message": "Conciliação realizada com sucesso",
        "conta_receber_id": conta.id,
        "nsu": conta.nsu,
        "conciliado": conta.conciliado,
        "data_conciliacao": conta.data_conciliacao,
        "adquirente": conta.adquirente,
        "valor": float(conta.valor_final or conta.valor_original),
        "status": conta.status,
    }


class ContaPendenteOut(BaseModel):
    """Schema de saída para contas pendentes de conciliação"""
    id: int
    nsu: Optional[str]
    adquirente: Optional[str]
    valor: float
    data_prevista: Optional[date]
    numero_parcela: Optional[int]
    total_parcelas: Optional[int]
    descricao: str
    status: str

    class Config:
        from_attributes = True


@router.get(
    "/conciliacao-cartao/pendentes",
    response_model=List[ContaPendenteOut],
    summary="Listar contas pendentes de conciliação",
    description="Lista todas as contas a receber com NSU informado e que ainda não foram conciliadas"
)
def listar_pendentes_conciliacao(
    data_inicio: Optional[date] = Query(None, description="Data inicial para filtro (data de vencimento)"),
    data_fim: Optional[date] = Query(None, description="Data final para filtro (data de vencimento)"),
    adquirente: Optional[str] = Query(None, description="Nome da adquirente para filtrar"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista contas a receber pendentes de conciliação.
    
    Retorna apenas contas que:
    - Possuem NSU informado
    - Não foram conciliadas ainda (conciliado = false)
    - Pertencem ao tenant do usuário autenticado
    
    Args:
        data_inicio: Data inicial para filtrar (opcional)
        data_fim: Data final para filtrar (opcional)
        adquirente: Nome da adquirente para filtrar (opcional)
        db: Sessão do banco de dados
        user_and_tenant: Tupla (usuário, tenant_id)
    
    Returns:
        List[ContaPendenteOut]: Lista de contas pendentes
    """
    current_user, tenant_id = user_and_tenant

    contas = buscar_contas_nao_conciliadas(
        db=db,
        tenant_id=tenant_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        adquirente=adquirente,
    )

    # Converter para formato de resposta
    return [
        ContaPendenteOut(
            id=conta.id,
            nsu=conta.nsu,
            adquirente=conta.adquirente,
            valor=float(conta.valor_final or conta.valor_original),
            data_prevista=conta.data_vencimento,
            numero_parcela=conta.numero_parcela,
            total_parcelas=conta.total_parcelas,
            descricao=conta.descricao,
            status=conta.status,
        )
        for conta in contas
    ]


@router.post(
    "/conciliacao-cartao/upload",
    status_code=status.HTTP_200_OK,
    summary="Upload de arquivo CSV para conciliação em lote",
    description="Processa um arquivo CSV com transações de cartão e concilia cada uma com as contas a receber"
)
def upload_conciliacao_cartao(
    file: UploadFile = File(..., description="Arquivo CSV com colunas: nsu, valor, data_recebimento, adquirente"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Processa upload de arquivo CSV para conciliação em lote.
    
    Formato do CSV (com cabeçalho):
    ```
    nsu,valor,data_recebimento,adquirente
    123456789,150.00,2026-01-31,Stone
    987654321,89.90,2026-01-31,Cielo
    ```
    
    Cada linha é processada individualmente. Se uma linha falhar, as outras
    continuam sendo processadas.
    
    Args:
        file: Arquivo CSV com as transações
        db: Sessão do banco de dados
        user_and_tenant: Tupla (usuário, tenant_id)
    
    Returns:
        dict: Resumo do processamento com total processado, conciliados e erros
    """
    current_user, tenant_id = user_and_tenant

    # Validar extensão do arquivo
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo deve ser CSV",
        )

    # Ler conteúdo do arquivo
    try:
        content = file.file.read().decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo deve estar codificado em UTF-8",
        )

    # Processar CSV
    reader = csv.DictReader(io.StringIO(content))
    
    # Validar cabeçalho
    colunas_esperadas = {"nsu", "valor", "data_recebimento", "adquirente"}
    if reader.fieldnames is None or not colunas_esperadas.issubset(set(reader.fieldnames)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV deve ter as colunas: {', '.join(sorted(colunas_esperadas))}",
        )

    resultados = {
        "processados": 0,
        "conciliados": 0,
        "erros": [],
    }

    # Processar cada linha
    for idx, row in enumerate(reader, start=2):  # start=2 porque linha 1 é o cabeçalho
        resultados["processados"] += 1
        
        try:
            # Validar campos obrigatórios
            if not row.get("nsu") or not row.get("valor") or not row.get("data_recebimento") or not row.get("adquirente"):
                raise ValueError("Campos obrigatórios ausentes")
            
            # Conciliar usando o service oficial
            conciliar_parcela_cartao(
                db=db,
                tenant_id=tenant_id,
                nsu=row["nsu"].strip(),
                valor=float(row["valor"].strip()),
                data_recebimento=date.fromisoformat(row["data_recebimento"].strip()),
                adquirente=row["adquirente"].strip(),
                usuario_id=current_user.id,
            )
            
            db.commit()
            resultados["conciliados"] += 1

        except HTTPException as e:
            # Erro de negócio (404, 409, 422)
            resultados["erros"].append({
                "linha": idx,
                "nsu": row.get("nsu", "N/A"),
                "erro": e.detail,
            })
            db.rollback()
            
        except ValueError as e:
            # Erro de validação/conversão
            resultados["erros"].append({
                "linha": idx,
                "nsu": row.get("nsu", "N/A"),
                "erro": f"Erro de formato: {str(e)}",
            })
            db.rollback()
            
        except Exception as e:
            # Erro genérico
            resultados["erros"].append({
                "linha": idx,
                "nsu": row.get("nsu", "N/A"),
                "erro": f"Erro inesperado: {str(e)}",
            })
            db.rollback()

    return {
        "message": f"Processamento concluído: {resultados['conciliados']}/{resultados['processados']} conciliados",
        "processados": resultados["processados"],
        "conciliados": resultados["conciliados"],
        "erros": resultados["erros"],
        "taxa_sucesso": round((resultados["conciliados"] / resultados["processados"] * 100), 2) if resultados["processados"] > 0 else 0,
    }
