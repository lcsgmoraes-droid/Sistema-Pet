-- Migration: Criar tabela whatsapp_messages
-- Data: 2026-01-23
-- Objetivo: Estrutura para histórico de mensagens WhatsApp integrado à Timeline

CREATE TABLE IF NOT EXISTS whatsapp_messages (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    pet_id INTEGER REFERENCES pets(id) ON DELETE SET NULL,
    telefone VARCHAR(20) NOT NULL,
    direcao VARCHAR(20) NOT NULL CHECK (direcao IN ('enviada', 'recebida')),
    conteudo TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'enviado' CHECK (status IN ('enviado', 'lido', 'erro', 'recebido')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Índices para otimizar queries
CREATE INDEX idx_whatsapp_messages_cliente_id ON whatsapp_messages(cliente_id);
CREATE INDEX idx_whatsapp_messages_telefone ON whatsapp_messages(telefone);
CREATE INDEX idx_whatsapp_messages_created_at ON whatsapp_messages(created_at DESC);
CREATE INDEX idx_whatsapp_messages_user_id ON whatsapp_messages(user_id);

-- Comentários
COMMENT ON TABLE whatsapp_messages IS 'Histórico de mensagens WhatsApp integrado à Timeline Unificada';
COMMENT ON COLUMN whatsapp_messages.direcao IS 'Direção da mensagem: enviada ou recebida';
COMMENT ON COLUMN whatsapp_messages.status IS 'Status: enviado, lido, erro, recebido';
COMMENT ON COLUMN whatsapp_messages.pet_id IS 'Pet relacionado à mensagem (opcional)';
