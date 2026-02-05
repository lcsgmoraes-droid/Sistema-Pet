-- Adicionar campo credito na tabela clientes
ALTER TABLE clientes ADD COLUMN credito DECIMAL(10, 2) NOT NULL DEFAULT 0.0;
