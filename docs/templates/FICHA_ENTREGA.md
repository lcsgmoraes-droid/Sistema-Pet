# Ficha de entrega

Use este modelo para nova funcionalidade, mudança de regra, integração,
migration, segurança, arquitetura ou alteração operacional relevante. A IA ou a
pessoa que implementa deve preenchê-lo antes de considerar a entrega pronta.

Remova instruções entre colchetes e marque `Não se aplica` com uma justificativa
curta quando uma seção realmente não fizer parte do escopo.

## Identificação

| Campo | Valor |
|---|---|
| Título | [preencher] |
| Data | [AAAA-MM-DD] |
| Responsável de negócio | [preencher] |
| Executor técnico | [IA/pessoa] |
| Issue/PR | [link ou número] |
| Prioridade | [P0/P1/P2/P3] |
| Risco | [baixo/médio/alto e motivo] |
| Domínios afetados | [ex.: vendas, estoque, financeiro] |

## 1. Necessidade e requisitos

- Problema que será resolvido:
- Usuários afetados:
- Resultado esperado para o negócio:
- Requisitos funcionais:
- Requisitos não funcionais relevantes, como segurança, desempenho,
  disponibilidade, acessibilidade ou volume:
- Comportamentos atuais que devem permanecer:
- Fora do escopo:
- Critérios objetivos de aceite:

## 2. Regras de negócio e dados

- Regras criadas ou alteradas:
- Entidade responsável pelo dado:
- Dados pessoais ou sensíveis envolvidos:
- Impacto de tenant/isolamento entre empresas:
- Migration, importação, retenção, auditoria ou histórico:
- Validações de integridade e concorrência:

## 3. Arquitetura e integrações

- Componentes e contratos afetados:
- Decisão arquitetural e motivo:
- Alternativas relevantes descartadas:
- Sistemas externos envolvidos:
- Timeout, retry, idempotência, fallback e reconciliação:
- Comportamento quando a dependência externa estiver indisponível:

## 4. Segurança e privacidade

- Autenticação e permissões:
- Riscos de exposição, abuso ou acesso entre empresas:
- Segredos e configurações necessários:
- Logs permitidos e dados que não podem ser registrados:
- Impacto LGPD, finalidade e retenção:
- Testes ou revisão de segurança:

## 5. Desenvolvimento e qualidade

- Plano em pequenas fatias:
- Testes unitários:
- Testes de integração/banco:
- Testes de contrato/API:
- Testes multiempresa/permissão:
- Testes E2E, regressão, desempenho ou segurança:
- Comandos executados e resultados:

## 6. Ambientes e homologação

- Configurações e variáveis por ambiente:
- Ambiente usado na validação:
- Massa de dados fictícia/descartável:
- Registro de homologação:
  `docs/templates/REGISTRO_HOMOLOGACAO.md` ou `Não se aplica` com motivo.
- Pendências e defeitos aceitos:

## 7. Publicação e rollback

- Tipo de entrega: [backend/frontend/mobile OTA/mobile nativo/documentação/infra]
- Commit ou versão identificável:
- Ordem de migrations e compatibilidade entre versões:
- Plano de publicação:
- Health/smoke pós-publicação:
- Critério para abortar ou reverter:
- Plano de rollback:

Preencher esta seção não autoriza produção. A autorização explícita continua
separada e obrigatória.

## 8. Observabilidade e sustentação

- Logs, métricas, auditoria e alertas esperados:
- Indicador técnico ou de negócio que comprova sucesso:
- Falhas previsíveis e diagnóstico:
- Classificação de incidente aplicável:
- Alternativa operacional segura:
- Quando uma recorrência deve virar melhoria estrutural:

## 9. Mudança, comunicação e treinamento

- Processo ou rotina do usuário que muda:
- Central de Ajuda/manual a atualizar:
- Comunicação necessária e público:
- Treinamento necessário:
- Data ou marco da comunicação:

## 10. Fechamento

- [ ] Critérios de aceite atendidos.
- [ ] Testes e evidências registrados.
- [ ] Tenant, permissões, dados e auditoria preservados.
- [ ] Documentação oficial atualizada.
- [ ] Homologação registrada ou dispensa justificada.
- [ ] Publicação, observabilidade e rollback definidos.
- [ ] Comunicação/treinamento avaliados.
- [ ] PR revisável, sem segredo, backup, dump ou artefato indevido.

Decisão final: [aprovado / aprovado com pendências / reprovado]

Pendências, responsável e prazo:

