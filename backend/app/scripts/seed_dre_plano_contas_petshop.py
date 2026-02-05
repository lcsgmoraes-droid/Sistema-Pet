"""
Script de seed para popular plano de contas DRE padrão Pet Shop.
Cria categorias e subcategorias DRE para todos os tenants existentes.

APENAS CADASTRO ESTRUTURAL - NÃO CRIA DRE.

Uso:
    python -m app.scripts.seed_dre_plano_contas_petshop
"""

from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.dre_plano_contas_models import (
    DRECategoria,
    DRESubcategoria,
    NaturezaDRE,
    TipoCusto,
    BaseRateio,
    EscopoRateio,
)
from app.models import Tenant
from app.utils.logger import logger


PLANO_CONTAS = [
    {
        "categoria": "Receitas",
        "natureza": NaturezaDRE.RECEITA,
        "ordem": 1,
        "subcategorias": [
            ("Vendas Loja Física", TipoCusto.DIRETO, None),
            ("Serviços (Banho e Tosa)", TipoCusto.DIRETO, None),
            ("Outras Receitas", TipoCusto.DIRETO, None),
        ],
    },
    {
        "categoria": "Custos",
        "natureza": NaturezaDRE.CUSTO,
        "ordem": 2,
        "subcategorias": [
            ("Custo das Mercadorias Vendidas (CMV)", TipoCusto.DIRETO, None),
            ("Comissões de Vendas", TipoCusto.DIRETO, None),
            ("Fretes sobre Vendas", TipoCusto.DIRETO, None),
        ],
    },
    {
        "categoria": "Despesas Operacionais",
        "natureza": NaturezaDRE.DESPESA,
        "ordem": 3,
        "subcategorias": [
            ("Aluguel", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Salários", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Encargos Trabalhistas", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Energia Elétrica", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Água", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Internet e Telefonia", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Marketing", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Sistema / Software", TipoCusto.CORPORATIVO, None),
            ("Contabilidade", TipoCusto.CORPORATIVO, None),
            ("Despesas Bancárias", TipoCusto.CORPORATIVO, None),
            ("Outras Despesas", TipoCusto.CORPORATIVO, None),
        ],
    },
]


def seed():
    """Popula plano de contas DRE padrão para todos os tenants"""
    db: Session = SessionLocal()

    try:
        # Buscar todos os tenants
        tenants = db.query(Tenant).all()
        
        if not tenants:
            logger.warning("⚠️  Nenhum tenant encontrado no sistema")
            return

        for tenant in tenants:
            tenant_id = tenant.id
            logger.info(f"🌱 Populando plano de contas DRE para tenant {tenant_id}")

            for bloco in PLANO_CONTAS:
                # Verificar se categoria já existe
                categoria = (
                    db.query(DRECategoria)
                    .filter(
                        DRECategoria.tenant_id == tenant_id,
                        DRECategoria.nome == bloco["categoria"],
                    )
                    .first()
                )

                if not categoria:
                    categoria = DRECategoria(
                        tenant_id=tenant_id,
                        nome=bloco["categoria"],
                        natureza=bloco["natureza"],
                        ordem=bloco["ordem"],
                        ativo=True,
                    )
                    db.add(categoria)
                    db.flush()
                    logger.info(f"  ✅ Categoria criada: {bloco['categoria']}")

                # Criar subcategorias
                for nome, tipo_custo, base_rateio in bloco["subcategorias"]:
                    existe = (
                        db.query(DRESubcategoria)
                        .filter(
                            DRESubcategoria.tenant_id == tenant_id,
                            DRESubcategoria.nome == nome,
                        )
                        .first()
                    )

                    if existe:
                        logger.info(f"  ⏭️  Subcategoria já existe: {nome}")
                        continue

                    sub = DRESubcategoria(
                        tenant_id=tenant_id,
                        categoria_id=categoria.id,
                        nome=nome,
                        tipo_custo=tipo_custo,
                        base_rateio=base_rateio,
                        escopo_rateio=EscopoRateio.AMBOS,
                        ativo=True,
                    )
                    db.add(sub)
                    logger.info(f"  ✅ Subcategoria criada: {nome}")

            db.commit()
            logger.info(f"✅ Plano de contas criado para tenant {tenant_id}\n")

        logger.info("🎉 Seed de plano de contas DRE concluído com sucesso!")

    except Exception as e:
        db.rollback()
        logger.info(f"❌ Erro ao executar seed: {e}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed()
