"""
VALIDAÇÃO AUTOMÁTICA DE PRODUTOS COM VARIAÇÃO
Sprint 2 - Sistema Pet Shop Pro (ENTERPRISE)

Este script valida que a arquitetura de produtos com variação está correta:
- Produtos pai não possuem preço
- Produtos pai não possuem estoque
- Variações possuem variation_signature
- Integridade de dados garantida
- Constraint único existe no banco

Executar após cada deploy ou migração para garantir que não há regressão.
"""

from app.db import SessionLocal
from app.produtos_models import Produto
from sqlalchemy import text

def validar_constraint_unico():
    """Valida que o constraint único existe no banco"""
    db = SessionLocal()
    erros = []
    
    try:
        # Verificar se constraint existe
        result = db.execute(text("""
            SELECT COUNT(*) as count
            FROM information_schema.table_constraints
            WHERE constraint_name = 'uq_produtos_variation_signature'
            AND table_name = 'produtos'
        """))
        
        count = result.fetchone()[0]
        
        if count == 0:
            erros.append("❌ CONSTRAINT ÚNICO 'uq_produtos_variation_signature' NÃO ENCONTRADO no banco de dados")
        else:
            print("✅ Constraint único 'uq_produtos_variation_signature' encontrado no banco")
        
    except Exception as e:
        erros.append(f"❌ Erro ao verificar constraint: {str(e)}")
    finally:
        db.close()
    
    return erros

def validar_produtos_com_variacao():
    """Valida a integridade dos produtos com variação"""
    
    db = SessionLocal()
    erros = []
    warnings = []
    
    try:
        # ====================================================
        # VALIDAÇÃO 1: PRODUTOS PAI NÃO PODEM TER PREÇO
        # ====================================================
        pais = db.query(Produto).filter(Produto.is_parent == True).all()
        
        print(f"\n🔍 Validando {len(pais)} produtos pai...")
        
        for p in pais:
            # Validar preço
            if p.preco_venda and p.preco_venda > 0:
                erros.append(f"❌ Produto pai #{p.id} ('{p.nome}') possui preço de venda: R$ {p.preco_venda}")
            
            # Validar estoque
            if p.estoque_atual and p.estoque_atual > 0:
                erros.append(f"❌ Produto pai #{p.id} ('{p.nome}') possui estoque: {p.estoque_atual}")
        
        # ====================================================
        # VALIDAÇÃO 2: VARIAÇÕES DEVEM TER SIGNATURE
        # ====================================================
        variacoes = db.query(Produto).filter(Produto.produto_pai_id != None).all()
        
        print(f"🔍 Validando {len(variacoes)} variações...")
        
        for v in variacoes:
            if not v.variation_signature:
                warnings.append(f"⚠️  Variação #{v.id} ('{v.nome}') sem variation_signature")
            
            # Validar que variação não é marcada como pai
            if v.is_parent:
                erros.append(f"❌ Variação #{v.id} ('{v.nome}') está marcada como is_parent=True (inconsistência)")
        
        # ====================================================
        # VALIDAÇÃO 3: PRODUTOS PAI DEVEM TER VARIAÇÕES
        # ====================================================
        for p in pais:
            count_variacoes = db.query(Produto).filter(
                Produto.produto_pai_id == p.id,
                Produto.ativo == True
            ).count()
            
            if count_variacoes == 0:
                warnings.append(f"⚠️  Produto pai #{p.id} ('{p.nome}') não possui variações ativas")
        
        # ====================================================
        # RESULTADO
        # ====================================================
        print("\n" + "="*60)
        print("RESULTADO DA VALIDAÇÃO")
        print("="*60)
        
        if erros:
            print("\n❌ ERROS CRÍTICOS ENCONTRADOS:")
            for e in erros:
                print(f"   {e}")
            print(f"\nTotal: {len(erros)} erro(s)")
        
        if warnings:
            print("\n⚠️  AVISOS (não bloqueiam o sistema):")
            for w in warnings:
                print(f"   {w}")
            print(f"\nTotal: {len(warnings)} aviso(s)")
        
        if not erros and not warnings:
            print("\n✅ VALIDAÇÃO DE VARIAÇÕES OK")
            print("   Todos os produtos com variação estão corretos!")
        
        print("="*60 + "\n")
        
        # Retornar código de erro se houver erros críticos
        if erros:
            exit(1)
        
        exit(0)
        
    except Exception as e:
        print(f"\n❌ ERRO AO EXECUTAR VALIDAÇÃO: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    print("="*60)
    print("VALIDAÇÃO DE PRODUTOS COM VARIAÇÃO - Sprint 2 (ENTERPRISE)")
    print("="*60)
    
    # Validar constraint único
    print("\n🔍 Validando constraint único no banco...")
    erros_constraint = validar_constraint_unico()
    
    # Validar produtos
    validar_produtos_com_variacao()
    
    # Se houver erros de constraint, forçar exit 1
    if erros_constraint:
        print("\n" + "="*60)
        print("❌ ERROS DE INTEGRIDADE ENCONTRADOS:")
        print("="*60)
        for e in erros_constraint:
            print(f"   {e}")
        exit(1)
