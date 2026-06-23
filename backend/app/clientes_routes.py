# âš ï¸ ARQUIVO CRÃTICO DE PRODUÃ‡ÃƒO
# Este arquivo impacta diretamente operaÃ§Ãµes reais (PDV / Financeiro / Estoque).
# NÃƒO alterar sem:
# 1. Entender o fluxo completo
# 2. Testar cenÃ¡rio real
# 3. Validar impacto financeiro

"""
Routes para gerenciamento de Clientes e Pets
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import case, or_, func
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import datetime as dt
import logging

from app.db import get_session
from app.models import User, Cliente, Pet, Raca
from app.auth.dependencies import get_current_user_and_tenant
from app.audit_log import log_create, log_update, log_delete
from app.pet_clinical_utils import normalize_pet_clinical_payload
from app.security.permissions_decorator import require_permission
from app.partner_utils import get_all_accessible_tenant_ids
from app.services.pessoa_merge_service import (
    executar_fusao_pessoas,
    montar_preview_fusao_pessoas,
)
from app.services.pessoa_duplicate_service import (
    executar_fusoes_automaticas_pessoas_duplicadas,
    listar_sugestoes_duplicidade_pessoas,
)
from app.services.cliente_alertas_pdv import normalizar_alertas_pdv
from app.clientes.schemas import (
    AjustarCreditoRequest,
    ClienteCreate,
    ClienteResponse,
    ClienteUpdate,
    ClientesListResponse,
    PessoaFusaoExecutarRequest,
    PessoaFusaoPreviewRequest,
    PetCreate,
    PetResponse,
    PetUpdate,
    ToggleParceiroRequest,
)
from app.utils.tenant_safe_sql import execute_tenant_safe
from app.clientes.timeline_routes import (
    TimelineEvento as TimelineEvento,
    _obter_timeline as _obter_timeline,
    obter_timeline_cliente as obter_timeline_cliente,
    obter_timeline_fornecedor as obter_timeline_fornecedor,
    router as timeline_router,
)
from app.clientes.financeiro_routes import (
    router as financeiro_router,
    baixar_vendas_lote,
    get_cliente_historico,
    get_extrato_credito,
    get_historico_compras,
    get_vendas_em_aberto,
)
from app.clientes.duplicidades_routes import (
    router as duplicidades_router,
    executar_fusao_pessoas_route,
    executar_fusoes_automaticas_pessoas_route,
    listar_sugestoes_duplicidade_pessoas_route,
    preview_fusao_pessoas,
    verificar_duplicata,
)
from app.clientes.pets_routes import (
    router as pets_router,
    _pet_response_dict,
    create_pet,
    delete_pet,
    get_pet,
    list_pets_by_cliente,
    listar_todos_pets,
    update_pet,
)
from app.clientes.credito_routes import (
    router as credito_router,
    adicionar_credito,
    remover_campo_duplicado,
    remover_credito,
)
from app.clientes.parceiros_routes import (
    router as parceiros_router,
    atualizar_controla_dre,
    obter_custo_operacional_entregador,
    toggle_parceiro,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clientes", tags=["clientes"])
router.include_router(timeline_router)
router.include_router(financeiro_router)
router.include_router(duplicidades_router)
router.include_router(pets_router)
router.include_router(credito_router)
router.include_router(parceiros_router)


def _somente_digitos_coluna(coluna):
    """Normaliza telefone/celular removendo caracteres de máscara para busca numérica."""
    return func.replace(
        func.replace(
            func.replace(
                func.replace(
                    func.replace(
                        func.replace(func.coalesce(coluna, ""), "(", ""),
                        ")",
                        "",
                    ),
                    "-",
                    "",
                ),
                " ",
                "",
            ),
            "+",
            "",
        ),
        ".",
        "",
    )


def _somente_digitos(valor) -> str:
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


def _validar_telefone_cliente_obrigatorio(cliente_data, cliente_atual=None) -> None:
    tipo = getattr(cliente_data, "tipo_cadastro", None)
    if tipo is None and cliente_atual is not None:
        tipo = getattr(cliente_atual, "tipo_cadastro", None)

    if tipo and tipo != "cliente":
        return

    telefone = getattr(cliente_data, "telefone", None)
    celular = getattr(cliente_data, "celular", None)
    if telefone is None and cliente_atual is not None:
        telefone = getattr(cliente_atual, "telefone", None)
    if celular is None and cliente_atual is not None:
        celular = getattr(cliente_atual, "celular", None)

    if max(len(_somente_digitos(telefone)), len(_somente_digitos(celular))) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telefone/celular obrigatorio para cadastro de cliente",
        )


# ========== HELPERS INTERNOS ==========


def _validar_tenant_e_obter_usuario(user_and_tenant):
    """Desempacota e valida user_and_tenant (padrÃ£o repetido 21x)"""
    current_user, tenant_id = user_and_tenant
    return current_user, tenant_id


def _obter_cliente_ou_404(db: Session, cliente_id: int, tenant_id: str):
    """Busca cliente com validaÃ§Ã£o de tenant e retorna 404 se nÃ£o encontrado"""
    cliente = (
        db.query(Cliente)
        .filter(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id)
        .first()
    )

    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente nÃ£o encontrado"
        )

    return cliente


def _anexar_metadados_criacao_cliente(db: Session, clientes):
    lista = clientes if isinstance(clientes, list) else [clientes]
    user_ids = {
        cliente.user_id for cliente in lista if getattr(cliente, "user_id", None)
    }
    usuarios_por_id = {}
    if user_ids:
        usuarios_por_id = {
            usuario.id: usuario
            for usuario in db.query(User).filter(User.id.in_(user_ids)).all()
        }

    for cliente in lista:
        criado_por_id = getattr(cliente, "user_id", None)
        usuario = usuarios_por_id.get(criado_por_id)
        setattr(cliente, "criado_por_id", criado_por_id)
        setattr(
            cliente,
            "criado_por_nome",
            (getattr(usuario, "nome", None) or getattr(usuario, "email", None))
            if usuario
            else None,
        )
        setattr(
            cliente,
            "criado_por_email",
            getattr(usuario, "email", None) if usuario else None,
        )
    return clientes


# ========== UTILITÃRIOS ==========


def gerar_codigo_cliente(
    db: Session, tipo_cadastro: str, tipo_pessoa: str, tenant_id: int
) -> str:
    """
    Gera código único e crescente para o cliente neste tenant.
    Pega o maior código numérico existente (ativo ou inativo) e soma 1.
    Código nunca é reutilizado mesmo se o cliente for inativado.
    """
    from sqlalchemy import func as sqlfunc, cast as sqcast
    from sqlalchemy.dialects.postgresql import BIGINT

    resultado = (
        db.query(sqlfunc.max(sqcast(Cliente.codigo, BIGINT)))
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.codigo.op("~")("^[0-9]+$"),  # apenas codigos numericos
        )
        .scalar()
    )

    proximo = (resultado or 10000) + 1
    return str(proximo)


# ==================== CLIENTES ====================


@router.post("/", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED)
def create_cliente(
    cliente_data: ClienteCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Criar novo cliente/fornecedor"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    _validar_telefone_cliente_obrigatorio(cliente_data)

    # Validar documento conforme tipo de pessoa (CPF nÃ£o Ã© obrigatÃ³rio)
    if cliente_data.tipo_pessoa == "PF":
        # Verificar se CPF jÃ¡ existe (se fornecido)
        if cliente_data.cpf:
            existing = (
                db.query(Cliente)
                .filter(
                    Cliente.tenant_id == tenant_id,
                    Cliente.cpf == cliente_data.cpf,
                    Cliente.ativo,
                )
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Já existe um {cliente_data.tipo_cadastro} cadastrado com este CPF",
                )

    elif cliente_data.tipo_pessoa == "PJ":
        if not cliente_data.cnpj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CNPJ é obrigatório para Pessoa Jurídica",
            )
        # Verificar se CNPJ jÃ¡ existe
        existing = (
            db.query(Cliente)
            .filter(
                Cliente.tenant_id == tenant_id,
                Cliente.cnpj == cliente_data.cnpj,
                Cliente.ativo,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Já existe um {cliente_data.tipo_cadastro} cadastrado com este CNPJ",
            )

    # Verificar se CRMV jÃ¡ existe (se fornecido e for veterinÃ¡rio)
    if cliente_data.crmv and cliente_data.tipo_cadastro == "veterinario":
        existing_crmv = (
            db.query(Cliente)
            .filter(
                Cliente.tenant_id == tenant_id,
                Cliente.crmv == cliente_data.crmv,
                Cliente.ativo,
            )
            .first()
        )
        if existing_crmv:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um veterinário cadastrado com este CRMV",
            )

    # Verificar se celular jÃ¡ existe (se fornecido)
    if cliente_data.celular:
        existing_cel = (
            db.query(Cliente)
            .filter(
                Cliente.tenant_id == tenant_id,
                Cliente.celular == cliente_data.celular,
                Cliente.ativo,
            )
            .first()
        )
        if existing_cel:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um cadastro com este celular",
            )

    # Verificar se telefone jÃ¡ existe (se fornecido)
    if cliente_data.telefone:
        existing_tel = (
            db.query(Cliente)
            .filter(
                Cliente.tenant_id == tenant_id,
                Cliente.telefone == cliente_data.telefone,
                Cliente.ativo,
            )
            .first()
        )
        if existing_tel:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um cliente cadastrado com este telefone",
            )

    # Gerar cÃ³digo usando a nova funÃ§Ã£o
    codigo = gerar_codigo_cliente(
        db, cliente_data.tipo_cadastro, cliente_data.tipo_pessoa, tenant_id
    )

    # Preparar dados do cliente
    dados_cliente = cliente_data.model_dump()

    # ðŸšš VALIDAÃ‡ÃƒO: Apenas 1 entregador padrÃ£o por vez
    if dados_cliente.get("entregador_padrao") is True:
        # Verificar se jÃ¡ existe outro entregador padrÃ£o
        entregador_padrao_atual = (
            db.query(Cliente)
            .filter(
                Cliente.tenant_id == tenant_id, Cliente.entregador_padrao, Cliente.ativo
            )
            .first()
        )

        if entregador_padrao_atual:
            # Desmarcar o antigo como padrÃ£o
            entregador_padrao_atual.entregador_padrao = False
            entregador_padrao_atual.updated_at = dt.utcnow()
            import logging

            logger = logging.getLogger(__name__)
            logger.info(
                f"ðŸšš Entregador padrÃ£o removido de: {entregador_padrao_atual.nome} (ID: {entregador_padrao_atual.id})"
            )

    # Serializar enderecos_adicionais para JSON (SQLite armazena como TEXT)
    if dados_cliente.get("enderecos_adicionais"):
        import json

        dados_cliente["enderecos_adicionais"] = json.dumps(
            dados_cliente["enderecos_adicionais"]
        )

    # Criar cliente
    novo_cliente = Cliente(
        user_id=current_user.id, tenant_id=tenant_id, codigo=codigo, **dados_cliente
    )

    db.add(novo_cliente)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Código de cliente já em uso. Tente cadastrar novamente.",
        )
    db.refresh(novo_cliente)

    # Log de auditoria
    log_create(
        db, current_user.id, "cliente", novo_cliente.id, cliente_data.model_dump()
    )

    _anexar_metadados_criacao_cliente(db, novo_cliente)
    return novo_cliente


@router.get("/", response_model=ClientesListResponse)
@require_permission("clientes.visualizar")
def list_clientes(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    ativo: Optional[bool] = None,
    incluir_inativos: bool = False,
    tipo_cadastro: Optional[List[str]] = Query(None),  # Aceita lista de tipos
    is_entregador: Optional[bool] = None,  # Filtro para entregadores
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Listar clientes/fornecedores do usuÃ¡rio"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    try:
        # Incluir clientes de tenants parceiros (ex.: pet shop parceiro da clínica)
        access_ids = get_all_accessible_tenant_ids(db, tenant_id)
        query = db.query(Cliente).filter(Cliente.tenant_id.in_(access_ids))

        # Filtro por tipo de cadastro (aceita lista ou string)
        if tipo_cadastro:
            if isinstance(tipo_cadastro, list):
                query = query.filter(Cliente.tipo_cadastro.in_(tipo_cadastro))
            else:
                query = query.filter(Cliente.tipo_cadastro == tipo_cadastro)

        # Filtro por entregador
        if is_entregador is not None:
            query = query.filter(Cliente.is_entregador == is_entregador)

        termo_busca = (search or "").strip()

        termo_digitos = "".join(ch for ch in termo_busca if ch.isdigit())
        termo_numerico = bool(termo_digitos)
        telefone_digitos = _somente_digitos_coluna(Cliente.telefone)
        celular_digitos = _somente_digitos_coluna(Cliente.celular)

        # Filtro de busca por múltiplas palavras (qualquer ordem)
        # Cada palavra precisa existir em pelo menos um dos campos pesquisáveis.
        if termo_busca:
            palavras = [p.strip() for p in termo_busca.split() if p.strip()]
            for palavra in palavras:
                like = f"%{palavra}%"
                palavra_digitos = "".join(ch for ch in palavra if ch.isdigit())
                filtros = [
                    Cliente.codigo.ilike(like),
                    Cliente.nome.ilike(like),
                    Cliente.nome_fantasia.ilike(like),
                    Cliente.razao_social.ilike(like),
                    Cliente.cpf.ilike(like),
                    Cliente.cnpj.ilike(like),
                    Cliente.email.ilike(like),
                    Cliente.telefone.ilike(like),
                    Cliente.celular.ilike(like),
                ]
                if palavra_digitos:
                    like_digitos = f"%{palavra_digitos}%"
                    filtros.extend(
                        [
                            telefone_digitos.ilike(like_digitos),
                            celular_digitos.ilike(like_digitos),
                        ]
                    )
                query = query.filter(or_(*filtros))

        # Filtro de ativo (padrao True - mostrar apenas ativos).
        # Fluxos de privacidade/LGPD podem incluir inativos para localizar titulares
        # ja removidos operacionalmente.
        if not incluir_inativos:
            if ativo is None:
                ativo = True
            if ativo:
                query = query.filter(
                    or_(Cliente.ativo.is_(True), Cliente.ativo.is_(None))
                )
            else:
                query = query.filter(Cliente.ativo.is_(False))

        # Contar total (ANTES do offset/limit)
        total = query.count()

        # Ordenação inteligente por campos visíveis ao usuário (id interno ignorado).
        if termo_busca:
            termo_lower = termo_busca.lower()
            if termo_numerico:
                query = query.order_by(
                    case(
                        (func.lower(Cliente.codigo) == termo_lower, 1),  # codigo exato
                        (telefone_digitos == termo_digitos, 2),  # telefone exato
                        (celular_digitos == termo_digitos, 3),  # celular exato
                        (
                            Cliente.codigo.ilike(f"{termo_digitos}%"),
                            4,
                        ),  # codigo começa com
                        (telefone_digitos.ilike(f"{termo_digitos}%"), 5),
                        (celular_digitos.ilike(f"{termo_digitos}%"), 6),
                        (func.lower(Cliente.nome) == termo_lower, 7),
                        (Cliente.nome.ilike(f"{termo_busca}%"), 8),
                        (Cliente.nome_fantasia.ilike(f"{termo_busca}%"), 9),
                        (Cliente.razao_social.ilike(f"{termo_busca}%"), 10),
                        else_=11,
                    ),
                    Cliente.nome,
                )
            else:
                query = query.order_by(
                    case(
                        (func.lower(Cliente.codigo) == termo_lower, 1),
                        (func.lower(Cliente.nome) == termo_lower, 2),
                        (func.lower(Cliente.nome_fantasia) == termo_lower, 3),
                        (func.lower(Cliente.razao_social) == termo_lower, 4),
                        (Cliente.codigo.ilike(f"{termo_busca}%"), 5),
                        (Cliente.nome.ilike(f"{termo_busca}%"), 6),
                        (Cliente.nome_fantasia.ilike(f"{termo_busca}%"), 7),
                        (Cliente.razao_social.ilike(f"{termo_busca}%"), 8),
                        else_=9,
                    ),
                    Cliente.nome,
                )
        else:
            query = query.order_by(Cliente.nome)

        # Buscar registros paginados
        clientes = query.offset(skip).limit(limit).all()

        # Marcar clientes que pertencem ao tenant parceiro
        tenant_id_str = str(tenant_id)
        for c in clientes:
            if str(c.tenant_id) != tenant_id_str:
                c.de_parceiro = True

        _anexar_metadados_criacao_cliente(db, clientes)

        return ClientesListResponse(items=clientes, total=total, skip=skip, limit=limit)

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao listar clientes: {e}")
        logger.error(f"Tipo do erro: {type(e).__name__}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar clientes: {str(e)}",
        )


# ==================== RAÃ‡AS ====================


@router.get("/racas-teste")
def list_racas_teste(especie: str = ""):
    """Teste simples sem dependÃªncias"""
    return [
        {"id": 1, "nome": "Labrador", "especie": "CÃ£o"},
        {"id": 2, "nome": "SiamÃªs", "especie": "Gato"},
    ]


@router.get("/racas")
def list_racas(
    especie: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Listar raÃ§as cadastradas (filtro por espÃ©cie)"""

    query = db.query(Raca).filter(Raca.ativo)

    if especie:
        query = query.filter(Raca.especie == especie)

    if search:
        query = query.filter(Raca.nome.ilike(f"%{search}%"))

    racas = query.order_by(Raca.nome).all()

    return [{"id": r.id, "nome": r.nome, "especie": r.especie} for r in racas]


