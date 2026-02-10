-- Script para adicionar permissões completas a roles de Administrador existentes
-- Útil para corrigir tenants criados antes da implementação automática de permissões
-- Execute: Get-Content backend\scripts\fix_admin_permissions.sql | docker exec -i petshop-dev-postgres psql -U postgres -d petshop_dev

-- Primeiro, garantir que todas as permissões necessárias existem
INSERT INTO permissions (code, description) VALUES 
  ('compras.gerenciar', 'Gerenciar compras e pedidos'),
  ('ia.fluxo_caixa', 'Acessar IA de Fluxo de Caixa'),
  ('ia.whatsapp', 'Acessar Bot WhatsApp'),
  ('usuarios.manage', 'Gerenciar usuários e permissões (frontend)')
ON CONFLICT (code) DO NOTHING;

-- Adicionar todas as permissões a todas as roles chamadas 'Administrador' que não têm permissões completas
INSERT INTO role_permissions (role_id, permission_id, tenant_id)
SELECT 
    r.id as role_id,
    p.id as permission_id,
    r.tenant_id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'Administrador'
  AND NOT EXISTS (
    SELECT 1 
    FROM role_permissions rp 
    WHERE rp.role_id = r.id 
      AND rp.permission_id = p.id
  )
ORDER BY r.id, p.id;

-- Mostrar resultado
SELECT 
    r.id as role_id,
    r.name as role_name,
    COUNT(rp.id) as total_permissions,
    r.tenant_id
FROM roles r
LEFT JOIN role_permissions rp ON r.id = rp.role_id
WHERE r.name = 'Administrador'
GROUP BY r.id, r.name, r.tenant_id
ORDER BY r.id;

-- Detalhes das permissões por role
SELECT 
    r.id as role_id,
    r.name as role_name,
    p.code as permission_code
FROM roles r
JOIN role_permissions rp ON r.id = rp.role_id
JOIN permissions p ON rp.permission_id = p.id
WHERE r.name = 'Administrador'
ORDER BY r.id, p.code;
