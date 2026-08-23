"""Transferencia atomica de estoque entre empresas de um mesmo grupo."""

from __future__ import annotations

from datetime import date, datetime, timezone
import logging
import secrets
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.bling_estoque_sync import sincronizar_bling_background
from app.empresa_grupo_models import (
    EmpresaGrupo,
    EmpresaGrupoMembro,
    EmpresaGrupoTransferencia,
)
from app.estoque.transferencia_grupo_schemas import (
    TransferenciaGrupoExecutarRequest,
    TransferenciaGrupoPreviaRequest,
)
from app.estoque.transferencia_parceiro_entrada_schemas import (
    TransferenciaParceiroEntradaItemRequest,
    TransferenciaParceiroEntradaRequest,
)
from app.estoque.transferencia_parceiro_entrada_service import (
    MOTIVO_ENTRADA_PARCEIRO,
    registrar_entrada_parceiro,
)
from app.estoque.transferencia_parceiro_mutacao_routes import (
    registrar_saida_parceiro,
)
from app.estoque.transferencia_parceiro_schemas import (
    TransferenciaParceiroItemRequest,
    TransferenciaParceiroRequest,
)
from app.estoque.transferencia_parceiro_support import (
    _MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE,
    _restaurar_lotes_consumidos_transferencia,
)
from app.evolucao_corepet import registrar_uso_funcionalidade
from app.financeiro_models import ContaPagar, ContaReceber, Pagamento, Recebimento
from app.models import Cliente, Tenant, User, UserTenant
from app.produtos_models import EstoqueMovimentacao, Produto
from app.services.business_audit_service import log_business_event
from app.tenancy.context import tenant_context

STATUS_MAPEADO = "mapeado"
MOTIVO_CANCELAMENTO_GRUPO = "transf_grupo_cancelamento"
REFERENCIA_CANCELAMENTO_GRUPO = "transferencia_grupo_cancelamento"
logger = logging.getLogger(__name__)


def _texto_limpo(valor) -> str | None:
    texto = str(valor or "").strip()
    return texto or None


def _codigo_forte(valor) -> str | None:
    texto = _texto_limpo(valor)
    return texto.upper() if texto else None


def _identificadores_produto(produto) -> list[str]:
    identificadores = []
    for campo in ("codigo_barras", "gtin_ean", "gtin_ean_tributario"):
        valor = _codigo_forte(getattr(produto, campo, None))
        if valor and valor not in identificadores:
            identificadores.append(valor)
    return identificadores


def _documento_integrado(valor: str | None) -> str:
    informado = _texto_limpo(valor)
    if informado:
        return informado
    agora = datetime.now(timezone.utc)
    return f"TRG-{agora:%Y%m%d%H%M%S}-{secrets.token_hex(2).upper()}"


def _empresa_ativa(db: Session, empresa_id: str) -> Tenant:
    empresa = (
        db.query(Tenant)
        .filter(Tenant.id == str(empresa_id), Tenant.status == "active")
        .first()
    )
    if empresa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa do grupo não encontrada ou inativa.",
        )
    return empresa


def _validar_vinculo(
    db: Session, *, grupo_id: int, empresa_origem_id: str, empresa_destino_id: str
) -> tuple[EmpresaGrupo, EmpresaGrupoMembro, EmpresaGrupoMembro]:
    if empresa_origem_id == empresa_destino_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A empresa de destino deve ser diferente da empresa atual.",
        )
    grupo = (
        db.query(EmpresaGrupo)
        .filter(EmpresaGrupo.id == grupo_id, EmpresaGrupo.status == "ativo")
        .first()
    )
    if grupo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grupo de empresas não encontrado.",
        )
    membros = (
        db.query(EmpresaGrupoMembro)
        .filter(
            EmpresaGrupoMembro.grupo_id == grupo.id,
            EmpresaGrupoMembro.empresa_id.in_([empresa_origem_id, empresa_destino_id]),
            EmpresaGrupoMembro.status == "ativo",
        )
        .all()
    )
    por_empresa = {str(membro.empresa_id): membro for membro in membros}
    origem = por_empresa.get(empresa_origem_id)
    destino = por_empresa.get(empresa_destino_id)
    if origem is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sua empresa não participa deste grupo.",
        )
    if destino is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A empresa de destino não é membro ativo deste grupo.",
        )
    return grupo, origem, destino


