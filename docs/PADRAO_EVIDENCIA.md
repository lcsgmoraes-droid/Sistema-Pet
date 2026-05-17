# Padrao de evidencia operacional

Atualizado em: 2026-05-17

Use este formato para registrar fatos operacionais sem espalhar informacao
incompleta pelos docs.

## Quando registrar

Registrar evidencia quando houver:

- deploy real;
- rollback;
- restore smoke;
- teste E2E contra ambiente real ou tenant de teste;
- alerta Ops/notificacao real;
- mudanca de branch protection, CI ou secret operacional;
- incidente ou correcao critica em producao.

## Campos obrigatorios

```text
Data:
PR:
Commit:
Ambiente:
Responsavel:
Comando:
Resultado:
Evidencia:
Impacto:
Proxima acao:
```

## Exemplo

```text
Data: 2026-05-17
PR: #110
Commit: 56c59119
Ambiente: producao
Responsavel: Codex/Lucas
Comando: python -m app.services.ops_alert_webhook_smoke --label email-producao-YYYYMMDDHHMMSS
Resultado: enabled=true, sent=1, sent_email=1, status=sent
Evidencia: backend/logs/ops_alert_notifications.jsonl registrou notification_key
Impacto: alerta Ops real por e-mail operacional validado
Proxima acao: confirmar recebimento humano do e-mail em prohubml@gmail.com
```

## Regras

- Nunca registrar senha, token, cookie, URL secreta de webhook ou chave de API.
- Pode registrar e-mail operacional quando ele nao for segredo.
- Para secrets, registrar somente `configurado=yes` ou `presente no ambiente`.
- Sempre diferenciar validacao local, CI, staging e producao.
- Evidencia de producao deve citar health/watchdog quando aplicavel.
- Quando o resultado for parcial, registrar a falha junto da correcao ou proxima
  acao.
