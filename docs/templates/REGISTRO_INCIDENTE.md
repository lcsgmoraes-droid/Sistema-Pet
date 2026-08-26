# Registro de incidente

Copie este arquivo para uma evidência da entrega ou incidente. Use o identificador
`INC-AAAAMMDD-NN`, remova as instruções e nunca inclua segredos ou dados pessoais
desnecessários.

## Identificação

| Campo | Valor |
|---|---|
| Incidente | INC-[AAAAMMDD]-[NN] |
| Título factual | [preencher] |
| Ambiente | [produção/homologação/outro] |
| Severidade atual | [P0/P1/P2/P3] |
| Estado | [detectado/reconhecido/em contenção/em correção/recuperado/encerrado] |
| Coordenador | [papel/pessoa] |
| Executor técnico | [IA/pessoa] |
| Responsável do negócio | [papel/pessoa] |

## Impacto confirmado

- Início estimado:
- Detecção:
- Reconhecimento:
- Jornadas afetadas:
- Quantidade de empresas/usuários afetados:
- Módulos, rotas, jobs ou integrações:
- Alternativa operacional segura:
- Risco de tenant, segurança, privacidade ou dados:

## Linha do tempo

| Data/hora BRT | Estado/ação | Evidência | Responsável |
|---|---|---|---|
| [preencher] | Detectado | [alerta/request_id/relato] | [preencher] |

## Evidências técnicas

- `request_id`/`correlation_id`:
- Commit/versão implantada:
- Eventos Ops e intervalo de logs:
- Health/watchdog:
- Filas, integrações e banco:
- Evidência preservada ou `legal hold`:
- Hipóteses descartadas:

Não cole tokens, cookies, senhas, certificados, payloads brutos nem dados de
clientes. Referencie a fonte segura e registre apenas o necessário.

## Contenção e recuperação

- Contenção aplicada:
- Horário da contenção:
- Risco/efeito colateral da contenção:
- Correção aplicada:
- PR e commit:
- Autorização e evidência de deploy:
- Backup/rollback disponível:
- Horário da recuperação:
- Jornada de regressão validada:

## Comunicação

| Data/hora BRT | Público/canal | Fato informado | Próxima atualização |
|---|---|---|---|
| [preencher] | [interno/cliente] | [resumo sem dado sensível] | [preencher] |

## Causa raiz

- Sintoma observado:
- Causa imediata:
- Causa raiz baseada em evidência:
- Por que os controles existentes não preveniram ou detectaram antes:
- Alcance confirmado e risco residual:

## Métricas

| Métrica | Valor |
|---|---|
| MTTD | [início até detecção] |
| MTTA | [detecção até reconhecimento] |
| MTTC | [detecção até contenção] |
| MTTR | [detecção até recuperação] |

## Ações preventivas

| Ação | Tipo | Prioridade | Responsável | Prazo | Issue/PR | Estado |
|---|---|---|---|---|---|---|
| [preencher] | [teste/alerta/código/processo/docs] | [P0/P1/P2/P3] | [preencher] | [data] | [link] | [aberta/concluída] |

## Encerramento

- [ ] Serviço e jornada afetada foram validados.
- [ ] Impacto e período foram delimitados.
- [ ] Causa raiz ou melhor explicação baseada em evidência foi registrada.
- [ ] Comunicação final foi realizada quando necessária.
- [ ] Ações preventivas têm responsável e prazo.
- [ ] Retenção normal ou `legal hold` foi decidido.
- [ ] Não há segredos ou dados pessoais desnecessários neste registro.

Decisão: [encerrado / manter monitorado / reabrir]

Data/hora e responsável pelo encerramento:

