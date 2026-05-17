# Indice operacional do Sistema Pet

Atualizado em: 2026-05-17

Este e o ponto de entrada oficial da documentacao. Se houver conflito entre este
indice e um documento historico, use este indice e o guia mestre de maturidade.

Guia mestre:

- `docs/MATURIDADE_GERAL_10_10_GUIA.md`

## Por onde comecar

| Necessidade | Ler primeiro | Depois validar com |
|---|---|---|
| Entender maturidade geral | `docs/MATURIDADE_GERAL_10_10_GUIA.md` | Historico de PRs no proprio guia |
| Preparar um PC DEV | `docs/DEV_ENVIRONMENT_CHECK.md` | `scripts/check_dev_environment.ps1` |
| Trabalhar em dois PCs | `docs/GIT_FLUXO_2_PCS.md` | `scripts/git_check_updates.ps1` |
| Usar MCPs locais | `mcp/README.md` | `scripts/test_mcp.ps1` |
| Entender CI e checks | `docs/CI_CD_DEPLOY_SAFETY_AUDIT.md` | GitHub Actions do PR |
| Deploy real | `docs/PRODUCAO_DEPLOY_SSH.md` | `petshop-status-producao` e health publico |
| Rollback | `docs/PRODUCAO_ROLLBACK_CHECKLIST.md` | Backup operacional do deploy |
| Backup/restore de banco | `docs/PRODUCAO_BACKUP_RESTORE_TESTE.md` | Restore smoke controlado |
| Observabilidade e auditoria | `docs/RETENCAO_LOGS_AUDITORIA.md` | Painel Ops e logs JSONL |
| Estrutura/refatoracao | `docs/auditorias/estrutura-geral-definition-of-done.md` | Testes focados da fatia |
| Vender Plano Basico | `docs/GUIA_VENDA_PLANO_BASICO.md` | Checklist de onboarding e clientes piloto |
| Demo Veterinario | `docs/GUIA_DEMO_VETERINARIO_CLINICA.md` | Roteiro de demo e limites de piloto |
| Maiara/Vet/Admin SaaS | `docs/CRONOGRAMA_MAIARA_VETERINARIO_ADMIN_SAAS.md` | Preparacao de demo, padronizacao Vet e admin global |
| Base oficial de dados | `docs/CRONOGRAMA_BASE_DADOS_OFICIAL.md` | Produtos, imagens, cadastros iniciais e atualizacoes |
| Plano Basico | `docs/auditorias/plano-basico-tenant-checklist.md` | E2E longo controlado |
| Produto/roadmap | `docs/ROADMAP_MASTER.md` | Checklist da frente especifica |

## Guias por area

| Area | Documento oficial |
|---|---|
| MCPs | `docs/MCP_MATURIDADE_GUIA.md` |
| Estrutura geral | `docs/auditorias/estrutura-geral-inventario.md` |
| Seguranca operacional | `docs/CI_CD_DEPLOY_SAFETY_AUDIT.md` |
| Testes/CI | `docs/auditorias/testes-ci-cobertura-critica.md` |
| Observabilidade/auditoria | `docs/RETENCAO_LOGS_AUDITORIA.md` |
| Portabilidade/configuracao | `docs/DEV_ENVIRONMENT_CHECK.md` |
| Venda do Plano Basico | `docs/GUIA_VENDA_PLANO_BASICO.md` |
| Demo/Piloto Veterinario | `docs/GUIA_DEMO_VETERINARIO_CLINICA.md` |
| Maiara, Veterinario e Admin SaaS | `docs/CRONOGRAMA_MAIARA_VETERINARIO_ADMIN_SAAS.md` |
| Base oficial de dados | `docs/CRONOGRAMA_BASE_DADOS_OFICIAL.md` |
| Evidencias | `docs/PADRAO_EVIDENCIA.md` |

## Rotina obrigatoria por PR

1. Confirmar se o PR muda runtime, CI, docs, infra ou produto.
2. Rodar a validacao apropriada e registrar resultado no PR.
3. Atualizar o guia vivo da area quando a maturidade ou o procedimento mudar.
4. Atualizar `docs/MATURIDADE_GERAL_10_10_GUIA.md` quando a nota, checklist ou
   historico de PR mudar.
5. Usar `docs/PADRAO_EVIDENCIA.md` para registrar deploy, teste operacional,
   restore, E2E, smoke real ou incidente.

## Documentos historicos

Documentos antigos, backups e notas soltas continuam disponiveis para consulta,
mas nao sao fonte oficial quando:

- apontam para scripts antigos;
- falam de ambiente local como se fosse producao real;
- mencionam IP, backup, branch ou fluxo diferente dos guias acima;
- nao registram data, PR ou validacao.

Ao encontrar documento historico ainda util, consolidar o conteudo em um guia
oficial e deixar o historico apenas como referencia.
