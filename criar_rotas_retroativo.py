"""
Script para criar rotas retroativamente para vendas abertas com entrega
"""
import asyncio
import sys
from pathlib import Path

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, and_
from datetime import datetime

from app.vendas.models import Venda
from app.rotas_entrega_models import RotaEntrega
from app.clientes_models import Cliente
from app.configuracao_entrega_models import ConfiguracaoEntrega


async def criar_rotas_retroativas():
    """Cria rotas para todas as vendas abertas com entrega que não têm rota"""
    
    # Database connection
    DATABASE_URL = "postgresql+asyncpg://petshop_user:petshop_password@localhost:5432/petshop_db"
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session_maker() as session:
        try:
            # Buscar vendas abertas com entrega que não têm rota
            stmt = (
                select(Venda)
                .outerjoin(RotaEntrega, RotaEntrega.venda_id == Venda.id)
                .where(
                    and_(
                        Venda.tem_entrega == True,
                        Venda.status == "aberta",
                        RotaEntrega.id == None  # Não tem rota
                    )
                )
            )
            
            result = await session.execute(stmt)
            vendas_sem_rota = result.scalars().all()
            
            print(f"\nEncontradas {len(vendas_sem_rota)} vendas sem rota")
            
            rotas_criadas = 0
            
            for venda in vendas_sem_rota:
                print(f"\nProcessando venda {venda.numero_venda} (ID: {venda.id})")
                print(f"  Endereço: {venda.endereco_entrega}")
                
                # Buscar entregador padrão do tenant
                stmt_entregador = select(Cliente).where(
                    and_(
                        Cliente.tenant_id == venda.tenant_id,
                        Cliente.entregador_padrao == True,
                        Cliente.entregador_ativo == True
                    )
                )
                result = await session.execute(stmt_entregador)
                entregador = result.scalar_one_or_none()
                
                if not entregador:
                    print(f"  ⚠️  Nenhum entregador padrão encontrado para o tenant")
                    continue
                
                print(f"  Entregador: {entregador.nome} (ID: {entregador.id})")
                
                # Buscar configuração de entrega
                stmt_config = select(ConfiguracaoEntrega).where(
                    ConfiguracaoEntrega.tenant_id == venda.tenant_id
                )
                result = await session.execute(stmt_config)
                config = result.scalar_one_or_none()
                
                ponto_inicial = None
                if config and config.ponto_inicial_rota:
                    ponto_inicial = config.ponto_inicial_rota
                    print(f"  Ponto inicial: {ponto_inicial}")
                
                # Criar a rota
                nova_rota = RotaEntrega(
                    tenant_id=venda.tenant_id,
                    venda_id=venda.id,
                    entregador_id=entregador.id,
                    endereco_destino=venda.endereco_entrega,
                    status="pendente",
                    taxa_entrega_cliente=venda.valor_entrega or 0.0,
                    ponto_inicial_rota=ponto_inicial,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                session.add(nova_rota)
                rotas_criadas += 1
                print(f"  ✅ Rota criada com status 'pendente'")
            
            # Commit todas as rotas de uma vez
            await session.commit()
            
            print(f"\n{'='*60}")
            print(f"RESUMO: {rotas_criadas} rotas criadas com sucesso!")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"\n❌ Erro ao criar rotas: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(criar_rotas_retroativas())
