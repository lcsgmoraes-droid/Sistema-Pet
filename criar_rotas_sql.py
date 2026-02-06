"""
Script para criar rotas retroativamente usando SQL direto
"""
import psycopg2
from datetime import datetime

# Conectar ao banco
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="petshop_db",
    user="petshop_user",
    password="petshop_password"
)

cursor = conn.cursor()

try:
    # Buscar tenant_id e entregador padrão
    cursor.execute("""
        SELECT DISTINCT v.tenant_id, c.id as entregador_id, c.nome
        FROM vendas v
        JOIN clientes c ON c.tenant_id = v.tenant_id
        WHERE c.entregador_padrao = true AND c.entregador_ativo = true
        LIMIT 1
    """)
    
    result = cursor.fetchone()
    if not result:
        print("❌ Nenhum entregador padrão encontrado!")
        exit(1)
    
    tenant_id, entregador_id, entregador_nome = result
    print(f"✓ Entregador padrão: {entregador_nome} (ID: {entregador_id})")
    print(f"✓ Tenant ID: {tenant_id}")
    
    # Buscar ponto inicial da configuração
    cursor.execute("""
        SELECT ponto_inicial_rota 
        FROM configuracoes_entrega 
        WHERE tenant_id = %s
    """, (tenant_id,))
    
    config = cursor.fetchone()
    ponto_inicial = config[0] if config else None
    if ponto_inicial:
        print(f"✓ Ponto inicial: {ponto_inicial}")
    
    # Buscar vendas sem rota
    cursor.execute("""
        SELECT v.id, v.numero_venda, v.endereco_entrega, v.valor_entrega
        FROM vendas v
        LEFT JOIN rotas_entrega r ON r.venda_id = v.id
        WHERE v.tem_entrega = true 
        AND v.status = 'aberta'
        AND r.id IS NULL
        ORDER BY v.id
    """)
    
    vendas = cursor.fetchall()
    print(f"\n✓ Encontradas {len(vendas)} vendas sem rota\n")
    
    rotas_criadas = 0
    
    for venda_id, numero_venda, endereco, valor_entrega in vendas:
        print(f"Processando venda {numero_venda} (ID: {venda_id})...")
        print(f"  Endereço: {endereco}")
        
        # Criar a rota
        cursor.execute("""
            INSERT INTO rotas_entrega (
                tenant_id, venda_id, entregador_id, endereco_destino,
                status, taxa_entrega_cliente, ponto_inicial_rota,
                created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            tenant_id,
            venda_id,
            entregador_id,
            endereco,
            "pendente",
            valor_entrega or 0.0,
            ponto_inicial,
            datetime.utcnow(),
            datetime.utcnow()
        ))
        
        rotas_criadas += 1
        print(f"  ✅ Rota criada!\n")
    
    # Commit
    conn.commit()
    
    print(f"{'='*60}")
    print(f"✅ SUCESSO: {rotas_criadas} rotas criadas!")
    print(f"{'='*60}")
    
except Exception as e:
    print(f"\n❌ Erro: {e}")
    conn.rollback()
    raise
finally:
    cursor.close()
    conn.close()
