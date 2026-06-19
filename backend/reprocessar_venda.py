"""
Script temporário para reprocessar comissão da venda 43
"""

from app.comissoes_service import gerar_comissoes_venda
from app.db import SessionLocal
from app.tenancy.context import set_tenant_context

db = SessionLocal()

try:
    # Definir tenant (assumindo tenant padrão)
    set_tenant_context("9b7e1e4d-4b5f-4f3d-8c2a-1e9f3b7c8d2a")

    print("🔄 Reprocessando venda 43...")
    resultado = gerar_comissoes_venda(venda_id=43, funcionario_id=1, db=db)

    print(f"\n✅ Sucesso: {resultado['success']}")
    print(f"💰 Total comissão: R$ {resultado.get('total_comissao', 0):.2f}")
    print(f"📋 Itens gerados: {len(resultado.get('itens', []))}")

    if resultado.get("itens"):
        for item in resultado["itens"]:
            print(f"\n  Item ID {item['id']}:")
            print(f"    Valor venda: R$ {item.get('valor_venda', 0):.2f}")
            print(f"    Base cálculo: R$ {item.get('valor_base_calculo', 0):.2f}")
            print(f"    Comissão: R$ {item.get('valor_comissao', 0):.2f}")
            print(f"    Taxa cartão: R$ {item.get('taxa_cartao_item', 0):.2f}")
            print(f"    Impostos: R$ {item.get('impostos_item', 0):.2f}")
            print(f"    Taxa entregador: R$ {item.get('taxa_entregador_item', 0):.2f}")
            print(
                f"    Custo operacional: R$ {item.get('custo_operacional_item', 0):.2f}"
            )

    db.commit()
    print("\n✅ Commit realizado!")

except Exception as e:
    import traceback

    print(f"\n❌ Erro: {str(e)}")
    print(traceback.format_exc())
    db.rollback()
finally:
    db.close()