def listar_destinos_transferencia(db: Session, *, empresa_origem_id) -> list[dict]:
    empresa_origem_id = str(empresa_origem_id)
    grupos_origem = (
        db.query(EmpresaGrupo, EmpresaGrupoMembro)
        .join(
            EmpresaGrupoMembro,
            EmpresaGrupoMembro.grupo_id == EmpresaGrupo.id,
        )
        .filter(
            EmpresaGrupo.status == "ativo",
            EmpresaGrupoMembro.empresa_id == empresa_origem_id,
            EmpresaGrupoMembro.status == "ativo",
        )
        .all()
    )
    destinos: list[dict] = []
    for grupo, _membro_origem in grupos_origem:
        membros = (
            db.query(EmpresaGrupoMembro, Tenant)
            .join(Tenant, Tenant.id == EmpresaGrupoMembro.empresa_id)
            .filter(
                EmpresaGrupoMembro.grupo_id == grupo.id,
                EmpresaGrupoMembro.empresa_id != empresa_origem_id,
                EmpresaGrupoMembro.status == "ativo",
                Tenant.status == "active",
            )
            .order_by(Tenant.name.asc())
            .all()
        )
        destinos.extend(
            {
                "grupo_id": grupo.id,
                "grupo_nome": grupo.nome,
                "empresa_id": str(membro.empresa_id),
                "empresa_nome": empresa.name,
            }
            for membro, empresa in membros
        )
    return destinos


def _produto_destino_valido(produto: Produto) -> str | None:
    if produto.is_parent:
        return "O produto correspondente no destino é um agrupador de variações."
    if produto.tipo_produto == "KIT" and produto.tipo_kit == "VIRTUAL":
        return "O produto correspondente no destino é um kit virtual."
    if produto.situacao is False:
        return "O produto correspondente está inativo no destino."
    return None


def preparar_previa_transferencia(
    db: Session, *, empresa_origem_id, payload: TransferenciaGrupoPreviaRequest
) -> dict:
    empresa_origem_id = str(empresa_origem_id)
    empresa_destino_id = str(payload.empresa_destino_id)
    empresa_origem_uuid = UUID(empresa_origem_id)
    empresa_destino_uuid = UUID(empresa_destino_id)
    grupo, _origem, _destino = _validar_vinculo(
        db,
        grupo_id=payload.grupo_id,
        empresa_origem_id=empresa_origem_id,
        empresa_destino_id=empresa_destino_id,
    )
    empresa_destino = _empresa_ativa(db, empresa_destino_id)
    ids_origem = sorted({int(item.produto_id) for item in payload.itens})
    produtos_origem = (
        db.query(Produto)
        .filter(
            Produto.id.in_(ids_origem),
            Produto.tenant_id == empresa_origem_uuid,
        )
        .all()
    )
    por_id = {int(produto.id): produto for produto in produtos_origem}
    resultados: list[dict] = []

    for produto_id in ids_origem:
        produto_origem = por_id.get(produto_id)
        if produto_origem is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Produto ID {produto_id} não encontrado na empresa de origem.",
            )
        identificadores = _identificadores_produto(produto_origem)
        base = {
            "produto_origem_id": produto_id,
            "produto_origem_nome": produto_origem.nome,
            "produto_destino_id": None,
            "produto_destino_nome": None,
            "identificador": identificadores[0] if identificadores else None,
        }
        if not identificadores:
            resultados.append(
                {
                    **base,
                    "status": "sem_codigo_barras",
                    "mensagem": "Cadastre um código de barras ou GTIN no produto de origem.",
                }
            )
            continue

        with tenant_context(empresa_destino_id):
            candidatos = (
                db.query(Produto)
                .filter(
                    Produto.tenant_id == empresa_destino_uuid,
                    or_(
                        func.upper(func.trim(Produto.codigo_barras)).in_(
                            identificadores
                        ),
                        func.upper(func.trim(Produto.gtin_ean)).in_(identificadores),
                        func.upper(func.trim(Produto.gtin_ean_tributario)).in_(
                            identificadores
                        ),
                    ),
                )
                .all()
            )
        if not candidatos:
            resultados.append(
                {
                    **base,
                    "status": "nao_encontrado",
                    "mensagem": (
                        "Nenhum produto com o mesmo código de barras foi encontrado "
                        "na empresa de destino."
                    ),
                }
            )
            continue
        if len(candidatos) > 1:
            resultados.append(
                {
                    **base,
                    "status": "ambiguo",
                    "mensagem": (
                        "Mais de um produto do destino usa este código. Corrija a "
                        "duplicidade antes de transferir."
                    ),
                }
            )
            continue
        produto_destino = candidatos[0]
        erro_destino = _produto_destino_valido(produto_destino)
        if erro_destino:
            resultados.append(
                {
                    **base,
                    "produto_destino_id": produto_destino.id,
                    "produto_destino_nome": produto_destino.nome,
                    "status": "invalido",
                    "mensagem": erro_destino,
                }
            )
            continue
        resultados.append(
            {
                **base,
                "produto_destino_id": produto_destino.id,
                "produto_destino_nome": produto_destino.nome,
                "status": STATUS_MAPEADO,
                "mensagem": "Produto correspondente confirmado pelo código de barras.",
            }
        )

    return {
        "grupo_id": grupo.id,
        "grupo_nome": grupo.nome,
        "empresa_destino_id": empresa_destino_id,
        "empresa_destino_nome": empresa_destino.name,
        "todos_mapeados": all(item["status"] == STATUS_MAPEADO for item in resultados),
        "itens": resultados,
    }