# ==================== CLIENTES - GET/UPDATE/DELETE ====================


@router.get("/{cliente_id}", response_model=ClienteResponse)
def get_cliente(
    cliente_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Obter cliente por ID"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)
    _anexar_metadados_criacao_cliente(db, cliente)
    return cliente


@router.put("/{cliente_id}")
def update_cliente(
    cliente_id: int,
    cliente_data: ClienteUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualizar cliente"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    import logging

    logger = logging.getLogger(__name__)
    logger.info("[update_cliente] Atualizando cliente")
    logger.info("[update_cliente] Dados de configuracao de entrega recebidos")

    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)
    _validar_telefone_cliente_obrigatorio(cliente_data, cliente)

    # Verificar CPF duplicado (se alterado)
    if cliente_data.cpf and cliente_data.cpf != cliente.cpf:
        existing = (
            db.query(Cliente)
            .filter(
                Cliente.tenant_id == tenant_id,
                Cliente.cpf == cliente_data.cpf,
                Cliente.id != cliente_id,
                Cliente.ativo,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JÃ¡ existe um cliente cadastrado com este CPF",
            )

    # Verificar CNPJ duplicado (se alterado)
    if cliente_data.cnpj and cliente_data.cnpj != cliente.cnpj:
        existing = (
            db.query(Cliente)
            .filter(
                Cliente.tenant_id == tenant_id,
                Cliente.cnpj == cliente_data.cnpj,
                Cliente.id != cliente_id,
                Cliente.ativo,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JÃ¡ existe um cadastro com este CNPJ",
            )

    # Verificar CRMV duplicado (se alterado)
    if cliente_data.crmv and cliente_data.crmv != cliente.crmv:
        existing = (
            db.query(Cliente)
            .filter(
                Cliente.tenant_id == tenant_id,
                Cliente.crmv == cliente_data.crmv,
                Cliente.id != cliente_id,
                Cliente.ativo,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JÃ¡ existe um veterinÃ¡rio cadastrado com este CRMV",
            )

    # Verificar celular duplicado (se alterado)
    if cliente_data.celular and cliente_data.celular != cliente.celular:
        existing_cel = (
            db.query(Cliente)
            .filter(
                Cliente.tenant_id == tenant_id,
                Cliente.celular == cliente_data.celular,
                Cliente.id != cliente_id,
                Cliente.ativo,
            )
            .first()
        )
        if existing_cel:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JÃ¡ existe um cliente cadastrado com este celular",
            )

    # Verificar telefone duplicado (se alterado)
    if cliente_data.telefone and cliente_data.telefone != cliente.telefone:
        existing_tel = (
            db.query(Cliente)
            .filter(
                Cliente.tenant_id == tenant_id,
                Cliente.telefone == cliente_data.telefone,
                Cliente.id != cliente_id,
                Cliente.ativo,
            )
            .first()
        )
        if existing_tel:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JÃ¡ existe um cliente cadastrado com este telefone",
            )

    # Atualizar campos
    update_data = cliente_data.model_dump(exclude_unset=True)

    # ðŸšš VALIDAÃ‡ÃƒO: Apenas 1 entregador padrÃ£o por vez
    if "entregador_padrao" in update_data and update_data["entregador_padrao"] is True:
        # Verificar se jÃ¡ existe outro entregador padrÃ£o
        entregador_padrao_atual = (
            db.query(Cliente)
            .filter(
                Cliente.tenant_id == tenant_id,
                Cliente.entregador_padrao,
                Cliente.id != cliente_id,
                Cliente.ativo,
            )
            .first()
        )

        if entregador_padrao_atual:
            # Desmarcar o antigo como padrÃ£o
            entregador_padrao_atual.entregador_padrao = False
            entregador_padrao_atual.updated_at = dt.utcnow()
            logger.info(
                f"ðŸšš Entregador padrÃ£o removido de: {entregador_padrao_atual.nome} (ID: {entregador_padrao_atual.id})"
            )

    # Serializar enderecos_adicionais para JSON (SQLite armazena como TEXT)
    if (
        "enderecos_adicionais" in update_data
        and update_data["enderecos_adicionais"] is not None
    ):
        import json

        update_data["enderecos_adicionais"] = json.dumps(
            update_data["enderecos_adicionais"]
        )

    # ðŸ”’ DETECTAR TRANSIÃ‡ÃƒO DE PARCEIRO_ATIVO (TRUE â†’ FALSE)
    parceiro_desativado = False
    comissoes_desativadas_count = 0

    if "parceiro_ativo" in update_data:
        # Cliente era parceiro e estÃ¡ sendo desmarcado
        if (
            hasattr(cliente, "parceiro_ativo")
            and cliente.parceiro_ativo
            and not update_data["parceiro_ativo"]
        ):
            parceiro_desativado = True

            # Desativar todas as comissÃµes ativas dessa pessoa

            # Contar comissÃµes ativas antes de desativar
            result = execute_tenant_safe(
                db,
                """
                    SELECT COUNT(*) 
                    FROM comissoes_configuracao 
                    WHERE funcionario_id = :funcionario_id 
                    AND (ativo = 1 OR ativo IS NULL)
                    AND {tenant_filter}
                """,
                {"funcionario_id": cliente_id},
                tenant_id=tenant_id,
            )
            comissoes_desativadas_count = result.fetchone()[0]

            # Desativar comissÃµes (preservando histÃ³rico)
            if comissoes_desativadas_count > 0:
                execute_tenant_safe(
                    db,
                    """
                        UPDATE comissoes_configuracao 
                        SET ativo = 0,
                            data_atualizacao = CURRENT_TIMESTAMP,
                            usuario_atualizacao = :usuario_id
                        WHERE funcionario_id = :funcionario_id 
                        AND (ativo = 1 OR ativo IS NULL)
                        AND {tenant_filter}
                    """,
                    {"funcionario_id": cliente_id, "usuario_id": current_user.id},
                    tenant_id=tenant_id,
                )

    # Salvar estado antigo para auditoria
    old_data = {field: getattr(cliente, field) for field in update_data.keys()}

    for field, value in update_data.items():
        setattr(cliente, field, value)

    # Se estiver reativando e nÃ£o tiver cÃ³digo, gerar um
    if cliente.ativo and not cliente.codigo:
        cliente.codigo = gerar_codigo_cliente(
            db, cliente.tipo_cadastro, cliente.tipo_pessoa, tenant_id
        )

    cliente.updated_at = dt.utcnow()
    db.commit()
    db.refresh(cliente)

    # Log de auditoria
    log_update(db, current_user.id, "cliente", cliente.id, old_data, update_data)

    _anexar_metadados_criacao_cliente(db, cliente)

    # ðŸ“¢ PREPARAR RESPOSTA COM AVISO SOBRE COMISSÃ•ES
    response = {
        "id": cliente.id,
        "codigo": cliente.codigo,
        "nome": cliente.nome,
        "tipo_cadastro": cliente.tipo_cadastro,
        "tipo_pessoa": cliente.tipo_pessoa,
        "cpf": cliente.cpf,
        "cnpj": cliente.cnpj,
        "email": cliente.email,
        "telefone": cliente.telefone,
        "celular": cliente.celular,
        "parceiro_ativo": cliente.parceiro_ativo
        if hasattr(cliente, "parceiro_ativo")
        else False,
        "data_fechamento_comissao": cliente.data_fechamento_comissao,
        "alertas_pdv": normalizar_alertas_pdv(getattr(cliente, "alertas_pdv", None)),
        "ativo": cliente.ativo,
        "created_at": cliente.created_at,
        "updated_at": cliente.updated_at,
        "criado_por_id": getattr(cliente, "criado_por_id", None),
        "criado_por_nome": getattr(cliente, "criado_por_nome", None),
        "criado_por_email": getattr(cliente, "criado_por_email", None),
    }

    # Adicionar aviso se comissÃµes foram desativadas
    if parceiro_desativado and comissoes_desativadas_count > 0:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            f"ðŸ”’ {comissoes_desativadas_count} comissÃ£o(Ãµes) desativada(s) automaticamente "
            f"para {cliente.nome} (ID: {cliente_id}) porque deixou de ser parceiro."
        )

        response["aviso"] = (
            f"ComissÃµes desativadas automaticamente porque o cliente deixou de ser parceiro. "
            f"Total desativado: {comissoes_desativadas_count}"
        )

    return response


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cliente(
    cliente_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Desativar cliente (soft delete)"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)

    # Soft delete
    cliente.ativo = False
    cliente.updated_at = dt.utcnow()

    # Desativar pets tambÃ©m
    for pet in cliente.pets:
        pet.ativo = False
        pet.updated_at = dt.utcnow()

    db.commit()

    # Log de auditoria
    log_delete(
        db,
        current_user.id,
        "cliente",
        cliente.id,
        {"codigo": cliente.codigo, "nome": cliente.nome, "cpf": cliente.cpf},
    )

    return None


# ============================================================
# TIMELINE UNIFICADA DO CLIENTE
# ============================================================
