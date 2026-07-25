"""Fila persistente de sincronizacao de custo do CorePet para o Bling."""

from __future__ import annotations

from datetime import timedelta
import logging
import math
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.bling_integration import BlingAPI
from app.bling_sync.product_export_enrichment import (
    _localizar_contato_fornecedor_bling,
    _texto,
    _vinculos_fornecedores_produto,
)
from app.db import SessionLocal
from app.models import Tenant
from app.produtos_models import (
    Marca,
    Produto,
    ProdutoBlingCostSyncQueue,
    ProdutoBlingSync,
    ProdutoFornecedor,
)
from app.tenancy.context import tenant_context

from .bling_sync_shared import (
    MAX_RETRIES,
    RETRY_BACKOFF_MINUTES,
    _detalhe_autenticacao_bling,
    _erro_autenticacao_bling,
    _erro_rate_limit_bling,
    _mensagem_autenticacao_bling,
    _mensagem_rate_limit_bling,
    _registrar_cooldown_rate_limit,
    _reservar_janela_envio_bling,
    utc_now,
)

logger = logging.getLogger(__name__)


class BlingCostSyncConfigurationError(RuntimeError):
    """Erro de cadastro que nao melhora apenas repetindo a mesma requisicao."""


def _custo_valido(value: Any) -> Optional[float]:
    try:
        cost = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(cost) or cost <= 0:
        return None
    return round(cost, 4)


def _bling_items(response: Any) -> list[dict[str, Any]]:
    if not isinstance(response, dict):
        return []
    data = response.get("data", [])
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _bling_id(value: Any) -> Optional[str]:
    text = _texto(value)
    return text or None


def _is_default_supplier(item: dict[str, Any]) -> bool:
    value = item.get("padrao")
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "sim", "s"}
    return bool(value)


