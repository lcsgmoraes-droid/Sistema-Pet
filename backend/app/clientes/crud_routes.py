"""CRUD principal de clientes, fornecedores e pessoas operacionais."""

from datetime import datetime as dt, timedelta
import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Float, Integer, and_, case, cast, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit_log import log_create, log_delete, log_update
from app.auth.dependencies import get_current_user_and_tenant
from app.clientes.common import (
    _anexar_metadados_criacao_cliente,
    _obter_cliente_ou_404,
    _somente_digitos_coluna,
    _validar_telefone_cliente_obrigatorio,
    _validar_tenant_e_obter_usuario,
    gerar_codigo_cliente,
)
from app.clientes.schemas import (
    ClienteCreate,
    ClienteResponse,
    ClientesListResponse,
    ClienteUpdate,
)
from app.db import get_session
from app.models import AppAccessProfile, Cliente, Role, User, UserTenant
from app.segmentacao_models import ClienteSegmento
from app.vendas_models import Venda
from app.partner_utils import get_all_accessible_tenant_ids
from app.security.permissions_decorator import require_permission
from app.services.cliente_alertas_pdv import normalizar_alertas_pdv
from app.services.app_access_profile_service import sync_cliente_app_access_profiles
from app.utils.tenant_safe_sql import execute_tenant_safe

logger = logging.getLogger(__name__)

base_router = APIRouter()
detail_router = APIRouter()
router = APIRouter()


@base_router.post(
    "/", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED
)
def create_cliente(
    cliente_data: ClienteCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Criar novo cliente/fornecedor."""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    _validar_telefone_cliente_obrigatorio(cliente_data)
    _validar_documentos_unicos_criacao(db, cliente_data, tenant_id)

    codigo = gerar_codigo_cliente(
        db, cliente_data.tipo_cadastro, cliente_data.tipo_pessoa, tenant_id
    )
    dados_payload = cliente_data.model_dump()
    auth_user_id = dados_payload.pop("auth_user_id", None)
    app_access_profiles = dados_payload.pop("app_access_profiles", [])
    _normalizar_campos_identidade(dados_payload)
    dados_cliente = _preparar_dados_cliente(
        dados_payload,
        serializar_lista_vazia=False,
    )
    _garantir_entregador_padrao_unico_criacao(db, dados_cliente, tenant_id)

    novo_cliente = Cliente(
        user_id=current_user.id,
        auth_user_id=_validar_conta_app(
            db,
            tenant_id=tenant_id,
            auth_user_id=auth_user_id,
        ),
        tenant_id=tenant_id,
        codigo=codigo,
        **dados_cliente,
    )

    db.add(novo_cliente)
    try:
        db.flush()
        sync_cliente_app_access_profiles(
            db,
            tenant_id=tenant_id,
            cliente=novo_cliente,
            profile_types=app_access_profiles,
            granted_by_user_id=current_user.id,
            linked_user_id=novo_cliente.auth_user_id,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Código de cliente já em uso. Tente cadastrar novamente.",
        ) from exc

    db.refresh(novo_cliente)
    log_create(
        db, current_user.id, "cliente", novo_cliente.id, cliente_data.model_dump()
    )
    _anexar_metadados_criacao_cliente(db, novo_cliente)
    return novo_cliente


@base_router.get("/acessos-app/usuarios")
@require_permission("clientes.editar")
def listar_usuarios_para_acesso_app(
    cliente_id: Optional[int] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista contas do tenant que podem ser vinculadas a uma pessoa no app."""
    _current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    rows = (
        db.query(User, UserTenant, Role)
        .join(
            UserTenant,
            (UserTenant.user_id == User.id) & (UserTenant.tenant_id == tenant_id),
        )
        .join(Role, Role.id == UserTenant.role_id)
        .filter(
            User.tenant_id == tenant_id,
            Role.tenant_id == tenant_id,
            User.is_active.is_(True),
            UserTenant.is_active.is_(True),
        )
        .order_by(User.nome.asc().nullslast(), User.email.asc())
        .all()
    )
    usuarios: dict[int, dict] = {}
    for user, _vinculo, role in rows:
        item = usuarios.setdefault(
            user.id,
            {
                "user_id": user.id,
                "nome": user.nome,
                "email": user.email,
                "perfis_sistema": [],
            },
        )
        if role.name not in item["perfis_sistema"]:
            item["perfis_sistema"].append(role.name)
    vinculados = {
        pessoa.auth_user_id: pessoa
        for pessoa in db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.auth_user_id.is_not(None),
            Cliente.ativo.is_not(False),
        )
        .all()
    }
    return [
        {
            **item,
            "perfil_sistema": ", ".join(item["perfis_sistema"]),
            "disponivel": (
                item["user_id"] not in vinculados
                or int(vinculados[item["user_id"]].id) == int(cliente_id or 0)
            ),
            "pessoa_vinculada_id": getattr(vinculados.get(item["user_id"]), "id", None),
            "pessoa_vinculada_nome": getattr(
                vinculados.get(item["user_id"]), "nome", None
            ),
        }
        for item in usuarios.values()
    ]