def _resolver_usuario_destino(
    db: Session, *, empresa_destino_id: str, membro_destino: EmpresaGrupoMembro
) -> int:
    empresa_destino_uuid = UUID(empresa_destino_id)
    usuario_referencia = membro_destino.usuario_referencia_id
    query = (
        db.query(UserTenant)
        .join(User, User.id == UserTenant.user_id)
        .filter(
            UserTenant.tenant_id == empresa_destino_uuid,
            UserTenant.is_active.is_(True),
            User.is_active.is_(True),
        )
    )
    if usuario_referencia:
        vinculo = query.filter(UserTenant.user_id == usuario_referencia).first()
        if vinculo:
            return int(vinculo.user_id)
    vinculo = query.order_by(UserTenant.id.asc()).first()
    if vinculo is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A empresa de destino não possui um usuário ativo para registrar a "
                "entrada automática."
            ),
        )
    return int(vinculo.user_id)


def _codigo_parceiro_empresa(db: Session, empresa_representada_id: str) -> str:
    base = f"GRP{empresa_representada_id.replace('-', '')[:12]}".upper()
    for sufixo in range(100):
        codigo = base if sufixo == 0 else f"{base[:17]}{sufixo:02d}"
        if db.query(Cliente.id).filter(Cliente.codigo == codigo).first() is None:
            return codigo
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Não foi possível criar o cadastro parceiro da outra empresa.",
    )


def _obter_ou_criar_parceiro_empresa(
    db: Session, *, empresa_representada: Tenant, user_id: int, tenant_id: UUID
) -> Cliente:
    marcador = f"Empresa do grupo CorePet: {empresa_representada.id}"
    filtros = [Cliente.parceiro_observacoes.contains(marcador)]
    if _texto_limpo(empresa_representada.cnpj):
        filtros.append(Cliente.cnpj == empresa_representada.cnpj)
    parceiro = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            or_(*filtros),
        )
        .order_by(Cliente.id.asc())
        .first()
    )
    if parceiro is not None:
        parceiro.parceiro_ativo = True
        if parceiro.parceiro_desde is None:
            parceiro.parceiro_desde = datetime.now(timezone.utc)
        return parceiro
    parceiro = Cliente(
        tenant_id=tenant_id,
        user_id=user_id,
        codigo=_codigo_parceiro_empresa(db, str(empresa_representada.id)),
        tipo_cadastro="fornecedor",
        tipo_pessoa="PJ",
        nome=empresa_representada.name,
        razao_social=empresa_representada.razao_social,
        nome_fantasia=empresa_representada.name,
        cnpj=empresa_representada.cnpj,
        telefone=empresa_representada.telefone,
        email=empresa_representada.email,
        parceiro_ativo=True,
        parceiro_desde=datetime.now(timezone.utc),
        parceiro_observacoes=marcador,
        ativo=True,
    )
    db.add(parceiro)
    db.flush()
    return parceiro