def selecionar_produto_fornecedor_bling(
    items: list[dict[str, Any]],
    cached_id: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Escolhe apenas um vinculo seguro, sem adivinhar entre fornecedores."""
    defaults = [item for item in items if _is_default_supplier(item)]
    if len(defaults) == 1:
        return defaults[0]
    if len(defaults) > 1:
        raise BlingCostSyncConfigurationError(
            "O produto possui mais de um fornecedor padrao no Bling."
        )

    cached = _bling_id(cached_id)
    if cached:
        matches = [item for item in items if _bling_id(item.get("id")) == cached]
        if len(matches) == 1:
            return matches[0]

    if len(items) == 1:
        return items[0]
    if not items:
        return None
    raise BlingCostSyncConfigurationError(
        "O produto possui varios fornecedores no Bling e nenhum esta marcado como padrao."
    )


def montar_payload_custo_produto_fornecedor(
    item: dict[str, Any],
    *,
    bling_produto_id: str,
    custo: float,
) -> dict[str, Any]:
    """Preserva o cadastro do vinculo e altera somente o preco de custo."""
    payload: dict[str, Any] = {}
    for field in ("descricao", "codigo", "precoCompra", "padrao", "garantia"):
        if field in item and item[field] is not None:
            payload[field] = item[field]

    payload["precoCusto"] = round(float(custo), 4)
    payload["produto"] = {"id": int(bling_produto_id)}

    supplier = item.get("fornecedor")
    supplier_id = (
        _bling_id(supplier.get("id")) if isinstance(supplier, dict) else None
    )
    if supplier_id:
        payload["fornecedor"] = {"id": int(supplier_id)}
    return payload


def _response_id(response: Any) -> Optional[str]:
    if not isinstance(response, dict):
        return None
    data = response.get("data")
    if isinstance(data, dict):
        result = _bling_id(data.get("id"))
        if result:
            return result
    return _bling_id(response.get("id"))


class BlingCostSyncService:
    """Enfileira, processa e audita o envio do custo canonico ao Bling."""

    @staticmethod
    def _retry_delay_minutes(attempts: int) -> int:
        index = min(max(attempts - 1, 0), len(RETRY_BACKOFF_MINUTES) - 1)
        return RETRY_BACKOFF_MINUTES[index]

    @classmethod
    def queue_product_cost_sync(
        cls,
        db: Session,
        *,
        produto_id: int,
        custo_novo: Optional[float] = None,
        motivo: str = "",
        origem: str = "evento",
        force: bool = False,
        produto: Optional[Produto] = None,
        flush: bool = True,
    ) -> dict[str, Any]:
        product = produto or (
            db.query(Produto).filter(Produto.id == produto_id).first()
        )
        if not product:
            return {"ok": False, "detail": "Produto nao encontrado"}

        cost = _custo_valido(
            product.preco_custo if custo_novo is None else custo_novo
        )
        if cost is None:
            return {
                "ok": False,
                "detail": "Custo vazio, zerado ou invalido nao sera enviado ao Bling",
                "produto_id": produto_id,
            }

        sync = (
            db.query(ProdutoBlingSync)
            .filter(
                ProdutoBlingSync.produto_id == produto_id,
                ProdutoBlingSync.tenant_id == product.tenant_id,
            )
            .first()
        )
        if (
            not sync
            or not sync.sincronizar
            or not _bling_id(sync.bling_produto_id)
        ):
            return {
                "ok": False,
                "detail": "Produto nao vinculado para sincronizacao com o Bling",
                "produto_id": produto_id,
            }

        queue = next(
            (
                item
                for item in db.new
                if isinstance(item, ProdutoBlingCostSyncQueue)
                and item.produto_id == produto_id
                and item.tenant_id == product.tenant_id
            ),
            None,
        )
        if queue is None:
            queue = (
                db.query(ProdutoBlingCostSyncQueue)
                .filter(
                    ProdutoBlingCostSyncQueue.produto_id == produto_id,
                    ProdutoBlingCostSyncQueue.tenant_id == product.tenant_id,
                )
                .first()
            )

        now = utc_now()
        if queue is None:
            queue = ProdutoBlingCostSyncQueue(
                tenant_id=product.tenant_id,
                produto_id=produto_id,
                preco_custo_novo=cost,
                motivo=motivo,
                origem=origem,
                status="pendente",
                forcar_sync=force,
                versao=1,
                tentativas=0,
                proxima_tentativa_em=now,
            )
            db.add(queue)
        else:
            queue.preco_custo_novo = cost
            queue.motivo = motivo
            queue.origem = origem
            queue.status = "pendente"
            queue.forcar_sync = bool(force or queue.forcar_sync)
            queue.versao = int(queue.versao or 0) + 1
            queue.tentativas = 0
            queue.ultima_tentativa_em = None
            queue.proxima_tentativa_em = now
            queue.processado_em = None
            queue.ultimo_erro = None

        if flush:
            db.flush()
        return {
            "ok": True,
            "produto_id": produto_id,
            "queue_id": queue.id,
            "preco_custo_enfileirado": cost,
            "motivo": motivo,
            "origem": origem,
        }

    @classmethod
    def _load_product_and_sync(
        cls,
        db: Session,
        queue: ProdutoBlingCostSyncQueue,
    ) -> tuple[Optional[Produto], Optional[ProdutoBlingSync]]:
        product = (
            db.query(Produto)
            .options(
                joinedload(Produto.fornecedor),
                joinedload(Produto.fornecedores_alternativos).joinedload(
                    ProdutoFornecedor.fornecedor
                ),
            )
            .filter(
                Produto.id == queue.produto_id,
                Produto.tenant_id == queue.tenant_id,
            )
            .first()
        )
        sync = (
            db.query(ProdutoBlingSync)
            .filter(
                ProdutoBlingSync.produto_id == queue.produto_id,
                ProdutoBlingSync.tenant_id == queue.tenant_id,
            )
            .first()
        )
        return product, sync

    @classmethod
    def _create_supplier_link(
        cls,
        *,
        bling: BlingAPI,
        product: Produto,
        bling_product_id: str,
        cost: float,
    ) -> str:
        links = _vinculos_fornecedores_produto(product)
        primary = next((item for item in links if item[2]), None)
        if primary is None:
            raise BlingCostSyncConfigurationError(
                "Produto sem fornecedor principal no CorePet para criar o vinculo no Bling."
            )

        supplier, local_link, _is_primary = primary
        _reservar_janela_envio_bling()
        bling_supplier_id = _localizar_contato_fornecedor_bling(bling, supplier)
        if not bling_supplier_id:
            raise BlingCostSyncConfigurationError(
                "Fornecedor principal nao foi localizado de forma segura no Bling."
            )

        payload = {
            "descricao": _texto(product.nome, 255),
            "codigo": _texto(
                getattr(local_link, "codigo_fornecedor", None) or product.codigo,
                80,
            ),
            "precoCusto": round(cost, 4),
            "padrao": True,
            "produto": {"id": int(bling_product_id)},
            "fornecedor": {"id": int(bling_supplier_id)},
        }
        _reservar_janela_envio_bling()
        response = bling.criar_produto_fornecedor(payload)
        relation_id = _response_id(response)
        if relation_id:
            return relation_id

        _reservar_janela_envio_bling()
        refreshed = bling.listar_produtos_fornecedores(
            produto_id=bling_product_id,
            limite=100,
        )
        selected = selecionar_produto_fornecedor_bling(_bling_items(refreshed))
        relation_id = _bling_id(selected.get("id")) if selected else None
        if not relation_id:
            raise RuntimeError(
                "Bling criou o fornecedor do produto, mas nao retornou o identificador."
            )
        return relation_id

    @classmethod
    def _send_cost(
        cls,
        *,
        queue: ProdutoBlingCostSyncQueue,
        product: Produto,
        sync: ProdutoBlingSync,
        cost: float,
    ) -> str:
        bling_product_id = _bling_id(sync.bling_produto_id)
        if not bling_product_id:
            raise BlingCostSyncConfigurationError(
                "Produto sem identificador do Bling."
            )

        bling = BlingAPI()
        _reservar_janela_envio_bling()
        response = bling.listar_produtos_fornecedores(
            produto_id=bling_product_id,
            limite=100,
        )
        selected = selecionar_produto_fornecedor_bling(
            _bling_items(response),
            cached_id=queue.bling_produto_fornecedor_id,
        )
        if selected is None:
            return cls._create_supplier_link(
                bling=bling,
                product=product,
                bling_product_id=bling_product_id,
                cost=cost,
            )

        relation_id = _bling_id(selected.get("id"))
        if not relation_id:
            raise RuntimeError(
                "Vinculo de fornecedor retornado pelo Bling esta sem identificador."
            )
        payload = montar_payload_custo_produto_fornecedor(
            selected,
            bling_produto_id=bling_product_id,
            custo=cost,
        )
        _reservar_janela_envio_bling()
        bling.atualizar_produto_fornecedor(relation_id, payload)
        return relation_id

    @classmethod
    def _mark_error(
        cls,
        queue: ProdutoBlingCostSyncQueue,
        error: Exception,
        *,
        final: bool = False,
    ) -> dict[str, Any]:
        now = utc_now()
        retry_allowed = not final and queue.tentativas < MAX_RETRIES
        delay = cls._retry_delay_minutes(queue.tentativas)
        next_retry = now + timedelta(minutes=delay) if retry_allowed else None
        message = str(error)[:500]

        queue.status = "erro" if retry_allowed else "falha_final"
        queue.ultimo_erro = message
        queue.proxima_tentativa_em = next_retry
        if not retry_allowed:
            queue.processado_em = now
        return {
            "ok": False,
            "queue_id": queue.id,
            "produto_id": queue.produto_id,
            "status": queue.status,
            "tentativas": queue.tentativas,
            "proxima_tentativa_em": next_retry,
            "erro": message,
        }

    @classmethod
    def process_queue_item(
        cls,
        db: Session,
        queue: ProdutoBlingCostSyncQueue,
    ) -> dict[str, Any]:
        product, sync = cls._load_product_and_sync(db, queue)
        if (
            not product
            or not sync
            or not sync.sincronizar
            or not _bling_id(sync.bling_produto_id)
        ):
            return cls._mark_error(
                queue,
                BlingCostSyncConfigurationError(
                    "Produto sem vinculo ativo com o Bling."
                ),
                final=True,
            )

        cost = _custo_valido(product.preco_custo)
        if cost is None:
            return cls._mark_error(
                queue,
                BlingCostSyncConfigurationError(
                    "Custo canonico vazio, zerado ou invalido."
                ),
                final=True,
            )

        queue.preco_custo_novo = cost
        queue.status = "processando"
        queue.ultima_tentativa_em = utc_now()
        queue.tentativas = int(queue.tentativas or 0) + 1
        db.flush()

        try:
            relation_id = cls._send_cost(
                queue=queue,
                product=product,
                sync=sync,
                cost=cost,
            )
        except Exception as error:
            if _erro_rate_limit_bling(error):
                cooldown = _registrar_cooldown_rate_limit(error)
                queue.tentativas = max(int(queue.tentativas or 0) - 1, 0)
                queue.status = "pendente"
                queue.proxima_tentativa_em = utc_now() + timedelta(
                    seconds=max(cooldown, 1)
                )
                queue.ultimo_erro = _mensagem_rate_limit_bling(error, cooldown)[:500]
                return {
                    "ok": False,
                    "queue_id": queue.id,
                    "produto_id": queue.produto_id,
                    "status": queue.status,
                    "rate_limited": True,
                    "cooldown_seconds": cooldown,
                    "erro": queue.ultimo_erro,
                }
            if _erro_autenticacao_bling(error):
                message = (
                    f"{_mensagem_autenticacao_bling(error)} "
                    f"[{_detalhe_autenticacao_bling(error)}]"
                )
                result = cls._mark_error(queue, RuntimeError(message), final=True)
                result["auth_invalid"] = True
                result["detail"] = _mensagem_autenticacao_bling(error)
                return result
            return cls._mark_error(
                queue,
                error,
                final=isinstance(error, BlingCostSyncConfigurationError),
            )

        now = utc_now()
        queue.bling_produto_fornecedor_id = relation_id
        queue.status = "sucesso"
        queue.forcar_sync = False
        queue.processado_em = now
        queue.proxima_tentativa_em = None
        queue.ultimo_custo_enviado = cost
        queue.ultimo_erro = None
        return {
            "ok": True,
            "queue_id": queue.id,
            "produto_id": queue.produto_id,
            "bling_produto_id": sync.bling_produto_id,
            "bling_produto_fornecedor_id": relation_id,
            "preco_custo_enviado": cost,
            "status": queue.status,
        }

    @classmethod
    def process_pending_queue(cls, limit: int = 20) -> dict[str, Any]:
        db = SessionLocal()
        now = utc_now()
        try:
            processed = 0
            successes = 0
            errors = 0
            rate_limited = False
            auth_invalid = False

            tenant_rows = (
                db.query(Tenant.id)
                .filter(Tenant.status == "active")
                .order_by(Tenant.created_at.asc())
                .all()
            )
            for (tenant_id_raw,) in tenant_rows:
                if processed >= limit:
                    break
                try:
                    tenant_id = UUID(str(tenant_id_raw))
                except (TypeError, ValueError):
                    continue

                with tenant_context(tenant_id):
                    queues = (
                        db.query(ProdutoBlingCostSyncQueue)
                        .filter(
                            ProdutoBlingCostSyncQueue.tenant_id == tenant_id,
                            ProdutoBlingCostSyncQueue.status.in_(
                                ["pendente", "erro"]
                            ),
                            ProdutoBlingCostSyncQueue.proxima_tentativa_em.isnot(
                                None
                            ),
                            ProdutoBlingCostSyncQueue.proxima_tentativa_em <= now,
                        )
                        .order_by(
                            ProdutoBlingCostSyncQueue.forcar_sync.desc(),
                            ProdutoBlingCostSyncQueue.proxima_tentativa_em.asc(),
                            ProdutoBlingCostSyncQueue.updated_at.asc(),
                        )
                        .limit(max(limit - processed, 0))
                        .all()
                    )
                    for queue in queues:
                        result = cls.process_queue_item(db, queue)
                        processed += 1
                        if result.get("ok"):
                            successes += 1
                        else:
                            errors += 1
                        if result.get("rate_limited"):
                            rate_limited = True
                            break
                        if result.get("auth_invalid"):
                            auth_invalid = True
                            break
                    db.commit()
                if rate_limited or auth_invalid:
                    break

            return {
                "processados": processed,
                "sucessos": successes,
                "erros": errors,
                "rate_limited": rate_limited,
                "auth_invalid": auth_invalid,
            }
        except Exception:
            db.rollback()
            logger.exception("[BLING COST SYNC] Erro ao processar fila")
            return {"processados": 0, "sucessos": 0, "erros": 1}
        finally:
            db.close()

    @classmethod
    def preview_or_enqueue_brand(
        cls,
        db: Session,
        *,
        tenant_id,
        brand_name: str,
        enqueue: bool = False,
    ) -> dict[str, Any]:
        normalized_brand = " ".join(str(brand_name or "").strip().split())
        if not normalized_brand:
            raise ValueError("Informe a marca para sincronizar os custos.")

        rows = (
            db.query(Produto, ProdutoBlingSync, ProdutoBlingCostSyncQueue)
            .join(
                Marca,
                (Marca.id == Produto.marca_id) & (Marca.tenant_id == tenant_id),
            )
            .outerjoin(
                ProdutoBlingSync,
                (ProdutoBlingSync.produto_id == Produto.id)
                & (ProdutoBlingSync.tenant_id == tenant_id),
            )
            .outerjoin(
                ProdutoBlingCostSyncQueue,
                (ProdutoBlingCostSyncQueue.produto_id == Produto.id)
                & (ProdutoBlingCostSyncQueue.tenant_id == tenant_id),
            )
            .filter(
                Produto.tenant_id == tenant_id,
                func.lower(func.trim(Marca.nome)) == normalized_brand.lower(),
            )
            .order_by(Produto.nome.asc(), Produto.id.asc())
            .all()
        )

        counters = {
            "total_marca": len(rows),
            "elegiveis": 0,
            "enfileirados": 0,
            "sem_vinculo_bling": 0,
            "custos_invalidos": 0,
            "produtos_pai_ignorados": 0,
        }
        items: list[dict[str, Any]] = []

        for product, sync, queue in rows:
            item = {
                "produto_id": product.id,
                "sku": product.codigo,
                "nome": product.nome,
                "preco_custo": _custo_valido(product.preco_custo),
                "bling_produto_id": (
                    _bling_id(sync.bling_produto_id) if sync else None
                ),
                "queue_status": queue.status if queue else None,
                "ultimo_custo_enviado": (
                    float(queue.ultimo_custo_enviado)
                    if queue and queue.ultimo_custo_enviado is not None
                    else None
                ),
                "ultimo_erro": queue.ultimo_erro if queue else None,
            }
            if str(product.tipo_produto or "").upper() == "PAI" or bool(
                getattr(product, "is_parent", False)
            ):
                item["status"] = "produto_pai_ignorado"
                counters["produtos_pai_ignorados"] += 1
            elif item["preco_custo"] is None:
                item["status"] = "custo_invalido"
                counters["custos_invalidos"] += 1
            elif (
                not sync
                or not sync.sincronizar
                or not _bling_id(sync.bling_produto_id)
            ):
                item["status"] = "sem_vinculo_bling"
                counters["sem_vinculo_bling"] += 1
            else:
                item["status"] = "elegivel"
                counters["elegiveis"] += 1
                if enqueue:
                    result = cls.queue_product_cost_sync(
                        db,
                        produto_id=product.id,
                        custo_novo=item["preco_custo"],
                        motivo=f"carga_marca_{normalized_brand[:48]}",
                        origem="carga_marca",
                        force=True,
                        produto=product,
                    )
                    if result.get("ok"):
                        item["status"] = "enfileirado"
                        item["queue_id"] = result.get("queue_id")
                        counters["enfileirados"] += 1
                    else:
                        item["status"] = "erro_enfileirar"
                        item["detail"] = result.get("detail")

            items.append(item)

        return {
            "ok": True,
            "marca": normalized_brand,
            "confirmado": enqueue,
            **counters,
            "itens": items,
        }