@base_router.get("/", response_model=ClientesListResponse)
@require_permission("clientes.visualizar")
def list_clientes(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    ativo: Optional[bool] = None,
    incluir_inativos: bool = False,
    tipo_cadastro: Optional[List[str]] = Query(None),
    is_entregador: Optional[bool] = None,
    visao_dashboard: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Listar clientes/fornecedores do usuario."""
    _current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    try:
        query = _montar_query_listagem_clientes(
            db,
            tenant_id=tenant_id,
            tipo_cadastro=tipo_cadastro,
            is_entregador=is_entregador,
            search=search,
            ativo=ativo,
            incluir_inativos=incluir_inativos,
            visao_dashboard=visao_dashboard,
        )
        total = query.count()
        query = _ordenar_query_listagem(query, search)
        clientes = query.offset(skip).limit(limit).all()
        _marcar_clientes_de_parceiro(clientes, tenant_id)
        _anexar_metadados_criacao_cliente(db, clientes)
        return ClientesListResponse(items=clientes, total=total, skip=skip, limit=limit)
    except Exception as exc:
        logger.exception("Erro ao listar clientes")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar clientes: {str(exc)}",
        ) from exc


@detail_router.get("/{cliente_id}", response_model=ClienteResponse)
def get_cliente(
    cliente_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Obter cliente por ID."""
    _current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)
    _anexar_metadados_criacao_cliente(db, cliente)
    return cliente


