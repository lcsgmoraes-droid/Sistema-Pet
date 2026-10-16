# Correção de campos em NF rejeitada

## Identificação

- Data: 2026-10-13. Responsável de negócio: Lucas. Executor: Codex.
- Prioridade: P1. Risco: médio, por editar cadastro fiscal e lote utilizado na emissão.
- Domínios: NF-e/NFC-e, produtos e dados fiscais de lotes.

## 1. Necessidade e aceite

A Central mostrava a rejeição 778 (NCM inexistente, item 23), mas a validação de formato aceitava os oito dígitos e o editor não exibia nenhum campo. Ao abrir uma nota IntNFe rejeitada, a tela deve mostrar nota, destinatário, total, itens, erro original e campo fiscal editável em vermelho, com orientação e eventual sugestão identificada. Salvar deve atualizar o dado efetivamente usado na emissão e revalidar antes da confirmação de reenvio.

## 2. Regras e dados

- O diagnóstico histórico orienta a correção sem criar bloqueio permanente depois de corrigir.
- Edição limitada a campos fiscais de item de venda da empresa autenticada, em tentativa IntNFe rejeitada sem autorização.
- NCM, CEST e origem provenientes do lote atualizam esse lote e o cadastro. A tela explica a origem e o alcance da correção.
- Venda, quantidades, preços e estoque não são editados. Sem migration ou importação.
- Travas de venda/item/produto/lote e auditoria de campos alterados preservam integridade e histórico.

## 3. Componentes e integração

- Diagnóstico interpreta código/motivo/nItem e preserva item_id, inclusive em produtos repetidos.
- GET/PUT `/nfe/vendas/{venda_id}/itens/{item_id}/fiscal` devolvem fonte efetiva e aceitam somente campos fiscais enviados.
- Editor reaproveita pré-validação, confirmação e reenvio existentes; processamento/autorização continuam protegidos.
- Indisponibilidade na leitura/salvamento mostra erro e impede a correção/retransmissão pelo editor.
- Sugestão para luvas de procedimento de látex é manual e condicional, apoiada na [consulta da SEFAZ-SP](https://legislacao.fazenda.sp.gov.br/Paginas/RC31692_2025.aspx), com conferência de material, finalidade e NF de entrada.

## 4. Segurança e privacidade

Autenticação e filtros de tenant em venda, item, produto e lote. Vínculos externos, notas pendentes/autorizadas e campos extras são recusados. Auditoria registra identificação da venda/item e campos fiscais alterados; não exige credenciais novas nem registra documentos do cliente. Testes incluem acesso cruzado e mudanças de situação.

## 5. Qualidade

- 109 testes backend passaram: diagnóstico, emissão, recuperação, rotas e persistência fiscal.
- 6 testes frontend e `test:nfe-fiscal-assistida` passaram; ESLint/Ruff focados passaram.
- Build frontend passou na cópia isolada baseada na main atual.
- Verificação visual local com 25 itens confirmou item 23, campo NCM vermelho, sugestão manual e PUT somente do NCM escolhido.
- Integração preserva o rateio de descontos da main. Regressão de descontos validada separadamente.

## 6. Homologação

Dados de demonstração e adaptador local, sem transmitir NF ou alterar cadastros reais. A rejeição real foi lida pela aba autenticada do tenant indicado. Dispensa de registro adicional: cenários e resultados estão nesta ficha; captura local em `runtime/nfe-correcao-qa/editor-ncm.png`, fora do Git. Homologação fiscal em produção pendente de publicação autorizada e operação do usuário.

## 7. Publicação e rollback

Entrega backend/frontend, sem mudança mobile. Publicação pelo fluxo oficial após revisão/checks e autorização explícita do Lucas. Conferir health e abertura da nota rejeitada após publicar. Abortar em falha dos checks ou health. Rollback por reversão do commit e deploy oficial; alterações fiscais já salvas exigem revisão da auditoria antes de eventual ajuste manual.

## 8. Sustentação

Auditoria `corrigir_item_nfe_rejeitada`; sucesso operacional significa conseguir revisar e salvar o campo apontado, validar e reenviar após confirmação. Rejeição sem identificação suficiente mantém orientação geral, sem escolher arbitrariamente outro item. Correções de destinatário/empresa permanecem pelos cadastros existentes.

## 9. Comunicação

Orientar usuários da Central: abrir nota rejeitada, revisar o campo destacado, conferir sugestão e fonte, salvar/verificar, confirmar transmissão. Explicar que o salvamento pode corrigir também o cadastro e lote identificados na tela.

## 10. Fechamento

Critérios implementados e validados localmente; isolamento, auditoria, documentação e rollback registrados. Produção não autorizada nesta entrega. A nota real segue para revisão fiscal e reenvio pelo usuário após publicação.
