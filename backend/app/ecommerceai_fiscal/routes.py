"""Fronteiras distintas de máquina e operador, sempre com tenant autenticado."""

from fastapi import APIRouter, Depends, Header, Response, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from app.auth.dependencies import get_current_user_and_tenant
from app.audit_log import log_action
from app.db import get_session
from app.ecommerceai_fiscal import service
from app.ecommerceai_fiscal import configuration
from app.ecommerceai_fiscal.models import (
    FiscalAccount,
    FiscalSkuMapping,
    ExternalFiscalOrder,
)
from app.ecommerceai_fiscal.schemas import (
    AccountInput,
    MappingInput,
    OrderInput,
    IssueInput,
    ReviewInput,
)
from app.intnfe.client import IntNFeClient, IntNFeError
from app.intnfe.emission import _connection, _access_token, DirectEmissionError
from app.intnfe.repository import get_tenant
from app.intnfe.presentation import normalize_cnpj, valid_cnpj
from app.produtos_models import Produto
from app.routes.ecommerceai_integration_routes import (
    _connection_for_token,
    _require_scope,
)
from app.security.permissions_service import check_permission

router = APIRouter(
    prefix="/integracoes/ecommerceai/fiscal", tags=["EcommerceAI fiscal"]
)


def api_client():
    try:
        api = IntNFeClient()
    except IntNFeError:
        service.fail(
            "emitter_not_configured",
            "A integração fiscal ainda não foi configurada.",
            503,
        )
    try:
        yield api
    finally:
        api.close()


def machine_connection(
    authorization: str | None = Header(default=None), db: Session = Depends(get_session)
):
    connection = _connection_for_token(db, authorization)
    tenant = get_tenant(db, connection.tenant_id)
    if str(tenant.status).lower() not in {"active", "ativo"}:
        service.fail(
            "tenant_inactive", "Empresa indisponível para esta integração.", 403
        )
    return connection


def scoped(scope):
    def dependency(connection=Depends(machine_connection)):
        _require_scope(connection, scope)
        return connection

    return dependency


preparer_connection = scoped("fiscal:prepare")
issuer_connection = scoped("fiscal:issue")
reader_connection = scoped("fiscal:read")


def reader(
    db: Session = Depends(get_session), pair=Depends(get_current_user_and_tenant)
):
    user, tenant = pair
    check_permission(db, user.id, "vendas.visualizar", tenant, current_user=user)
    return pair


def manager(
    db: Session = Depends(get_session), pair=Depends(get_current_user_and_tenant)
):
    user, tenant = pair
    check_permission(db, user.id, "configuracoes.editar", tenant, current_user=user)
    return pair


def run(db, operation):
    try:
        return operation()
    except SQLAlchemyError:
        db.rollback()
        service.fail(
            "fiscal_storage_unavailable",
            "Não foi possível preservar o processamento fiscal. Consulte o estado antes de repetir.",
            503,
        )
    except (IntNFeError, DirectEmissionError):
        service.fail(
            "emitter_unavailable",
            "O emissor está indisponível. O pedido e seu envio foram preservados.",
            503,
        )


def account_view(row, db=None):
    result = configuration.public_account(row)
    if db is not None:
        result["configuration_revision"] = configuration.account_revision(db, row)
    return result


def get_account(db, tenant_id, account_id, *, lock=False):
    query = db.query(FiscalAccount).filter(
        FiscalAccount.tenant_id == tenant_id, FiscalAccount.id == account_id
    )
    row = query.with_for_update().populate_existing().first() if lock else query.first()
    if row is None:
        service.fail("not_found", "Conta fiscal não encontrada nesta empresa.", 404)
    return row


def save_account(db, tenant_id, user_id, body, account_id=None):
    tenant = get_tenant(db, tenant_id)
    if not valid_cnpj(body.emitter_cnpj) or body.emitter_cnpj != normalize_cnpj(
        tenant.cnpj
    ):
        service.fail(
            "emitter_mismatch",
            "Confira o CNPJ da empresa antes de autorizar a conta.",
            422,
        )
    if not body.seller_id.strip() or body.seller_id != body.seller_id.strip():
        service.fail(
            "seller_invalid", "Informe o Seller ID exato da conta Amazon.", 422
        )
    if (body.auto_issue_enabled or body.upload_enabled) and not body.active:
        service.fail(
            "account_invalid",
            "Ative o fluxo antes de autorizar emissão ou upload automático.",
            422,
        )
    row = (
        get_account(db, tenant_id, account_id, lock=True)
        if account_id
        else FiscalAccount(tenant_id=tenant_id)
    )
    if account_id and (row.channel != body.channel or row.seller_id != body.seller_id):
        service.fail(
            "account_identity_frozen",
            "Canal e Seller ID são identidades permanentes.",
            409,
        )
    previous = account_view(row) if account_id else {}
    if (body.active and not row.active) or (
        body.auto_issue_enabled and not row.auto_issue_enabled
    ):
        row.activated_at = service.now()
    row.configuration_version = int(row.configuration_version or 0) + 1
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    row.approved_by_user_id = user_id
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        service.fail(
            "account_exists", "Esta conta Amazon já está configurada nesta empresa."
        )
    log_action(
        db,
        user_id,
        "eai_fiscal_account_save",
        "eai_fiscal_account",
        row.id,
        tenant_id=tenant_id,
        old_value=jsonable_encoder(previous),
        new_value=jsonable_encoder(account_view(row)),
        commit=False,
    )
    db.commit()
    return account_view(row, db)


