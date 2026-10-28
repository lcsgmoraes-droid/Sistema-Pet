# INC-20261023-01 - Indisponibilidade de rede do CorePet

## Identificacao

- Ambiente: producao. Severidade: P1. Estado: recuperado e monitorado.
- Responsavel de negocio: Lucas. Executor tecnico: Codex.
- VPS: `srv1887462.hstgr.cloud`, Hostinger, Brazil - Campinas.

## Impacto confirmado

Site e SSH retornaram timeout; o console web da Hostinger encerrou a sessao.
A indisponibilidade ocorria antes da autenticacao, afetando o acesso ao ERP.
O total de usuarios afetados nao foi medido. Nao houve evidencia de perda de
dados ou quebra de isolamento entre empresas.

## Linha do tempo (BRT, 2026-10-23)

| Horario | Fato e evidencia |
|---|---|
| 15:38 | Hostinger registrou manutencao emergencial de rede em BR-CAM. |
| 15:51 em diante | Relatos de vitrine de modulo e timeout ao abrir o ERP. |
| 15:57 | Primeiro reinicio pelo hPanel, autorizado por Lucas. |
| 15:58 | SSH, health publico e todos os containers saudaveis. |
| Cerca de 16:00 | Nova falha simultanea de HTTPS e SSH. |
| 16:04:42 | Segunda tentativa de reinicio, confirmada pelo suporte. |
| 16:06-16:15 | Relato tecnico enviado ao suporte e revisao humana solicitada. |
| 16:16 | Segundo reinicio concluido; health/watchdog e containers saudaveis. |
| 16:18 | Regras reais de acesso da empresa indicada verificadas em transacao somente leitura. |
| 16:18:31-16:21:19 | Doze checagens publicas consecutivas saudaveis, sem falhas. |
| 16:21 | Central XML validada na sessao autenticada; monitoramento mantido. |

## Evidencias tecnicas

- Commit servido durante todo o incidente: `adddc310fc9aad332d165b57bb99326ad16f6337`.
- DNS publico coincidiu com o IP apresentado na VPS do hPanel.
- Health `/api/health`: HTTP 200 e `status=ok`; watchdog: `healthy` apos recuperacao.
- Postgres, backend, nginx e dois workers ficaram saudaveis apos o reinicio.
- Disco cerca de 33%, memoria disponivel e conexoes muito abaixo do limite.
- Firewall local permitia 22/80/443; Fail2ban sem IPs banidos.
- Nenhuma unidade systemd falha ou erro de nivel `err` no boot anterior.
- Comandos de diagnostico registrados pelo wrapper de auditoria de producao.
- Atendimento preservado na conversa da Hostinger sobre indisponibilidade da VPS.
- Incidente oficial: https://statuspage.hostinger.com/incidents/5dwh8670y07s

## Contencao e recuperacao

Dois reinicios operacionais autorizados pelo hPanel. Nenhum deploy,
restauracao de banco, mudanca de credenciais ou ajuste de firewall foi usado.
O segundo reinicio demorou cerca de dez minutos para concluir na plataforma.

O cadastro da empresa indicada estava ativo e suas regras reais preservavam
Compras/XML e demais recursos de teste, sem bloqueio automatico financeiro.
Nenhuma cobranca foi alterada durante a recuperacao.

## Causa e risco residual

A melhor explicacao baseada em evidencia e a manutencao emergencial de rede
no mesmo datacenter, com inicio coincidente com os sintomas. O suporte ainda
precisa confirmar a causa especifica da VPS e explicar a recaida apos a
primeira recuperacao. Nao foi encontrada evidencia de bloqueio de origem,
exaustao de recursos ou falha de aplicativo que explique a perda do SSH.

Uma falha de consulta de permissoes tambem podia aparecer como vitrine Beta
no frontend; a correcao de codigo esta na entrega de acesso administrativo,
separada da recuperacao de infraestrutura.

## Comunicacao e acompanhamento

Lucas autorizou diagnostico, restabelecimento e envio de dados tecnicos ao
suporte. O atendimento foi atualizado apos a recuperacao. Um acompanhamento
neste chat verifica saude a cada cinco minutos e avisa somente em mudanca
relevante. Deve encerrar apos resolucao oficial e estabilidade confirmada.

Decisao: manter monitorado; tempos de deteccao/resolucao completos nao foram
medidos com precisao suficiente para declarar metricas finais de incidente.