def _detalhe_mapeamentos_bloqueados(previa: dict) -> str:
    bloqueados = [item for item in previa["itens"] if item["status"] != STATUS_MAPEADO]
    nomes = ", ".join(item["produto_origem_nome"] for item in bloqueados[:4])
    complemento = "" if len(bloqueados) <= 4 else f" e mais {len(bloqueados) - 4}"
    return (
        "A entrada automática foi bloqueada porque existem produtos sem "
        f"correspondência segura no destino: {nomes}{complemento}."
    )


def executar_transferencia_integrada(
    db: Session,
    *,
    empresa_origem_id,
    usuario_origem_id: int,
    payload: TransferenciaGrupoExecutarRequest,
) -> dict:
    empresa_origem_id = str(empresa_origem_id)
    empresa_destino_id = str(payload.empresa_destino_id)
    empresa_origem_uuid = UUID(empresa_origem_id)
    empresa_destino_uuid = UUID(empresa_destino_id)
    chave_idempotencia = str(payload.chave_idempotencia)
    existente = (
        db.query(EmpresaGrupoTransferencia)
        .filter(
            EmpresaGrupoTransferencia.empresa_origem_id == empresa_origem_id,
            EmpresaGrupoTransferencia.chave_idempotencia == chave_idempotencia,
        )
        .first()
    )
    if existente is not None:
        if existente.status == "concluida" and existente.resultado:
            return {**existente.resultado, "idempotente": True}
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta transferência já está sendo processada.",
        )

    previa = preparar_previa_transferencia(
        db,
        empresa_origem_id=empresa_origem_id,
        payload=payload,
    )
    if not previa["todos_mapeados"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "mensagem": _detalhe_mapeamentos_bloqueados(previa),
                "previa": previa,
            },
        )
    grupo, _membro_origem, membro_destino = _validar_vinculo(
        db,
        grupo_id=payload.grupo_id,
        empresa_origem_id=empresa_origem_id,
        empresa_destino_id=empresa_destino_id,
    )
    empresa_origem = _empresa_ativa(db, empresa_origem_id)
    empresa_destino = _empresa_ativa(db, empresa_destino_id)
    documento = _documento_integrado(payload.documento)
    transferencia = EmpresaGrupoTransferencia(
        grupo_id=grupo.id,
        empresa_origem_id=empresa_origem_id,
        empresa_destino_id=empresa_destino_id,
        usuario_origem_id=usuario_origem_id,
        chave_idempotencia=chave_idempotencia,
        documento=documento,
        status="processando",
        itens_snapshot=previa["itens"],
    )
    db.add(transferencia)
    db.flush()

    parceiro_destino = _obter_ou_criar_parceiro_empresa(
        db,
        empresa_representada=empresa_destino,
        user_id=usuario_origem_id,
        tenant_id=empresa_origem_uuid,
    )
    observacao_base = (
        f"Transferência integrada #{transferencia.id} para {empresa_destino.name}."
    )
    observacao = (
        f"{observacao_base} {payload.observacao}"
        if _texto_limpo(payload.observacao)
        else observacao_base
    )
    itens_saida = [
        TransferenciaParceiroItemRequest(
            produto_id=item.produto_id,
            quantidade=item.quantidade,
            custo_unitario=item.custo_unitario,
            valor_total=item.valor_total,
        )
        for item in payload.itens
    ]
    saida = registrar_saida_parceiro(
        db,
        tenant_id=empresa_origem_uuid,
        user_id=usuario_origem_id,
        payload=TransferenciaParceiroRequest(
            parceiro_id=parceiro_destino.id,
            data_vencimento=payload.data_vencimento,
            documento=documento,
            observacao=observacao,
            itens=itens_saida,
        ),
        commit=False,
        sincronizar=False,
    )
    log_business_event(
        db=db,
        tenant_id=empresa_origem_id,
        user_id=usuario_origem_id,
        event="transferencia_grupo_saida_integrada",
        entity_type="empresa_grupo_transferencia",
        entity_id=transferencia.id,
        metadata={
            "grupo_id": grupo.id,
            "empresa_destino_id": empresa_destino_id,
            "documento": documento,
        },
        commit=False,
    )
    db.flush()

    mapeamento_por_origem = {
        item["produto_origem_id"]: item for item in previa["itens"]
    }
    saldos_destino: list[dict] = []
    with tenant_context(empresa_destino_id):
        usuario_destino_id = _resolver_usuario_destino(
            db,
            empresa_destino_id=empresa_destino_id,
            membro_destino=membro_destino,
        )
        parceiro_origem = _obter_ou_criar_parceiro_empresa(
            db,
            empresa_representada=empresa_origem,
            user_id=usuario_destino_id,
            tenant_id=empresa_destino_uuid,
        )
        itens_entrada = [
            TransferenciaParceiroEntradaItemRequest(
                produto_id=mapeamento_por_origem[item.produto_id]["produto_destino_id"],
                quantidade=item.quantidade,
                custo_unitario=item.custo_unitario,
                valor_total=item.valor_total,
            )
            for item in payload.itens
        ]
        entrada = registrar_entrada_parceiro(
            db,
            tenant_id=empresa_destino_uuid,
            user_id=usuario_destino_id,
            payload=TransferenciaParceiroEntradaRequest(
                parceiro_id=parceiro_origem.id,
                data_emissao=date.today(),
                data_vencimento=payload.data_vencimento,
                documento=documento,
                observacao=(
                    f"Transferência integrada #{transferencia.id} recebida de "
                    f"{empresa_origem.name}."
                ),
                entrar_estoque=True,
                itens=itens_entrada,
            ),
            commit=False,
            sincronizar=False,
        )
        log_business_event(
            db=db,
            tenant_id=empresa_destino_id,
            user_id=usuario_destino_id,
            event="transferencia_grupo_entrada_integrada",
            entity_type="empresa_grupo_transferencia",
            entity_id=transferencia.id,
            metadata={
                "grupo_id": grupo.id,
                "empresa_origem_id": empresa_origem_id,
                "documento": documento,
            },
            commit=False,
        )
        db.flush()
        ids_destino = sorted({int(item.produto_id) for item in itens_entrada})
        produtos_destino = (
            db.query(Produto)
            .filter(
                Produto.id.in_(ids_destino),
                Produto.tenant_id == empresa_destino_uuid,
            )
            .all()
        )
        saldos_destino = [
            {
                "produto_id": int(produto.id),
                "estoque_novo": float(produto.estoque_atual or 0),
            }
            for produto in produtos_destino
        ]

    resultado = {
        "sucesso": True,
        "transferencia_grupo_id": transferencia.id,
        "grupo_id": grupo.id,
        "grupo_nome": grupo.nome,
        "empresa_origem_id": empresa_origem_id,
        "empresa_origem_nome": empresa_origem.name,
        "empresa_destino_id": empresa_destino_id,
        "empresa_destino_nome": empresa_destino.name,
        "documento": documento,
        "conta_receber_origem_id": saida["conta_receber_id"],
        "conta_pagar_destino_id": entrada["conta_pagar_id"],
        "total": saida["total_ressarcimento"],
        "itens": previa["itens"],
        "idempotente": False,
    }
    transferencia.usuario_destino_id = usuario_destino_id
    transferencia.conta_receber_origem_id = saida["conta_receber_id"]
    transferencia.conta_pagar_destino_id = entrada["conta_pagar_id"]
    transferencia.status = "concluida"
    transferencia.resultado = resultado
    transferencia.concluido_em = datetime.now(timezone.utc)
    db.commit()

    for item in saida["itens"]:
        try:
            sincronizar_bling_background(
                item["produto_id"],
                item["estoque_novo"],
                "transferencia_grupo_saida",
            )
        except Exception:
            logger.warning(
                "Nao foi possivel agendar o Bling da saida integrada",
                exc_info=True,
            )
    for item in saldos_destino:
        try:
            sincronizar_bling_background(
                item["produto_id"],
                item["estoque_novo"],
                "transferencia_grupo_entrada",
            )
        except Exception:
            logger.warning(
                "Nao foi possivel agendar o Bling da entrada integrada",
                exc_info=True,
            )
    registrar_uso_funcionalidade(db, "grupos-empresas-transferencia-integrada")
    return resultado


