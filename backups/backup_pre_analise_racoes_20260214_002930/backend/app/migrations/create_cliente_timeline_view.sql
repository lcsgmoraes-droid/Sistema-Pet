-- ============================================================
-- VIEW: TIMELINE UNIFICADA DO CLIENTE
-- Consolida eventos financeiros e de pets
-- ============================================================

CREATE VIEW IF NOT EXISTS cliente_timeline AS

-- 1️⃣ VENDAS
SELECT 
    'venda' as tipo_evento,
    v.id as evento_id,
    v.cliente_id,
    NULL as pet_id,
    v.data_venda as data_evento,
    'Venda #' || v.numero_venda as titulo,
    'R$ ' || printf('%.2f', v.total) || ' - ' || v.status as descricao,
    v.status,
    CASE v.status 
        WHEN 'finalizada' THEN 'green'
        WHEN 'pendente' THEN 'yellow'
        WHEN 'cancelada' THEN 'red'
        ELSE 'gray'
    END as cor_badge
FROM vendas v
WHERE v.cliente_id IS NOT NULL

UNION ALL

-- 2️⃣ CONTAS A RECEBER
SELECT 
    'conta_receber' as tipo_evento,
    cr.id as evento_id,
    cr.cliente_id,
    NULL as pet_id,
    cr.data_vencimento as data_evento,
    'Conta a Receber' as titulo,
    'R$ ' || printf('%.2f', cr.valor_original) || ' - ' || cr.descricao as descricao,
    cr.status,
    CASE cr.status 
        WHEN 'recebido' THEN 'green'
        WHEN 'pendente' THEN 'yellow'
        WHEN 'vencido' THEN 'red'
        WHEN 'cancelado' THEN 'gray'
        ELSE 'blue'
    END as cor_badge
FROM contas_receber cr
WHERE cr.cliente_id IS NOT NULL

UNION ALL

-- 3️⃣ PETS - CADASTRO
SELECT 
    'pet_cadastro' as tipo_evento,
    p.id as evento_id,
    p.cliente_id,
    p.id as pet_id,
    p.created_at as data_evento,
    '🐾 Pet cadastrado: ' || p.nome as titulo,
    p.especie || COALESCE(' - ' || p.raca, '') as descricao,
    CASE p.ativo WHEN 1 THEN 'ativo' ELSE 'inativo' END as status,
    CASE p.ativo WHEN 1 THEN 'blue' ELSE 'gray' END as cor_badge
FROM pets p

UNION ALL

-- 4️⃣ PETS - ATUALIZAÇÃO
SELECT 
    'pet_atualizacao' as tipo_evento,
    p.id as evento_id,
    p.cliente_id,
    p.id as pet_id,
    p.updated_at as data_evento,
    '✏️ Pet atualizado: ' || p.nome as titulo,
    'Informações atualizadas' as descricao,
    CASE p.ativo WHEN 1 THEN 'ativo' ELSE 'inativo' END as status,
    'purple' as cor_badge
FROM pets p
WHERE p.updated_at > p.created_at

UNION ALL

-- 5️⃣ WHATSAPP - MENSAGENS
SELECT 
    'whatsapp' as tipo_evento,
    wm.id as evento_id,
    wm.cliente_id,
    wm.pet_id,
    wm.created_at as data_evento,
    CASE wm.direcao 
        WHEN 'enviada' THEN '💬 Mensagem enviada'
        WHEN 'recebida' THEN '💬 Mensagem recebida'
        ELSE '💬 Mensagem WhatsApp'
    END as titulo,
    CASE 
        WHEN LENGTH(wm.conteudo) > 100 THEN SUBSTR(wm.conteudo, 1, 100) || '...'
        ELSE wm.conteudo
    END as descricao,
    wm.status,
    CASE wm.direcao 
        WHEN 'enviada' THEN 'green'
        WHEN 'recebida' THEN 'blue'
        ELSE 'gray'
    END as cor_badge
FROM whatsapp_messages wm

-- Futuros: vacinas, consultas, serviços
-- UNION ALL ...

ORDER BY data_evento DESC;

-- ============================================================
-- ÍNDICE PARA PERFORMANCE
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_vendas_cliente_data 
ON vendas(cliente_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_contas_receber_cliente_data 
ON contas_receber(cliente_id, data_vencimento DESC);

CREATE INDEX IF NOT EXISTS idx_pets_cliente_data 
ON pets(cliente_id, created_at DESC, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_cliente_data 
ON whatsapp_messages(cliente_id, created_at DESC);
