"""Rotas de parceiros, controle DRE e custo operacional de entregadores."""

from datetime import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.audit_log import log_update
from app.db import get_session
from app.models import Cliente
from app.clientes.schemas import ToggleParceiroRequest

router = APIRouter()


def _validar_tenant_e_obter_usuario(user_and_tenant):
    current_user, tenant_id = user_and_tenant
    return current_user, tenant_id


def _obter_cliente_ou_404(db: Session, cliente_id: int, tenant_id: str):
    cliente = (
        db.query(Cliente)
        .filter(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id)
        .first()
    )
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente n??o encontrado"
        )
    return cliente

# ==================== PARCEIROS ====================


@router.patch("/{cliente_id}/parceiro")
def toggle_parceiro(
    cliente_id: int,
    request: ToggleParceiroRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Ativar ou desativar um cliente como parceiro para receber comissÃµes.

    Permite que QUALQUER pessoa (cliente, veterinÃ¡rio, funcionÃ¡rio, fornecedor)
    seja ativada como parceiro, independente do tipo_cadastro.
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)

    # Salvar estado anterior para auditoria e lÃ³gica
    old_status = cliente.parceiro_ativo
    old_parceiro_desde = cliente.parceiro_desde

    # ========================================================================
    # LÃ“GICA DE ATIVAÃ‡ÃƒO/DESATIVAÃ‡ÃƒO COM PRESERVAÃ‡ÃƒO DE HISTÃ“RICO
    # ========================================================================

    # CenÃ¡rio 1: Ativando parceiro (false â†’ true ou None â†’ true)
    if request.parceiro_ativo and not old_status:
        cliente.parceiro_ativo = True

        # Se Ã© primeira ativaÃ§Ã£o (nunca foi parceiro antes)
        if not old_parceiro_desde:
            cliente.parceiro_desde = dt.utcnow()
            acao = "primeira_ativacao"
        # Se Ã© reativaÃ§Ã£o (jÃ¡ foi parceiro antes)
        else:
            # Manter data original de parceiro_desde
            # Adicionar registro de reativaÃ§Ã£o nas observaÃ§Ãµes
            data_reativacao = dt.utcnow().strftime("%d/%m/%Y")
            observacao_reativacao = f"\n[Reativado como parceiro em {data_reativacao}]"

            if cliente.parceiro_observacoes:
                cliente.parceiro_observacoes += observacao_reativacao
            else:
                cliente.parceiro_observacoes = (
                    f"Reativado como parceiro em {data_reativacao}"
                )

            acao = "reativacao"

    # CenÃ¡rio 2: Desativando parceiro (true â†’ false)
    elif not request.parceiro_ativo and old_status:
        cliente.parceiro_ativo = False
        # NÃƒO limpar parceiro_desde - preservar histÃ³rico
        # Adicionar registro de desativaÃ§Ã£o nas observaÃ§Ãµes
        data_desativacao = dt.utcnow().strftime("%d/%m/%Y")
        observacao_desativacao = f"\n[Desativado como parceiro em {data_desativacao}]"

        if cliente.parceiro_observacoes:
            cliente.parceiro_observacoes += observacao_desativacao
        else:
            cliente.parceiro_observacoes = (
                f"Desativado como parceiro em {data_desativacao}"
            )

        acao = "desativacao"

    # CenÃ¡rio 3: Status nÃ£o mudou (idempotÃªncia)
    else:
        acao = "sem_alteracao"

    # Atualizar observaÃ§Ãµes adicionais se fornecidas pelo usuÃ¡rio
    # (concatena com as automÃ¡ticas)
    if (
        request.parceiro_observacoes is not None
        and request.parceiro_observacoes.strip()
    ):
        if cliente.parceiro_observacoes:
            cliente.parceiro_observacoes = (
                f"{request.parceiro_observacoes}\n{cliente.parceiro_observacoes}"
            )
        else:
            cliente.parceiro_observacoes = request.parceiro_observacoes

    cliente.updated_at = dt.utcnow()
    db.commit()
    db.refresh(cliente)

    # Log de auditoria detalhado
    log_update(
        db,
        current_user.id,
        "cliente_parceiro",
        cliente.id,
        {
            "parceiro_ativo": old_status,
            "parceiro_desde": old_parceiro_desde.isoformat()
            if old_parceiro_desde
            else None,
        },
        {
            "parceiro_ativo": cliente.parceiro_ativo,
            "parceiro_desde": cliente.parceiro_desde.isoformat()
            if cliente.parceiro_desde
            else None,
            "acao": acao,
        },
    )

    # Mensagens especÃ­ficas por aÃ§Ã£o
    mensagens = {
        "primeira_ativacao": f"Parceiro ativado pela primeira vez em {cliente.parceiro_desde.strftime('%d/%m/%Y')}",
        "reativacao": f"Parceiro reativado com sucesso (parceiro desde {cliente.parceiro_desde.strftime('%d/%m/%Y')})",
        "desativacao": f"Parceiro desativado (histÃ³rico preservado desde {cliente.parceiro_desde.strftime('%d/%m/%Y') if cliente.parceiro_desde else 'N/A'})",
        "sem_alteracao": f"Status de parceiro jÃ¡ estava como {'ativo' if cliente.parceiro_ativo else 'inativo'}",
    }

    return {
        "success": True,
        "message": mensagens.get(acao, "Status atualizado"),
        "acao": acao,
        "data": {
            "id": cliente.id,
            "nome": cliente.nome,
            "tipo_cadastro": cliente.tipo_cadastro,
            "parceiro_ativo": cliente.parceiro_ativo,
            "parceiro_desde": cliente.parceiro_desde.isoformat()
            if cliente.parceiro_desde
            else None,
            "parceiro_observacoes": cliente.parceiro_observacoes,
            "foi_reativacao": acao == "reativacao",
            "historico_preservado": cliente.parceiro_desde is not None,
        },
    }


