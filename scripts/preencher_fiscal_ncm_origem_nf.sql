-- Script: preencher_fiscal_ncm_origem_nf.sql
-- Objetivo:
-- 1) Garantir registro fiscal para todos os produtos/kit
-- 2) Preencher origem e NCM por nome/categoria
-- 3) Completar CFOP/PIS/COFINS para emissao de NF
--
-- Uso DEV:
-- docker exec -i petshop-dev-postgres psql -U postgres -d petshop_dev < scripts/preencher_fiscal_ncm_origem_nf.sql
--
-- Uso PROD (servidor):
-- docker exec -i petshop-prod-postgres psql -U postgres -d petshop_producao < /opt/petshop/scripts/preencher_fiscal_ncm_origem_nf.sql

BEGIN;

-- 1) Inserir configuracoes fiscais faltantes (produto normal)
INSERT INTO produto_config_fiscal (
    tenant_id,
    produto_id,
    herdado_da_empresa,
    origem_mercadoria,
    ncm,
    cest,
    cst_icms,
    icms_aliquota,
    icms_st,
    cfop_venda,
    cfop_compra,
    pis_cst,
    pis_aliquota,
    cofins_cst,
    cofins_aliquota,
    created_at,
    updated_at
)
SELECT
    p.tenant_id,
    p.id,
    FALSE,
    p.origem,
    NULLIF(p.ncm, ''),
    NULL,
    NULL,
    COALESCE(p.aliquota_icms, ecf.icms_aliquota_interna),
    FALSE,
    COALESCE(NULLIF(p.cfop, ''), NULLIF(ecf.cfop_venda_interna, ''), '5102'),
    COALESCE(NULLIF(p.cfop, ''), NULLIF(ecf.cfop_compra, ''), '1102'),
    NULLIF(ecf.pis_cst_padrao, ''),
    COALESCE(p.aliquota_pis, ecf.pis_aliquota, 0),
    NULLIF(ecf.cofins_cst_padrao, ''),
    COALESCE(p.aliquota_cofins, ecf.cofins_aliquota, 0),
    NOW(),
    NOW()
FROM produtos p
LEFT JOIN empresa_config_fiscal ecf
    ON ecf.tenant_id = p.tenant_id
WHERE p.tipo_produto <> 'KIT'
  AND NOT EXISTS (
      SELECT 1
      FROM produto_config_fiscal pc
      WHERE pc.tenant_id = p.tenant_id
        AND pc.produto_id = p.id
  );

-- 2) Inserir configuracoes fiscais faltantes (kit)
INSERT INTO kit_config_fiscal (
    tenant_id,
    produto_kit_id,
    herdado_da_empresa,
    origem_mercadoria,
    ncm,
    cest,
    cst_icms,
    icms_aliquota,
    icms_st,
    cfop_venda,
    cfop_compra,
    pis_cst,
    pis_aliquota,
    cofins_cst,
    cofins_aliquota,
    observacao_fiscal,
    created_at,
    updated_at
)
SELECT
    p.tenant_id,
    p.id,
    FALSE,
    p.origem,
    NULLIF(p.ncm, ''),
    NULL,
    NULL,
    COALESCE(p.aliquota_icms, ecf.icms_aliquota_interna),
    FALSE,
    COALESCE(NULLIF(p.cfop, ''), NULLIF(ecf.cfop_venda_interna, ''), '5102'),
    COALESCE(NULLIF(p.cfop, ''), NULLIF(ecf.cfop_compra, ''), '1102'),
    NULLIF(ecf.pis_cst_padrao, ''),
    COALESCE(p.aliquota_pis, ecf.pis_aliquota, 0),
    NULLIF(ecf.cofins_cst_padrao, ''),
    COALESCE(p.aliquota_cofins, ecf.cofins_aliquota, 0),
    NULL,
    NOW(),
    NOW()
FROM produtos p
LEFT JOIN empresa_config_fiscal ecf
    ON ecf.tenant_id = p.tenant_id
WHERE p.tipo_produto = 'KIT'
  AND NOT EXISTS (
      SELECT 1
      FROM kit_config_fiscal kc
      WHERE kc.tenant_id = p.tenant_id
        AND kc.produto_kit_id = p.id
  );

-- 3) Mapear NCM por nome/categoria em tabela temporaria
DROP TABLE IF EXISTS tmp_mapa_ncm;

