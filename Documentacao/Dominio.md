---
tipo: base
atualizado: 2026-09-13
---

# Domínio e Entidades

Conceitos de negócio centrais, confirmados nos modelos SQLAlchemy (`backend/app/*_models.py`). Ver [[Banco-de-Dados]] para o mapa completo de todos os ~50 arquivos de modelo; aqui estão detalhadas apenas as entidades estruturalmente centrais.

## Entidades documentadas

- [[Tenant]] — empresa, raiz do isolamento multiempresa
- [[Usuario]] — pessoa com login no sistema
- [[Role-Permission]] — RBAC por tenant
- [[Cliente]] — pessoa física/jurídica (compradora, e também reaproveitada como fornecedor/entregador)
- [[Pet]] — animal, tutor = [[Cliente]]
- [[Produto]] — item de catálogo/estoque
- [[Venda]] — transação do PDV (distinta de `Pedido` do e-commerce)
- [[ContaPagar]] — obrigação financeira do tenant
- [[ContaReceber]] — direito financeiro do tenant

### Licenciamento e multiempresa (por loja)

- [[Plano]] — plano contratado, assinatura e mecânica do trial de 30 dias
- [[Modulo]] — liberação de áreas premium (financeiro avançado, WhatsApp, e-commerce, etc.) por tenant
- [[EmpresaGrupo]] — agrupamento de tenants com estoque seletivamente compartilhado, sem afetar plano/billing individual
- [[UserTenant]] — vínculo pessoa↔loja↔perfil; base do modelo "uma pessoa, múltiplas lojas"

## Relação estrutural (visão simplificada)

```text
Tenant ── plan/billing_status/trial_ends_at
 ├─ Usuario ──(UserTenant: role_id por tenant)── Role ── Permission
 ├─ AssinaturaModulo (módulo avulso) ─┐
 ├─ PlanDefinition (catálogo estático) ┴─→ módulos/entitlements ativos (Modulo)
 ├─ EmpresaGrupoMembro ── EmpresaGrupo ── EmpresaGrupoEstoqueCompartilhado (outro Tenant)
 ├─ Cliente ── Pet
 ├─ Produto (categoria, marca, lote)
 ├─ Venda ── VendaItem (Produto, Pet, Lote)
 │          └─ ContaReceber (se a prazo)
 └─ ContaPagar (fornecedor = Cliente)
```

Licenciamento por loja, resumido: cada [[Tenant]] tem seu próprio `plan` + `billing_status` (ver [[Plano]]), que junto com módulos avulsos (`AssinaturaModulo`) determina quais [[Modulo|módulos]] estão ativos. Um tenant pode pertencer a um [[EmpresaGrupo]] para compartilhar estoque com outras lojas, mas isso **não** compartilha plano/billing — cada loja paga e licencia separadamente. Uma pessoa ([[Usuario]]) pode ter acesso a várias lojas via [[UserTenant]], com um perfil ([[Role-Permission]]) potencialmente diferente em cada uma.

## Mapeamento completo por tabela (em andamento)

O sistema tem **333 tabelas** em 117 arquivos de modelo (contagem confirmada via `grep -r __tablename__`, 2026-09-13) — bem mais do que as entidades conceituais acima cobrem sozinhas. A pedido explícito, estamos documentando **1 arquivo por tabela do banco** (nome do arquivo = nome da tabela), com relacionamentos completos (quem referencia / é referenciado, uso real em service/rota). Trabalho dividido em blocos temáticos, processado um por vez. Achados de risco/dead-code encontrados pelo caminho estão centralizados em [[Achados-Revisao-Equipe]].

| # | Bloco | Status |
|---|---|---|
| 1 | Estoque & Produto (satélites) | ✅ Feito — 26 tabelas |
| 2 | Vendas & Caixa & Formas de Pagamento | ✅ Feito — 12 tabelas |
| 3 | Financeiro & DRE & Conciliação & Comissões | ✅ Feito — 32 tabelas |
| 4 | Compras (pedidos de compra, notas de entrada) | ✅ Feito — 9 tabelas |
| 5 | Fiscal (NF-e, Simples Nacional, config fiscal) | ✅ Feito — 9 tabelas |
| 6 | Veterinário (~25 tabelas) | ✅ Feito — 25 tabelas |
| 7 | Banho & Tosa | ✅ Feito — 20 tabelas |
| 8 | E-commerce & Pedido Integrado & Marketplaces | ✅ Feito — 13 tabelas |
| 9 | Integrações externas (Bling, iFood, Stone, WhatsApp) | ✅ Feito — 22 tabelas |
| 10 | RH (cargo, funcionário, contagem) | ✅ Feito — 3 tabelas |
| 11 | Entregas & Rotas | ✅ Feito — 4 tabelas |
| 12 | Plataforma & Segurança (sessões, auditoria, admin) | ✅ Feito — 11 tabelas |
| 13 | IA & Catálogo Mestre & Oportunidades | ✅ Feito — 45 tabelas |
| 14 | Diversos (templates, LGPD, ops, idempotência) | ✅ Feito — 18 tabelas |

