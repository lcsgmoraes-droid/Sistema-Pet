"""
Teste de Estorno de Comissões
Valida funcionalidade implementada na Sprint 3 - Hardening Financeiro
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.db import get_db_connection
from app.comissoes_estorno import estornar_comissoes_venda


def criar_comissao_teste():
    """Cria uma comissão de teste"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Inserir comissão fake
    cursor.execute("""
        INSERT INTO comissoes_itens (
            venda_id, venda_item_id, funcionario_id, produto_id, configuracao_id,
            quantidade, valor_item, custo_item,
            tipo_calculo, base_calculo, percentual, valor_comissao,
            status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        9999,  # venda_id teste
        1, 1, 1, 1,  # IDs fake
        1.0, 100.0, 50.0,  # quantidade, valor, custo
        'percentual', 100.0, 10.0, 10.0,  # cálculo
        'pendente'  # status
    ))
    
    comissao_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return comissao_id


def limpar_teste():
    """Remove dados de teste"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM comissoes_itens WHERE venda_id = 9999")
    conn.commit()
    conn.close()


def testar_estorno():
    """Testa funcionalidade de estorno"""
    
    print("\n" + "="*60)
    print("TESTE: Estorno de Comissões")
    print("="*60 + "\n")
    
    # Limpar dados anteriores
    limpar_teste()
    
    # 1. Criar comissão de teste
    print("1️⃣ Criando comissão de teste...")
    comissao_id = criar_comissao_teste()
    print(f"   ✅ Comissão criada (ID: {comissao_id})")
    
    # 2. Estornar pela primeira vez
    print("\n2️⃣ Testando estorno (primeira vez)...")
    resultado = estornar_comissoes_venda(
        venda_id=9999,
        motivo="Teste de estorno",
        usuario_id=1
    )
    
    print(f"   Success: {resultado['success']}")
    print(f"   Quantidade estornada: {resultado['comissoes_estornadas']}")
    print(f"   Valor estornado: R$ {resultado['valor_estornado']:.2f}")
    print(f"   Duplicated: {resultado['duplicated']}")
    
    assert resultado['success'] == True, "Estorno deveria ter sucesso"
    assert resultado['comissoes_estornadas'] == 1, "Deveria estornar 1 comissão"
    assert resultado['duplicated'] == False, "Primeira vez não é duplicação"
    print("   ✅ PASSOU")
    
    # 3. Estornar novamente (idempotência)
    print("\n3️⃣ Testando idempotência (segunda vez)...")
    resultado2 = estornar_comissoes_venda(
        venda_id=9999,
        motivo="Teste de estorno",
        usuario_id=1
    )
    
    print(f"   Success: {resultado2['success']}")
    print(f"   Quantidade estornada: {resultado2['comissoes_estornadas']}")
    print(f"   Duplicated: {resultado2['duplicated']}")
    
    assert resultado2['success'] == True, "Deveria retornar sucesso"
    assert resultado2['comissoes_estornadas'] == 0, "Não deveria estornar novamente"
    assert resultado2['duplicated'] == True, "Deveria detectar duplicação"
    print("   ✅ PASSOU (Idempotência OK)")
    
    # 4. Verificar estado final no banco
    print("\n4️⃣ Verificando estado no banco...")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT status, data_estorno, motivo_estorno, estornado_por
        FROM comissoes_itens WHERE id = ?
    """, (comissao_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    print(f"   Status: {row[0]}")
    print(f"   Data estorno: {row[1]}")
    print(f"   Motivo: {row[2]}")
    print(f"   Estornado por: {row[3]}")
    
    assert row[0] == 'estornado', "Status deveria ser 'estornado'"
    assert row[1] is not None, "Data de estorno deveria estar preenchida"
    assert row[2] == "Teste de estorno", "Motivo deveria estar correto"
    assert row[3] == 1, "Estornado_por deveria ser 1"
    print("   ✅ PASSOU")
    
    # Limpar
    print("\n5️⃣ Limpando dados de teste...")
    limpar_teste()
    print("   ✅ Limpo")
    
    print("\n" + "="*60)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("="*60 + "\n")


if __name__ == '__main__':
    try:
        testar_estorno()
    except AssertionError as e:
        print(f"\n❌ FALHA: {e}\n")
        exit(1)
    except Exception as e:
        print(f"\n❌ ERRO: {e}\n")
        import traceback
        traceback.print_exc()
        exit(1)
