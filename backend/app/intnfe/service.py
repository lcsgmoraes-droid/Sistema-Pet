"""Criar, reconciliar e comprovar acesso ao emitente sem emitir documentos."""

from datetime import datetime, timezone

from app.intnfe.client import IntNFeError
from app.intnfe.presentation import certificate_state, normalize_cnpj
from app.intnfe.repository import ActivationError, reserve, save
from app.security.tenant_config_crypto import SecretDecryptionError, encrypt_secret


def _find(api, token, cnpj):
    matches = [
        row
        for row in api.list_emitters(token)
        if normalize_cnpj(row.get("cnpj")) == cnpj
    ]
    if len(matches) > 1:
        raise IntNFeError("CadastroAmbiguo")
    if not matches:
        return None
    row = matches[0]
    if row.get("integradorId") != api.integrador_id or any(
        not isinstance(row.get(key), str) or not 1 <= len(row[key]) <= 128
        for key in ("tenantId", "clientId")
    ):
        raise IntNFeError("RespostaInvalida")
    return row


def _check_certificate(db, tenant_id, operation, connection, api):
    token = api.emitter_token(connection.client_id, connection.client_secret)
    state, expires = certificate_state(api.certificate(token), connection.cnpj)
    return save(
        db,
        tenant_id,
        operation,
        finish=True,
        status=state,
        certificado_valido_ate=expires,
    )


def _record_error(db, tenant_id, operation, exc, *, posting=False):
    values = {"ultimo_codigo": exc.code, "correlation_id": exc.correlation}
    if exc.uncertain:
        state = "conciliacao_pendente"
    elif exc.code == "EmitenteDuplicado":
        state = "cnpj_em_uso"
    elif exc.code == "AcessoIntegradorInvalido":
        state = "acesso_integrador_invalido"
    elif exc.code in {"CredenciaisInvalidas", "AcessoNegado"}:
        state = "credenciais_invalidas"
    else:
        state = "falha"
    if posting and not exc.uncertain:
        values["criacao_iniciada"] = False
    return save(db, tenant_id, operation, finish=True, status=state, **values)


def activate(db, tenant_id, api, *, consult_only=False):
    connection, operation, previous_status = reserve(db, tenant_id, api.integrador_id)
    posting = False
    try:
        token = api.integrator_token()
        existing = _find(api, token, connection.cnpj)
        if existing:
            if existing.get("ativo") is not True:
                return save(
                    db, tenant_id, operation, finish=True, status="emitente_inativo"
                )
            if connection.client_secret_encrypted:
                if (existing["tenantId"], existing["clientId"]) != (
                    connection.emitente_id,
                    connection.client_id,
                ):
                    return save(
                        db,
                        tenant_id,
                        operation,
                        finish=True,
                        status="vinculo_inconsistente",
                    )
                return _check_certificate(db, tenant_id, operation, connection, api)
            # CNPJ publico nao comprova posse. Nunca rotacionar segredo automaticamente.
            return save(
                db, tenant_id, operation, finish=True, status="credenciais_pendentes"
            )
        if connection.client_secret_encrypted:
            return save(
                db, tenant_id, operation, finish=True, status="vinculo_inconsistente"
            )
        if connection.criacao_iniciada:
            return save(
                db, tenant_id, operation, finish=True, status="conciliacao_pendente"
            )
        if consult_only:
            state = (
                "cnpj_em_uso" if previous_status == "cnpj_em_uso" else "nao_vinculado"
            )
            return save(db, tenant_id, operation, finish=True, status=state)
        connection = save(db, tenant_id, operation, criacao_iniciada=True)
        posting = True
        created = api.create_emitter(
            token,
            {
                "cnpj": connection.cnpj,
                "razaoSocial": connection.razao_social,
                "nomeFantasia": connection.nome_fantasia,
            },
        )
        # Persistir o segredo imediatamente, antes de autenticar/consultar certificado.
        connection = save(
            db,
            tenant_id,
            operation,
            status="vinculado",
            emitente_id=created["tenantId"],
            client_id=created["clientId"],
            client_secret_encrypted=encrypt_secret(created["clientSecret"]),
            vinculado_em=datetime.now(timezone.utc),
        )
        posting = False
        return _check_certificate(db, tenant_id, operation, connection, api)
    except IntNFeError as exc:
        return _record_error(db, tenant_id, operation, exc, posting=posting)
    except SecretDecryptionError:
        return _record_error(
            db, tenant_id, operation, IntNFeError("CredenciaisIlegiveis")
        )


def bind_existing(db, tenant_id, api, client_id, client_secret):
    client_id, client_secret = client_id.strip(), client_secret.strip()
    if not 1 <= len(client_id) <= 128 or not 1 <= len(client_secret) <= 4096:
        raise ActivationError("Informe os dois códigos do emitente.", 422)
    connection, operation, _previous = reserve(db, tenant_id, api.integrador_id)
    try:
        existing = _find(api, api.integrator_token(), connection.cnpj)
        if not existing or existing["clientId"] != client_id:
            return _record_error(
                db, tenant_id, operation, IntNFeError("CredenciaisInvalidas")
            )
        if connection.emitente_id and connection.emitente_id != existing["tenantId"]:
            return save(
                db, tenant_id, operation, finish=True, status="vinculo_inconsistente"
            )
        if existing.get("ativo") is not True:
            return save(
                db, tenant_id, operation, finish=True, status="emitente_inativo"
            )
        token = api.emitter_token(client_id, client_secret)
        certificate = api.certificate(token)
        if certificate and normalize_cnpj(certificate.get("cnpj")) != connection.cnpj:
            return save(
                db, tenant_id, operation, finish=True, status="vinculo_inconsistente"
            )
        state, expires = certificate_state(certificate, connection.cnpj)
        return save(
            db,
            tenant_id,
            operation,
            finish=True,
            status=state,
            emitente_id=existing["tenantId"],
            client_id=client_id,
            client_secret_encrypted=encrypt_secret(client_secret),
            vinculado_em=datetime.now(timezone.utc),
            certificado_valido_ate=expires,
        )
    except IntNFeError as exc:
        return _record_error(db, tenant_id, operation, exc)