@detail_router.put("/{cliente_id}")
def update_cliente(
    cliente_id: int,
    cliente_data: ClienteUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualizar cliente."""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    logger.info("[update_cliente] Atualizando cliente")
    logger.info("[update_cliente] Dados de configuracao de entrega recebidos")

    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)
    _validar_telefone_cliente_obrigatorio(cliente_data, cliente)
    _validar_documentos_unicos_update(db, cliente, cliente_data, cliente_id, tenant_id)

    dados_payload = cliente_data.model_dump(exclude_unset=True)
    auth_user_informado = "auth_user_id" in dados_payload
    perfis_informados = "app_access_profiles" in dados_payload
    auth_user_id = dados_payload.pop("auth_user_id", None)
    app_access_profiles = dados_payload.pop("app_access_profiles", None)
    _normalizar_campos_identidade(dados_payload)
    update_data = _preparar_dados_cliente(
        dados_payload,
        serializar_lista_vazia=True,
    )
    _garantir_entregador_padrao_unico_update(db, update_data, cliente_id, tenant_id)
    parceiro_desativado, comissoes_desativadas_count = _desativar_comissoes_se_preciso(
        db,
        cliente=cliente,
        cliente_id=cliente_id,
        update_data=update_data,
        current_user_id=current_user.id,
        tenant_id=tenant_id,
    )

    old_data = {field: getattr(cliente, field) for field in update_data.keys()}
    for field, value in update_data.items():
        setattr(cliente, field, value)

    if auth_user_informado:
        cliente.auth_user_id = _validar_conta_app(
            db,
            tenant_id=tenant_id,
            auth_user_id=auth_user_id,
            cliente_id=cliente.id,
        )
    if perfis_informados or auth_user_informado:
        perfis_para_sincronizar = app_access_profiles
        if not perfis_informados:
            perfis_para_sincronizar = [
                perfil.profile_type
                for perfil in db.query(AppAccessProfile)
                .filter(
                    AppAccessProfile.tenant_id == tenant_id,
                    AppAccessProfile.cliente_id == cliente.id,
                    AppAccessProfile.is_active.is_(True),
                )
                .all()
            ]
        sync_cliente_app_access_profiles(
            db,
            tenant_id=tenant_id,
            cliente=cliente,
            profile_types=perfis_para_sincronizar or [],
            granted_by_user_id=current_user.id,
            linked_user_id=cliente.auth_user_id,
        )

    if cliente.ativo and not cliente.codigo:
        cliente.codigo = gerar_codigo_cliente(
            db, cliente.tipo_cadastro, cliente.tipo_pessoa, tenant_id
        )

    cliente.updated_at = dt.utcnow()
    db.commit()
    db.refresh(cliente)

    log_update(db, current_user.id, "cliente", cliente.id, old_data, update_data)
    _anexar_metadados_criacao_cliente(db, cliente)

    response = _montar_resposta_update(cliente)
    if parceiro_desativado and comissoes_desativadas_count > 0:
        logger.warning(
            "%s comissao(oes) desativada(s) automaticamente para cliente %s",
            comissoes_desativadas_count,
            cliente_id,
        )
        response["aviso"] = (
            "Comissões desativadas automaticamente porque o cliente deixou de ser "
            f"parceiro. Total desativado: {comissoes_desativadas_count}"
        )
    return response


def _validar_conta_app(
    db: Session,
    *,
    tenant_id,
    auth_user_id: int | None,
    cliente_id: int | None = None,
) -> int | None:
    if auth_user_id is None:
        return None

    vinculo = (
        db.query(UserTenant)
        .join(User, User.id == UserTenant.user_id)
        .filter(
            UserTenant.tenant_id == tenant_id,
            UserTenant.user_id == auth_user_id,
            UserTenant.is_active.is_(True),
            User.tenant_id == tenant_id,
            User.is_active.is_(True),
        )
        .first()
    )
    if not vinculo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conta de acesso invalida ou inativa para esta loja.",
        )

    query = db.query(Cliente).filter(
        Cliente.tenant_id == tenant_id,
        Cliente.auth_user_id == auth_user_id,
        Cliente.ativo.is_not(False),
    )
    if cliente_id is not None:
        query = query.filter(Cliente.id != cliente_id)
    ja_vinculada = query.first()
    if ja_vinculada:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Esta conta ja esta vinculada a outra pessoa ativa: "
                f"{ja_vinculada.nome} (codigo {ja_vinculada.codigo or '-'})."
            ),
        )
    return auth_user_id


@detail_router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cliente(
    cliente_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Desativar cliente (soft delete)."""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)

    cliente.ativo = False
    cliente.updated_at = dt.utcnow()
    for pet in cliente.pets:
        pet.ativo = False
        pet.updated_at = dt.utcnow()

    db.commit()
    log_delete(
        db,
        current_user.id,
        "cliente",
        cliente.id,
        {"codigo": cliente.codigo, "nome": cliente.nome, "cpf": cliente.cpf},
    )
    return None


def _validar_documentos_unicos_criacao(
    db: Session, cliente_data: ClienteCreate, tenant_id: int
) -> None:
    if cliente_data.tipo_pessoa == "PF" and cliente_data.cpf:
        _validar_campo_unico(
            db,
            tenant_id=tenant_id,
            campo=Cliente.cpf,
            valor=cliente_data.cpf,
            detail=f"Já existe um {cliente_data.tipo_cadastro} cadastrado com este CPF",
        )
    elif cliente_data.tipo_pessoa == "PJ":
        if not cliente_data.cnpj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CNPJ é obrigatório para Pessoa Jurídica",
            )
        _validar_campo_unico(
            db,
            tenant_id=tenant_id,
            campo=Cliente.cnpj,
            valor=cliente_data.cnpj,
            detail=f"Já existe um {cliente_data.tipo_cadastro} cadastrado com este CNPJ",
        )

    if cliente_data.crmv and cliente_data.tipo_cadastro == "veterinario":
        _validar_campo_unico(
            db,
            tenant_id=tenant_id,
            campo=Cliente.crmv,
            valor=cliente_data.crmv,
            detail="Já existe um veterinário cadastrado com este CRMV",
        )


