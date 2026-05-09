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
    # =================================================================
    # 1. RECEITAS (Todas entradas de dinheiro)
    # =================================================================
    {
        "categoria": "Receitas de Vendas",
        "natureza": NaturezaDRE.RECEITA,
        "ordem": 1,
        "subcategorias": [
            # Produtos
            ("Vendas de Produtos - Pet Food", TipoCusto.DIRETO, None),
            ("Vendas de Produtos - Acessórios", TipoCusto.DIRETO, None),
            ("Vendas de Produtos - Higiene", TipoCusto.DIRETO, None),
            ("Vendas de Produtos - Medicamentos", TipoCusto.DIRETO, None),
            # Serviços
            ("Serviços - Banho e Tosa", TipoCusto.DIRETO, None),
            ("Serviços - Veterinário", TipoCusto.DIRETO, None),
            ("Serviços - Hotel/Day Care", TipoCusto.DIRETO, None),
            ("Serviços - Adestramento", TipoCusto.DIRETO, None),
        ],
    },
    {
        "categoria": "Outras Receitas",
        "natureza": NaturezaDRE.RECEITA,
        "ordem": 2,
        "subcategorias": [
            ("Receitas Financeiras", TipoCusto.DIRETO, None),
            ("Descontos Obtidos", TipoCusto.DIRETO, None),
            ("Bonificações de Fornecedores", TipoCusto.DIRETO, None),
            ("Outras Receitas Operacionais", TipoCusto.DIRETO, None),
        ],
    },
    
    # =================================================================
    # 2. DEDUÇÕES DA RECEITA
    # =================================================================
    {
        "categoria": "Deduções da Receita",
        "natureza": NaturezaDRE.DESPESA,
        "ordem": 3,
        "subcategorias": [
            ("Devoluções e Cancelamentos", TipoCusto.DIRETO, None),
            ("Descontos Concedidos", TipoCusto.DIRETO, None),
            ("Abatimentos", TipoCusto.DIRETO, None),
        ],
    },
    
    # =================================================================
    # 3. CUSTOS DIRETOS (Custos variáveis ligados às vendas)
    # =================================================================
    {
        "categoria": "Custo das Mercadorias Vendidas (CMV)",
        "natureza": NaturezaDRE.CUSTO,
        "ordem": 4,
        "subcategorias": [
            ("CMV - Pet Food", TipoCusto.DIRETO, None),
            ("CMV - Acessórios", TipoCusto.DIRETO, None),
            ("CMV - Higiene", TipoCusto.DIRETO, None),
            ("CMV - Medicamentos", TipoCusto.DIRETO, None),
            ("CMV - Materiais Serviços", TipoCusto.DIRETO, None),
        ],
    },
    {
        "categoria": "Custos Diretos de Venda",
        "natureza": NaturezaDRE.CUSTO,
        "ordem": 5,
        "subcategorias": [
            ("Fretes sobre Vendas", TipoCusto.DIRETO, None),
            ("Embalagens", TipoCusto.DIRETO, None),
            ("Taxas de Marketplace - Mercado Livre", TipoCusto.DIRETO, None),
            ("Taxas de Marketplace - Shopee", TipoCusto.DIRETO, None),
            ("Taxas de Marketplace - Amazon", TipoCusto.DIRETO, None),
            ("Taxas de Cartão de Crédito", TipoCusto.DIRETO, None),
            ("Taxas de Cartão de Débito", TipoCusto.DIRETO, None),
            ("Taxas PIX/Boleto", TipoCusto.DIRETO, None),
            ("Comissões de Vendas - Vendedores", TipoCusto.DIRETO, None),
            ("Comissões de Vendas - Afiliados", TipoCusto.DIRETO, None),
        ],
    },
    
    # =================================================================
    # 4. DESPESAS OPERACIONAIS - PESSOAL
    # =================================================================
    {
        "categoria": "Despesas com Pessoal",
        "natureza": NaturezaDRE.DESPESA,
        "ordem": 6,
        "subcategorias": [
            # Salários
            ("Salários - Administrativo", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Salários - Vendas", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Salários - Operacional", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Pró-Labore Sócios", TipoCusto.CORPORATIVO, None),
            # Encargos
            ("INSS Patronal", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("FGTS", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("PIS sobre Folha", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("IRRF sobre Folha", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Contribuição Sindical", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            # Benefícios
            ("Vale Transporte", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Vale Alimentação/Refeição", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Plano de Saúde", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Seguro de Vida", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Auxílio Creche", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            # Outros
            ("Férias e 13º Salário", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Rescisões", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Treinamento e Capacitação", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Uniformes", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
        ],
    },
    
    # =================================================================
    # 5. DESPESAS OPERACIONAIS - OCUPAÇÃO
    # =================================================================
    {
        "categoria": "Despesas de Ocupação",
        "natureza": NaturezaDRE.DESPESA,
        "ordem": 7,
        "subcategorias": [
            ("Aluguel - Loja", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Aluguel - Escritório", TipoCusto.CORPORATIVO, None),
            ("Condomínio", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("IPTU", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Energia Elétrica", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Água e Esgoto", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Gás", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Internet e Telefonia", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Segurança e Alarme", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Limpeza e Conservação", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Manutenção Predial", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
        ],
    },
    
    # =================================================================
    # 6. DESPESAS OPERACIONAIS - COMERCIAL/MARKETING
    # =================================================================
    {
        "categoria": "Despesas Comerciais",
        "natureza": NaturezaDRE.DESPESA,
        "ordem": 8,
        "subcategorias": [
            ("Marketing Digital - Google Ads", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Marketing Digital - Facebook/Instagram Ads", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Marketing Digital - TikTok Ads", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Marketing Tradicional - Panfletos/Outdoor", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Brindes e Amostras Grátis", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Programas de Fidelidade", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Eventos e Patrocínios", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Material de Ponto de Venda", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Agência de Marketing", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
        ],
    },
    
    # =================================================================
    # 7. DESPESAS OPERACIONAIS - ADMINISTRATIVAS
    # =================================================================
    {
        "categoria": "Despesas Administrativas",
        "natureza": NaturezaDRE.DESPESA,
        "ordem": 9,
        "subcategorias": [
            ("Contabilidade", TipoCusto.CORPORATIVO, None),
            ("Assessoria Jurídica", TipoCusto.CORPORATIVO, None),
            ("Softwares e Sistemas - ERP", TipoCusto.CORPORATIVO, None),
            ("Softwares e Sistemas - E-commerce", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Softwares e Sistemas - Gestão", TipoCusto.CORPORATIVO, None),
            ("Correios e Sedex", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Material de Escritório", TipoCusto.CORPORATIVO, None),
            ("Material de Limpeza", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Cópias e Impressões", TipoCusto.CORPORATIVO, None),
            ("Assinaturas e Anuidades", TipoCusto.CORPORATIVO, None),
            ("Taxas e Certificados Digitais", TipoCusto.CORPORATIVO, None),
        ],
    },
    
    # =================================================================
    # 8. DESPESAS OPERACIONAIS - VEÍCULOS E LOGÍSTICA
    # =================================================================
    {
        "categoria": "Despesas com Veículos",
        "natureza": NaturezaDRE.DESPESA,
        "ordem": 10,
        "subcategorias": [
            ("Combustível", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Manutenção de Veículos", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("IPVA", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Seguro de Veículos", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Licenciamento", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Estacionamento", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Pedágios", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
        ],
    },
    
    # =================================================================
    # 9. DESPESAS OPERACIONAIS - TRIBUTOS
    # =================================================================
    {
        "categoria": "Tributos sobre Vendas",
        "natureza": NaturezaDRE.DESPESA,
        "ordem": 11,
        "subcategorias": [
            ("Simples Nacional", TipoCusto.DIRETO, None),
            ("ICMS", TipoCusto.DIRETO, None),
            ("PIS/COFINS", TipoCusto.DIRETO, None),
            ("ISS", TipoCusto.DIRETO, None),
        ],
    },
    
    # =================================================================
    # 10. DESPESAS FINANCEIRAS
    # =================================================================
    {
        "categoria": "Despesas Financeiras",
        "natureza": NaturezaDRE.DESPESA,
        "ordem": 12,
        "subcategorias": [
            ("Juros de Empréstimos", TipoCusto.CORPORATIVO, None),
            ("Juros de Financiamentos", TipoCusto.CORPORATIVO, None),
            ("Tarifas Bancárias", TipoCusto.CORPORATIVO, None),
            ("IOF", TipoCusto.CORPORATIVO, None),
            ("Multas e Juros por Atraso", TipoCusto.CORPORATIVO, None),
            ("Descontos Concedidos Financeiros", TipoCusto.CORPORATIVO, None),
        ],
    },
    
    # =================================================================
    # 11. OUTRAS DESPESAS
    # =================================================================
    {
        "categoria": "Outras Despesas Operacionais",
        "natureza": NaturezaDRE.DESPESA,
        "ordem": 13,
        "subcategorias": [
            ("Depreciação", TipoCusto.CORPORATIVO, None),
            ("Amortização", TipoCusto.CORPORATIVO, None),
            ("Perdas com Créditos Incobráveis", TipoCusto.CORPORATIVO, None),
            ("Seguros Gerais", TipoCusto.INDIRETO_RATEAVEL, BaseRateio.FATURAMENTO),
            ("Doações", TipoCusto.CORPORATIVO, None),
            ("Multas e Penalidades", TipoCusto.CORPORATIVO, None),
            ("Despesas Não Operacionais", TipoCusto.CORPORATIVO, None),
        ],
    },
]


def seed_tenant_dre_plano_contas(db: Session, tenant_id):
    """Cria o plano de contas DRE padrao para um tenant especifico."""
    logger.info(f"Populando plano de contas DRE para tenant {tenant_id}")

    for bloco in PLANO_CONTAS:
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
            logger.info(f"  Categoria criada: {bloco['categoria']}")

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
                logger.info(f"  Subcategoria ja existe: {nome}")
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
            logger.info(f"  Subcategoria criada: {nome}")


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
