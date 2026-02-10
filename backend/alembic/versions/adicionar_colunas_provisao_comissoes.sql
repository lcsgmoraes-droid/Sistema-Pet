-- Migration: Adicionar colunas de provisão DRE em comissoes_itens
-- Criado em: 2026-02-09
-- Descrição: Adiciona campos para controle de provisão automática de comissões na DRE

-- Adicionar coluna comissao_provisionada (boolean, default false)
ALTER TABLE comissoes_itens 
ADD COLUMN IF NOT EXISTS comissao_provisionada BOOLEAN DEFAULT FALSE;

-- Adicionar coluna conta_pagar_id (FK para contas_pagar)
ALTER TABLE comissoes_itens 
ADD COLUMN IF NOT EXISTS conta_pagar_id INTEGER REFERENCES contas_pagar(id) ON DELETE SET NULL;

-- Adicionar coluna data_provisao (data da provisão)
ALTER TABLE comissoes_itens 
ADD COLUMN IF NOT EXISTS data_provisao DATE;

-- Criar índice para facilitar consultas de comissões não provisionadas
CREATE INDEX IF NOT EXISTS ix_comissoes_itens_comissao_provisionada 
ON comissoes_itens(comissao_provisionada) WHERE comissao_provisionada = FALSE;

-- Criar índice para FK conta_pagar_id
CREATE INDEX IF NOT EXISTS ix_comissoes_itens_conta_pagar_id 
ON comissoes_itens(conta_pagar_id);

COMMENT ON COLUMN comissoes_itens.comissao_provisionada IS 'Indica se a comissão já foi provisionada automaticamente na DRE';
COMMENT ON COLUMN comissoes_itens.conta_pagar_id IS 'Referência para a conta a pagar criada na provisão automática';
COMMENT ON COLUMN comissoes_itens.data_provisao IS 'Data em que a comissão foi provisionada automaticamente';
