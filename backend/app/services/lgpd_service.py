import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.lgpd_models import DataSubjectRequest
from app.whatsapp.security import DataAccessLog, DataDeletionRequest, DataPrivacyConsent


DEFAULT_REQUEST_DUE_DAYS = 15

PREFERENCE_TYPES = (
    "marketing_email",
    "marketing_whatsapp",
    "marketing_sms",
    "marketing_push",
    "analytics",
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _json_dump(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=_json_default)


def _json_load(value: str | None, fallback: Any = None) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return None


def _num(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except Exception:
        return None


class PrivacyOpsService:
    """General LGPD operations used by ERP, ecommerce and app clients."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = str(tenant_id)

    def record_consent(
        self,
        *,
        subject_type: str,
        subject_id: str,
        consent_type: str,
        consent_given: bool,
        consent_text: str,
        phone_number: str | None = None,
        email: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        revoke_previous: bool = True,
    ) -> DataPrivacyConsent:
        now = utcnow()
        if revoke_previous:
            previous = (
                self.db.query(DataPrivacyConsent)
                .filter(
                    DataPrivacyConsent.tenant_id == self.tenant_id,
                    DataPrivacyConsent.subject_type == subject_type,
                    DataPrivacyConsent.subject_id == str(subject_id),
                    DataPrivacyConsent.consent_type == consent_type,
                    DataPrivacyConsent.revoked_at.is_(None),
                )
                .all()
            )
            for item in previous:
                item.revoked_at = now
                item.revoke_reason = "substituido_por_novo_registro"

        consent = DataPrivacyConsent(
            tenant_id=self.tenant_id,
            subject_type=subject_type,
            subject_id=str(subject_id),
            phone_number=phone_number,
            email=email,
            consent_type=consent_type,
            consent_given=bool(consent_given),
            consent_text=consent_text,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now,
            updated_at=now,
        )
        self.db.add(consent)
        self.db.flush()
        return consent

    def set_customer_preferences(
        self,
        *,
        cliente,
        preferences: dict[str, bool],
        actor_user_id: int | None,
        ip_address: str | None,
        user_agent: str | None,
        source: str,
    ) -> list[DataPrivacyConsent]:
        created: list[DataPrivacyConsent] = []
        for key in PREFERENCE_TYPES:
            if key not in preferences or preferences[key] is None:
                continue
            label = "autorizado" if preferences[key] else "revogado"
            consent = self.record_consent(
                subject_type="customer",
                subject_id=str(cliente.id),
                consent_type=key,
                consent_given=bool(preferences[key]),
                consent_text=f"Preferencia {key} {label} via {source}.",
                phone_number=getattr(cliente, "telefone", None) or getattr(cliente, "celular", None),
                email=getattr(cliente, "email", None),
                ip_address=ip_address,
                user_agent=user_agent,
            )
            created.append(consent)

        if created:
            self.log_data_access(
                subject_type="customer",
                subject_id=str(cliente.id),
                access_type="write",
                resource_type="privacy_preferences",
                resource_id=str(cliente.id),
                accessed_by_user_id=actor_user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                justification="Atualizacao de preferencias LGPD",
            )
        return created

    def current_preferences(self, subject_type: str, subject_id: str) -> dict[str, Any]:
        result = {
            key: {
                "enabled": False,
                "defined": False,
                "updated_at": None,
                "source_text": None,
            }
            for key in PREFERENCE_TYPES
        }
        rows = (
            self.db.query(DataPrivacyConsent)
            .filter(
                DataPrivacyConsent.tenant_id == self.tenant_id,
                DataPrivacyConsent.subject_type == subject_type,
                DataPrivacyConsent.subject_id == str(subject_id),
                DataPrivacyConsent.consent_type.in_(PREFERENCE_TYPES),
            )
            .order_by(DataPrivacyConsent.created_at.desc(), DataPrivacyConsent.id.desc())
            .all()
        )
        seen: set[str] = set()
        for row in rows:
            if row.consent_type in seen:
                continue
            seen.add(row.consent_type)
            result[row.consent_type] = {
                "enabled": bool(row.consent_given) and row.revoked_at is None,
                "defined": True,
                "updated_at": _iso(row.created_at),
                "source_text": row.consent_text,
            }
        return result

    def consent_history(self, subject_type: str, subject_id: str, limit: int = 100) -> list[dict[str, Any]]:
        rows = (
            self.db.query(DataPrivacyConsent)
            .filter(
                DataPrivacyConsent.tenant_id == self.tenant_id,
                DataPrivacyConsent.subject_type == subject_type,
                DataPrivacyConsent.subject_id == str(subject_id),
            )
            .order_by(DataPrivacyConsent.created_at.desc(), DataPrivacyConsent.id.desc())
            .limit(max(1, min(limit, 500)))
            .all()
        )
        return [self._serialize_consent(row) for row in rows]

    def create_subject_request(
        self,
        *,
        subject_type: str,
        subject_id: str,
        request_type: str,
        details: str | None,
        requester_name: str | None,
        requester_email: str | None,
        requester_phone: str | None,
        channel: str,
        payload: dict[str, Any] | None,
        created_by_user_id: int | None,
        ip_address: str | None,
        user_agent: str | None,
    ) -> DataSubjectRequest:
        now = utcnow()
        subject_request = DataSubjectRequest(
            tenant_id=self.tenant_id,
            subject_type=subject_type,
            subject_id=str(subject_id),
            request_type=request_type,
            status="pending",
            requester_name=requester_name,
            requester_email=requester_email,
            requester_phone=requester_phone,
            channel=channel,
            details=details,
            request_payload=_json_dump(payload),
            created_by_user_id=created_by_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            due_at=now + timedelta(days=DEFAULT_REQUEST_DUE_DAYS),
            created_at=now,
            updated_at=now,
        )
        self.db.add(subject_request)
        self.db.flush()

        if request_type == "deletion":
            legacy = DataDeletionRequest(
                tenant_id=self.tenant_id,
                subject_type=subject_type,
                subject_id=str(subject_id),
                request_date=now,
                reason=details,
                status="pending",
                contact_phone=requester_phone,
                contact_email=requester_email,
                extra_metadata=_json_dump({"data_subject_request_id": subject_request.id}),
            )
            self.db.add(legacy)
            self.db.flush()
            subject_request.response_payload = _json_dump({"legacy_deletion_request_id": legacy.id})

        self.log_data_access(
            subject_type=subject_type,
            subject_id=str(subject_id),
            access_type="write",
            resource_type="data_subject_request",
            resource_id=str(subject_request.id),
            accessed_by_user_id=created_by_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            justification=f"Solicitacao LGPD criada: {request_type}",
            flush_only=True,
        )
        return subject_request

    def list_subject_requests(
        self,
        *,
        status: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        query = self.db.query(DataSubjectRequest).filter(DataSubjectRequest.tenant_id == self.tenant_id)
        if status:
            query = query.filter(DataSubjectRequest.status == status)
        if subject_type:
            query = query.filter(DataSubjectRequest.subject_type == subject_type)
        if subject_id:
            query = query.filter(DataSubjectRequest.subject_id == str(subject_id))
        rows = (
            query.order_by(DataSubjectRequest.created_at.desc(), DataSubjectRequest.id.desc())
            .limit(max(1, min(limit, 500)))
            .all()
        )
        return [self._serialize_request(row) for row in rows]

    def process_subject_request(
        self,
        *,
        request_id: int,
        status: str,
        processed_by_user_id: int,
        resolution_notes: str | None = None,
        response_payload: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> DataSubjectRequest:
        allowed = {"pending", "in_review", "waiting_customer", "completed", "rejected", "cancelled"}
        if status not in allowed:
            raise ValueError("Status LGPD invalido")

        row = (
            self.db.query(DataSubjectRequest)
            .filter(DataSubjectRequest.tenant_id == self.tenant_id, DataSubjectRequest.id == request_id)
            .first()
        )
        if not row:
            raise ValueError("Solicitacao LGPD nao encontrada")

        now = utcnow()
        row.status = status
        row.processed_by_user_id = processed_by_user_id
        row.processed_at = now if status in {"completed", "rejected", "cancelled"} else row.processed_at
        row.updated_at = now
        row.resolution_notes = resolution_notes
        if response_payload is not None:
            row.response_payload = _json_dump(response_payload)

        self.log_data_access(
            subject_type=row.subject_type,
            subject_id=row.subject_id,
            access_type="write",
            resource_type="data_subject_request",
            resource_id=str(row.id),
            accessed_by_user_id=processed_by_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            justification=f"Solicitacao LGPD atualizada para {status}",
            flush_only=True,
        )
        return row

    def anonymize_customer_from_request(
        self,
        *,
        request_id: int,
        processed_by_user_id: int,
        resolution_notes: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[DataSubjectRequest, dict[str, Any]]:
        from app.models import Cliente, Pet

        row = (
            self.db.query(DataSubjectRequest)
            .filter(DataSubjectRequest.tenant_id == self.tenant_id, DataSubjectRequest.id == request_id)
            .first()
        )
        if not row:
            raise ValueError("Solicitacao LGPD nao encontrada")
        if row.subject_type != "customer":
            raise ValueError("Anonimizacao automatica disponivel apenas para clientes")
        if row.request_type != "deletion":
            raise ValueError("Anonimizacao exige uma solicitacao do tipo exclusao")
        if row.status in {"completed", "cancelled", "rejected"}:
            raise ValueError("Solicitacao ja foi encerrada")

        try:
            cliente_id = int(row.subject_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("Titular da solicitacao nao aponta para um cliente valido") from exc

        cliente = (
            self.db.query(Cliente)
            .filter(Cliente.tenant_id == self.tenant_id, Cliente.id == cliente_id)
            .first()
        )
        if not cliente:
            raise ValueError("Cliente nao encontrado para anonimizacao")

        now = utcnow()
        pets = (
            self.db.query(Pet)
            .filter(Pet.tenant_id == self.tenant_id, Pet.cliente_id == cliente.id)
            .all()
        )

        cliente.nome = f"Cliente anonimizado #{cliente.id}"
        cliente.ativo = False
        cliente.updated_at = now
        for field in (
            "cpf",
            "telefone",
            "celular",
            "email",
            "data_nascimento",
            "cnpj",
            "inscricao_estadual",
            "razao_social",
            "nome_fantasia",
            "responsavel",
            "crmv",
            "parceiro_observacoes",
            "parceiro_email_principal",
            "parceiro_emails_copia",
            "cep",
            "endereco",
            "numero",
            "complemento",
            "bairro",
            "cidade",
            "estado",
            "endereco_entrega",
            "endereco_entrega_2",
            "enderecos_adicionais",
            "observacoes",
        ):
            if hasattr(cliente, field):
                setattr(cliente, field, None)

        for pet in pets:
            pet.nome = f"Pet anonimizado #{pet.id}"
            pet.ativo = False
            pet.updated_at = now
            for field in (
                "data_nascimento",
                "idade_aproximada",
                "peso",
                "cor",
                "cor_pelagem",
                "microchip",
                "alergias",
                "alergias_lista",
                "doencas_cronicas",
                "condicoes_cronicas_lista",
                "medicamentos_continuos",
                "medicamentos_continuos_lista",
                "restricoes_alimentares_lista",
                "historico_clinico",
                "tipo_sanguineo",
                "pedigree_registro",
                "castrado_data",
                "observacoes",
                "foto_url",
            ):
                if hasattr(pet, field):
                    setattr(pet, field, None)

        revoked_consents = 0
        active_consents = (
            self.db.query(DataPrivacyConsent)
            .filter(
                DataPrivacyConsent.tenant_id == self.tenant_id,
                DataPrivacyConsent.subject_type == "customer",
                DataPrivacyConsent.subject_id == str(cliente.id),
                DataPrivacyConsent.revoked_at.is_(None),
            )
            .all()
        )
        for consent in active_consents:
            consent.revoked_at = now
            consent.revoke_reason = "anonimizacao_lgpd"
            consent.updated_at = now
            revoked_consents += 1

        operation = {
            "operation": "customer_anonymization",
            "cliente_id": cliente.id,
            "cliente_codigo": cliente.codigo,
            "pets_anonymized": len(pets),
            "consents_revoked": revoked_consents,
            "completed_at": now.isoformat(),
        }

        previous_payload = _json_load(row.response_payload, {}) or {}
        row.status = "completed"
        row.processed_by_user_id = processed_by_user_id
        row.processed_at = now
        row.updated_at = now
        row.resolution_notes = resolution_notes or "Cliente anonimizado por solicitacao LGPD de exclusao."
        row.response_payload = _json_dump({**previous_payload, **operation})

        legacy = self._linked_legacy_deletion_request(row)
        if legacy:
            legacy.status = "completed"
            legacy.processed_by_user_id = processed_by_user_id
            legacy.processed_at = now

        self.log_data_access(
            subject_type="customer",
            subject_id=str(cliente.id),
            access_type="delete",
            resource_type="customer_anonymization",
            resource_id=str(cliente.id),
            accessed_by_user_id=processed_by_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            justification="Anonimizacao LGPD executada preservando historico operacional",
            flush_only=True,
        )
        return row, operation

    def export_customer_data(
        self,
        *,
        cliente_id: int,
        actor_user_id: int | None,
        ip_address: str | None,
        user_agent: str | None,
        include_sales_limit: int = 200,
    ) -> dict[str, Any]:
        from app.models import Cliente, Pet
        from app.pedido_models import Pedido, PedidoItem
        from app.vendas_models import Venda

        cliente = (
            self.db.query(Cliente)
            .filter(Cliente.tenant_id == self.tenant_id, Cliente.id == cliente_id)
            .first()
        )
        if not cliente:
            raise ValueError("Cliente nao encontrado")

        pets = (
            self.db.query(Pet)
            .filter(Pet.tenant_id == self.tenant_id, Pet.cliente_id == cliente.id)
            .order_by(Pet.nome.asc())
            .all()
        )

        vendas = (
            self.db.query(Venda)
            .filter(Venda.tenant_id == self.tenant_id, Venda.cliente_id == cliente.id)
            .order_by(Venda.data_venda.desc(), Venda.id.desc())
            .limit(max(1, min(include_sales_limit, 500)))
            .all()
        )

        ecommerce_pedidos = []
        if getattr(cliente, "user_id", None):
            ecommerce_rows = (
                self.db.query(Pedido)
                .filter(Pedido.tenant_id == self.tenant_id, Pedido.cliente_id == cliente.user_id)
                .order_by(Pedido.created_at.desc(), Pedido.id.desc())
                .limit(200)
                .all()
            )
            pedido_ids = [row.pedido_id for row in ecommerce_rows]
            itens_por_pedido: dict[str, list[PedidoItem]] = {pid: [] for pid in pedido_ids}
            if pedido_ids:
                for item in self.db.query(PedidoItem).filter(PedidoItem.pedido_id.in_(pedido_ids)).all():
                    itens_por_pedido.setdefault(item.pedido_id, []).append(item)
            ecommerce_pedidos = [
                {
                    "id": row.id,
                    "pedido_id": row.pedido_id,
                    "origem": row.origem,
                    "status": row.status,
                    "total": _num(row.total),
                    "created_at": _iso(row.created_at),
                    "itens": [
                        {
                            "produto_id": item.produto_id,
                            "nome": item.nome,
                            "quantidade": item.quantidade,
                            "preco_unitario": _num(item.preco_unitario),
                            "subtotal": _num(item.subtotal),
                        }
                        for item in itens_por_pedido.get(row.pedido_id, [])
                    ],
                }
                for row in ecommerce_rows
            ]

        export = {
            "generated_at": utcnow().isoformat(),
            "tenant_id": self.tenant_id,
            "subject": {"type": "customer", "id": str(cliente.id)},
            "cliente": self._serialize_cliente(cliente),
            "pets": [self._serialize_pet(pet) for pet in pets],
            "vendas": [self._serialize_venda(venda) for venda in vendas],
            "ecommerce_pedidos": ecommerce_pedidos,
            "preferencias": self.current_preferences("customer", str(cliente.id)),
            "consentimentos": self.consent_history("customer", str(cliente.id), limit=300),
            "solicitacoes": self.list_subject_requests(subject_type="customer", subject_id=str(cliente.id), limit=300),
            "solicitacoes_exclusao": self._legacy_deletion_requests("customer", str(cliente.id)),
            "logs_acesso": self._access_logs("customer", str(cliente.id)),
        }

        self.log_data_access(
            subject_type="customer",
            subject_id=str(cliente.id),
            access_type="export",
            resource_type="customer_dossier",
            resource_id=str(cliente.id),
            accessed_by_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            justification="Exportacao/dossie LGPD do cliente",
        )
        return export

    def log_data_access(
        self,
        *,
        subject_type: str,
        subject_id: str,
        access_type: str,
        resource_type: str,
        resource_id: str | None,
        accessed_by_user_id: int | None,
        ip_address: str | None,
        user_agent: str | None = None,
        justification: str | None = None,
        flush_only: bool = False,
    ) -> DataAccessLog:
        log = DataAccessLog(
            tenant_id=self.tenant_id,
            subject_type=subject_type,
            subject_id=str(subject_id),
            accessed_by_user_id=accessed_by_user_id,
            access_type=access_type,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            justification=justification,
            created_at=utcnow(),
        )
        self.db.add(log)
        self.db.flush()
        if not flush_only:
            self.db.commit()
        return log

    def _legacy_deletion_requests(self, subject_type: str, subject_id: str) -> list[dict[str, Any]]:
        rows = (
            self.db.query(DataDeletionRequest)
            .filter(
                DataDeletionRequest.tenant_id == self.tenant_id,
                DataDeletionRequest.subject_type == subject_type,
                DataDeletionRequest.subject_id == str(subject_id),
            )
            .order_by(DataDeletionRequest.request_date.desc(), DataDeletionRequest.id.desc())
            .limit(100)
            .all()
        )
        return [
            {
                "id": row.id,
                "status": row.status,
                "reason": row.reason,
                "request_date": _iso(row.request_date),
                "processed_at": _iso(row.processed_at),
                "rejection_reason": row.rejection_reason,
            }
            for row in rows
        ]

    def _linked_legacy_deletion_request(self, row: DataSubjectRequest) -> DataDeletionRequest | None:
        payload = _json_load(row.response_payload, {}) or {}
        legacy_id = payload.get("legacy_deletion_request_id")
        query = self.db.query(DataDeletionRequest).filter(
            DataDeletionRequest.tenant_id == self.tenant_id,
            DataDeletionRequest.subject_type == row.subject_type,
            DataDeletionRequest.subject_id == str(row.subject_id),
        )
        if legacy_id:
            return query.filter(DataDeletionRequest.id == legacy_id).first()

        candidates = query.order_by(DataDeletionRequest.request_date.desc(), DataDeletionRequest.id.desc()).limit(50).all()
        for candidate in candidates:
            metadata = _json_load(candidate.extra_metadata, {}) or {}
            if str(metadata.get("data_subject_request_id")) == str(row.id):
                return candidate
        return None

    def _access_logs(self, subject_type: str, subject_id: str) -> list[dict[str, Any]]:
        rows = (
            self.db.query(DataAccessLog)
            .filter(
                DataAccessLog.tenant_id == self.tenant_id,
                DataAccessLog.subject_type == subject_type,
                DataAccessLog.subject_id == str(subject_id),
            )
            .order_by(DataAccessLog.created_at.desc(), DataAccessLog.id.desc())
            .limit(200)
            .all()
        )
        return [
            {
                "id": row.id,
                "access_type": row.access_type,
                "resource_type": row.resource_type,
                "resource_id": row.resource_id,
                "accessed_by_user_id": row.accessed_by_user_id,
                "justification": row.justification,
                "created_at": _iso(row.created_at),
            }
            for row in rows
        ]

    def _serialize_cliente(self, cliente) -> dict[str, Any]:
        return {
            "id": cliente.id,
            "codigo": cliente.codigo,
            "tipo_cadastro": cliente.tipo_cadastro,
            "tipo_pessoa": cliente.tipo_pessoa,
            "nome": cliente.nome,
            "cpf": cliente.cpf,
            "cnpj": cliente.cnpj,
            "razao_social": cliente.razao_social,
            "nome_fantasia": cliente.nome_fantasia,
            "responsavel": cliente.responsavel,
            "email": cliente.email,
            "telefone": cliente.telefone,
            "celular": cliente.celular,
            "data_nascimento": _iso(cliente.data_nascimento),
            "endereco": {
                "cep": cliente.cep,
                "endereco": cliente.endereco,
                "numero": cliente.numero,
                "complemento": cliente.complemento,
                "bairro": cliente.bairro,
                "cidade": cliente.cidade,
                "estado": cliente.estado,
                "endereco_entrega": cliente.endereco_entrega,
                "enderecos_adicionais": cliente.enderecos_adicionais,
            },
            "credito": _num(cliente.credito),
            "ativo": bool(cliente.ativo),
            "observacoes": cliente.observacoes,
            "created_at": _iso(cliente.created_at),
            "updated_at": _iso(cliente.updated_at),
        }

    def _serialize_pet(self, pet) -> dict[str, Any]:
        return {
            "id": pet.id,
            "codigo": pet.codigo,
            "nome": pet.nome,
            "especie": pet.especie,
            "raca": pet.raca,
            "sexo": pet.sexo,
            "castrado": bool(pet.castrado),
            "data_nascimento": _iso(pet.data_nascimento),
            "idade_aproximada": pet.idade_aproximada,
            "peso": _num(pet.peso),
            "cor": pet.cor,
            "porte": pet.porte,
            "microchip": pet.microchip,
            "alergias": pet.alergias,
            "doencas_cronicas": pet.doencas_cronicas,
            "medicamentos_continuos": pet.medicamentos_continuos,
            "restricoes_alimentares_lista": pet.restricoes_alimentares_lista,
            "historico_clinico": pet.historico_clinico,
            "observacoes": pet.observacoes,
            "ativo": bool(pet.ativo),
            "created_at": _iso(pet.created_at),
            "updated_at": _iso(pet.updated_at),
        }

    def _serialize_venda(self, venda) -> dict[str, Any]:
        return {
            "id": venda.id,
            "numero_venda": venda.numero_venda,
            "status": venda.status,
            "canal": venda.canal,
            "subtotal": _num(venda.subtotal),
            "desconto_valor": _num(venda.desconto_valor),
            "total": _num(venda.total),
            "tem_entrega": bool(venda.tem_entrega),
            "status_entrega": venda.status_entrega,
            "data_venda": _iso(venda.data_venda),
            "data_finalizacao": _iso(venda.data_finalizacao),
            "observacoes": venda.observacoes,
            "itens": [
                {
                    "id": item.id,
                    "tipo": item.tipo,
                    "produto_id": item.produto_id,
                    "descricao": item.servico_descricao or (item.produto.nome if item.produto else None),
                    "quantidade": _num(item.quantidade),
                    "preco_unitario": _num(item.preco_unitario),
                    "subtotal": _num(item.subtotal),
                    "pet_id": item.pet_id,
                }
                for item in getattr(venda, "itens", []) or []
            ],
            "pagamentos": [
                {
                    "id": pagamento.id,
                    "forma_pagamento": getattr(pagamento, "forma_pagamento", None),
                    "valor": _num(getattr(pagamento, "valor", None)),
                    "data_pagamento": _iso(getattr(pagamento, "data_pagamento", None)),
                }
                for pagamento in getattr(venda, "pagamentos", []) or []
            ],
        }

    def _serialize_consent(self, row: DataPrivacyConsent) -> dict[str, Any]:
        return {
            "id": row.id,
            "subject_type": row.subject_type,
            "subject_id": row.subject_id,
            "consent_type": row.consent_type,
            "consent_given": bool(row.consent_given),
            "consent_text": row.consent_text,
            "phone_number": row.phone_number,
            "email": row.email,
            "created_at": _iso(row.created_at),
            "revoked_at": _iso(row.revoked_at),
            "revoke_reason": row.revoke_reason,
        }

    def _serialize_request(self, row: DataSubjectRequest) -> dict[str, Any]:
        return {
            "id": row.id,
            "subject_type": row.subject_type,
            "subject_id": row.subject_id,
            "request_type": row.request_type,
            "status": row.status,
            "requester_name": row.requester_name,
            "requester_email": row.requester_email,
            "requester_phone": row.requester_phone,
            "channel": row.channel,
            "details": row.details,
            "request_payload": _json_load(row.request_payload, {}),
            "response_payload": _json_load(row.response_payload, {}),
            "resolution_notes": row.resolution_notes,
            "created_by_user_id": row.created_by_user_id,
            "processed_by_user_id": row.processed_by_user_id,
            "due_at": _iso(row.due_at),
            "processed_at": _iso(row.processed_at),
            "created_at": _iso(row.created_at),
            "updated_at": _iso(row.updated_at),
        }