CREATE TEMP TABLE tmp_mapa_ncm AS
WITH base AS (
    SELECT
        p.id,
        p.tenant_id,
        LOWER(COALESCE(p.nome, '')) AS nome_lower,
        LOWER(COALESCE(c.nome, '')) AS categoria_lower
    FROM produtos p
    LEFT JOIN categorias c
        ON c.id = p.categoria_id
       AND c.tenant_id = p.tenant_id
)
SELECT
    b.id,
    b.tenant_id,
        CASE
                WHEN b.nome_lower LIKE '%nexgard%' OR b.nome_lower LIKE '%medicamento%' OR b.nome_lower LIKE '%remedio%'
          OR b.nome_lower LIKE '%vermifugo%' OR b.nome_lower LIKE '%antipulga%'
          OR b.categoria_lower LIKE '%medicamento%'
            THEN '30049099'

                WHEN b.nome_lower LIKE '%racao%' OR b.nome_lower LIKE '%petisco%'
                    OR b.nome_lower LIKE '%golden%' OR b.nome_lower LIKE '%premier%' OR b.nome_lower LIKE '%royal canin%'
                    OR b.nome_lower LIKE '%special dog%' OR b.nome_lower LIKE '%hills%' OR b.nome_lower LIKE '%n&d%'
                    OR b.nome_lower LIKE '%pedigree%'
                    OR b.nome_lower LIKE '%calopsita%' OR b.categoria_lower LIKE '%racao%'
                    OR b.categoria_lower LIKE '%racoes%'
                        THEN '23091000'

        WHEN b.nome_lower LIKE '%shampoo%' OR b.nome_lower LIKE '%condicionador%' OR b.nome_lower LIKE '%higiene%'
          OR b.nome_lower LIKE '%colonia%' OR b.nome_lower LIKE '%perfume%'
            THEN '33059000'

        WHEN b.nome_lower LIKE '%brinquedo%' OR b.nome_lower LIKE '%bolinha%' OR b.nome_lower LIKE '%mordedor%'
          OR b.nome_lower LIKE '%pelucia%'
            THEN '95030099'

        WHEN b.nome_lower LIKE '%coleira%' OR b.nome_lower LIKE '%peitoral%' OR b.nome_lower LIKE '%guia%'
            THEN '42010000'

        WHEN b.nome_lower LIKE '%areia%' OR b.nome_lower LIKE '%granulado%'
            THEN '25081000'

        WHEN b.nome_lower LIKE '%comedouro%' OR b.nome_lower LIKE '%bebedouro%' OR b.nome_lower LIKE '%pote%'
          OR b.nome_lower LIKE '%tigela%'
            THEN '39249000'

        WHEN b.nome_lower LIKE '%agulha%'
            THEN '90183219'

        WHEN b.nome_lower LIKE '%seringa%'
            THEN '90183119'

        WHEN b.nome_lower LIKE '%gaze%' OR b.nome_lower LIKE '%atadura%' OR b.nome_lower LIKE '%algodao%'
          OR b.nome_lower LIKE '%micropore%'
            THEN '30059090'

        WHEN b.nome_lower LIKE '%luva%'
            THEN '40151900'

        WHEN b.nome_lower LIKE '%mascara%'
            THEN '63079010'

        WHEN b.nome_lower LIKE '%coletor perfurocortante%'
            THEN '39269090'

        WHEN b.nome_lower LIKE '%soro fisiologico%'
            THEN '30049099'

        ELSE NULL
    END AS ncm_sugerido
FROM base b;

-- 4) Atualizar legado de produtos (origem, ncm, cfop)
UPDATE produtos p
SET
    origem = COALESCE(NULLIF(p.origem, ''), '0'),
    ncm = COALESCE(NULLIF(p.ncm, ''), m.ncm_sugerido),
    cfop = COALESCE(NULLIF(p.cfop, ''), NULLIF(ecf.cfop_venda_interna, ''), '5102')
FROM tmp_mapa_ncm m
LEFT JOIN empresa_config_fiscal ecf
    ON ecf.tenant_id = m.tenant_id
WHERE p.id = m.id
  AND p.tenant_id = m.tenant_id
  AND (
      p.origem IS NULL OR p.origem = '' OR
      p.ncm IS NULL OR p.ncm = '' OR
      p.cfop IS NULL OR p.cfop = ''
  );

