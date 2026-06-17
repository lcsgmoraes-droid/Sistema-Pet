"""
Criar tabelas para Formas de Pagamento com Taxas e Configuração de Impostos
"""

import sys
from pathlib import Path

# Adicionar o diretório pai ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import engine, SessionLocal
from app.formas_pagamento_models import FormaPagamentoTaxa, ConfiguracaoImposto
from app.financeiro_models import FormaPagamento
from app.utils.logger import logger


def criar_tabelas():
    """Cria as tabelas de formas de pagamento e configurações"""

    logger.info("🔧 Criando tabelas de formas de pagamento e taxas...")

    # Criar tabelas
    FormaPagamentoTaxa.__table__.create(engine, checkfirst=True)
    ConfiguracaoImposto.__table__.create(engine, checkfirst=True)

    logger.info("✅ Tabelas criadas com sucesso!")

    # Criar configuração de imposto padrão
    db = SessionLocal()
    try:
        # Verificar se já existe configuração padrão
        config_existente = (
            db.query(ConfiguracaoImposto)
            .filter(ConfiguracaoImposto.padrao.is_(True))
            .first()
        )

        if not config_existente:
            logger.info("📝 Criando configuração de imposto padrão...")

            config_padrao = ConfiguracaoImposto(
                nome="Simples Nacional",
                percentual=5.0,  # 5%
                ativo=True,
                padrao=True,
                descricao="Imposto padrão - Simples Nacional (estimativa 5%)",
            )

            db.add(config_padrao)
            db.commit()

            logger.info("✅ Configuração de imposto padrão criada!")
        else:
            logger.info("ℹ️  Configuração de imposto padrão já existe")

        # Verificar se existem formas de pagamento cadastradas
        formas = db.query(FormaPagamento).filter(FormaPagamento.ativo.is_(True)).all()

        if formas:
            logger.info(f"\n📋 Formas de pagamento cadastradas: {len(formas)}")

            for forma in formas[:5]:  # Mostrar primeiras 5
                logger.info(f"   - {forma.nome} ({forma.tipo})")

                # Verificar se já tem taxas
                qtd_taxas = (
                    db.query(FormaPagamentoTaxa)
                    .filter(FormaPagamentoTaxa.forma_pagamento_id == forma.id)
                    .count()
                )

                if qtd_taxas > 0:
                    logger.info(f"     ✓ {qtd_taxas} taxa(s) cadastrada(s)")
                else:
                    logger.info(
                        "     ⚠️  Nenhuma taxa cadastrada - configure no sistema"
                    )

            if len(formas) > 5:
                logger.info(f"   ... e mais {len(formas) - 5} formas de pagamento")
        else:
            logger.info("\n⚠️  Nenhuma forma de pagamento cadastrada")
            logger.info(
                "   Configure formas de pagamento no sistema para usar a análise de vendas"
            )

    except Exception as e:
        logger.info(f"❌ Erro ao criar configurações: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    criar_tabelas()
    logger.info("\n✅ Migração concluída!")
    logger.info("\n📝 Próximos passos:")
    logger.info("   1. Configure as taxas para cada forma de pagamento")
    logger.info("   2. Ajuste o percentual de imposto se necessário")
    logger.info("   3. Use o endpoint POST /formas-pagamento/analisar-venda no PDV")
