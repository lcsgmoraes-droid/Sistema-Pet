"""Reserva duravel e exclusao mutua entre requisicoes de ativacao."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from app.intnfe.models import IntNFeConnection
from app.intnfe.presentation import company_data, company_pending, normalize_cnpj, utc
from app.models import Tenant
from app.security.tenant_config_crypto import encrypt_secret


class ActivationError(Exception):
    def __init__(self, message, status=409):
        super().__init__(message)
        self.status = status


def get_tenant(db, tenant_id, *, lock=False):
    query = db.query(Tenant).filter(Tenant.id == str(tenant_id))
    tenant = (query.with_for_update() if lock else query).first()
    if tenant is None:
        raise ActivationError("Empresa não encontrada.", 404)
    return tenant


def get_connection(db, tenant_id):
    return (
        db.query(IntNFeConnection)
        .filter(IntNFeConnection.tenant_id == UUID(str(tenant_id)))
        .first()
    )


def reserve(db, tenant_id, integrador_id):
    # A linha da empresa existe antes da conexao; serializa tambem a 1a ativacao.
    tenant = get_tenant(db, tenant_id, lock=True)
    pending = company_pending(tenant)
    if pending:
        db.rollback()
        raise ActivationError(
            "Complete os dados cadastrais da empresa antes de ativar.", 422
        )
    connection = get_connection(db, tenant_id)
    if connection and connection.cnpj != normalize_cnpj(tenant.cnpj):
        db.rollback()
        raise ActivationError("O CNPJ mudou. Solicite a revisão do vínculo ao suporte.")
    if connection and connection.integrador_id != integrador_id:
        db.rollback()
        raise ActivationError(
            "A conta do emissor mudou. Solicite a revisão ao suporte."
        )
    now = datetime.now(timezone.utc)
    if connection and connection.operacao_id and connection.operacao_iniciada_em:
        if (now - utc(connection.operacao_iniciada_em)).total_seconds() < 120:
            db.rollback()
            raise ActivationError(
                "Já existe uma verificação em andamento. Aguarde e consulte novamente."
            )
    # Detectar falha na chave mestra ANTES de criar algo que retorna segredo uma vez.
    try:
        encrypt_secret("intnfe-preflight")
    except (RuntimeError, ValueError):
        db.rollback()
        raise ActivationError(
            "O armazenamento seguro precisa ser configurado pelo suporte.", 503
        ) from None
    if connection is None:
        company = company_data(tenant)
        connection = IntNFeConnection(
            tenant_id=UUID(str(tenant_id)),
            cnpj=company["cnpj"],
            razao_social=company["razaoSocial"],
            nome_fantasia=company["nomeFantasia"],
            integrador_id=integrador_id,
            criacao_iniciada=False,
        )
        db.add(connection)
    elif not connection.criacao_iniciada and not connection.client_secret_encrypted:
        # Uma recusa confirmada permite corrigir os nomes antes da nova tentativa.
        company = company_data(tenant)
        connection.razao_social = company["razaoSocial"]
        connection.nome_fantasia = company["nomeFantasia"]
    previous_status = connection.status
    connection.operacao_id = str(uuid4())
    connection.operacao_iniciada_em = now
    connection.status = "processando"
    connection.ultimo_codigo = None
    connection.correlation_id = None
    operation_id = connection.operacao_id
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # A unicidade global impede que outro tenant reivindique o mesmo CNPJ.
        raise ActivationError(
            "Este CNPJ já possui uma solicitação de vínculo no CorePet. Solicite revisão ao suporte."
        ) from None
    return connection, operation_id, previous_status


def save(db, tenant_id, operation_id, *, finish=False, **values):
    if finish:
        values["operacao_id"] = None
    values["updated_at"] = datetime.now(timezone.utc)
    affected = (
        db.query(IntNFeConnection)
        .filter(
            IntNFeConnection.tenant_id == UUID(str(tenant_id)),
            IntNFeConnection.operacao_id == operation_id,
        )
        .update(values, synchronize_session=False)
    )
    if affected != 1:
        db.rollback()
        raise ActivationError(
            "Esta verificação foi substituída. Consulte a situação atual."
        )
    db.commit()
    db.expire_all()
    return get_connection(db, tenant_id)
