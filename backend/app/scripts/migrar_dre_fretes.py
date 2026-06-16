"""
Script de migração para atribuir subcategoria DRE "Fretes sobre Vendas"
a todas as contas a pagar relacionadas a frete/entrega que não têm categoria DRE.

Uso:
    python -m app.scripts.migrar_dre_fretes
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db import SessionLocal
import logging

logger = logging.getLogger(__name__)


def migrar_fretes():
    """Atualiza contas a pagar de frete/entrega com a subcategoria DRE correta"""
    db: Session = SessionLocal()

    try:
        # Buscar todos os tenants
        result = db.execute(text("SELECT id FROM tenants"))
        tenants = result.fetchall()

        if not tenants:
            print("⚠️  Nenhum tenant encontrado no sistema")
            return

        total_atualizado = 0

        for tenant_row in tenants:
            tenant_id = tenant_row[0]
            print(f"🔄 Processando tenant {tenant_id}...")

            # Buscar subcategoria "Fretes sobre Vendas"
            result = db.execute(
                text("""
                SELECT id FROM dre_subcategorias 
                WHERE tenant_id = :tenant_id 
                AND nome = 'Fretes sobre Vendas'
                LIMIT 1
            """),
                {"tenant_id": tenant_id},
            )

            subcategoria_row = result.fetchone()

            if not subcategoria_row:
                print(
                    f"   ⚠️ Subcategoria 'Fretes sobre Vendas' não encontrada para tenant {tenant_id}"
                )
                print(
                    "   💡 Execute o seed: python -m app.scripts.seed_dre_plano_contas_petshop"
                )
                continue

            subcategoria_id = subcategoria_row[0]
            print(f"   ✅ Subcategoria encontrada: ID {subcategoria_id}")

            # Buscar contas sem categoria DRE que contenham palavras-chave de frete/entrega
            result = db.execute(
                text("""
                SELECT id, descricao FROM contas_pagar
                WHERE tenant_id = :tenant_id
                AND dre_subcategoria_id IS NULL
                AND (
                    LOWER(descricao) LIKE '%frete%'
                    OR LOWER(descricao) LIKE '%entrega%'
                    OR LOWER(descricao) LIKE '%entregador%'
                    OR LOWER(descricao) LIKE '%taxa de entrega%'
                    OR LOWER(descricao) LIKE '%custo operacional%entrega%'
                )
            """),
                {"tenant_id": tenant_id},
            )

            contas = result.fetchall()

            if not contas:
                print(f"   ℹ️  Nenhuma conta a atualizar para tenant {tenant_id}")
                continue

            print(f"   🔍 Encontradas {len(contas)} contas para atualizar:")

            # Atualizar cada conta
            for conta in contas:
                conta_id, descricao = conta[0], conta[1]
                print(f"      • ID {conta_id}: {descricao[:60]}...")

                db.execute(
                    text("""
                    UPDATE contas_pagar 
                    SET dre_subcategoria_id = :subcategoria_id
                    WHERE id = :conta_id
                """),
                    {"subcategoria_id": subcategoria_id, "conta_id": conta_id},
                )

                total_atualizado += 1

            # Commit para este tenant
            db.commit()
            print(f"   ✅ {len(contas)} contas atualizadas para tenant {tenant_id}\n")

        print(f"🎉 Migração concluída! Total de contas atualizadas: {total_atualizado}")

    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao executar migração: {e}")
        import traceback

        traceback.print_exc()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 80)
    print("🚀 MIGRAÇÃO: Atribuir subcategoria DRE para fretes/entregas")
    print("=" * 80)
    print("")

    migrar_fretes()

    print("")
    print("=" * 80)
    print("✨ Processo finalizado!")
    print("=" * 80)