def mapping_view(db, row):
    product = (
        db.query(Produto)
        .filter(Produto.tenant_id == row.tenant_id, Produto.id == row.product_id)
        .first()
    )
    return {
        "id": row.id,
        "account_id": row.account_id,
        "seller_sku": row.seller_sku,
        "product_id": row.product_id,
        "active": row.active,
        "product_name": product.nome if product else None,
        "product_sku": product.codigo if product else None,
    }


@router.get("/manage/accounts")
def accounts(db: Session = Depends(get_session), pair=Depends(reader)):
    return {
        "items": [
            account_view(row, db)
            for row in db.query(FiscalAccount)
            .filter(FiscalAccount.tenant_id == pair[1])
            .order_by(FiscalAccount.id)
            .all()
        ]
    }


@router.post("/manage/accounts")
def create_account(
    body: AccountInput, db: Session = Depends(get_session), pair=Depends(manager)
):
    return run(db, lambda: save_account(db, pair[1], pair[0].id, body))


@router.put("/manage/accounts/{account_id}")
def update_account(
    account_id: int,
    body: AccountInput,
    db: Session = Depends(get_session),
    pair=Depends(manager),
):
    return run(db, lambda: save_account(db, pair[1], pair[0].id, body, account_id))


@router.get("/manage/products")
def products(
    q: str = Query(default="", max_length=100),
    db: Session = Depends(get_session),
    pair=Depends(reader),
):
    query = db.query(Produto).filter(
        Produto.tenant_id == pair[1], Produto.deleted_at.is_(None)
    )
    if q:
        query = query.filter(
            (Produto.nome.ilike("%" + q + "%")) | (Produto.codigo.ilike("%" + q + "%"))
        )
    return {
        "items": [
            {
                "id": p.id,
                "sku": p.codigo,
                "name": p.nome,
                "product_type": p.tipo_produto,
            }
            for p in query.order_by(Produto.nome, Produto.id).limit(50).all()
        ]
    }


@router.get("/manage/mappings")
def mappings(
    account_id: int | None = None,
    db: Session = Depends(get_session),
    pair=Depends(reader),
):
    query = db.query(FiscalSkuMapping).filter(FiscalSkuMapping.tenant_id == pair[1])
    if account_id:
        get_account(db, pair[1], account_id)
        query = query.filter(FiscalSkuMapping.account_id == account_id)
    return {
        "items": [
            mapping_view(db, row) for row in query.order_by(FiscalSkuMapping.id).all()
        ]
    }


def save_mapping(db, pair, body, mapping_id=None):
    tenant_id = pair[1]
    account = get_account(db, tenant_id, body.account_id, lock=True)
    if body.seller_sku != body.seller_sku.strip() or not body.seller_sku.strip():
        service.fail("sku_invalid", "Informe o SKU exato, sem espaços adicionais.", 422)
    product = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.id == body.product_id,
            Produto.deleted_at.is_(None),
        )
        .first()
    )
    if not product:
        service.fail("product_not_found", "Produto não encontrado nesta empresa.", 404)
    row = (
        db.query(FiscalSkuMapping)
        .filter(
            FiscalSkuMapping.tenant_id == tenant_id, FiscalSkuMapping.id == mapping_id
        )
        .with_for_update()
        .first()
        if mapping_id
        else FiscalSkuMapping(tenant_id=tenant_id)
    )
    if row is None:
        service.fail("not_found", "Mapeamento não encontrado nesta empresa.", 404)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    row.approved_by_user_id = pair[0].id
    account.configuration_version = int(account.configuration_version or 0) + 1
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        service.fail(
            "mapping_exists", "Já existe um vínculo para este SKU nesta conta."
        )
    log_action(
        db,
        pair[0].id,
        "eai_fiscal_mapping_save",
        "eai_fiscal_mapping",
        row.id,
        tenant_id=tenant_id,
        new_value=body.model_dump(),
        commit=False,
    )
    db.commit()
    return mapping_view(db, row)


@router.post("/manage/mappings")
def create_mapping(
    body: MappingInput, db: Session = Depends(get_session), pair=Depends(manager)
):
    return run(db, lambda: save_mapping(db, pair, body))


@router.put("/manage/mappings/{mapping_id}")
def update_mapping(
    mapping_id: int,
    body: MappingInput,
    db: Session = Depends(get_session),
    pair=Depends(manager),
):
    return run(db, lambda: save_mapping(db, pair, body, mapping_id))


