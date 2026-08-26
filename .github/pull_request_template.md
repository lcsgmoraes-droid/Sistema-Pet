## Resumo

- 

## Governanca da entrega

- Tipo: [correcao / funcionalidade / refatoracao / dados / integracao / infra / documentacao]
- Risco: [baixo / medio / alto, com motivo]
- Ficha de entrega: [link / nao se aplica, com motivo]
- Homologacao: [link para evidencia / nao se aplica, com motivo]
- Rollback: [resumo curto]

Para funcionalidade, regra de negocio, integracao, migration, seguranca,
arquitetura ou operacao relevante, use `docs/templates/FICHA_ENTREGA.md`.

## Validacao

- Comandos/cenarios executados:
- Resultado:

## Checklist

- [ ] Testei o que alterei ou expliquei por que nao foi possivel.
- [ ] Registrei criterios de aceite e evidencias proporcionais ao risco.
- [ ] Avaliei tenant, permissoes, dados, integracoes e observabilidade quando aplicavel.
- [ ] Avaliei impacto em Ajuda, comunicacao e treinamento quando visivel ao usuario.
- [ ] Nao inclui `.env`, backups, dumps, certificados, `node_modules` ou arquivos temporarios.
- [ ] A mudanca esta em branch de tarefa, nao direto na `main`.
- [ ] Se alterei frontend, rodei o build quando necessario.
- [ ] Se alterei backend/banco, conferi migrations/scripts necessarios.
- [ ] Entendo que este PR nao autoriza deploy em producao.
