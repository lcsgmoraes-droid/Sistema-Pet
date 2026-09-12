---
tipo: integracao
atualizado: 2026-09-12
---

# Integração — IA (OpenAI + alternativos)

Parte de [[Integracoes]]. Ver [[Veterinario]], [[Campanhas]] (calculadora de ração), docs pré-existentes `docs/VETERINARIO_BASE_CONHECIMENTO_E_IA.md`, `docs/CATALOGO_MESTRE_ENRIQUECIMENTO_CONTINUO.md`.

## Identificação
- **Finalidade:** funções auxiliares de IA — atendimento (WhatsApp), IA clínica veterinária, enriquecimento contínuo do catálogo mestre de produtos, fluxo de caixa preditivo, comparador de rações.
- **Confirmado explicitamente no código:** IA **não é fonte de verdade** para venda/estoque/financeiro — é auxiliar.

## Arquivos
`ai/providers/openai_provider.py`, `ai/engine.py`, `ai/settings.py`, `ai/llm_client.py`, `ai/intent_classifier.py`, `ai_core/` (analyzers, engines, domain — conteúdo interno não auditado a fundo).

## Comunicação
REST via SDK oficial `openai` (Python), versão 2.43.0.

## Autenticação
`OPENAI_API_KEY`. Providers alternativos configuráveis: `GROQ_API_KEY`, `GOOGLE_AI_API_KEY` — ❓ não confirmado se há implementação ativa (`groq_provider.py`/`google_ai_provider.py`) para esses dois além da variável de ambiente existir.

## Webhook
Não há — uso é apenas de saída (CorePet chama a OpenAI).

## Falhas, retry e resiliência
- `asyncio.wait_for(..., timeout=request.timeout_seconds)`.
- Captura explícita de `asyncio.TimeoutError`, `openai.RateLimitError`, `openai.AuthenticationError`.
- Retry configurável (padrão 2 tentativas).
- 🔵 **Fallback determinístico quando a IA falha** — funcionalidade não trava se o provedor de IA estiver indisponível.

## Fluxo (exemplo — atendimento WhatsApp)
```text
Mensagem do cliente → whatsapp/ai_service.py → ai/engine.py
  → chamada OpenAI (com timeout e retry)
  → resposta gerada OU fallback determinístico se IA falhar
  → enviada de volta ao cliente
```

## Dependências de funcionalidade
Atendimento WhatsApp (ver [[WhatsApp-WAHA]]), [[Veterinario]] (assistente IA vet, calculadora de doses), catálogo mestre de produtos (enriquecimento automático).

## Não identificado
- ❓ Confirmar implementação real dos providers Groq/Google AI como alternativos, ou se são apenas variáveis reservadas para uso futuro.
