import logging
from pathlib import Path
from typing import Any

from app.lgpd_models import DataSubjectRequest
from app.services.lgpd_utils import (
    COMPLETED_DELETION_SCRUB_NOTE,
    iso,
    json_dump,
    json_load,
    num,
    utcnow,
)
from app.whatsapp.security import DataPrivacyConsent

logger = logging.getLogger(__name__)
PET_UPLOAD_DIR = Path("uploads/pets")


def _delete_local_pet_photo(url: str | None) -> bool:
    normalized = str(url or "").strip()
    if not normalized.startswith("/uploads/pets/"):
        return False

    path = Path(normalized.lstrip("/"))
    try:
        resolved_path = path.resolve()
        resolved_base = PET_UPLOAD_DIR.resolve()
        if resolved_base not in resolved_path.parents:
            return False
        path.unlink(missing_ok=True)
        return True
    except OSError:
        logger.warning("Nao foi possivel remover foto local do pet: %s", normalized)
        return False


class PrivacyCustomerDataMixin:
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
            .filter(
                DataSubjectRequest.tenant_id == self.tenant_id,
                DataSubjectRequest.id == request_id,
            )
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
            raise ValueError(
                "Titular da solicitacao nao aponta para um cliente valido"
            ) from exc

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

        deleted_pet_photos = 0
        for pet in pets:
            if _delete_local_pet_photo(getattr(pet, "foto_url", None)):
                deleted_pet_photos += 1
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
            "pet_photos_deleted": deleted_pet_photos,
            "consents_revoked": revoked_consents,
            "completed_at": now.isoformat(),
        }

        previous_payload = json_load(row.response_payload, {}) or {}
        safe_previous_payload = {}
        if previous_payload.get("legacy_deletion_request_id"):
            safe_previous_payload["legacy_deletion_request_id"] = previous_payload[
                "legacy_deletion_request_id"
            ]
        row.status = "completed"
        row.processed_by_user_id = processed_by_user_id
        row.processed_at = now
        row.updated_at = now
        row.requester_name = f"Titular anonimizado #{cliente.id}"
        row.requester_email = None
        row.requester_phone = None
        row.details = COMPLETED_DELETION_SCRUB_NOTE
        row.request_payload = None
        row.resolution_notes = COMPLETED_DELETION_SCRUB_NOTE
        row.response_payload = json_dump({**safe_previous_payload, **operation})

        legacy = self._linked_legacy_deletion_request(row)
        if legacy:
            legacy.status = "completed"
            legacy.processed_by_user_id = processed_by_user_id
            legacy.processed_at = now
            legacy.reason = COMPLETED_DELETION_SCRUB_NOTE
            legacy.contact_phone = None
            legacy.contact_email = None
            legacy.extra_metadata = json_dump(
                {"data_subject_request_id": row.id, "scrubbed_after_completion": True}
            )

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
                .filter(
                    Pedido.tenant_id == self.tenant_id,
                    Pedido.cliente_id == cliente.user_id,
                )
                .order_by(Pedido.created_at.desc(), Pedido.id.desc())
                .limit(200)
                .all()
            )
            pedido_ids = [row.pedido_id for row in ecommerce_rows]
            itens_por_pedido: dict[str, list[PedidoItem]] = {
                pid: [] for pid in pedido_ids
            }
            if pedido_ids:
                for item in (
                    self.db.query(PedidoItem)
                    .filter(PedidoItem.pedido_id.in_(pedido_ids))
                    .all()
                ):
                    itens_por_pedido.setdefault(item.pedido_id, []).append(item)
            ecommerce_pedidos = [
                {
                    "id": row.id,
                    "pedido_id": row.pedido_id,
                    "origem": row.origem,
                    "status": row.status,
                    "total": num(row.total),
                    "created_at": iso(row.created_at),
                    "itens": [
                        {
                            "produto_id": item.produto_id,
                            "nome": item.nome,
                            "quantidade": item.quantidade,
                            "preco_unitario": num(item.preco_unitario),
                            "subtotal": num(item.subtotal),
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
            "consentimentos": self.consent_history(
                "customer", str(cliente.id), limit=300
            ),
            "solicitacoes": self.list_subject_requests(
                subject_type="customer", subject_id=str(cliente.id), limit=300
            ),
            "solicitacoes_exclusao": self._legacy_deletion_requests(
                "customer", str(cliente.id)
            ),
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


__all__ = ["PrivacyCustomerDataMixin"]