**Mapeamento completo — todos os 14 blocos concluídos (2026-09-13).**

### Bloco 1 — Estoque & Produto (concluído)
[[produto_imagens]] · [[produto_kit_componentes]] · [[produto_granel_vinculos]] · [[granel_conversoes]] · [[produto_lotes]] · [[campanha_validade_automatica]] · [[campanha_validade_exclusoes]] · [[produto_fornecedores]] · [[listas_preco]] · [[produto_listas_preco]] · [[estoque_movimentacoes]] · [[produto_bling_sync]] · [[produto_bling_sync_queue]] · [[produto_bling_cost_sync_queue]] · [[alertas_estoque_negativo]] · [[locais_estoque]] · [[estoque_fracionamento_vinculos]] · [[estoque_fracionamento_conversoes]] · [[estoque_validade_bloqueios]] · [[pendencias_estoque]] · [[kit_composicao]] · [[produto_sku_aliases]] · [[produto_fusao_logs]] · [[produtos_atributos]] · [[produtos_atributos_opcoes]] · [[produtos_variacoes_atributos]]

⚠️ **Dois achados de dead code/risco confirmados neste bloco**, ambos documentados no arquivo da tabela correspondente:
- [[locais_estoque]] — modelo duplicado em 2 arquivos; o service que o usa tem import quebrado (`EstoqueLocal` inexistente); rotas dependentes não estão registradas no app.
- [[kit_composicao]] — tabela existe no banco mas não é lida/escrita por nenhum código vivo; risco de colisão de metadata se o arquivo órfão for importado.

### Bloco 2 — Vendas & Caixa & Formas de Pagamento (concluído)
[[venda_itens]] · [[venda_pagamentos]] · [[venda_baixas]] · [[caixas]] · [[movimentacoes_caixa]] · [[formas_pagamento_taxas]] · [[configuracao_impostos]] · [[formas_pagamento_comissoes]] · [[operadoras_cartao]] · [[operadoras_cartao_taxas]] · [[nao_vendas]] · [[nao_venda_itens]]

⚠️ Mais um dead-code confirmado ([[operadoras_cartao]] duplicado, igual ao padrão do Bloco 1), uma tabela órfã autodocumentada ([[formas_pagamento_comissoes]]), uma tabela sem caminho de escrita confirmado ([[venda_baixas]]), e um padrão recorrente de "FKs fantasmas" (Integer sem `ForeignKey()` real) espalhado por [[venda_pagamentos]], [[caixas]] e [[movimentacoes_caixa]] — detalhes em [[Achados-Revisao-Equipe]].

### Bloco 3 — Financeiro & DRE & Conciliação & Comissões (concluído, 32 tabelas)
`financeiro/`: [[contas_bancarias]] · [[movimentacoes_financeiras]] · [[lancamentos_manuais]] · [[lancamentos_recorrentes]] · [[categorias_financeiras]] · [[formas_pagamento]] · [[tipo_despesas]] · [[extratos_bancarios]] · [[movimentacoes_bancarias]] · [[regras_conciliacao]] · [[provisoes_automaticas]] · [[templates_adquirentes]] · [[bens_imobilizados]] · [[valor_empresa_configuracoes]]
DRE: [[dre_categorias]] · [[dre_subcategorias]] · [[regras_classificacao_dre]] · [[historico_classificacao_dre]]
Conciliação de cartões (Fase 1): [[empresa_parametros]] · [[adquirentes_templates]] · [[arquivos_evidencia]] · [[conciliacao_importacoes]] · [[conciliacao_lotes]] · [[conciliacao_validacoes]] · [[conciliacao_logs]] · [[conciliacao_recebimentos]] · [[conciliacao_metricas]] · [[historico_conciliacao]]
Comissões: [[comissoes_configuracao]] · [[comissoes_itens]] · [[comissoes_vendas]]
Diversos: [[duplicatas_ignoradas]]