def _validar_documentos_unicos_update(
    db: Session,
    cliente: Cliente,
    cliente_data: ClienteUpdate,
    cliente_id: int,
    tenant_id: int,
) -> None:
    checks = [
        (
            cliente_data.cpf,
            cliente.cpf,
            Cliente.cpf,
            "Já existe um cliente cadastrado com este CPF",
        ),
        (
            cliente_data.cnpj,
            cliente.cnpj,
            Cliente.cnpj,
            "Já existe um cadastro com este CNPJ",
        ),
        (
            cliente_data.crmv,
            cliente.crmv,
            Cliente.crmv,
            "Já existe um veterinário cadastrado com este CRMV",
        ),
    ]
    for novo_valor, valor_atual, campo, detail in checks:
        if novo_valor and novo_valor != valor_atual:
            _validar_campo_unico(
                db,
                tenant_id=tenant_id,
                campo=campo,
                valor=novo_valor,
                detail=detail,
                cliente_id_excluir=cliente_id,
            )


def _validar_campo_unico(
    db: Session,
    *,
    tenant_id: int,
    campo,
    valor,
    detail: str,
    cliente_id_excluir: int | None = None,
) -> None:
    campo_nome = getattr(campo, "key", "")
    valor_normalizado = str(valor or "").strip()
    expressao = campo == valor_normalizado
    if campo_nome in {"cpf", "cnpj"}:
        valor_normalizado = "".join(ch for ch in valor_normalizado if ch.isdigit())
        expressao = _somente_digitos_coluna(campo) == valor_normalizado
    elif campo_nome == "crmv":
        valor_normalizado = "".join(
            ch for ch in valor_normalizado.casefold() if ch.isalnum()
        )
        expressao = (
            func.lower(
                func.replace(
                    func.replace(
                        func.replace(func.replace(campo, "-", ""), "/", ""),
                        ".",
                        "",
                    ),
                    " ",
                    "",
                )
            )
            == valor_normalizado
        )

    query = db.query(Cliente).filter(
        Cliente.tenant_id == tenant_id,
        expressao,
        Cliente.ativo.is_not(False),
    )
    if cliente_id_excluir is not None:
        query = query.filter(Cliente.id != cliente_id_excluir)
    if query.first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _preparar_dados_cliente(
    dados_cliente: dict,
    *,
    serializar_lista_vazia: bool,
) -> dict:
    enderecos = dados_cliente.get("enderecos_adicionais")
    deve_serializar = (
        enderecos is not None if serializar_lista_vazia else bool(enderecos)
    )
    if deve_serializar:
        dados_cliente["enderecos_adicionais"] = json.dumps(
            dados_cliente["enderecos_adicionais"]
        )
    return dados_cliente


def _normalizar_campos_identidade(dados_cliente: dict) -> None:
    """Grava identificadores em formato estavel para prevenir novas duplicidades."""
    for campo in ("cpf", "cnpj", "telefone", "celular", "cep"):
        if campo in dados_cliente and dados_cliente[campo] is not None:
            dados_cliente[campo] = (
                "".join(ch for ch in str(dados_cliente[campo]) if ch.isdigit()) or None
            )
    if "email" in dados_cliente and dados_cliente["email"] is not None:
        dados_cliente["email"] = str(dados_cliente["email"]).strip().casefold() or None
    if "crmv" in dados_cliente and dados_cliente["crmv"] is not None:
        dados_cliente["crmv"] = str(dados_cliente["crmv"]).strip().upper() or None


