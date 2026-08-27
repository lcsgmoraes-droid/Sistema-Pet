# Registros de decisões arquiteturais (ADR)

Atualizado em: 2026-08-27

Este diretório registra decisões técnicas duradouras do CorePet. Um ADR explica
o contexto, a decisão, as alternativas e as consequências. Ele não substitui o
código, os testes ou os guias operacionais; evita que uma decisão importante
dependa da memória de uma conversa.

## Estados

- **Proposto:** ainda precisa de aceite.
- **Aceito:** orienta o desenvolvimento atual.
- **Substituído:** permanece histórico e aponta para o novo ADR.
- **Revogado:** não deve mais orientar mudanças.

## Índice

| ADR | Estado | Decisão |
|---|---|---|
| [ADR-0001](0001-monolito-modular.md) | Aceito | Manter um monólito modular e extrair serviços somente com evidência |
| [ADR-0002](0002-isolamento-multitenant-em-camadas.md) | Aceito | Proteger dados multiempresa em camadas complementares |
| [ADR-0003](0003-escala-orientada-por-medicao.md) | Aceito | Aprovar escala por SLOs e carga em homologação, nunca por suposição |

## Regra para novos ADRs

Criar um ADR quando a decisão afetar vários módulos ou PRs, for difícil de
reverter, mudar dados/infraestrutura/segurança ou definir um padrão que outra
pessoa precisará seguir. Correções locais e escolhas triviais ficam no PR.

Todo novo registro deve conter:

1. contexto e problema;
2. decisão e motivo;
3. alternativas consideradas;
4. consequências positivas e custos;
5. gatilhos objetivos para revisão;
6. evidências e documentos relacionados.
