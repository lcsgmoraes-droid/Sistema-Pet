# Entrega - fila de acompanhamento do onboarding

Data: 2026-08-27

## Problema tratado

O painel operacional ja reunia os sinais de acesso, configuracao, primeira
operacao, erros e alertas de cada empresa. Ainda era necessario interpretar
esses dados manualmente para decidir quem precisava de ajuda primeiro.

## Mudancas

- Classificacao objetiva da atencao em `em dia`, `acompanhar`, `acao
  necessaria` ou `urgente`.
- Identificacao dos marcos de onboarding atrasados em D1, D3 e D7.
- Proxima acao calculada com prioridade para alerta critico, acesso, erro 5xx,
  configuracao inicial e primeira operacao.
- Contador de empresas com proxima acao no painel `/ops/tenants`.
- Nova coluna de acompanhamento, sem alterar os fluxos usados pelas empresas.
- Contratos e testes para as regras do backend e da interface.

## Decisoes

- A fila usa somente informacoes que o sistema ja coleta; nao cria um segundo
  cadastro nem exige preenchimento manual para funcionar.
- A mudanca e deliberadamente simples para a fase atual de tres empresas.
- Testes artificiais para centenas ou milhares de empresas ficaram fora deste
  bloco; o foco e reduzir risco operacional e dar clareza ao acompanhamento
  real de cada nova empresa.

## Seguranca e compatibilidade

- Nenhuma migration ou mudanca de banco foi necessaria.
- Nenhum dado sensivel novo e armazenado ou exibido.
- O acesso continua restrito ao administrador da plataforma.
- A entrega nao executa nem autoriza producao.

## Evidencia

Backend, contratos da interface, lint, formatacao, build de producao e E2E do
Plano Basico passaram. A homologacao Docker permaneceu saudavel. Detalhes:
`docs/homologacoes/2026-08-27-fila-onboarding-proxima-acao.md`.