-- 4.1) Correcao forcada para medicamentos veterinarios por palavra-chave
UPDATE produtos p
SET
    origem = COALESCE(NULLIF(p.origem, ''), '0'),
    ncm = '30049099'
WHERE LOWER(COALESCE(p.nome, '')) LIKE '%nexgard%'
   OR LOWER(COALESCE(p.nome, '')) LIKE '%antipulga%'
   OR LOWER(COALESCE(p.nome, '')) LIKE '%vermifugo%'
   OR LOWER(COALESCE(p.nome, '')) LIKE '%medicamento%'
   OR LOWER(COALESCE(p.nome, '')) LIKE '%remedio%';

-- 5) Atualizar produto_config_fiscal
UPDATE produto_config_fiscal pc
SET
    origem_mercadoria = COALESCE(NULLIF(pc.origem_mercadoria, ''), NULLIF(p.origem, ''), '0'),
    ncm = COALESCE(NULLIF(pc.ncm, ''), NULLIF(p.ncm, ''), m.ncm_sugerido),
    cfop_venda = COALESCE(NULLIF(pc.cfop_venda, ''), NULLIF(p.cfop, ''), NULLIF(ecf.cfop_venda_interna, ''), '5102'),
    cfop_compra = COALESCE(NULLIF(pc.cfop_compra, ''), NULLIF(ecf.cfop_compra, ''), '1102'),
    icms_aliquota = COALESCE(pc.icms_aliquota, p.aliquota_icms, ecf.icms_aliquota_interna),
    pis_cst = COALESCE(NULLIF(pc.pis_cst, ''), NULLIF(ecf.pis_cst_padrao, '01')),
    pis_aliquota = COALESCE(pc.pis_aliquota, p.aliquota_pis, ecf.pis_aliquota, 1.65),
    cofins_cst = COALESCE(NULLIF(pc.cofins_cst, ''), NULLIF(ecf.cofins_cst_padrao, '01')),
    cofins_aliquota = COALESCE(pc.cofins_aliquota, p.aliquota_cofins, ecf.cofins_aliquota, 7.60),
    updated_at = NOW()
FROM produtos p
LEFT JOIN tmp_mapa_ncm m
    ON m.id = p.id
   AND m.tenant_id = p.tenant_id
LEFT JOIN empresa_config_fiscal ecf
    ON ecf.tenant_id = p.tenant_id
WHERE pc.produto_id = p.id
  AND pc.tenant_id = p.tenant_id;

-- 5.1) Correcao forcada para config fiscal de medicamentos veterinarios
UPDATE produto_config_fiscal pc
SET
        origem_mercadoria = COALESCE(NULLIF(pc.origem_mercadoria, ''), '0'),
        ncm = '30049099',
        updated_at = NOW()
FROM produtos p
WHERE pc.produto_id = p.id
    AND pc.tenant_id = p.tenant_id
    AND (
            LOWER(COALESCE(p.nome, '')) LIKE '%nexgard%'
            OR LOWER(COALESCE(p.nome, '')) LIKE '%antipulga%'
            OR LOWER(COALESCE(p.nome, '')) LIKE '%vermifugo%'
            OR LOWER(COALESCE(p.nome, '')) LIKE '%medicamento%'
            OR LOWER(COALESCE(p.nome, '')) LIKE '%remedio%'
    );

-- 5.2) Herdar NCM mais frequente por categoria (tenant + categoria)
WITH base_categoria AS (
        SELECT
                p.id,
                p.tenant_id,
                p.categoria_id,
                pc.ncm
        FROM produtos p
        JOIN produto_config_fiscal pc
            ON pc.produto_id = p.id
         AND pc.tenant_id = p.tenant_id
        WHERE p.tipo_produto <> 'KIT'
),
moda_categoria AS (
        SELECT
                tenant_id,
                categoria_id,
                ncm,
                ROW_NUMBER() OVER (
                        PARTITION BY tenant_id, categoria_id
                        ORDER BY COUNT(*) DESC, ncm
                ) AS rn
        FROM base_categoria
        WHERE ncm IS NOT NULL
            AND ncm <> ''
            AND categoria_id IS NOT NULL
        GROUP BY tenant_id, categoria_id, ncm
)
UPDATE produto_config_fiscal pc
SET
        ncm = mc.ncm,
        updated_at = NOW()
