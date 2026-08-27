# Homologacao - fila de acompanhamento do onboarding

Data: 2026-08-27

Ambiente: homologacao local isolada em Docker

## Objetivo

Validar que os sinais ja existentes geram uma fila de proxima acao sem alterar
as jornadas normais das empresas.

## Cenarios automatizados

- Empresa saudavel permanece sem pendencia e recebe acompanhamento semanal.
- Alerta critico aberto gera prioridade urgente.
- Configuracao e primeira operacao atrasadas identificam D3 e D7.
- Erro 5xx recente gera acao de investigacao mesmo quando o piloto continua
  ativo.
- O resumo da interface contabiliza corretamente as empresas que precisam de
  acompanhamento.

## Resultado

- Testes do servico de empresas: 8 aprovados.
- Testes dos resumos da interface: 5 aprovados.
- Contrato da tela de empresas: aprovado.
- Contrato dos indicadores de jornada: 6 aprovados.
- Ruff, ESLint, Prettier e `git diff --check`: aprovados.
- Build de producao do frontend: aprovado.
- Frontend e backend Docker: saudaveis.
- E2E do Plano Basico com dados ficticios: aprovado.
- Rota `/ops/tenants`: carregou corretamente ate o login administrativo.

## Limites da evidencia

A area interna exige credencial de administrador da plataforma, portanto a
conferencia visual autenticada nao foi contornada nem executada com credencial
inventada. As regras, o contrato da tela, o build e a jornada E2E foram
validados. Nenhum comando foi executado em producao.
