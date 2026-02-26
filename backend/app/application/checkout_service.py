import uuid
from uuid import uuid4
from uuid import UUID, NAMESPACE_DNS, uuid5
import hashlib
import json
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from app.application.commands.checkout_command import CheckoutCommand
from app.idempotency_models import IdempotencyKey
from app.pedido_models import Pedido


class CheckoutService:
    """
    Application Layer (DDD)
    Orquestra checkout sem lógica HTTP.
    """

    def __init__(self, db):
        self.db = db

    @staticmethod
    def calcular_items_metadata(items):
        itens = items or []
        items_count = len(itens)
        subtotal_items = round(
            sum(
                i.get("quantidade", 1) * i.get("preco_unitario", 0)
                for i in itens
            ),
            2,
        )
        return items_count, subtotal_items

    @staticmethod
    def _build_request_hash(command: CheckoutCommand) -> str:
        payload = {
            "cliente_id": command.cliente_id,
            "origem": command.origem,
            "tenant_id": command.tenant_id,
            "items": command.items,
        }
        normalized = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_tenant_uuid(tenant_id: str) -> str:
        try:
            return str(UUID(str(tenant_id)))
        except Exception:
            raise ValueError("tenant_id inválido: UUID obrigatório")

    @staticmethod
    def gerar_correlation_id() -> str:
        return str(uuid.uuid4())

    def _find_idempotent_pedido(self, command: CheckoutCommand, tenant_uuid: str):
        if not command.idempotency_key:
            return None

        existente = self.db.query(IdempotencyKey).filter(
            IdempotencyKey.user_id == command.cliente_id,
            IdempotencyKey.endpoint == "POST /ecommerce/checkout",
            IdempotencyKey.chave_idempotencia == command.idempotency_key,
            IdempotencyKey.tenant_id == tenant_uuid,
        ).first()

        if not existente:
            return None

        request_hash_atual = self._build_request_hash(command)
        if existente.request_hash and existente.request_hash != request_hash_atual:
            raise ValueError(
                "Conflito de idempotência: a mesma Idempotency-Key foi usada com payload diferente"
            )

        if existente.response_body:
            try:
                payload = json.loads(existente.response_body)
                pedido_id = payload.get("pedido_id")
                if pedido_id:
                    pedido = self.db.query(Pedido).filter(
                        Pedido.pedido_id == pedido_id,
                        Pedido.tenant_id == tenant_uuid,
                    ).first()
                    if pedido:
                        return pedido
            except Exception:
                return None

        return None

    def processar_checkout(self, command: CheckoutCommand):
        tenant_uuid = self._normalize_tenant_uuid(command.tenant_id)

        pedido_existente = self._find_idempotent_pedido(command, tenant_uuid)
        if pedido_existente:
            return pedido_existente

        pedido_id = str(uuid4())

        total_inicial = 99.90 if not command.items else 0.0

        pedido = Pedido(
            pedido_id=pedido_id,
            cliente_id=command.cliente_id,
            total=total_inicial,
            origem=command.origem,
            status="criado",
            tenant_id=tenant_uuid,
        )

        self.db.add(pedido)

        for item in command.items:
            pedido.adicionar_item(
                self.db,
                produto_id=item["produto_id"],
                nome=item["nome"],
                quantidade=item.get("quantidade", 1),
                preco_unitario=item["preco_unitario"],
                tenant_id=tenant_uuid,
            )

        if command.items:
            pedido.recalcular_total(self.db)

        self.db.flush()
        self.db.commit()
        self.db.refresh(pedido)

        if command.idempotency_key:
            request_hash = self._build_request_hash(command)
            registro = IdempotencyKey(
                user_id=command.cliente_id,
                endpoint="POST /ecommerce/checkout",
                chave_idempotencia=command.idempotency_key,
                request_hash=request_hash,
                status="completed",
                response_status_code=200,
                response_body=json.dumps({"pedido_id": pedido.pedido_id}),
                completed_at=datetime.utcnow(),
                tenant_id=tenant_uuid,
            )
            self.db.add(registro)
            try:
                self.db.commit()
            except IntegrityError:
                self.db.rollback()

        return pedido
