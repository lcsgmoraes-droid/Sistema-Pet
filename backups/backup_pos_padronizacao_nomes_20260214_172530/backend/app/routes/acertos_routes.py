"""
Rotas de Acerto Financeiro de Parceiros
Consolidação periódica automática de comissões com compensação de dívidas e notificação
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

from app.db import get_session
from app.models import AcertoParceiro, EmailTemplate, Cliente, EmailEnvio
from app.services.acerto_service import AcertoService, EmailService, EmailQueueService
from app.auth import get_current_user_and_tenant
from app.utils.logger import logger


router = APIRouter()


# ====================
# SCHEMAS PYDANTIC
# ====================

class GerarAcertoRequest(BaseModel):
    """Request para gerar acerto financeiro"""
    parceiro_id: int = Field(..., description="ID do parceiro")
    data_acerto: Optional[datetime] = Field(None, description="Data do acerto (default: hoje)")
    forcar_manual: bool = Field(False, description="Forçar acerto manual ignorando configuração")
    enviar_email: bool = Field(True, description="Enviar email de notificação")


class GerarAcertoResponse(BaseModel):
    """Response do acerto financeiro gerado"""
    sucesso: bool
    acerto_id: int
    comissoes_fechadas: int
    valor_bruto: float
    valor_compensado: float
    valor_liquido: float
    email_enviado: bool = False
    mensagem: Optional[str] = None


class AcertoDetalheResponse(BaseModel):
    """Response detalhada de um acerto"""
    id: int
    parceiro_id: int
    parceiro_nome: str
    data_acerto: datetime
    periodo_inicio: datetime
    periodo_fim: datetime
    tipo_acerto: str
    comissoes_fechadas: int
    valor_bruto: float
    valor_compensado: float
    valor_liquido: float
    status: str
    email_enviado: bool
    created_at: datetime


class TemplateEmailRequest(BaseModel):
    """Request para criar/atualizar template"""
    codigo: str = Field(..., max_length=50, description="Código único do template")
    nome: str = Field(..., max_length=255, description="Nome descritivo")
    descricao: Optional[str] = None
    assunto: str = Field(..., max_length=255, description="Assunto do email")
    corpo_html: str = Field(..., description="Corpo em HTML com placeholders {{variavel}}")
    corpo_texto: Optional[str] = Field(None, description="Corpo em texto puro (fallback)")
    placeholders: Optional[List[str]] = Field(None, description="Lista de placeholders disponíveis")
    categoria: Optional[str] = Field(None, max_length=50, description="Categoria do template")
    ativo: bool = Field(True, description="Template ativo?")


class TemplateEmailResponse(BaseModel):
    """Response de template de email"""
    id: int
    codigo: str
    nome: str
    descricao: Optional[str]
    assunto: str
    corpo_html: str
    corpo_texto: Optional[str]
    placeholders: Optional[List[str]]
    categoria: Optional[str]
    ativo: bool
    created_at: datetime
    updated_at: Optional[datetime]


# ====================
# ENDPOINTS - ACERTOS
# ====================

@router.post("/gerar", response_model=GerarAcertoResponse, tags=["Acertos"])
def gerar_acerto(
    request: GerarAcertoRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Gera acerto financeiro para um parceiro.
    
    FLUXO COMPLETO:
    1. Valida parceiro ativo
    2. Calcula período baseado em configuração
    3. Busca TODAS comissões pendentes (status != 'pago')
    4. Fecha cada comissão com compensação automática
    5. Cria registro consolidado em acertos_parceiro
    6. Envia email de notificação (se configurado)
    
    **IMPORTANTE**: Este endpoint fecha TODAS as comissões pendentes do período,
    independente de fechamentos parciais manuais anteriores.
    """
    current_user, tenant_id = user_and_tenant
    try:
        # Gerar acerto
        resultado = AcertoService.gerar_acerto(
            db=db,
            parceiro_id=request.parceiro_id,
            tenant_id=tenant_id,
            data_acerto=request.data_acerto,
            forcar_manual=request.forcar_manual
        )
        
        email_enviado = False
        
        # Enviar email se solicitado e parceiro configurado para receber
        if request.enviar_email and resultado.get('parceiro', {}).get('notificar'):
            parceiro_info = resultado['parceiro']
            
            # Preparar destinatários
            destinatarios = []
            if parceiro_info.get('email'):
                destinatarios.append(parceiro_info['email'])
            
            if parceiro_info.get('emails_copia'):
                emails_copia = [e.strip() for e in parceiro_info['emails_copia'].split(',') if e.strip()]
                destinatarios.extend(emails_copia)
            
            if destinatarios:
                try:
                    # Renderizar template
                    assunto, corpo_html, corpo_texto = EmailService.renderizar_template(
                        db=db,
                        codigo_template='ACERTO_PARCEIRO',
                        placeholders=resultado['dados_email'],
                        user_id=current_user.id
                    )
                    
                    # Enviar email
                    envio_resultado = EmailService.enviar_email(
                        destinatarios=destinatarios,
                        assunto=assunto,
                        corpo_html=corpo_html,
                        corpo_texto=corpo_texto
                    )
                    
                    email_enviado = envio_resultado.get('sucesso', False)
                    
                    # Atualizar registro de acerto
                    acerto = db.query(AcertoParceiro).filter(
                        AcertoParceiro.id == resultado['acerto_id']
                    ).first()
                    
                    if acerto:
                        acerto.email_enviado = email_enviado
                        acerto.email_destinatarios = ', '.join(destinatarios)
                        if not email_enviado:
                            acerto.email_erro = envio_resultado.get('erro', 'Erro desconhecido')
                        db.commit()
                
                except Exception as e:
                    # Erro ao enviar email não deve quebrar o acerto
                    logger.info(f"❌ Erro ao enviar email: {str(e)}")
                    
                    # Registrar erro no acerto
                    acerto = db.query(AcertoParceiro).filter(
                        AcertoParceiro.id == resultado['acerto_id']
                    ).first()
                    
                    if acerto:
                        acerto.email_erro = str(e)
                        db.commit()
        
        return GerarAcertoResponse(
            sucesso=resultado['sucesso'],
            acerto_id=resultado['acerto_id'],
            comissoes_fechadas=resultado['comissoes_fechadas'],
            valor_bruto=resultado['valor_bruto'],
            valor_compensado=resultado['valor_compensado'],
            valor_liquido=resultado['valor_liquido'],
            email_enviado=email_enviado,
            mensagem=resultado.get('mensagem')
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.info(f"❌ Erro ao gerar acerto: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar acerto: {str(e)}")


@router.get("/parceiro/{parceiro_id}", response_model=List[AcertoDetalheResponse], tags=["Acertos"])
def listar_acertos_parceiro(
    parceiro_id: int,
    limit: int = Query(50, ge=1, le=500, description="Limite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """Lista todos os acertos de um parceiro (mais recentes primeiro)"""
    current_user, tenant_id = user_and_tenant
    
    acertos = db.query(AcertoParceiro).filter(
        AcertoParceiro.parceiro_id == parceiro_id,
        AcertoParceiro.tenant_id == tenant_id
    ).order_by(
        AcertoParceiro.created_at.desc()
    ).limit(limit).offset(offset).all()
    
    resultado = []
    for acerto in acertos:
        # Buscar nome do parceiro
        parceiro = db.query(Cliente).filter(Cliente.id == acerto.parceiro_id).first()
        
        resultado.append(AcertoDetalheResponse(
            id=acerto.id,
            parceiro_id=acerto.parceiro_id,
            parceiro_nome=parceiro.nome if parceiro else "Desconhecido",
            data_acerto=acerto.data_acerto,
            periodo_inicio=acerto.periodo_inicio,
            periodo_fim=acerto.periodo_fim,
            tipo_acerto=acerto.tipo_acerto,
            comissoes_fechadas=acerto.comissoes_fechadas,
            valor_bruto=float(acerto.valor_bruto),
            valor_compensado=float(acerto.valor_compensado),
            valor_liquido=float(acerto.valor_liquido),
            status=acerto.status,
            email_enviado=acerto.email_enviado,
            created_at=acerto.created_at
        ))
    
    return resultado


@router.get("/{acerto_id}", response_model=AcertoDetalheResponse, tags=["Acertos"])
def obter_acerto(
    acerto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """Obtém detalhes de um acerto específico"""
    current_user, tenant_id = user_and_tenant
    
    acerto = db.query(AcertoParceiro).filter(
        AcertoParceiro.id == acerto_id,
        AcertoParceiro.tenant_id == tenant_id
    ).first()
    
    if not acerto:
        raise HTTPException(status_code=404, detail="Acerto não encontrado")
    
    # Buscar nome do parceiro
    parceiro = db.query(Cliente).filter(Cliente.id == acerto.parceiro_id).first()
    
    return AcertoDetalheResponse(
        id=acerto.id,
        parceiro_id=acerto.parceiro_id,
        parceiro_nome=parceiro.nome if parceiro else "Desconhecido",
        data_acerto=acerto.data_acerto,
        periodo_inicio=acerto.periodo_inicio,
        periodo_fim=acerto.periodo_fim,
        tipo_acerto=acerto.tipo_acerto,
        comissoes_fechadas=acerto.comissoes_fechadas,
        valor_bruto=float(acerto.valor_bruto),
        valor_compensado=float(acerto.valor_compensado),
        valor_liquido=float(acerto.valor_liquido),
        status=acerto.status,
        email_enviado=acerto.email_enviado,
        created_at=acerto.created_at
    )


# ====================
# ENDPOINTS - TEMPLATES DE EMAIL
# ====================

@router.get("/templates/", response_model=List[TemplateEmailResponse], tags=["Templates Email"])
def listar_templates(
    apenas_ativos: bool = Query(True, description="Filtrar apenas templates ativos"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoria"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """Lista todos os templates de email"""
    current_user, tenant_id = user_and_tenant
    
    query = db.query(EmailTemplate).filter(EmailTemplate.tenant_id == tenant_id)
    
    if apenas_ativos:
        query = query.filter(EmailTemplate.ativo == True)
    
    if categoria:
        query = query.filter(EmailTemplate.categoria == categoria)
    
    templates = query.order_by(EmailTemplate.nome).all()
    
    return [
        TemplateEmailResponse(
            id=t.id,
            codigo=t.codigo,
            nome=t.nome,
            descricao=t.descricao,
            assunto=t.assunto,
            corpo_html=t.corpo_html,
            corpo_texto=t.corpo_texto,
            placeholders=t.placeholders,
            categoria=t.categoria,
            ativo=t.ativo,
            created_at=t.created_at,
            updated_at=t.updated_at
        )
        for t in templates
    ]


@router.get("/templates/{codigo}", response_model=TemplateEmailResponse, tags=["Templates Email"])
def obter_template(
    codigo: str,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """Obtém um template específico por código"""
    current_user, tenant_id = user_and_tenant
    
    template = db.query(EmailTemplate).filter(
        EmailTemplate.codigo == codigo,
        EmailTemplate.tenant_id == tenant_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    
    return TemplateEmailResponse(
        id=template.id,
        codigo=template.codigo,
        nome=template.nome,
        descricao=template.descricao,
        assunto=template.assunto,
        corpo_html=template.corpo_html,
        corpo_texto=template.corpo_texto,
        placeholders=template.placeholders,
        categoria=template.categoria,
        ativo=template.ativo,
        created_at=template.created_at,
        updated_at=template.updated_at
    )


@router.post("/templates/", response_model=TemplateEmailResponse, tags=["Templates Email"])
def criar_template(
    request: TemplateEmailRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """Cria novo template de email"""
    current_user, tenant_id = user_and_tenant
    
    # Verificar se código já existe
    existe = db.query(EmailTemplate).filter(
        EmailTemplate.codigo == request.codigo,
        EmailTemplate.tenant_id == tenant_id
    ).first()
    
    if existe:
        raise HTTPException(status_code=400, detail=f"Template com código '{request.codigo}' já existe")
    
    template = EmailTemplate(
        tenant_id=tenant_id,
        codigo=request.codigo,
        nome=request.nome,
        descricao=request.descricao,
        assunto=request.assunto,
        corpo_html=request.corpo_html,
        corpo_texto=request.corpo_texto,
        placeholders=request.placeholders,
        categoria=request.categoria,
        ativo=request.ativo
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return TemplateEmailResponse(
        id=template.id,
        codigo=template.codigo,
        nome=template.nome,
        descricao=template.descricao,
        assunto=template.assunto,
        corpo_html=template.corpo_html,
        corpo_texto=template.corpo_texto,
        placeholders=template.placeholders,
        categoria=template.categoria,
        ativo=template.ativo,
        created_at=template.created_at,
        updated_at=template.updated_at
    )


@router.put("/templates/{template_id}", response_model=TemplateEmailResponse, tags=["Templates Email"])
def atualizar_template(
    template_id: int,
    request: TemplateEmailRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """Atualiza template existente"""
    current_user, tenant_id = user_and_tenant
    
    template = db.query(EmailTemplate).filter(
        EmailTemplate.id == template_id,
        EmailTemplate.tenant_id == tenant_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    
    # Verificar se novo código já existe em outro template
    if request.codigo != template.codigo:
        existe = db.query(EmailTemplate).filter(
            EmailTemplate.codigo == request.codigo,
            EmailTemplate.tenant_id == tenant_id,
            EmailTemplate.id != template_id
        ).first()
        
        if existe:
            raise HTTPException(status_code=400, detail=f"Template com código '{request.codigo}' já existe")
    
    # Atualizar campos
    template.codigo = request.codigo
    template.nome = request.nome
    template.descricao = request.descricao
    template.assunto = request.assunto
    template.corpo_html = request.corpo_html
    template.corpo_texto = request.corpo_texto
    template.placeholders = request.placeholders
    template.categoria = request.categoria
    template.ativo = request.ativo
    
    db.commit()
    db.refresh(template)
    
    return TemplateEmailResponse(
        id=template.id,
        codigo=template.codigo,
        nome=template.nome,
        descricao=template.descricao,
        assunto=template.assunto,
        corpo_html=template.corpo_html,
        corpo_texto=template.corpo_texto,
        placeholders=template.placeholders,
        categoria=template.categoria,
        ativo=template.ativo,
        created_at=template.created_at,
        updated_at=template.updated_at
    )


@router.delete("/templates/{template_id}", tags=["Templates Email"])
def deletar_template(
    template_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """Deleta um template (desativa ao invés de remover)"""
    current_user, tenant_id = user_and_tenant
    
    template = db.query(EmailTemplate).filter(
        EmailTemplate.id == template_id,
        EmailTemplate.tenant_id == tenant_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    
    # Desativar ao invés de deletar (soft delete)
    template.ativo = False
    db.commit()
    
    return {"sucesso": True, "mensagem": "Template desativado com sucesso"}


# ====================
# ENDPOINTS - FILA DE EMAILS
# ====================

class EmailEnvioResponse(BaseModel):
    """Response de email na fila"""
    id: int
    parceiro_id: int
    parceiro_nome: str
    acerto_id: Optional[int]
    destinatarios: str
    assunto: str
    status: str
    tentativas: int
    max_tentativas: int
    data_enfileiramento: datetime
    data_envio: Optional[datetime]
    proxima_tentativa: Optional[datetime]
    ultimo_erro: Optional[str]
    created_at: datetime


@router.get("/emails/fila", response_model=List[EmailEnvioResponse], tags=["Fila de Emails"])
def listar_fila_emails(
    status: Optional[str] = Query(None, description="Filtrar por status: pendente, enviado, erro"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """Lista emails na fila de envio"""
    current_user, tenant_id = user_and_tenant
    
    query = db.query(EmailEnvio).filter(EmailEnvio.tenant_id == tenant_id)
    
    if status:
        query = query.filter(EmailEnvio.status == status)
    
    emails = query.order_by(EmailEnvio.data_enfileiramento.desc()).limit(limit).offset(offset).all()
    
    resultado = []
    for email in emails:
        parceiro = db.query(Cliente).filter(Cliente.id == email.parceiro_id).first()
        
        resultado.append(EmailEnvioResponse(
            id=email.id,
            parceiro_id=email.parceiro_id,
            parceiro_nome=parceiro.nome if parceiro else "Desconhecido",
            acerto_id=email.acerto_id,
            destinatarios=email.destinatarios,
            assunto=email.assunto,
            status=email.status,
            tentativas=email.tentativas,
            max_tentativas=email.max_tentativas,
            data_enfileiramento=email.data_enfileiramento,
            data_envio=email.data_envio,
            proxima_tentativa=email.proxima_tentativa,
            ultimo_erro=email.ultimo_erro,
            created_at=email.created_at
        ))
    
    return resultado


@router.post("/emails/{email_id}/reenviar", tags=["Fila de Emails"])
def reenviar_email(
    email_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """Reenvia um email que falhou"""
    current_user, tenant_id = user_and_tenant
    
    email = db.query(EmailEnvio).filter(
        EmailEnvio.id == email_id,
        EmailEnvio.tenant_id == tenant_id
    ).first()
    
    if not email:
        raise HTTPException(status_code=404, detail="Email não encontrado")
    
    try:
        resultado = EmailQueueService.reenviar_email(db, email_id)
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao reenviar email: {str(e)}")


@router.post("/emails/processar-fila", tags=["Fila de Emails"])
def processar_fila_manual(
    limite: int = Query(10, ge=1, le=100, description="Quantidade de emails a processar"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """Processa manualmente a fila de emails pendentes"""
    current_user, tenant_id = user_and_tenant
    
    try:
        resultado = EmailQueueService.processar_fila(db, limite=limite)
        return {
            "sucesso": True,
            "processados": resultado['processados'],
            "enviados": resultado['enviados'],
            "erros": resultado['erros']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar fila: {str(e)}")