⚠️ O bloco mais denso em achados até agora: um mesmo comentário equivocado ("tabela X não existe") foi copiado entre 3 arquivos diferentes desabilitando FKs reais ([[conciliacao_validacoes]] ↔ [[conciliacao_logs]]/[[conciliacao_recebimentos]]), duas tabelas de comissão com ORM não usado (todo acesso real é via SQL cru paralelo), uma tabela de provisão automática aparentemente nunca implementada ([[provisoes_automaticas]]), e uma armadilha de nomenclatura entre dois módulos de conciliação diferentes ([[templates_adquirentes]] vs [[adquirentes_templates]]) — detalhes completos em [[Achados-Revisao-Equipe]].

### Bloco 4 — Compras (concluído)
[[pedidos_compra]] · [[pedidos_compra_notas_entrada]] · [[pedidos_compra_itens]] · [[notas_entrada]] · [[notas_entrada_itens]] · [[produtos_historico_precos]] · [[compras_pendencias_fornecedor]] · [[compras_pendencias_fornecedor_itens]] · [[compras_pendencias_fornecedor_historico]]

⚠️ [[notas_entrada]] confirmado como hub central de integração compras↔estoque↔financeiro; achada uma dupla fonte de verdade pedido↔nota em [[pedidos_compra]] (campo direto `nota_entrada_id` vs. tabela de junção N:N) e dois caminhos paralelos de entrada física em estoque (via recebimento de pedido e via processamento de nota) — detalhes em [[Achados-Revisao-Equipe]].

### Bloco 5 — Fiscal (concluído)
[[fiscal_catalogo_produtos]] · [[fiscal_estado_padrao]] · [[simples_nacional_mensal]] · [[nota_fiscal_rateio_canal]] · [[nota_fiscal_item_rateio_canal]] · [[bling_notas_fiscais_cache]] · [[empresa_config_fiscal]] · [[produto_config_fiscal]] · [[variacao_config_fiscal]]

🔴 **O achado mais sério do mapeamento até agora**: [[fiscal_catalogo_produtos]] e [[fiscal_estado_padrao]] têm duas classes ORM cada mapeando a mesma tabela no mesmo registry SQLAlchemy — reproduzido isoladamente que isso gera `InvalidRequestError: Table already defined` se ambas forem importadas no mesmo processo (hoje não acontece só porque o runtime do FastAPI nunca importa o caminho de import da cópia órfã). Também achados dois routers de rateio fiscal por canal inteiramente mortos (nunca registrados no app), um deles com SQL cru contra uma tabela que não existe. Cadeia de resolução fiscal do PDV confirmada e documentada: `KitConfigFiscal → VariacaoConfigFiscal → ProdutoConfigFiscal → EmpresaConfigFiscal` — detalhes completos em [[Achados-Revisao-Equipe]].

### Bloco 6 — Veterinário (concluído, 25 tabelas)
Catálogos globais: [[vet_produtos_regulatorios]] · [[vet_conhecimento_fontes]] · [[vet_conhecimento_documentos]] · [[vet_medicamentos_catalogo]] · [[vet_protocolos_vacinas]] · [[vet_catalogo_procedimentos]]
Agenda/config: [[vet_lembrete_configuracoes]] · [[vet_consultorios]] · [[vet_agendamentos]] · [[vet_internacao_configuracoes]]
Clínico: [[vet_consultas]] · [[vet_prescricoes]] · [[vet_itens_prescricao]] · [[vet_vacinas_registros]] · [[vet_exames]] · [[vet_peso_registros]] · [[vet_fotos_clinicas]] · [[vet_perfil_comportamental]]
Procedimento/financeiro: [[vet_procedimentos_consulta]] · [[vet_orcamentos]] · [[vet_orcamento_itens]]
Internação: [[vet_internacoes]] · [[vet_evolucoes_internacao]] · [[vet_internacao_procedimentos_agenda]]
Cross-tenant: [[vet_partner_link]]

