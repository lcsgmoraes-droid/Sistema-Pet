#!/usr/bin/env python3
"""Script de teste para venda 42 - verificar correções"""

import sys

sys.path.insert(0, "/app")

from app.db import SessionLocal
from app.comissoes_service import gerar_comissoes_venda
from decimal import Decimal

db = SessionLocal()

try:
    print("=" * 60)
    print("🧪 TESTE: Gerando comissão para venda 42")
    print("=" * 60)

    resultado = gerar_comissoes_venda(
        venda_id=42,
        funcionario_id=1,
        valor_pago=Decimal("115.65"),
        parcela_numero=1,
        db=db,
    )

    print(f"\n✅ Resultado: {resultado}")

    db.commit()
    print("\n✅ Commit realizado com sucesso!")

except Exception as e:
    print(f"\n❌ Erro: {e}")
    import traceback

    traceback.print_exc()
    db.rollback()
finally:
    db.close()
