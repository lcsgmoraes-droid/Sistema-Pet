from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_session as get_db
from app.dre_ia_routes_parts.dependencies import _usuario_dre
from app.ia.aba7_models import DREPeriodo

router = APIRouter()


@router.get("/{dre_id}/anomalias")
def obter_anomalias_dre(
    dre_id: int,
    current_user: dict = Depends(_usuario_dre),
    db: Session = Depends(get_db),
):
    """
    Retorna alertas de anomalias detectadas no DRE

    Anomalias são valores significativamente fora do padrão histórico:
    - Receita muito abaixo/acima da média
    - Custos anormalmente altos
    - Margens fora do esperado
    - Despesas fora do padrão
    """
    from app.ia.aba7_anomalias import DetectorAnomalias

    usuario_id = current_user.id

    # Verificar se DRE pertence ao usuário
    dre = (
        db.query(DREPeriodo)
        .filter(DREPeriodo.id == dre_id, DREPeriodo.usuario_id == usuario_id)
        .first()
    )

    if not dre:
        raise HTTPException(status_code=404, detail="DRE não encontrado")

    detector = DetectorAnomalias(db)
    alertas = detector.obter_alertas_ativos(usuario_id, dre_id)

    return {
        "dre_id": dre_id,
        "periodo": f"{dre.data_inicio} a {dre.data_fim}",
        "total_alertas": len(alertas),
        "alertas": alertas,
    }


@router.post("/{dre_id}/recalcular-anomalias")
def recalcular_anomalias(
    dre_id: int,
    current_user: dict = Depends(_usuario_dre),
    db: Session = Depends(get_db),
):
    """Força recálculo de detecção de anomalias"""
    from app.ia.aba7_anomalias import DetectorAnomalias

    usuario_id = current_user.id

    # Verificar se DRE pertence ao usuário
    dre = (
        db.query(DREPeriodo)
        .filter(DREPeriodo.id == dre_id, DREPeriodo.usuario_id == usuario_id)
        .first()
    )

    if not dre:
        raise HTTPException(status_code=404, detail="DRE não encontrado")

    detector = DetectorAnomalias(db)
    anomalias = detector.detectar_anomalias_periodo(usuario_id, dre_id)

    return {
        "sucesso": True,
        "dre_id": dre_id,
        "anomalias_detectadas": len(anomalias),
        "anomalias": anomalias,
    }


@router.get("/{dre_id}/exportar/pdf")
def exportar_dre_pdf(
    dre_id: int,
    incluir_produtos: bool = Query(True, description="Incluir análise de produtos"),
    incluir_categorias: bool = Query(True, description="Incluir análise de categorias"),
    current_user: dict = Depends(_usuario_dre),
    db: Session = Depends(get_db),
):
    """
    Exporta DRE para PDF com formatação profissional

    Inclui:
    - Demonstração completa do resultado
    - Indicadores de performance
    - Score de saúde financeira
    - Top 10 produtos (opcional)
    - Análise por categoria (opcional)
    """
    from app.ia.aba7_exportador import ExportadorDRE

    usuario_id = current_user.id

    # Verificar se DRE pertence ao usuário
    dre = (
        db.query(DREPeriodo)
        .filter(DREPeriodo.id == dre_id, DREPeriodo.usuario_id == usuario_id)
        .first()
    )

    if not dre:
        raise HTTPException(status_code=404, detail="DRE não encontrado")

    exportador = ExportadorDRE(db)
    pdf_buffer = exportador.exportar_pdf(
        dre_periodo_id=dre_id,
        usuario_id=usuario_id,
        incluir_produtos=incluir_produtos,
        incluir_categorias=incluir_categorias,
    )

    filename = f"DRE_{dre.data_inicio}_{dre.data_fim}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{dre_id}/exportar/excel")
def exportar_dre_excel(
    dre_id: int,
    current_user: dict = Depends(_usuario_dre),
    db: Session = Depends(get_db),
):
    """
    Exporta DRE para planilha Excel (.xlsx)

    Formato editável para análises personalizadas
    """
    from app.ia.aba7_exportador import ExportadorDRE

    usuario_id = current_user.id

    # Verificar se DRE pertence ao usuário
    dre = (
        db.query(DREPeriodo)
        .filter(DREPeriodo.id == dre_id, DREPeriodo.usuario_id == usuario_id)
        .first()
    )

    if not dre:
        raise HTTPException(status_code=404, detail="DRE não encontrado")

    exportador = ExportadorDRE(db)
    excel_buffer = exportador.exportar_excel(
        dre_periodo_id=dre_id, usuario_id=usuario_id
    )

    filename = f"DRE_{dre.data_inicio}_{dre.data_fim}.xlsx"

    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