def _garantir_entregador_padrao_unico_criacao(
    db: Session, dados_cliente: dict, tenant_id: int
) -> None:
    if dados_cliente.get("entregador_padrao") is True:
        entregador_padrao_atual = _buscar_entregador_padrao(db, tenant_id)
        if entregador_padrao_atual:
            entregador_padrao_atual.entregador_padrao = False
            entregador_padrao_atual.updated_at = dt.utcnow()
            logger.info("Entregador padrao anterior removido")


def _garantir_entregador_padrao_unico_update(
    db: Session, update_data: dict, cliente_id: int, tenant_id: int
) -> None:
    if update_data.get("entregador_padrao") is True:
        entregador_padrao_atual = _buscar_entregador_padrao(
            db, tenant_id, cliente_id_excluir=cliente_id
        )
        if entregador_padrao_atual:
            entregador_padrao_atual.entregador_padrao = False
            entregador_padrao_atual.updated_at = dt.utcnow()
            logger.info("Entregador padrao anterior removido")


def _buscar_entregador_padrao(
    db: Session, tenant_id: int, cliente_id_excluir: int | None = None
):
    query = db.query(Cliente).filter(
        Cliente.tenant_id == tenant_id,
        Cliente.entregador_padrao,
        Cliente.ativo,
    )
    if cliente_id_excluir is not None:
        query = query.filter(Cliente.id != cliente_id_excluir)
    return query.first()


def _montar_query_listagem_clientes(
    db: Session,
    *,
    tenant_id: int,
    tipo_cadastro,
    is_entregador,
    search,
    ativo,
    incluir_inativos,
    visao_dashboard=None,
):
    access_ids = get_all_accessible_tenant_ids(db, tenant_id)
    query = db.query(Cliente).filter(Cliente.tenant_id.in_(access_ids))
    if tipo_cadastro:
        if isinstance(tipo_cadastro, list):
            query = query.filter(Cliente.tipo_cadastro.in_(tipo_cadastro))
        else:
            query = query.filter(Cliente.tipo_cadastro == tipo_cadastro)
    if is_entregador is not None:
        query = query.filter(Cliente.is_entregador == is_entregador)

    query = _aplicar_filtro_busca(query, search)
    if not incluir_inativos:
        query = _aplicar_filtro_ativo(query, ativo)
    if visao_dashboard == "ativos":
        query = query.filter(
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "cliente",
        )
    elif visao_dashboard == "vip_em_risco":
        query = query.join(
            ClienteSegmento,
            and_(
                ClienteSegmento.cliente_id == Cliente.id,
                ClienteSegmento.tenant_id == Cliente.tenant_id,
            ),
        ).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "cliente",
            ClienteSegmento.segmento == "VIP",
            cast(ClienteSegmento.metricas["ultima_compra_dias"].astext, Integer) > 20,
        )
    elif visao_dashboard == "inativos_90_dias":
        ultima_venda = (
            db.query(
                Venda.cliente_id.label("cliente_id"),
                func.max(Venda.data_venda).label("ultima_venda"),
            )
            .filter(Venda.tenant_id == tenant_id, Venda.status == "finalizada")
            .group_by(Venda.cliente_id)
            .subquery()
        )
        query = query.outerjoin(
            ultima_venda, ultima_venda.c.cliente_id == Cliente.id
        ).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "cliente",
            or_(
                ultima_venda.c.ultima_venda.is_(None),
                ultima_venda.c.ultima_venda < dt.utcnow() - timedelta(days=90),
            ),
        )
    elif visao_dashboard == "novos_promissores":
        query = query.join(
            ClienteSegmento,
            and_(
                ClienteSegmento.cliente_id == Cliente.id,
                ClienteSegmento.tenant_id == Cliente.tenant_id,
            ),
        ).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "cliente",
            ClienteSegmento.segmento == "Novo",
            cast(ClienteSegmento.metricas["ticket_medio"].astext, Float) > 200,
        )
    elif visao_dashboard == "sem_whatsapp":
        query = query.filter(
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "cliente",
            or_(Cliente.celular.is_(None), func.trim(Cliente.celular) == ""),
        )
    return query


