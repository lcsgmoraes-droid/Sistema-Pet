# Registro de homologação

Use este modelo para provar que uma entrega atende aos critérios de aceite antes
de produção. Homologação não substitui autorização de deploy.

## Identificação

| Campo | Valor |
|---|---|
| Entrega | [preencher] |
| Issue/PR | [link ou número] |
| Commit/versão testada | [preencher] |
| Data e horário | [preencher] |
| Ambiente | [DEV controlado/HOMOLOG/outro] |
| Responsável técnico | [preencher] |
| Responsável pelo aceite de negócio | [preencher] |
| Tenant/massa de teste | [identificador fictício, sem segredo] |

## Pré-condições

- Configuração e versão do ambiente:
- Dados fictícios ou descartáveis preparados:
- Dependências externas simuladas ou controladas:
- Riscos conhecidos:
- Confirmação de que nenhum dado real desnecessário foi copiado:

## Cenários de aceite

| ID | Cenário | Resultado esperado | Resultado obtido | Evidência | Status |
|---|---|---|---|---|---|
| H01 | [preencher] | [preencher] | [preencher] | [log/print/teste sem dado sensível] | [aprovado/reprovado] |

Incluir, quando aplicável:

- caminho principal do usuário;
- permissão negada e perfil sem acesso;
- isolamento entre empresas;
- erro de validação e indisponibilidade externa;
- repetição/idempotência;
- regressão do comportamento preservado;
- auditoria, logs, métricas e alertas;
- migration, rollback ou compatibilidade entre versões;
- visualização responsiva e acessibilidade básica.

## Inconsistências

| ID | Severidade | Descrição | Responsável | Prazo | Decisão |
|---|---|---|---|---|---|
| I01 | [P0/P1/P2/P3] | [preencher] | [preencher] | [preencher] | [corrigir/bloquear/aceitar] |

Nenhuma inconsistência P0 pode ser aceita para publicação. Uma inconsistência
aceita deve ter justificativa, responsável e prazo.

## Evidências

Registre comando, resultado, data, commit e impacto conforme
`docs/PADRAO_EVIDENCIA.md`. Não registre senhas, tokens, dados pessoais
desnecessários, dumps ou URLs sensíveis.

## Decisão

- [ ] Aprovado.
- [ ] Aprovado com pendências não bloqueantes registradas.
- [ ] Reprovado.

Justificativa:

Responsável pelo aceite:

Data:

Próximo passo:

Esta decisão confirma o aceite da entrega testada. Qualquer publicação em
produção ainda exige o fluxo e a autorização definidos no repositório.