def _adicionar_historico_cancelamento(texto_atual: str | None, mensagem: str) -> str:
    texto_atual = _texto_limpo(texto_atual)
    return f"{texto_atual}\n\n{mensagem}" if texto_atual else mensagem


def _validar_financeiro_cancelavel(
    db: Session,
    *,
    conta_receber: ContaReceber,
    conta_pagar: ContaPagar,
    empresa_origem_id: str,
    empresa_destino_id: str,
) -> None:
    empresa_origem_uuid = UUID(empresa_origem_id)
    empresa_destino_uuid = UUID(empresa_destino_id)
    with tenant_context(empresa_origem_id):
        possui_recebimento = (
            db.query(Recebimento.id)
            .filter(
                Recebimento.tenant_id == empresa_origem_uuid,
                Recebimento.conta_receber_id == conta_receber.id,
            )
            .first()
            is not None
        )
    status_receber = str(conta_receber.status or "").strip().lower()
    if (
        float(conta_receber.valor_recebido or 0) > 0
        or possui_recebimento
        or status_receber in {"recebido", "pago", "parcial", "baixa_parcial"}
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A transferência integrada possui recebimento na empresa de origem. "
                "Desfaça a baixa financeira antes de cancelar."
            ),
        )

    with tenant_context(empresa_destino_id):
        possui_pagamento = (
            db.query(Pagamento.id)
            .filter(
                Pagamento.tenant_id == empresa_destino_uuid,
                Pagamento.conta_pagar_id == conta_pagar.id,
            )
            .first()
            is not None
        )
    status_pagar = str(conta_pagar.status or "").strip().lower()
    if (
        float(conta_pagar.valor_pago or 0) > 0
        or possui_pagamento
        or status_pagar in {"pago", "recebido", "parcial"}
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A transferência integrada possui pagamento na empresa de destino. "
                "Desfaça a baixa financeira antes de cancelar."
            ),
        )