def _aplicar_filtro_busca(query, search):
    termo_busca = (search or "").strip()
    if not termo_busca:
        return query

    telefone_digitos = _somente_digitos_coluna(Cliente.telefone)
    celular_digitos = _somente_digitos_coluna(Cliente.celular)
    for palavra in [p.strip() for p in termo_busca.split() if p.strip()]:
        like = f"%{palavra}%"
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
        palavra_digitos = "".join(ch for ch in palavra if ch.isdigit())
        if palavra_digitos:
            like_digitos = f"%{palavra_digitos}%"
            filtros.extend(
                [
                    telefone_digitos.ilike(like_digitos),
                    celular_digitos.ilike(like_digitos),
                ]
            )
        query = query.filter(or_(*filtros))
    return query


def _aplicar_filtro_ativo(query, ativo):
    if ativo is None:
        ativo = True
    if ativo:
        return query.filter(or_(Cliente.ativo.is_(True), Cliente.ativo.is_(None)))
    return query.filter(Cliente.ativo.is_(False))


def _ordenar_query_listagem(query, search):
    termo_busca = (search or "").strip()
    if not termo_busca:
        return query.order_by(Cliente.nome)

    termo_lower = termo_busca.lower()
    termo_digitos = "".join(ch for ch in termo_busca if ch.isdigit())
    if termo_digitos:
        return query.order_by(
            case(
                (func.lower(Cliente.codigo) == termo_lower, 1),
                (_somente_digitos_coluna(Cliente.telefone) == termo_digitos, 2),
                (_somente_digitos_coluna(Cliente.celular) == termo_digitos, 3),
                (Cliente.codigo.ilike(f"{termo_digitos}%"), 4),
                (
                    _somente_digitos_coluna(Cliente.telefone).ilike(
                        f"{termo_digitos}%"
                    ),
                    5,
                ),
                (
                    _somente_digitos_coluna(Cliente.celular).ilike(f"{termo_digitos}%"),
                    6,
                ),
                (func.lower(Cliente.nome) == termo_lower, 7),
                (Cliente.nome.ilike(f"{termo_busca}%"), 8),
                (Cliente.nome_fantasia.ilike(f"{termo_busca}%"), 9),
                (Cliente.razao_social.ilike(f"{termo_busca}%"), 10),
                else_=11,
            ),
            Cliente.nome,
        )

    return query.order_by(
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


def _marcar_clientes_de_parceiro(clientes, tenant_id: int) -> None:
    tenant_id_str = str(tenant_id)
    for cliente in clientes:
        if str(cliente.tenant_id) != tenant_id_str:
            cliente.de_parceiro = True


def _desativar_comissoes_se_preciso(
    db: Session,
    *,
    cliente: Cliente,
    cliente_id: int,
    update_data: dict,
    current_user_id: int,
    tenant_id: int,
) -> tuple[bool, int]:
    if not _parceiro_sera_desativado(cliente, update_data):
        return False, 0

    count = _contar_comissoes_ativas(db, cliente_id, tenant_id)
    if count > 0:
        _desativar_comissoes_ativas(db, cliente_id, current_user_id, tenant_id)
    return True, count


def _parceiro_sera_desativado(cliente: Cliente, update_data: dict) -> bool:
    return (
        "parceiro_ativo" in update_data
        and hasattr(cliente, "parceiro_ativo")
        and cliente.parceiro_ativo
        and not update_data["parceiro_ativo"]
    )


def _contar_comissoes_ativas(db: Session, cliente_id: int, tenant_id: int) -> int:
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
    return result.fetchone()[0]


def _desativar_comissoes_ativas(
    db: Session, cliente_id: int, current_user_id: int, tenant_id: int
) -> None:
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
        {"funcionario_id": cliente_id, "usuario_id": current_user_id},
        tenant_id=tenant_id,
    )


def _montar_resposta_update(cliente: Cliente) -> dict:
    return {
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
        "auth_user_id": getattr(cliente, "auth_user_id", None),
        "auth_user_nome": getattr(cliente, "auth_user_nome", None),
        "auth_user_email": getattr(cliente, "auth_user_email", None),
        "app_access_profiles": getattr(cliente, "app_access_profiles", []),
    }


router.include_router(base_router)
router.include_router(detail_router)