@router.get("/manage/orders")
def orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    status: str | None = None,
    seller_id: str | None = None,
    db: Session = Depends(get_session),
    pair=Depends(reader),
):
    query = db.query(ExternalFiscalOrder).filter(
        ExternalFiscalOrder.tenant_id == pair[1]
    )
    if status:
        query = query.filter(ExternalFiscalOrder.status == status)
    if seller_id:
        query = query.filter(ExternalFiscalOrder.seller_id == seller_id)
    total = query.count()
    rows = (
        query.order_by(ExternalFiscalOrder.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [service.view(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/manage/orders/{order_id}")
def order_detail(
    order_id: int, db: Session = Depends(get_session), pair=Depends(reader)
):
    return service.view(service.get_order(db, pair[1], order_id), details=True)


@router.post("/manage/orders/{order_id}/review")
def review_order(
    order_id: int,
    body: ReviewInput,
    db: Session = Depends(get_session),
    pair=Depends(manager),
):
    return run(db, lambda: service.review(db, pair[1], order_id, pair[0].id))


@router.post("/manage/orders/{order_id}/emitir")
def human_issue(
    order_id: int,
    body: IssueInput,
    db: Session = Depends(get_session),
    pair=Depends(manager),
    api=Depends(api_client),
):
    return run(
        db,
        lambda: service.issue(
            db,
            pair[1],
            order_id,
            body.expected_revision,
            body.expected_payload_hash,
            api,
            machine=False,
            user_id=pair[0].id,
        ),
    )


@router.post("/manage/orders/{order_id}/consultar")
def human_consult(
    order_id: int,
    db: Session = Depends(get_session),
    pair=Depends(reader),
    api=Depends(api_client),
):
    return run(db, lambda: service.consult(db, pair[1], order_id, api))


def xml_response(db, tenant_id, order_id):
    row, content = service.xml_document(db, tenant_id, order_id)
    return Response(
        content,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="NF-{row.numero}.xml"'},
    )


def danfe_response(db, tenant_id, order_id, api):
    row, _content = service.xml_document(db, tenant_id, order_id)
    connection = _connection(db, tenant_id, require_enabled=False)
    content = api.document_danfe(
        _access_token(api, connection, row.payload["ambienteCodigo"]),
        "nfe",
        row.correlation_id,
    )
    if not content.startswith(b"%PDF-"):
        service.fail(
            "danfe_invalid", "O emissor não disponibilizou um PDF válido.", 502
        )
    return Response(
        content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="NF-{row.numero}.pdf"'},
    )


@router.get("/manage/orders/{order_id}/xml")
def human_xml(order_id: int, db: Session = Depends(get_session), pair=Depends(reader)):
    return run(db, lambda: xml_response(db, pair[1], order_id))


@router.get("/manage/orders/{order_id}/danfe")
def human_danfe(
    order_id: int,
    db: Session = Depends(get_session),
    pair=Depends(reader),
    api=Depends(api_client),
):
    return run(db, lambda: danfe_response(db, pair[1], order_id, api))


@router.get("/configuration/accounts")
def machine_configuration(
    db: Session = Depends(get_session), connection=Depends(reader_connection)
):
    return run(
        db, lambda: configuration.configuration_accounts(db, connection.tenant_id)
    )


@router.post("/orders")
def prepare_order(
    body: OrderInput,
    db: Session = Depends(get_session),
    connection=Depends(preparer_connection),
):
    _require_scope(connection, "fiscal:prepare")
    return run(db, lambda: service.upsert(db, connection, body.model_dump(mode="json")))


@router.get("/orders/{order_id}")
def machine_detail(
    order_id: int,
    db: Session = Depends(get_session),
    connection=Depends(reader_connection),
):
    _require_scope(connection, "fiscal:read")
    return service.view(service.get_order(db, connection.tenant_id, order_id))


@router.post("/orders/{order_id}/emitir")
def machine_issue(
    order_id: int,
    body: IssueInput,
    db: Session = Depends(get_session),
    connection=Depends(issuer_connection),
    api=Depends(api_client),
):
    _require_scope(connection, "fiscal:issue")
    return run(
        db,
        lambda: service.issue(
            db,
            connection.tenant_id,
            order_id,
            body.expected_revision,
            body.expected_payload_hash,
            api,
        ),
    )


@router.post("/orders/{order_id}/consultar")
def machine_consult(
    order_id: int,
    db: Session = Depends(get_session),
    connection=Depends(reader_connection),
    api=Depends(api_client),
):
    _require_scope(connection, "fiscal:read")
    return run(db, lambda: service.consult(db, connection.tenant_id, order_id, api))


@router.get("/orders/{order_id}/xml")
def machine_xml(
    order_id: int,
    db: Session = Depends(get_session),
    connection=Depends(reader_connection),
):
    _require_scope(connection, "fiscal:read")
    return run(db, lambda: xml_response(db, connection.tenant_id, order_id))


@router.get("/orders/{order_id}/danfe")
def machine_danfe(
    order_id: int,
    db: Session = Depends(get_session),
    connection=Depends(reader_connection),
    api=Depends(api_client),
):
    _require_scope(connection, "fiscal:read")
    return run(db, lambda: danfe_response(db, connection.tenant_id, order_id, api))
