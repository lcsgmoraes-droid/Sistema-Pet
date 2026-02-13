"""
🔄 DEDUPLICAÇÃO DE CLIENTES

Remove clientes duplicados mantendo o registro com telefone/celular.
Critério: clientes com mesmo `codigo` são considerados duplicados.
"""

import sys
sys.path.insert(0, r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend")

from app.db import SessionLocal
from app.models import Cliente
from sqlalchemy import func, text

def deduplicar_clientes():
    """Remove duplicatas de clientes mantendo o que tem telefone/celular"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*70)
        print("DEDUPLICAÇÃO DE CLIENTES".center(70))
        print("="*70)
        
        # 1. Encontrar códigos duplicados
        print("\n[1/4] Identificando clientes duplicados...")
        duplicados = db.execute(text("""
            SELECT codigo, COUNT(*) as total
            FROM clientes
            WHERE codigo IS NOT NULL
            GROUP BY codigo
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
        """)).fetchall()
        
        print(f"   ✓ Encontrados {len(duplicados)} códigos duplicados")
        
        if len(duplicados) == 0:
            print("\n✅ Nenhum cliente duplicado encontrado!")
            return
        
        # 2. Para cada código duplicado, manter o melhor registro
        print("\n[2/4] Analisando duplicatas...")
        total_removidos = 0
        
        for codigo, total in duplicados:
            # Buscar todos os registros com este código
            registros = db.query(Cliente).filter(Cliente.codigo == codigo).order_by(
                # Priorizar registros COM telefone/celular
                Cliente.celular.desc().nullsfirst(),
                Cliente.telefone.desc().nullsfirst(),
                Cliente.id.asc()  # Se empate, manter o mais antigo (menor ID)
            ).all()
            
            if len(registros) <= 1:
                continue
            
            # Manter o primeiro (melhor) registro
            manter = registros[0]
            remover = registros[1:]
            
            print(f"\n   Código {codigo}: {len(registros)} registros")
            print(f"      MANTER → ID {manter.id} - {manter.nome}")
            print(f"               Tel: {manter.telefone or 'N/A'} | Cel: {manter.celular or 'N/A'}")
            
            # 3. Atualizar referências de Pets antes de deletar
            for registro in remover:
                # Contar pets vinculados
                pets_count = db.execute(text(
                    "SELECT COUNT(*) FROM pets WHERE cliente_id = :id"
                ), {"id": registro.id}).scalar()
                
                if pets_count > 0:
                    print(f"      REMOVER → ID {registro.id} - {registro.nome} ({pets_count} pets)")
                    print(f"                Movendo pets para ID {manter.id}...")
                    db.execute(text(
                        "UPDATE pets SET cliente_id = :novo WHERE cliente_id = :antigo"
                    ), {"novo": manter.id, "antigo": registro.id})
                else:
                    print(f"      REMOVER → ID {registro.id} - {registro.nome}")
                
                # Deletar o registro duplicado
                db.delete(registro)
                total_removidos += 1
        
        # 4. Commit das mudanças
        print(f"\n[3/4] Salvando alterações...")
        db.commit()
        print(f"   ✓ {total_removidos} registros duplicados removidos")
        
        # 5. Verificar resultado
        print(f"\n[4/4] Verificando resultado...")
        duplicados_final = db.execute(text("""
            SELECT codigo, COUNT(*) as total
            FROM clientes
            WHERE codigo IS NOT NULL
            GROUP BY codigo
            HAVING COUNT(*) > 1
        """)).fetchall()
        
        if len(duplicados_final) == 0:
            print("   ✓ Nenhuma duplicata restante!")
        else:
            print(f"   ⚠️ Ainda existem {len(duplicados_final)} códigos duplicados")
        
        # Estatísticas finais
        total_clientes = db.query(func.count(Cliente.id)).scalar()
        com_telefone = db.query(func.count(Cliente.id)).filter(
            (Cliente.telefone != None) | (Cliente.celular != None)
        ).scalar()
        
        print("\n" + "="*70)
        print("RESULTADO FINAL".center(70))
        print("="*70)
        print(f"  Total de clientes: {total_clientes}")
        print(f"  Com telefone/celular: {com_telefone} ({com_telefone/total_clientes*100:.1f}%)")
        print(f"  Registros removidos: {total_removidos}")
        print("="*70)
        print("\n✅ DEDUPLICAÇÃO CONCLUÍDA!\n")
        
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("\n⚠️  ATENÇÃO: Este script irá DELETAR registros duplicados!")
    print("   Critério: clientes com mesmo 'codigo'")
    print("   Prioridade: mantém registro com telefone/celular")
    
    resposta = input("\nDeseja continuar? (SIM para confirmar): ")
    
    if resposta.upper() == "SIM":
        deduplicar_clientes()
    else:
        print("\n❌ Operação cancelada pelo usuário.\n")
