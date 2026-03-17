# Setup Rapido - Piloto WAHA + n8n

Data: 2026-03-16
Escopo: subir ambiente de teste sem depender de numero oficial.

## 1) O que instalar

1. Docker Desktop
2. FFmpeg (recomendado para tratar audio no n8n)

## 2) Arquivos usados

- `docker-compose.whatsapp-pilot.yml`
- `.env.whatsapp-pilot.example`
- Endpoint interno backend: `POST /internal/whatsapp-orchestrator/{tenant_id}/ingest`

## 3) Preparar variaveis

1. Copiar `.env.whatsapp-pilot.example` para `.env.whatsapp-pilot`
2. Preencher senhas/tokens
3. No backend (`.env` real), configurar:
   - `WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN` com o mesmo valor de `BACKEND_INTERNAL_TOKEN`

## 4) Subir stack piloto

```bash
docker compose --env-file .env.whatsapp-pilot -f docker-compose.whatsapp-pilot.yml up -d
```

Atalho simples no projeto:

```bash
PILOTO_WHATSAPP.bat up
```

Comandos uteis:

```bash
PILOTO_WHATSAPP.bat status
PILOTO_WHATSAPP.bat logs
PILOTO_WHATSAPP.bat down
```

## 5) Teste rapido do endpoint interno

```bash
curl -X POST "http://localhost:8000/internal/whatsapp-orchestrator/SEU_TENANT_ID/ingest" \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: SEU_TOKEN_INTERNO" \
  -d '{
    "phone": "+55 11 99999-9999",
    "message_type": "text",
    "text": "Quais racoes voces tem para filhote?"
  }'
```

## 6) Formato para audio e imagem

Audio:

```json
{
  "phone": "+55 11 99999-9999",
  "message_type": "audio",
  "transcription_text": "preciso de racao renal para gato"
}
```

Imagem:

```json
{
  "phone": "+55 11 99999-9999",
  "message_type": "image",
  "caption": "essa racao serve para filhote?",
  "media_url": "https://exemplo.com/imagem.jpg"
}
```

## 7) Proximo passo

1. Criar workflow n8n:
   - Trigger WAHA
   - Opcional: transcricao de audio
   - POST para endpoint interno
2. Testar 10 cenarios guiados (texto/audio/imagem)
3. Ajustar prompts e handoff

Workflow pronto para importar:
- `automation/n8n/whatsapp_pilot_ingest_workflow.json`
- Guia: `docs/N8N_WORKFLOW_PILOTO_WHATSAPP.md`