FROM produtos p
JOIN moda_categoria mc
    ON mc.tenant_id = p.tenant_id
 AND mc.categoria_id = p.categoria_id
 AND mc.rn = 1
WHERE pc.produto_id = p.id
    AND pc.tenant_id = p.tenant_id
    AND (pc.ncm IS NULL OR pc.ncm = '');

-- 5.3) Regra explicita para vacinas veterinarias
UPDATE produtos p
SET
        ncm = '30023010',
        origem = COALESCE(NULLIF(p.origem, ''), '0')
WHERE LOWER(COALESCE(p.nome, '')) LIKE '%vacina%'
    AND (p.ncm IS NULL OR p.ncm = '');

UPDATE produto_config_fiscal pc
SET
        ncm = '30023010',
        origem_mercadoria = COALESCE(NULLIF(pc.origem_mercadoria, ''), '0'),
        updated_at = NOW()
FROM produtos p
WHERE pc.produto_id = p.id
    AND pc.tenant_id = p.tenant_id
    AND LOWER(COALESCE(p.nome, '')) LIKE '%vacina%'
    AND (pc.ncm IS NULL OR pc.ncm = '');

    -- 5.4) Padrao para servicos (NCM tecnico para nao travar emissao no fluxo atual)
    UPDATE produtos p
    SET
        ncm = '00000000',
        origem = COALESCE(NULLIF(p.origem, ''), '0')
    WHERE LOWER(COALESCE(p.tipo, '')) = 'servico';

    UPDATE produto_config_fiscal pc
    SET
        ncm = '00000000',
        origem_mercadoria = COALESCE(NULLIF(pc.origem_mercadoria, ''), '0'),
        updated_at = NOW()
    FROM produtos p
    WHERE pc.produto_id = p.id
      AND pc.tenant_id = p.tenant_id
      AND LOWER(COALESCE(p.tipo, '')) = 'servico';

-- 6) Atualizar kit_config_fiscal
UPDATE kit_config_fiscal kc
SET
    origem_mercadoria = COALESCE(NULLIF(kc.origem_mercadoria, ''), NULLIF(p.origem, ''), '0'),
    ncm = COALESCE(NULLIF(kc.ncm, ''), NULLIF(p.ncm, ''), m.ncm_sugerido),
    cfop_venda = COALESCE(NULLIF(kc.cfop_venda, ''), NULLIF(p.cfop, ''), NULLIF(ecf.cfop_venda_interna, ''), '5102'),
    cfop_compra = COALESCE(NULLIF(kc.cfop_compra, ''), NULLIF(ecf.cfop_compra, ''), '1102'),
    icms_aliquota = COALESCE(kc.icms_aliquota, p.aliquota_icms, ecf.icms_aliquota_interna),
    pis_cst = COALESCE(NULLIF(kc.pis_cst, ''), NULLIF(ecf.pis_cst_padrao, '01')),
    pis_aliquota = COALESCE(kc.pis_aliquota, p.aliquota_pis, ecf.pis_aliquota, 1.65),
    cofins_cst = COALESCE(NULLIF(kc.cofins_cst, ''), NULLIF(ecf.cofins_cst_padrao, '01')),
    cofins_aliquota = COALESCE(kc.cofins_aliquota, p.aliquota_cofins, ecf.cofins_aliquota, 7.60),
    updated_at = NOW()
FROM produtos p
LEFT JOIN tmp_mapa_ncm m
    ON m.id = p.id
   AND m.tenant_id = p.tenant_id
LEFT JOIN empresa_config_fiscal ecf
    ON ecf.tenant_id = p.tenant_id
WHERE kc.produto_kit_id = p.id
  AND kc.tenant_id = p.tenant_id;

COMMIT;

-- Relatorio rapido apos execucao
SELECT
    COUNT(*) AS produto_config_sem_origem
FROM produto_config_fiscal
WHERE origem_mercadoria IS NULL OR origem_mercadoria = '';

SELECT
    COUNT(*) AS produto_config_sem_ncm
FROM produto_config_fiscal
WHERE ncm IS NULL OR ncm = '';

SELECT
    COUNT(*) AS kit_config_sem_origem
FROM kit_config_fiscal
WHERE origem_mercadoria IS NULL OR origem_mercadoria = '';

SELECT
    COUNT(*) AS kit_config_sem_ncm
FROM kit_config_fiscal
WHERE ncm IS NULL OR ncm = '';