⚠️ Achado de modelagem importante: procedimento veterinário realizado ([[vet_procedimentos_consulta]]) **não gera [[Venda]]** — gera [[ContaReceber]] diretamente e baixa estoque diretamente, um caminho financeiro paralelo ao PDV. [[vet_partner_link]] é um caso sensível e intencional de compartilhamento de dados entre tenants (vet parceiro ↔ empresa dona da loja) que vale auditoria de segurança. Nenhuma duplicação de tabela encontrada neste bloco (diferente dos blocos 1, 2 e 5) — detalhes em [[Achados-Revisao-Equipe]].

### Bloco 7 — Banho & Tosa (concluído, 20 tabelas)
Agenda: [[banho_tosa_agendamentos]] · [[banho_tosa_agendamento_servicos]] · [[banho_tosa_avaliacoes]]
Cadastros: [[banho_tosa_configuracoes]] · [[banho_tosa_recursos]] · [[banho_tosa_servicos]] · [[banho_tosa_parametros_porte]] · [[banho_tosa_precos_servico]]
Operacional: [[banho_tosa_atendimentos]] · [[banho_tosa_etapas]] · [[banho_tosa_fotos]] · [[banho_tosa_insumos_previstos]] · [[banho_tosa_insumos_usados]]
Custos: [[banho_tosa_custos_snapshot]] · [[banho_tosa_taxi_dog]]
Pacotes: [[banho_tosa_pacotes]] · [[banho_tosa_pacote_creditos]] · [[banho_tosa_pacote_movimentos]] · [[banho_tosa_recorrencias]]
Retornos: [[banho_tosa_retorno_templates]]

✅ Ao contrário do Veterinário, este módulo usa o fluxo normal de [[Venda]]/PDV para cobrança (e o estoque é baixado via `EstoqueService` real, sem SQL cru) — bom exemplo de referência. ⚠️ Achada uma docstring enganosa: [[vet_perfil_comportamental]] afirma "alimentar Banho e Tosa", mas não há nenhum vínculo real — o campo parecido em [[banho_tosa_agendamentos]] usa só dados físicos do Pet. Vários "FKs fantasmas" pontuais, nenhuma duplicação de tabela, nenhum router morto — detalhes em [[Achados-Revisao-Equipe]].

### Bloco 8 — E-commerce & Pedido Integrado & Marketplaces (concluído, 13 tabelas)
Checkout: [[pedidos]] · [[pedido_itens]]
Integração Bling/marketplace: [[pedidos_integrados]] · [[pedidos_integrados_itens]]
Analytics/pagamento: [[ecommerce_analytics_events]] · [[ecommerce_payment_gateway_configs]] · [[ecommerce_notify_requests]]
Integração EcommerceAI: [[ecommerceai_connection_requests]] · [[ecommerceai_connections]] · [[ecommerceai_inbound_events]]
Estúdio de ofertas: [[oferta_publicacoes]] · [[oferta_publicacao_tokens]]
Segmentação: [[cliente_segmentos]]

✅ Confirma e aprofunda achado prévio de [[Venda]]: [[pedidos]] (checkout nativo) converte corretamente em [[Venda]] → [[ContaReceber]] via `_integrar_venda_ao_motor()`, sem FK de schema (vínculo só por texto livre + chave de idempotência) — padrão correto, igual ao Banho & Tosa. ⚠️ [[pedidos_integrados]] (import do Bling/marketplace) é um conceito **totalmente separado** de [[pedidos]] apesar do nome parecido — nunca vira Venda, serve só para reserva de estoque. Mesmo padrão "ORM só leitura, escrita via SQL cru" já visto alhures reaparece em [[cliente_segmentos]]. Nenhuma duplicação de tabela nem router morto neste bloco — detalhes em [[Achados-Revisao-Equipe]].

### Bloco 9 — Integrações externas (concluído, 22 tabelas)
Bling: [[bling_connections]] · [[bling_company_tenant_links]] · [[bling_flow_events]] · [[bling_flow_incidents]] · [[bling_pedido_webhook_events]]
iFood: [[ifood_merchant_configs]] · [[ifood_orders]] · [[ifood_events]]
Stone (morto): [[stone_transactions]] · [[stone_transaction_logs]] · [[stone_configs]]
WhatsApp: [[tenant_whatsapp_config]] · [[whatsapp_ia_sessions]] · [[whatsapp_ia_messages]] · [[whatsapp_ia_metrics]] · [[whatsapp_agents]] · [[whatsapp_handoffs]] · [[whatsapp_internal_notes]]
LGPD/Segurança: [[data_privacy_consents]] · [[data_access_logs]] · [[data_deletion_requests]] · [[security_audit_logs]]

