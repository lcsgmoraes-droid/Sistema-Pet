"""
Configurar Roles e Permissões Funcionais do Sistema
"""
import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "petshop_db",
    "user": "petshop_user",
    "password": "petshop_password_2026"
}

def configurar_roles():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        print("🔧 Configurando Roles e Permissões...\n")
        
        # Buscar tenant padrão (primeiro tenant do sistema)
        cur.execute("SELECT id FROM tenants ORDER BY created_at LIMIT 1")
        tenant_row = cur.fetchone()
        if not tenant_row:
            print("❌ Nenhum tenant encontrado!")
            return
        
        tenant_id = tenant_row[0]
        print(f"🏢 Usando tenant: {tenant_id}\n")
        
        # Buscar todas as permissões disponíveis
        cur.execute("SELECT id, code FROM permissions")
        permissions_map = {code: perm_id for perm_id, code in cur.fetchall()}
        
        print(f"📋 {len(permissions_map)} permissões encontradas\n")
        
        # Definir roles e suas permissões
        roles_config = {
            "admin": {
                "permissions": list(permissions_map.keys()),  # Todas as permissões
                "descricao": "Administrador - Acesso total ao sistema"
            },
            "gerente": {
                "permissions": [
                    "clientes.visualizar", "clientes.criar", "clientes.editar",
                    "produtos.visualizar", "produtos.criar", "produtos.editar",
                    "vendas.visualizar", "vendas.criar", "vendas.editar",
                    "relatorios.financeiro", "relatorios.gerencial",
                    "configuracoes.editar"
                ],
                "descricao": "Gerente - Acesso a operações e relatórios"
            },
            "caixa": {
                "permissions": [
                    "clientes.visualizar", "clientes.criar", "clientes.editar",
                    "produtos.visualizar",
                    "vendas.visualizar", "vendas.criar", "vendas.editar"
                ],
                "descricao": "Caixa/Vendedor - PDV e atendimento ao cliente"
            },
            "estoque": {
                "permissions": [
                    "produtos.visualizar", "produtos.criar", "produtos.editar",
                    "clientes.visualizar"  # Para entrada de produtos
                ],
                "descricao": "Estoquista - Gestão de produtos e compras"
            },
            "visualizador": {
                "permissions": [
                    "clientes.visualizar",
                    "produtos.visualizar",
                    "vendas.visualizar"
                ],
                "descricao": "Visualizador - Apenas consulta (sem edição)"
            }
        }
        
        for role_name, config in roles_config.items():
            # Verificar se role já existe
            cur.execute("SELECT id FROM roles WHERE name = %s", (role_name,))
            role_row = cur.fetchone()
            
            if role_row:
                role_id = role_row[0]
                print(f"✏️  Atualizando role: {role_name} (ID: {role_id})")
                
                # Limpar permissões antigas
                cur.execute("DELETE FROM role_permissions WHERE role_id = %s", (role_id,))
            else:
                # Criar nova role
                cur.execute("INSERT INTO roles (name) VALUES (%s) RETURNING id", (role_name,))
                role_id = cur.fetchone()[0]
                print(f"✅ Criando role: {role_name} (ID: {role_id})")
            
            # Adicionar permissões
            permissions_added = 0
            for perm_code in config["permissions"]:
                if perm_code in permissions_map:
                    perm_id = permissions_map[perm_code]
                    cur.execute(
                        "INSERT INTO role_permissions (role_id, permission_id, tenant_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                        (role_id, perm_id, tenant_id)
                    )
                    permissions_added += 1
            
            print(f"   📌 {permissions_added} permissões vinculadas")
            print(f"   📝 {config['descricao']}\n")
        
        conn.commit()
        
        print("=" * 60)
        print("✅ Configuração de roles concluída com sucesso!\n")
        
        # Mostrar resumo
        cur.execute("""
            SELECT r.name, COUNT(rp.permission_id) as total_perms
            FROM roles r
            LEFT JOIN role_permissions rp ON rp.role_id = r.id
            GROUP BY r.id, r.name
            ORDER BY r.name
        """)
        
        print("📊 RESUMO DAS ROLES:\n")
        for role_name, total_perms in cur.fetchall():
            print(f"   {role_name:20s} → {total_perms} permissões")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    configurar_roles()
