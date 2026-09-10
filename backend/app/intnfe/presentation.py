"""Validacao do cadastro de origem e respostas publicas sem credenciais."""

import re
from datetime import datetime, timezone

from app.intnfe.client import IntNFeError, available


MESSAGES = {
    "nao_vinculado": "Ative para preparar o vínculo fiscal desta empresa.",
    "processando": "Estamos verificando o vínculo com o emissor.",
    "cnpj_em_uso": "O emissor informou que este CNPJ já está cadastrado. Consulte novamente após o suporte conferir o vínculo.",
    "credenciais_pendentes": "Encontramos um cadastro para este CNPJ. Informe as credenciais desse emitente para comprovar o acesso e concluir o vínculo.",
    "conciliacao_pendente": "O envio do cadastro ficou sem confirmação. Vamos consultar o resultado antes de tentar criar outro cadastro.",
    "certificado_pendente": "Vínculo criado. Falta cadastrar um certificado A1 válido no emissor.",
    "certificado_invalido": "Vínculo criado. Confira o CNPJ e a validade do certificado A1 no emissor.",
    "certificado_validado": "Vínculo e certificado conferidos. A próxima etapa é homologar a emissão de uma nota.",
    "vinculado": "Vínculo salvo. Consulte para verificar o certificado no emissor.",
    "emitente_inativo": "O cadastro está desativado no emissor. Solicite a regularização ao suporte.",
    "vinculo_inconsistente": "O cadastro no emissor mudou ou não está mais acessível. Solicite a revisão do vínculo ao suporte.",
    "falha": "Não foi possível concluir a verificação. Tente novamente ou acione o suporte.",
    "credenciais_invalidas": "As credenciais do emitente não foram aceitas. Confira os códigos fornecidos pelo emissor.",
    "acesso_integrador_invalido": "O acesso do CorePet ao emissor precisa ser revisado pelo suporte.",
    "cnpj_alterado": "O CNPJ da empresa mudou após o início da ativação. Solicite a revisão do vínculo ao suporte.",
    "integrador_alterado": "A conta do emissor foi alterada. O suporte precisa revisar o vínculo existente.",
    "indisponivel": "A ativação de notas ainda não foi liberada para este ambiente. Entre em contato com o suporte.",
    "dados_pendentes": "Complete os dados da empresa antes de ativar as notas.",
}


def normalize_cnpj(value):
    return re.sub(r"[.\s/-]", "", str(value or ""))


def valid_cnpj(value):
    if not re.fullmatch(r"[0-9]{14}", value) or len(set(value)) == 1:
        return False
    digits = [int(digit) for digit in value]
    for size, weights in (
        (12, (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)),
        (13, (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)),
    ):
        remainder = sum(a * b for a, b in zip(digits[:size], weights)) % 11
        if digits[size] != (0 if remainder < 2 else 11 - remainder):
            return False
    return True


def company_data(tenant):
    return {
        "cnpj": normalize_cnpj(tenant.cnpj),
        "razaoSocial": str(tenant.razao_social or "").strip(),
        "nomeFantasia": str(tenant.name or "").strip(),
    }


def company_pending(tenant):
    data = company_data(tenant)
    pending = []
    if not valid_cnpj(data["cnpj"]):
        pending.append("Informe um CNPJ numérico válido nos dados da empresa.")
    for field, label in (
        ("razaoSocial", "razão social"),
        ("nomeFantasia", "nome fantasia"),
    ):
        if not 1 <= len(data[field]) <= 60:
            pending.append(
                f"Informe {label} com até 60 caracteres nos dados da empresa."
            )
    return pending


def utc(value):
    return (
        value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value
    )


def certificate_state(certificate, cnpj):
    if certificate is None:
        return "certificado_pendente", None
    try:
        end = utc(
            datetime.fromisoformat(str(certificate["validoAte"]).replace("Z", "+00:00"))
        )
        start = utc(
            datetime.fromisoformat(str(certificate["validoDe"]).replace("Z", "+00:00"))
        )
    except (KeyError, ValueError, TypeError):
        raise IntNFeError("RespostaInvalida") from None
    now = datetime.now(timezone.utc)
    valid = (
        normalize_cnpj(certificate.get("cnpj")) == cnpj
        and not certificate.get("expirado", False)
        and start <= now < end
    )
    return ("certificado_validado" if valid else "certificado_invalido"), end


def public_status(tenant, connection, integrador_id):
    pending = company_pending(tenant)
    state = connection.status if connection else "nao_vinculado"
    if connection and connection.cnpj != normalize_cnpj(tenant.cnpj):
        state = "cnpj_alterado"
    elif connection and connection.integrador_id != integrador_id:
        state = "integrador_alterado"
    elif pending:
        state = "dados_pendentes"
    enabled = available()
    if not enabled:
        state = "indisponivel"
    linked = bool(
        connection and connection.client_secret_encrypted and connection.emitente_id
    )
    blocked = state in {
        "cnpj_alterado",
        "integrador_alterado",
        "dados_pendentes",
        "indisponivel",
    }
    busy = bool(
        connection
        and connection.operacao_id
        and utc(connection.operacao_iniciada_em)
        and (
            datetime.now(timezone.utc) - utc(connection.operacao_iniciada_em)
        ).total_seconds()
        < 120
    )
    return {
        "status": state,
        "mensagem": MESSAGES.get(state, MESSAGES["falha"]),
        "empresa": {
            "cnpj": tenant.cnpj,
            "razao_social": tenant.razao_social,
            "nome_fantasia": tenant.name,
        },
        "pendencias": pending,
        "vinculado": linked,
        "ambiente": "homologacao",
        "emissao_disponivel": False,
        "pode_ativar": not blocked
        and not busy
        and not linked
        and state
        in {"nao_vinculado", "cnpj_em_uso", "falha", "acesso_integrador_invalido"},
        "pode_consultar": not blocked and not busy and bool(connection),
        "pode_vincular": not blocked
        and not busy
        and state in {"credenciais_pendentes", "credenciais_invalidas"},
        "certificado_valido_ate": connection.certificado_valido_ate
        if connection
        else None,
        "codigo": connection.ultimo_codigo if connection else None,
        "protocolo_suporte": connection.correlation_id if connection else None,
    }