🔴 **Módulo Stone inteiro é código morto** (3 tabelas nunca importadas fora de si mesmas) — e ainda promete criptografia de senha que não implementa de fato. ⚠️ [[ifood_orders]] segue o padrão "bypass" do veterinário (não gera Venda), diferente do padrão correto do e-commerce nativo. ✅ Confirmado mais um caso de vínculo cross-tenant deliberado ([[bling_company_tenant_links]], mesma categoria de [[vet_partner_link]]) e um bom exemplo de migração segredo legado→criptografado ([[tenant_whatsapp_config]]) — detalhes em [[Achados-Revisao-Equipe]].

### Bloco 10 — RH (concluído, 3 tabelas)
[[cargos]] · [[funcionario_contagens]] · [[funcionario_contagem_itens]]

⚠️ Módulo bem menor do que o esperado: não existe tabela de ponto/escala/jornada/banco de horas, e eventos de RH (férias, 13º) não têm tabela própria — são calculados on-the-fly a partir de `Cargo` e gravados diretamente em DRE/[[ContaPagar]]. [[cargos]] tem outra FK fantasma notável (`Cliente.cargo_id`, com comentário desatualizado dizendo que a tabela alvo "não existe ainda"). `funcionario_contagens`/`_itens` são na verdade um recurso de estoque via app mobile, não RH de verdade — nome enganoso — detalhes em [[Achados-Revisao-Equipe]].

### Bloco 11 — Entregas & Rotas (concluído, 4 tabelas)
[[rotas_entrega]] · [[rotas_entrega_rastreio_tokens]] · [[rotas_entrega_paradas]] · [[entrega_avaliacoes]]

🔴 Mais uma duplicação de tabela morta encontrada: `app/ia/aba8_models.py` (um "ABA 8 — Otimização de Entregas" abandonado) redefine `rotas_entrega`/`entregas`/`historico_entregas` com schema totalmente diferente, nunca importado em produção — risco latente de quebrar o boot se alguém importar por engano. ⚠️ Achado de padrão preocupante: várias colunas reais de [[rotas_entrega]]/[[rotas_entrega_paradas]] (lat/lon, distância real) existem no banco via DDL de runtime mas não estão declaradas no ORM — lidas via SQL cru e "penduradas" como atributos Python dinâmicos. Confirmado: rota de entrega sempre liga a [[Venda]] (PDV), nunca a Pedido de e-commerce diretamente — detalhes em [[Achados-Revisao-Equipe]].

### Bloco 12 — Plataforma & Segurança (concluído, 11 tabelas)
Admin da plataforma: [[platform_admins]] · [[platform_admin_sessions]]
Sessão/notificação de usuário: [[user_sessions]] · [[user_push_devices]] · [[app_notifications]] · [[usuario_menu_favoritos]]
Auditoria: [[audit_logs]]
Acerto/e-mail: [[acertos_parceiro]] · [[emails_templates]] · [[email_envios]]
Idempotência: [[idempotency_keys]]

✅ [[platform_admins]] confirmado como super-admin da plataforma, estruturalmente acima e isolado de qualquer tenant (não confundir com "superadmin" de tenant, que é só uma Role). 🔴 Achado sistêmico: 4 tabelas ([[audit_logs]], [[acertos_parceiro]], `emails_templates`, `email_envios`) sobrescrevem manualmente o `id` do mixin `BaseTenantModel`, perdendo a proteção contra duplicate-key que o próprio framework interno documenta existir — provável cópia de um template antigo pré-mixin. [[idempotency_keys]]`.user_id` tem três semânticas diferentes dependendo do caller — detalhes em [[Achados-Revisao-Equipe]].

