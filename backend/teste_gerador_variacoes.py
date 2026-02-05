"""
Script de Teste - Gerador de Variações

Demonstra o funcionamento do GeradorVariacoesService
sem modificar dados reais.

Para usar de verdade:
1. Criar produto PAI
2. Criar atributos (Peso, Sabor, etc)
3. Criar opções para cada atributo
4. Executar generate_variacoes()
"""

from app.db import SessionLocal
from app.services.gerador_variacoes_service import GeradorVariacoesService

def testar_gerador_dry_run():
    """
    Teste DRY RUN - apenas mostra como usar o service
    """
    
    print("=" * 60)
    print("TESTE DRY RUN - GeradorVariacoesService")
    print("=" * 60)
    
    print("\n📖 Como usar o GeradorVariacoesService:")
    print("-" * 60)
    
    print("""
1️⃣ CRIAR PRODUTO PAI:
   produto_pai = Produto(
       codigo='PROD-PAI-001',
       nome='Ração Golden Adulto',
       tipo_produto='PAI',
       user_id=1
   )

2️⃣ CRIAR ATRIBUTOS:
   atributo_peso = ProdutoAtributo(
       produto_pai_id=produto_pai.id,
       nome='Peso',
       ordem=1,
       user_id=1
   )
   
   atributo_sabor = ProdutoAtributo(
       produto_pai_id=produto_pai.id,
       nome='Sabor',
       ordem=2,
       user_id=1
   )

3️⃣ CRIAR OPÇÕES:
   # Opções de Peso
   ProdutoAtributoOpcao(atributo_id=peso.id, valor='1kg', ordem=1)
   ProdutoAtributoOpcao(atributo_id=peso.id, valor='3kg', ordem=2)
   ProdutoAtributoOpcao(atributo_id=peso.id, valor='15kg', ordem=3)
   
   # Opções de Sabor
   ProdutoAtributoOpcao(atributo_id=sabor.id, valor='Carne', ordem=1)
   ProdutoAtributoOpcao(atributo_id=sabor.id, valor='Frango', ordem=2)

4️⃣ GERAR VARIAÇÕES AUTOMATICAMENTE:
   db = SessionLocal()
   try:
       variacoes = GeradorVariacoesService.generate_variacoes(
           produto_pai_id=produto_pai.id,
           db=db,
           user_id=1
       )
       
       print(f"✅ {len(variacoes)} variações criadas!")
       for v in variacoes:
           print(f"  - {v.nome}")
           
   finally:
       db.close()

5️⃣ RESULTADO ESPERADO:
   6 variações criadas:
   ✓ Ração Golden Adulto - 1kg - Carne
   ✓ Ração Golden Adulto - 1kg - Frango
   ✓ Ração Golden Adulto - 3kg - Carne
   ✓ Ração Golden Adulto - 3kg - Frango
   ✓ Ração Golden Adulto - 15kg - Carne
   ✓ Ração Golden Adulto - 15kg - Frango

6️⃣ IMPORTANTE:
   - Cada variação é criada com preco_venda = 0
   - Cada variação é criada com estoque = 0
   - Usuário deve definir preços e estoque depois
   - Se executar novamente, variações existentes são ignoradas
    """)
    
    print("\n" + "=" * 60)
    print("✅ Teste concluído - Nenhum dado foi modificado")
    print("=" * 60)


if __name__ == '__main__':
    testar_gerador_dry_run()