@router.patch("/{cliente_id}/controla-dre")
def atualizar_controla_dre(
    cliente_id: int,
    controla_dre: bool,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Atualizar o controle DRE de um cliente/fornecedor.

    - controla_dre=True: LanÃ§amentos deste fornecedor/cliente VÃƒO para DRE (padrÃ£o)
    - controla_dre=False: LanÃ§amentos NÃƒO vÃ£o para DRE (ex: fornecedor de produtos para revenda como Buendia)

    Quando controla_dre=False, os lanÃ§amentos deste fornecedor/cliente:
    - NÃƒO aparecem na lista de pendentes de classificaÃ§Ã£o
    - NÃƒO geram sugestÃµes de classificaÃ§Ã£o DRE
    - SÃ£o automaticamente ignorados no processo de classificaÃ§Ã£o
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)

    # Atualizar campo
    old_value = cliente.controla_dre
    cliente.controla_dre = controla_dre
    cliente.updated_at = dt.utcnow()

    db.commit()
    db.refresh(cliente)

    # Log de auditoria
    log_update(
        db,
        current_user.id,
        "cliente_controla_dre",
        cliente.id,
        {"controla_dre": old_value},
        {"controla_dre": controla_dre},
    )

    return {
        "success": True,
        "message": f"{'Ativado' if controla_dre else 'Desativado'} controle DRE para {cliente.nome}",
        "data": {
            "id": cliente.id,
            "nome": cliente.nome,
            "tipo_cadastro": cliente.tipo_cadastro,
            "controla_dre": cliente.controla_dre,
        },
    }

@router.get("/entregadores/{entregador_id}/custo-operacional")
def obter_custo_operacional_entregador(
    entregador_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna o custo operacional calculado para o entregador.

    Para modelo 'rateio_rh':
    - Calcula custo_por_entrega = custo_rh_ajustado / media_entregas_real (se disponÃ­vel)
    - SenÃ£o usa media_entregas_configurada como fallback

    Para modelo 'taxa_fixa':
    - Retorna taxa_fixa_entrega

    Para modelo 'por_km':
    - Retorna valor_por_km_entrega (frontend precisa multiplicar pela distÃ¢ncia)
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Buscar entregador
    entregador = (
        db.query(Cliente)
        .filter(
            Cliente.id == entregador_id,
            Cliente.tenant_id == tenant_id,
            Cliente.is_entregador,
        )
        .first()
    )

    if not entregador:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Entregador nÃ£o encontrado"
        )

    custo_por_entrega = 0
    modelo = entregador.modelo_custo_entrega
    detalhes = {}

    if modelo == "rateio_rh" and entregador.controla_rh:
        # Usar custo_rh_ajustado se disponÃ­vel
        if entregador.custo_rh_ajustado:
            custo_rh = float(entregador.custo_rh_ajustado)
            # Usar mÃ©dia real se disponÃ­vel, senÃ£o configurada
            media_entregas = (
                entregador.media_entregas_real
                or entregador.media_entregas_configurada
                or 1
            )
            custo_por_entrega = custo_rh / media_entregas if media_entregas > 0 else 0

            detalhes = {
                "custo_rh": custo_rh,
                "media_entregas": media_entregas,
                "tipo_media": "real"
                if entregador.media_entregas_real
                else "configurada",
            }
        else:
            # Sem custo RH configurado
            custo_por_entrega = 0
            detalhes = {"aviso": "Custo RH nÃ£o configurado"}

    elif modelo == "taxa_fixa":
        custo_por_entrega = float(entregador.taxa_fixa_entrega or 0)
        detalhes = {"taxa_fixa": custo_por_entrega}

    elif modelo == "por_km":
        custo_por_entrega = float(entregador.valor_por_km_entrega or 0)
        detalhes = {
            "valor_por_km": custo_por_entrega,
            "observacao": "Requer cÃ¡lculo de distÃ¢ncia no frontend",
        }

    else:
        # Sem modelo configurado
        detalhes = {"aviso": "Modelo de custo nÃ£o configurado"}

    return {
        "entregador_id": entregador_id,
        "nome": entregador.nome_fantasia or entregador.nome,
        "modelo_custo": modelo,
        "custo_por_entrega": round(custo_por_entrega, 2),
        "detalhes": detalhes,
    }