### Bloco 13 — IA & Catálogo Mestre & Oportunidades (concluído, 45 tabelas — o maior bloco)
Catálogo Mestre: [[catalogo_mestre_produtos]] · [[catalogo_mestre_imagens]] · [[catalogo_mestre_produto_candidatos]] · [[catalogo_mestre_candidato_evidencias]] · [[catalogo_mestre_pendencias]] · [[catalogo_mestre_enriquecimento_execucoes]] · [[catalogo_mestre_sincronizacoes]]
Oportunidades/Evolução: [[opportunities]] · [[opportunity_events]] · [[evolucao_funcionalidade_usos]]
Fluxo de caixa preditivo: [[fluxo_caixa]] · [[indices_saude_caixa]] · [[projecao_fluxo_caixa]]
WhatsApp/IA de cliente (legado): [[conversas_whatsapp]] · [[mensagens_whatsapp]] · [[analise_cliente_inteligente]]
Chat IA financeiro: [[conversas_ia]] · [[mensagens_chat]] · [[contexto_financeiro_chat]]
DRE Inteligente: [[dre_periodos]] · [[dre_produtos]] · [[dre_categorias_analise]] · [[dre_comparacoes]] · [[dre_insights]] · [[indices_mercado]]
DRE por canal: [[dre_detalhe_canais]] · [[dre_consolidado]] · [[alocacao_despesa_canal]]
Extrato com IA: [[padroes_categorizacao_ia]] · [[lancamentos_importados]] · [[arquivos_extrato_importados]] · [[historico_atualizacao_dre]] · [[configuracao_tributaria]]
`ai_core/` (órfão): [[ai_decision_logs]] · [[ai_feedback_logs]] · [[ai_review_queue]] · [[ai_metrics_snapshots]] · [[ai_learning_patterns]] · [[ai_guardrail_violations]] · [[ai_circuit_breaker_logs]]
Read models CQRS: [[read_vendas_resumo_diario]] · [[read_performance_parceiro]] · [[read_receita_mensal]] · [[pedido_checkout_read]] · [[pedido_dashboard_read]]

🔴 **Maior achado de módulo órfão do mapeamento inteiro**: `ai_core/` (7 tabelas, framework completo de decisão de IA com feedback/revisão/circuit breaker) nunca é importado por nada fora de si mesmo. 🔴 [[dre_detalhe_canais]] é a tabela mais usada de todo o módulo `ia/` mas **não está registrada no Alembic/`db/base.py`** — risco real de drift. ⚠️ FKs fantasmas com nome de tabela errado em [[conversas_whatsapp]]/`analise_cliente_inteligente` (`"usuarios"`/`"cliente"` em vez de `users`/`clientes`). [[opportunities]], [[pedido_checkout_read]] e [[pedido_dashboard_read]] são scaffolding nunca conectado — detalhes completos em [[Achados-Revisao-Equipe]].

### Bloco 14 — Diversos (concluído, 18 tabelas — fecha o mapeamento)
Templates de onboarding: [[template_bundles]] · [[template_items]] · [[tenant_template_installs]] · [[tenant_template_item_installs]]
LGPD: [[data_subject_requests]]
Ops/plataforma: [[ops_error_events]] · [[ops_alerts]] · [[ops_recovery_actions]] · [[ops_journey_events]] · [[ops_tenant_onboarding_notes]]
Fiscal/ração: [[kit_config_fiscal]] · [[linhas_racao]] · [[portes_animal]] · [[fases_publico]] · [[tipos_tratamento]] · [[sabores_proteina]] · [[apresentacoes_peso]]
Outros: [[controle_processamento_mensal]]

✅ Achado positivo raro: [[kit_config_fiscal]] é um caso de duplicação de tabela **corretamente resolvida** pelo próprio time (cópia antiga removida, só reexport de compatibilidade permanece) — contraste com [[fiscal_catalogo_produtos]]/[[fiscal_estado_padrao]], ainda não corrigidas. 🔴 Mais um código morto: `controle_processamento_mensal` tem serviço completo de idempotência mensal nunca chamado por nenhuma rota. Confirmado pela pesquisa: nenhuma tabela adicional com `__tablename__` real ficou de fora do levantamento — detalhes em [[Achados-Revisao-Equipe]].

---

## Mapeamento por tabela: concluído

Todos os 14 blocos foram documentados. Total de arquivos de tabela criados nesta fase: 249, cobrindo (junto com os 9 documentos conceituais de entidade já existentes antes desta fase) a esmagadora maioria das 333 tabelas do banco. Todos os achados de risco/dead-code/inconsistência encontrados pelo caminho estão centralizados e organizados por bloco em [[Achados-Revisao-Equipe]] — recomenda-se essa leitura antes de qualquer refatoração grande no backend.

## Entidades confirmadas mas sem documento próprio (fora do mapeamento por tabela)

Algumas entidades muito periféricas continuam listadas só em bloco no [[Banco-de-Dados]] até seu bloco temático ser processado acima.

## Não identificado

- ❓ Dicionário de dados campo-a-campo (fora do escopo desta fase; priorizado por entidade central, não por tabela completa, conforme instrução do escopo desta análise).
