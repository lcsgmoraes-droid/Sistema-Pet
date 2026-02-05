-- ============================================================
-- VIEW: TIMELINE UNIFICADA DO FORNECEDOR
-- Consolida pedidos de compra e pagamentos a fornecedores
-- ============================================================

CREATE VIEW IF NOT EXISTS fornecedor_timeline AS

-- 1️⃣ PEDIDOS DE COMPRA
SELECT 
    'pedido_compra' as tipo_evento,
    pc.id as evento_id,
    pc.fornecedor_id,
    NULL as produto_id,
    pc.data_pedido as data_evento,
    'Pedido #' || pc.numero_pedido as titulo,
    'R$ ' || printf('%.2f', pc.valor_final) || ' - ' || pc.status as descricao,
    pc.status,
    CASE pc.status 
        WHEN 'recebido' THEN 'green'
        WHEN 'parcialmente_recebido' THEN 'blue'
        WHEN 'em_transito' THEN 'yellow'
        WHEN 'aguardando' THEN 'yellow'
        WHEN 'cancelado' THEN 'red'
        ELSE 'gray'
    END as cor_badge
FROM pedidos_compra pc
WHERE pc.fornecedor_id IS NOT NULL

UNION ALL

-- 2️⃣ CONTAS A PAGAR
SELECT 
    'conta_pagar' as tipo_evento,
    cp.id as evento_id,
    cp.fornecedor_id,
    NULL as produto_id,
    cp.data_vencimento as data_evento,
    'Conta a Pagar' as titulo,
    'R$ ' || printf('%.2f', cp.valor_original) || ' - ' || cp.descricao as descricao,
    cp.status,
    CASE cp.status 
        WHEN 'pago' THEN 'green'
        WHEN 'pendente' THEN 'yellow'
        WHEN 'vencido' THEN 'red'
        WHEN 'cancelado' THEN 'gray'
        ELSE 'blue'
    END as cor_badge
FROM contas_pagar cp
WHERE cp.fornecedor_id IS NOT NULL

UNION ALL

-- 3️⃣ RECEBIMENTOS DE PEDIDOS (últimas entregas)
SELECT 
    'recebimento' as tipo_evento,
    pc.id as evento_id,
    pc.fornecedor_id,
    NULL as produto_id,
    pc.data_recebimento as data_evento,
    'Recebimento Pedido #' || pc.numero_pedido as titulo,
    'Entrega realizada - ' || COUNT(pci.id) || ' itens' as descricao,
    'recebido' as status,
    'blue' as cor_badge
FROM pedidos_compra pc
LEFT JOIN pedidos_compra_itens pci ON pci.pedido_compra_id = pc.id
WHERE pc.fornecedor_id IS NOT NULL 
  AND pc.data_recebimento IS NOT NULL
GROUP BY pc.id, pc.fornecedor_id, pc.data_recebimento, pc.numero_pedido

ORDER BY data_evento DESC;

-- ============================================================
-- ÍNDICES PARA PERFORMANCE
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_pedidos_compra_fornecedor_data 
ON pedidos_compra(fornecedor_id, data_pedido);

CREATE INDEX IF NOT EXISTS idx_contas_pagar_fornecedor_data 
ON contas_pagar(fornecedor_id, data_vencimento);
