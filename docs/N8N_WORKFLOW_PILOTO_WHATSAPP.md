# n8n - Workflow Piloto WhatsApp

Data: 2026-03-16

Arquivo do workflow:
- automation/n8n/whatsapp_pilot_ingest_workflow.json

## 1) O que esse workflow faz

1. Recebe evento de entrada do WAHA no webhook do n8n
2. Normaliza o payload para contrato unico
3. Trata os tipos: texto, audio e imagem
4. Envia para o endpoint interno do backend
5. Retorna 200 para o remetente

## 2) Variaveis necessarias no n8n

Definir no container/ambiente do n8n:

1. BACKEND_INTERNAL_BASE_URL
2. BACKEND_TENANT_ID
3. BACKEND_INTERNAL_TOKEN
4. OPENAI_API_KEY (somente se for habilitar transcricao no node desativado)

Observacao importante:
- No Docker local, use `BACKEND_INTERNAL_BASE_URL=http://petshop-dev-backend:8000`.
- O backend de desenvolvimento precisa participar da rede `petshop-whatsapp-pilot-network` para o n8n falar com ele diretamente.

## 3) Como importar

1. Abrir n8n em http://localhost:5678
2. Workflows -> Import from File
3. Selecionar automation/n8n/whatsapp_pilot_ingest_workflow.json
4. Salvar
5. Ajustar variaveis de ambiente
6. Ativar workflow

## 4) URL do webhook no n8n

Depois de ativar, usar o endpoint:

POST /webhook/waha-inbound

Exemplo local:

http://localhost:5678/webhook/waha-inbound

## 5) Exemplo de payload de entrada (WAHA ou simulador)

Envelope real do WAHA para texto:

```json
{
  "event": "message.any",
  "session": "default",
  "engine": "WEBJS",
  "payload": {
    "id": "false_5511999999999@c.us_ABC123",
    "from": "5511999999999@c.us",
    "fromMe": false,
    "body": "Voces tem racao para filhote?",
    "hasMedia": false,
    "source": "app"
  }
}
```

Envelope real do WAHA para audio:

```json
{
  "event": "message.any",
  "session": "default",
  "engine": "WEBJS",
  "payload": {
    "id": "false_5511999999999@c.us_DEF456",
    "from": "5511999999999@c.us",
    "fromMe": false,
    "body": "",
    "hasMedia": true,
    "ptt": true,
    "media": {
      "url": "http://waha:3000/api/files/audio.ogg",
      "mimetype": "audio/ogg"
    },
    "source": "app"
  }
}
```

Envelope real do WAHA para imagem:

```json
{
  "event": "message.any",
  "session": "default",
  "engine": "WEBJS",
  "payload": {
    "id": "false_5511999999999@c.us_GHI789",
    "from": "5511999999999@c.us",
    "fromMe": false,
    "body": "Essa serve para gato adulto?",
    "hasMedia": true,
    "media": {
      "url": "http://waha:3000/api/files/imagem.jpg",
      "mimetype": "image/jpeg",
      "caption": "Essa serve para gato adulto?"
    },
    "source": "app"
  }
}
```

Observacao importante:
- O WAHA envia os dados da mensagem dentro de `payload`.
- O workflow ignora eventos sem remetente util, mensagens enviadas por voce (`fromMe=true`) e eventos que nao sao de mensagem.

## 6) Observacao sobre transcricao de audio

O node "Transcribe Audio (OpenAI)" esta criado e desativado para nao quebrar o fluxo minimo.

Quando quiser ativar transcricao real:
1. Adicionar passo de download do audio para binary
2. Ligar o node de transcricao
3. Mapear transcription_text para o payload final

## 7) Teste rapido com curl

```bash
curl -X POST "http://localhost:5678/webhook/waha-inbound" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "message.any",
    "session": "default",
    "engine": "WEBJS",
    "payload": {
      "id": "false_5511999999999@c.us_local-test",
      "from": "5511999999999@c.us",
      "fromMe": false,
      "body": "Tem racao renal?",
      "hasMedia": false,
      "source": "app"
    }
  }'
```
