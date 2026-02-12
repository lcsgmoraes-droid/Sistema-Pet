import sys
import os

# Adicionar o diretório backend ao path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.db import SessionLocal
from app.produtos_models import Produto
from sqlalchemy import text

# Importar modelos fiscais diretamente dos arquivos
import importlib.util

# Carregar ProdutoConfigFiscal
spec = importlib.util.spec_from_file_location(
    "produto_config_fiscal", 
    os.path.join(backend_dir, "app", "models", "produto_config_fiscal.py")
)
produto_fiscal_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(produto_fiscal_module)
ProdutoConfigFiscal = produto_fiscal_module.ProdutoConfigFiscal

# Carregar KitConfigFiscal
spec = importlib.util.spec_from_file_location(
    "kit_config_fiscal", 
    os.path.join(backend_dir, "app", "models", "kit_config_fiscal.py")
)
kit_fiscal_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kit_fiscal_module)
KitConfigFiscal = kit_fiscal_module.KitConfigFiscal


def migrar():
    db = SessionLocal()

    produtos = db.query(Produto).all()
    migrados = 0

    for produto in produtos:
        # verifica se tem algum dado fiscal legado
        if not any([
            produto.ncm,
            produto.cest,
            produto.cfop,
            produto.aliquota_icms,
            produto.aliquota_pis,
            produto.aliquota_cofins,
        ]):
            continue

        if produto.tipo_produto == "KIT":
            # Verificar usando SQL direto
            result = db.execute(
                text("SELECT id FROM kit_config_fiscal WHERE produto_kit_id = :produto_id AND tenant_id = :tenant_id LIMIT 1"),
                {"produto_id": produto.id, "tenant_id": produto.tenant_id}
            ).first()

            if result:
                continue

            fiscal = KitConfigFiscal(
                tenant_id=produto.tenant_id,
                produto_kit_id=produto.id,
                herdado_da_empresa=False,
                origem_mercadoria=produto.origem_mercadoria,
                ncm=produto.ncm,
                cest=produto.cest,
                cfop=produto.cfop,  # kit_config_fiscal usa cfop (não cfop_venda/compra)
                cst_icms=produto.cst_icms,
                icms_aliquota=produto.aliquota_icms,
                icms_st=produto.icms_st,
                pis_aliquota=produto.aliquota_pis,
                cofins_aliquota=produto.aliquota_cofins,
            )
            db.add(fiscal)
            migrados += 1

        else:
            # Verificar usando SQL direto
            result = db.execute(
                text("SELECT id FROM produto_config_fiscal WHERE produto_id = :produto_id AND tenant_id = :tenant_id LIMIT 1"),
                {"produto_id": produto.id, "tenant_id": produto.tenant_id}
            ).first()

            if result:
                continue

            fiscal = ProdutoConfigFiscal(
                tenant_id=produto.tenant_id,
                produto_id=produto.id,
                herdado_da_empresa=False,
                origem_mercadoria=produto.origem,
                ncm=produto.ncm,
                cest=produto.cest,
                cfop_venda=produto.cfop,
                cfop_compra=produto.cfop,
                icms_aliquota=produto.aliquota_icms,
                pis_aliquota=produto.aliquota_pis,
                cofins_aliquota=produto.aliquota_cofins,
            )
            db.add(fiscal)
            migrados += 1

    db.commit()
    db.close()

    print(f"✅ Migração concluída. Registros migrados: {migrados}")


if __name__ == "__main__":
    migrar()
