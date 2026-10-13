# Ficha de entrega — devolução assistida

## Identificação

- Data: 2026-10-13.
- Responsável de negócio: Lucas; implementação: Codex.
- Branch: `codex/devolucao-assistida`; PR e commit consultáveis no histórico Git.
- Prioridade: P1. Risco médio: restituição de saldo e movimentação financeira.
- Domínios: vendas, clientes, caixa, campanhas e estoque.

## 1. Necessidade e aceite

A devolução de uma venda paga com cashback ou Crédito Cliente era bloqueada sem ação de correção. O fluxo agora oferece restituição aos saldos originais, prévia discriminada e botões para corrigir impedimentos. Deve preservar itens e motivo, suportar devoluções parciais e evitar repetição de uma operação confirmada cuja resposta se perdeu.

## 2. Regras e dados

O rateio usa os pagamentos originais e o valor cumulativo já devolvido, com centavos monotônicos. Cashback retorna ao lote e à validade originais; saldo já vencido aparece na prévia. Crédito original volta ao cliente. Apenas o restante segue dinheiro ou novo crédito. Frete permanece fora do reembolso dos itens. Nenhuma migration é necessária. `CreditoLog`, histórico da venda e evento de devolução registram a operação na mesma transação.

## 3. Contratos e concorrência

Prévia e registro recebem `devolver_na_origem`. O registro confere `restituicao_prevista` antes das alterações. Divergências exigem nova confirmação. Chave e hash identificam a operação; após resposta incerta, o frontend reenvia o payload originalmente confirmado mesmo se o rascunho mudou. Uma operação pendente impede iniciar outra venda. Locks de caixa, venda e cliente seguem as proteções existentes.

## 4. Segurança e privacidade

Autenticação e isolamento por tenant permanecem nos endpoints e consultas. Não há novas credenciais ou permissões. Pagamento, lote, resgate ou histórico sem comprovação mantêm bloqueio de integridade com atalhos de conferência. Não se inventa saldo nem se converte cashback em dinheiro. Testes usam dados fictícios e verificam rollback e isolamento entre empresas.

## 5. Qualidade

- Backend: testes de rateio, restituição original, recebimentos, atomicidade, lotes, carteira real SQLite, rollback, campanhas e DRE.
- Frontend: testes dos handlers reais, mensagens estruturadas, ações disponíveis, retry após timeout, invalidação da prévia e preservação do modal quando o caixa muda.
- Ruff, ESLint, Prettier, `git diff --check` e build de produção verificados no escopo.
- `FLUXO_UNICO.bat check`: uma head de migration, sem artefatos proibidos rastreados.

## 6. Homologação local

Ambiente: checkout isolado, navegador Chrome conectado e API simulada. Nenhum dado de produção copiado. A tela mostrou o botão de restituição, preservou a seleção e o motivo, exibiu prévia de R$ 38,90 (cashback R$ 10,00, crédito R$ 8,00, dinheiro R$ 20,90), abriu um caixa fictício e retornou aviso de sucesso. Evidência local, fora do Git: `runtime/devolucao-assistida/previa.jpg`.

Aceite técnico local documentado; aceite de negócio e validação em produção dependem do Lucas. Um teste de transferência de parceiro fora deste escopo usa vencimento fixo de setembro e expectativa de status anterior ao vencimento; não foi alterado.

## 7. Publicação e rollback

Entrega backend/frontend. Publicar somente após PR, checks e autorização explícita, pelo launcher oficial `scripts/deploy_producao_remoto.ps1`, reconstruindo o backend e gerando frontend no servidor. Verificar saúde e fluxo de devolução em tenant autorizado. Rollback por reversão do commit e novo deploy seguro. Não apagar lançamentos já registrados: a operação persiste no histórico e qualquer correção exige conciliação auditável.

## 8. Sustentação

O sucesso é uma única devolução com estoque, saldos e saída de caixa correspondentes à prévia. Falhas previsíveis mostram ações para abrir caixa, conferir saldos, revisar motivo/quantidades ou acessar financeiro, campanhas e estoque. Dados históricos sem rastreabilidade exigem conciliação pelo responsável antes de prosseguir.

## 9. Comunicação

O operador deve selecionar “Devolver aos saldos originais”, revisar a prévia e confirmar. Os demais bloqueios passam a incluir orientação e ação na própria tela. Comunicar essa mudança aos operadores do PDV quando publicada.

## 10. Fechamento

- Critérios técnicos e evidências locais registrados.
- Tenant, auditoria, histórico e atomicidade preservados.
- Publicação ainda não autorizada nem executada.
