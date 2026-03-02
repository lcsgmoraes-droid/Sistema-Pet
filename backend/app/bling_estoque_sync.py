"""
Sincronização automática de estoque com o Bling

Este módulo é chamado pelo EstoqueService TODA VEZ que o estoque de um produto
muda — seja por venda PDV, entrada por XML, ajuste manual, devolução, etc.

A sincronização roda em background (thread separada) para NÃO bloquear a operação
principal. Se o Bling estiver fora do ar, apenas registra warning — a operação de
estoque no sistema continua normalmente.

Ponto de entrada único: sincronizar_bling_background(produto_id, estoque_novo, motivo)
"""

import threading
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def sincronizar_bling_background(produto_id: int, estoque_novo: float, motivo: str = "") -> None:
    """
    Agenda sincronização de estoque com o Bling em background.

    Não bloqueia. Se o Bling falhar, registra warning mas NÃO desfaz a operação
    de estoque no sistema (que já foi commitada pelo caller).

    Args:
        produto_id: ID do produto no sistema
        estoque_novo: Novo saldo físico de estoque
        motivo: Motivo da alteração (venda, devolucao, ajuste_manual, etc.)
    """
    t = threading.Thread(
        target=_executar_sync,
        args=(produto_id, estoque_novo, motivo),
        daemon=True,
        name=f"bling-sync-{produto_id}"
    )
    t.start()


def _executar_sync(produto_id: int, estoque_novo: float, motivo: str) -> None:
    """Executa a sincronização com o Bling (roda em thread separada)."""
    sync = None
    try:
        from app.db import SessionLocal
        from app.produtos_models import ProdutoBlingSync
        from app.bling_integration import BlingAPI

        db = SessionLocal()
        try:
            # Verificar se produto está configurado para sincronizar com Bling
            sync = db.query(ProdutoBlingSync).filter(
                ProdutoBlingSync.produto_id == produto_id,
                ProdutoBlingSync.sincronizar == True
            ).first()

            if not sync or not sync.bling_produto_id:
                # Produto não vinculado — silencioso (normal para produtos sem Bling)
                return

            bling_produto_id = sync.bling_produto_id

            # Chamar API do Bling para atualizar estoque
            bling = BlingAPI()
            bling.atualizar_estoque_produto(
                produto_id=bling_produto_id,
                estoque_novo=estoque_novo,
                observacao=f"Sync automático - {motivo}" if motivo else "Sync automático - Sistema Pet"
            )

            # Registrar sincronização bem-sucedida
            sync.ultima_sincronizacao = datetime.utcnow()
            sync.status = 'ativo'
            sync.erro_mensagem = None
            db.commit()

            logger.info(
                f"✅ Bling sync OK: produto_id={produto_id} "
                f"bling_id={bling_produto_id} estoque={estoque_novo} motivo={motivo}"
            )

        except Exception as e:
            logger.warning(
                f"⚠️ Bling sync falhou (produto_id={produto_id}, estoque={estoque_novo}): {e}"
            )
            # Registrar erro no banco sem travar
            try:
                if sync:
                    sync.status = 'erro'
                    sync.erro_mensagem = str(e)[:500]
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()

    except Exception as e:
        logger.warning(f"⚠️ Bling sync thread error (produto_id={produto_id}): {e}")