def _criar_movimentacao_cancelamento(
    db: Session,
    *,
    produto: Produto,
    movimento_original: EstoqueMovimentacao,
    transferencia: EmpresaGrupoTransferencia,
    tenant_id: str,
    user_id: int,
    tipo: str,
) -> dict:
    quantidade = float(movimento_original.quantidade or 0)
    estoque_anterior = float(produto.estoque_atual or 0)
    if tipo == "saida" and estoque_anterior + 1e-9 < quantidade:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Não é possível cancelar porque o produto '{produto.nome}' não possui "
                "mais a quantidade recebida no estoque de destino. Reponha o estoque "
                "antes de cancelar."
            ),
        )
    estoque_novo = (
        estoque_anterior + quantidade
        if tipo == "entrada"
        else estoque_anterior - quantidade
    )
    produto.estoque_atual = estoque_novo
    movimento = EstoqueMovimentacao(
        produto_id=produto.id,
        tipo=tipo,
        motivo=MOTIVO_CANCELAMENTO_GRUPO,
        quantidade=quantidade,
        quantidade_anterior=estoque_anterior,
        quantidade_nova=estoque_novo,
        custo_unitario=float(movimento_original.custo_unitario or 0),
        valor_total=float(movimento_original.valor_total or 0),
        documento=transferencia.documento,
        referencia_id=transferencia.id,
        referencia_tipo=REFERENCIA_CANCELAMENTO_GRUPO,
        observacao=(
            f"Cancelamento da transferência integrada #{transferencia.id}. "
            "Estoque revertido nas duas empresas."
        ),
        user_id=user_id,
        tenant_id=tenant_id,
    )
    db.add(produto)
    db.add(movimento)
    db.flush()
    return {
        "movimentacao_id": movimento.id,
        "produto_id": produto.id,
        "estoque_novo": float(estoque_novo),
    }


def cancelar_transferencia_integrada_por_conta(
    db: Session,
    *,
    empresa_origem_id,
    usuario_origem_id: int,
    conta_receber_origem_id: int,
) -> dict | None:
    """Cancela os dois lados de uma transferência integrada, em uma transação."""
    empresa_origem_id = str(empresa_origem_id)
    empresa_origem_uuid = UUID(empresa_origem_id)
    transferencia = (
        db.query(EmpresaGrupoTransferencia)
        .filter(
            EmpresaGrupoTransferencia.empresa_origem_id == empresa_origem_id,
            EmpresaGrupoTransferencia.conta_receber_origem_id
            == int(conta_receber_origem_id),
        )
        .with_for_update()
        .first()
    )
    if transferencia is None:
        return None
    if transferencia.status == "cancelada":
        cancelamento = dict((transferencia.resultado or {}).get("cancelamento") or {})
        return {
            "sucesso": True,
            "transferencia_integrada": True,
            "transferencia_grupo_id": transferencia.id,
            "conta_receber_id": conta_receber_origem_id,
            "conta_pagar_destino_id": transferencia.conta_pagar_destino_id,
            "status": "cancelada",
            **cancelamento,
            "idempotente": True,
        }
    if transferencia.status != "concluida":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A transferência integrada não está concluída e não pode ser cancelada.",
        )
    if not transferencia.conta_pagar_destino_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A transferência integrada não possui a conta de destino vinculada.",
        )

    empresa_destino_id = str(transferencia.empresa_destino_id)
    empresa_destino_uuid = UUID(empresa_destino_id)
    with tenant_context(empresa_origem_id):
        conta_receber = (
            db.query(ContaReceber)
            .filter(
                ContaReceber.id == int(conta_receber_origem_id),
                ContaReceber.tenant_id == empresa_origem_uuid,
                ContaReceber.canal == "transferencia_parceiro",
            )
            .with_for_update()
            .first()
        )
        movimentos_origem = (
            db.query(EstoqueMovimentacao)
            .filter(
                EstoqueMovimentacao.tenant_id == empresa_origem_uuid,
                EstoqueMovimentacao.referencia_id == int(conta_receber_origem_id),
                EstoqueMovimentacao.tipo == "saida",
                EstoqueMovimentacao.motivo.in_(
                    [_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE, "transferencia_parceiro"]
                ),
            )
            .order_by(EstoqueMovimentacao.id.asc())
            .all()
        )
    with tenant_context(empresa_destino_id):
        conta_pagar = (
            db.query(ContaPagar)
            .filter(
                ContaPagar.id == int(transferencia.conta_pagar_destino_id),
                ContaPagar.tenant_id == empresa_destino_uuid,
                ContaPagar.canal == "transferencia_parceiro_entrada",
            )
            .with_for_update()
            .first()
        )
        movimentos_destino = (
            db.query(EstoqueMovimentacao)
            .filter(
                EstoqueMovimentacao.tenant_id == empresa_destino_uuid,
                EstoqueMovimentacao.referencia_id
                == int(transferencia.conta_pagar_destino_id),
                EstoqueMovimentacao.tipo == "entrada",
                EstoqueMovimentacao.motivo == MOTIVO_ENTRADA_PARCEIRO,
            )
            .order_by(EstoqueMovimentacao.id.asc())
            .all()
        )

    if conta_receber is None or conta_pagar is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Os lançamentos financeiros da transferência integrada não foram encontrados.",
        )
    if not movimentos_origem or not movimentos_destino:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="As movimentações de estoque da transferência integrada não foram encontradas.",
        )
    _validar_financeiro_cancelavel(
        db,
        conta_receber=conta_receber,
        conta_pagar=conta_pagar,
        empresa_origem_id=empresa_origem_id,
        empresa_destino_id=empresa_destino_id,
    )

    quantidades_destino: dict[int, float] = {}
    for movimento in movimentos_destino:
        quantidades_destino[movimento.produto_id] = quantidades_destino.get(
            movimento.produto_id, 0.0
        ) + float(movimento.quantidade or 0)
    with tenant_context(empresa_destino_id):
        produtos_destino = (
            db.query(Produto)
            .filter(
                Produto.tenant_id == empresa_destino_uuid,
                Produto.id.in_(list(quantidades_destino)),
            )
            .with_for_update()
            .all()
        )
    produtos_destino_por_id = {produto.id: produto for produto in produtos_destino}
    for produto_id, quantidade in quantidades_destino.items():
        produto = produtos_destino_por_id.get(produto_id)
        if produto is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Produto ID {produto_id} não foi encontrado na empresa de destino.",
            )
        if float(produto.estoque_atual or 0) + 1e-9 < quantidade:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Não é possível cancelar porque o produto '{produto.nome}' não possui "
                    "mais a quantidade recebida no estoque de destino. Reponha o estoque "
                    "antes de cancelar."
                ),
            )

    movimentos_cancelamento_origem: list[dict] = []
    with tenant_context(empresa_origem_id):
        produtos_origem = (
            db.query(Produto)
            .filter(
                Produto.tenant_id == empresa_origem_uuid,
                Produto.id.in_([mov.produto_id for mov in movimentos_origem]),
            )
            .with_for_update()
            .all()
        )
        produtos_origem_por_id = {produto.id: produto for produto in produtos_origem}
        for movimento in movimentos_origem:
            produto = produtos_origem_por_id.get(movimento.produto_id)
            if produto is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Produto ID {movimento.produto_id} não foi encontrado na origem.",
                )
            _restaurar_lotes_consumidos_transferencia(db, movimento)
            movimentos_cancelamento_origem.append(
                _criar_movimentacao_cancelamento(
                    db,
                    produto=produto,
                    movimento_original=movimento,
                    transferencia=transferencia,
                    tenant_id=empresa_origem_uuid,
                    user_id=usuario_origem_id,
                    tipo="entrada",
                )
            )

    usuario_destino_id = int(transferencia.usuario_destino_id or usuario_origem_id)
    movimentos_cancelamento_destino: list[dict] = []
    with tenant_context(empresa_destino_id):
        for movimento in movimentos_destino:
            movimentos_cancelamento_destino.append(
                _criar_movimentacao_cancelamento(
                    db,
                    produto=produtos_destino_por_id[movimento.produto_id],
                    movimento_original=movimento,
                    transferencia=transferencia,
                    tenant_id=empresa_destino_uuid,
                    user_id=usuario_destino_id,
                    tipo="saida",
                )
            )

    cancelado_em = datetime.now(timezone.utc)
    mensagem_historico = (
        f"Transferência integrada #{transferencia.id} cancelada em "
        f"{cancelado_em:%d/%m/%Y %H:%M}. Estoque e financeiro revertidos nas duas empresas."
    )
    conta_receber.status = "cancelado"
    conta_receber.observacoes = _adicionar_historico_cancelamento(
        conta_receber.observacoes, mensagem_historico
    )
    conta_pagar.status = "cancelado"
    conta_pagar.observacoes = _adicionar_historico_cancelamento(
        conta_pagar.observacoes, mensagem_historico
    )
    transferencia.status = "cancelada"
    cancelamento = {
        "cancelado_em": cancelado_em.isoformat(),
        "cancelado_por_usuario_id": usuario_origem_id,
        "movimentacoes_origem": movimentos_cancelamento_origem,
        "movimentacoes_destino": movimentos_cancelamento_destino,
    }
    transferencia.resultado = {
        **dict(transferencia.resultado or {}),
        "status": "cancelada",
        "cancelamento": cancelamento,
    }
    with tenant_context(empresa_origem_id):
        log_business_event(
            db=db,
            tenant_id=empresa_origem_id,
            user_id=usuario_origem_id,
            event="transferencia_grupo_cancelada_origem",
            entity_type="empresa_grupo_transferencia",
            entity_id=transferencia.id,
            metadata={"empresa_destino_id": empresa_destino_id},
            commit=False,
        )
    with tenant_context(empresa_destino_id):
        log_business_event(
            db=db,
            tenant_id=empresa_destino_id,
            user_id=usuario_destino_id,
            event="transferencia_grupo_cancelada_destino",
            entity_type="empresa_grupo_transferencia",
            entity_id=transferencia.id,
            metadata={"empresa_origem_id": empresa_origem_id},
            commit=False,
        )
    db.commit()

    for movimento in movimentos_cancelamento_origem:
        try:
            sincronizar_bling_background(
                movimento["produto_id"],
                movimento["estoque_novo"],
                "transferencia_grupo_cancelamento_origem",
            )
        except Exception:
            logger.warning(
                "Nao foi possivel agendar o Bling do cancelamento na origem",
                exc_info=True,
            )
    for movimento in movimentos_cancelamento_destino:
        try:
            sincronizar_bling_background(
                movimento["produto_id"],
                movimento["estoque_novo"],
                "transferencia_grupo_cancelamento_destino",
            )
        except Exception:
            logger.warning(
                "Nao foi possivel agendar o Bling do cancelamento no destino",
                exc_info=True,
            )

    return {
        "sucesso": True,
        "transferencia_integrada": True,
        "transferencia_grupo_id": transferencia.id,
        "conta_receber_id": conta_receber.id,
        "conta_pagar_destino_id": conta_pagar.id,
        "status": "cancelada",
        **cancelamento,
        "idempotente": False,
    }
