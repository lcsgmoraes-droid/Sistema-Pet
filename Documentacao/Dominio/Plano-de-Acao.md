---
tipo: base
atualizado: 2026-09-13
---

# Plano de ação — achados técnicos

Espelha [[Achados-Revisao-Equipe]] bloco a bloco (1 a 14) — todo item tem uma ação proposta e uma ponderação, inclusive os que são só confirmação de um padrão bom. Tipo de ação: **🔧 Corrigir** (dá pra fazer direto), **🧭 Decidir** (precisa de alinhamento antes), **✅ Referência** (não é problema, só vale registrar). Itens marcados **⚠️ alta prioridade** são os mesmos do índice crítico original.

## Rodada de correções (2026-09-14)

Todos os itens de **zero risco de banco** (arquivo órfão nunca importado, comentário/docstring, colisão de nome, FK apontando errado num módulo que nem está registrado no Alembic) foram corrigidos nesta rodada — marcados **✅ CORRIGIDO** abaixo. Verificado por importação real do backend: `app.db.base` (módulo que o Alembic usa pra ver todas as tabelas) carrega os 150 modelos sem lançar o `InvalidRequestError` que era o risco central do achado fiscal.

Itens que envolvem **restaurar FK numa tabela já populada** (ex.: `Cliente.cargo_id`, `conciliacao_validacoes`, as FKs de `users.id` marcadas `# FK para users`, `vet_conhecimento_documentos`/`vet_evolucoes_internacao`) **não foram tocados nesta rodada** — precisam de uma migration + checagem de dado órfão antes de aplicar a constraint, o que é uma categoria de risco diferente de "apagar arquivo morto". Ver seção own em baixo.

## Não corrigidos ainda — precisam de migration (próxima rodada, mediante confirmação)

| Achado | Por que não foi junto | Esforço |
|---|---|---|
| `Cliente.cargo_id` → restaurar FK | Tabela `clientes` populada — precisa checar dado órfão antes do `ADD CONSTRAINT` | S/M |
| FK de [[conciliacao_validacoes]] em [[conciliacao_logs]]/[[conciliacao_recebimentos]] | Idem — checar dado órfão primeiro | S/M |
| FKs `# FK para users` em [[data_access_logs]]/[[data_deletion_requests]]/[[security_audit_logs]] | Idem | S/M |
| FKs em [[vet_conhecimento_documentos]]/[[vet_evolucoes_internacao]] | Idem | S |
| [[caixas]]: `Float` → `DECIMAL(10,2)` | Migration de tipo de coluna, possível conversão de dado existente | M |
| [[historico_classificacao_dre]]`.valor`: `Integer` → `Numeric` | Migration de tipo de coluna | S |
| [[duplicatas_ignoradas]]: normalizar ordem do par | Checagem de aplicação, não é só schema | S |
| Override de `id` em 4 tabelas ([[audit_logs]] etc.) | Migration de identity + resync de sequence — a mais delicada da lista | M |

Avise se quiser que eu já prepare as migrations dessas, uma de cada vez (com a checagem de dado órfão antes de cada `ADD CONSTRAINT`).

Versão interativa (com checklist "discutido em reunião" por item, salvo no navegador): [Raio-X do Schema](https://claude.ai/code/artifact/ab2e8966-2656-459c-b64c-a167289943ac).

## Bloco 1 — Estoque & Produto

| Achado | Ação | Solução proposta | Ponderação |
|---|---|---|---|
| [[locais_estoque]]: duplicação + service quebrado | 🔧 | Apagar um dos dois modelos duplicados (manter o com `origem_padrao`); decidir o destino de `estoque_transferencia_service.py`. | Confirmar se "estoque por local" já foi plano de produto antes de apagar — pode ser feature pela metade. |
| [[kit_composicao]]: duplicação morta dos dois lados | 🔧 | Remover `app/kit_composicao_models.py`; avaliar dropar a tabela física via migration. | Risco de colisão de metadata se importado por engano, mesma classe do achado fiscal. |
| [[listas_preco]]/[[produto_listas_preco]]: sem rota CRUD | 🧭 | Perguntar se ainda é plano; se sim, construir CRUD; se não, remover. | Hoje só é tocada indiretamente — feature incompleta, não código morto puro. |
| Padrão `ondelete`: `RESTRICT` no fracionamento vs. `CASCADE` no resto | ✅ | Nenhuma correção — documentar como padrão de referência. | Vale revisar se outras tabelas de dado histórico sensível deveriam adotar o mesmo `RESTRICT`. |
| Inconsistência JSON: `Text` manual vs. coluna `JSON` nativa | 🔧 | Padronizar [[estoque_movimentacoes]] para `JSON` nativo, como em [[estoque_fracionamento_conversoes]]. | Exige migration de tipo + conversão do dado já serializado como texto. |
| [[produto_fornecedores]]`.fornecedor_id` aponta para `clientes.id` | ✅ | Nenhuma correção — padrão intencional (fornecedor = Cliente). | Repetido em dezenas de tabelas — mudar agora teria custo alto e nenhum benefício. |

## Bloco 2 — Vendas & Caixa & Formas de Pagamento

| Achado | Ação | Solução proposta | Ponderação |
|---|---|---|---|
| [[operadoras_cartao]]: duplicação órfã | 🔧 | Remover `operadoras_cartao_models.py` — nunca importado. | Baixo risco, confirmado por busca exaustiva. |
| [[formas_pagamento_comissoes]]: tabela órfã autodocumentada | 🔧 | Remover modelo e avaliar drop da tabela. | Já rotulada como órfã pelo próprio time. |
| [[venda_baixas]]: só lida, nunca escrita via ORM | 🧭 | Confirmar se foi substituída por `VendaPagamento`/[[ContaReceber]]; se sim, deprecar. | `routes/ecommerce_entregador.py` ainda lê — não apagar sem migrar essa leitura. |
| FKs fantasmas em [[venda_pagamentos]]/[[caixas]]/[[movimentacoes_caixa]] | 🔧 | Restaurar as FKs reais após checagem de dados órfãos. | Comentários "tabela não existe" no código estão desatualizados. Tratar no épico geral. |
| [[caixas]] usa `Float` para dinheiro | 🔧 | Migrar para `DECIMAL(10,2)`, como em `vendas_models.py`. | Requer migration de tipo; avaliar imprecisão de ponto flutuante já armazenada. |

## Bloco 3 — Financeiro & DRE & Conciliação & Comissões

| Achado | Ação | Solução proposta | Ponderação |
|---|---|---|---|
| Comentário "tabela não existe" copiado em [[conciliacao_logs]]/[[conciliacao_recebimentos]] | 🔧 ⚠️ | Restaurar as duas FKs para [[conciliacao_validacoes]]`.id`. | Checar dado órfão antes de aplicar a constraint. |
| [[formas_pagamento]]`.operadora_id`: mesmo padrão | 🔧 | Restaurar FK real para `operadoras_cartao.id`. | Mesma dívida do Bloco 2 — tratar junto. |
| [[comissoes_configuracao]]/[[comissoes_vendas]]: ORM não usado, escrita via SQL cru paralelo | 🔧 | Migrar `ComissoesConfig` para sessão ORM real. | Mudança de maior superfície — testar bem antes de trocar o caminho de escrita. |
| [[provisoes_automaticas]]: nunca usada | 🧭 | Confirmar se é roadmap; se não, remover. | Nenhum dado depende dela hoje. |
| Nomenclatura quase-espelhada: [[templates_adquirentes]] vs. [[adquirentes_templates]] | 🔧 | Renomear uma das duas classes. | Exige atualizar todos os call sites — refactor isolado. |
| Colisão de nomes `ComissaoItem`/`FormaPagamento` (ORM vs. Pydantic) | 🔧 | Sufixar as classes Pydantic (`Schema`/`DTO`). | Seguro — só afeta imports internos. |
| [[conciliacao_lotes]]: relationship com [[ContaReceber]] nunca implementado | 🧭 | Implementar de verdade (tabela de associação) ou remover o contador manual. | Relatórios que dependem de `quantidade_parcelas` podem estar contando errado. |
| [[historico_classificacao_dre]]`.valor` em `Integer` (centavos) | 🔧 | Migrar para `Numeric`. | Baixo risco — é tabela de histórico/log. |
| [[duplicatas_ignoradas]]: `UniqueConstraint` não normaliza ordem do par | 🔧 | Checagem na aplicação garantindo `produto_id_1 < produto_id_2`. | Baixo impacto, barato de corrigir. |

## Bloco 4 — Compras

| Achado | Ação | Solução proposta | Ponderação |
|---|---|---|---|
| Dupla fonte de verdade pedido↔nota em [[pedidos_compra]] | 🔧 | Deprecar `nota_entrada_id`, migrar fluxo de confronto para a tabela de junção N:N. | Lógica de negócio ativa — QA cuidadoso. |
| Dois caminhos paralelos de entrada em estoque (recebimento vs. nota) | 🧭 | Mapear se são mutuamente exclusivos ou se podem colidir. | Se houver sobreposição, pode estar duplicando estoque silenciosamente. |
| FK fantasma em `fornecedor_id` ([[pedidos_compra]], [[notas_entrada]], [[compras_pendencias_fornecedor]]) | 🔧 | Restaurar as FKs para `clientes.id`. | Tratar no épico geral de FKs fantasmas. |
| [[notas_entrada]] confirmada como hub central | ✅ | Nenhuma correção — documentar como tabela de alto cuidado. | Qualquer mudança de schema tem raio de impacto grande. |
| Desnormalização deliberada em [[compras_pendencias_fornecedor]] | ✅ | Nenhuma correção — snapshot em texto é o design correto. | Documentar que pode divergir do estado atual das tabelas de origem. |
| Nenhuma duplicação de tabela neste bloco | ✅ | Nenhuma ação. | — |

## Bloco 5 — Fiscal

| Achado | Ação | Solução proposta | Ponderação |
|---|---|---|---|
| [[fiscal_catalogo_produtos]]/[[fiscal_estado_padrao]]: duplicação com risco real de crash | 🔧 ⚠️ | Remover as cópias órfãs em `fiscal_models/`; reexportar dos módulos canônicos (padrão já usado em [[kit_config_fiscal]]/[[produto_config_fiscal]]). | Grep final antes de mesclar + rodar suíte/autogenerate. PR pequeno e isolado. |
| Dois routers de código morto (rateio por canal) | 🔧 | Remover os routers e as tabelas [[nota_fiscal_rateio_canal]]/[[nota_fiscal_item_rateio_canal]]. | Se "rateio por canal" ainda for necessidade real, redesenhar contra [[bling_notas_fiscais_cache]]. |
| `empresa_config_fiscal.fiscal_estado_padrao_id` sempre `NULL` | 🔧 ⚠️ | Corrigir `obter_ou_criar_config_fiscal_empresa_padrao` para popular o campo, ou depreciar. | Se restaurado, precisa de migration de backfill por `uf`. |
| Desenho duplicado nunca plugado (rateio vs. canal único) | ✅ | Mesma ação do item de routers mortos — usar [[bling_notas_fiscais_cache]] como referência de desenho funcional. | — |
| [[produto_config_fiscal]]: duplicação já corrigida pelo time | ✅ | Nenhuma ação — usar como modelo para corrigir os casos pendentes. | Prova de que o processo de correção já funcionou uma vez. |
| [[variacao_config_fiscal]]`.variacao_id` aponta para tabela inexistente | 🧭 | Confirmar que variação = `Produto.tipo_produto='VARIACAO'`; remover campo vestigial se sim. | Mesmo padrão já visto em [[kit_composicao]]. |
| Cadeia de resolução fiscal do PDV confirmada | ✅ | Nenhuma ação — usar como material de onboarding. | — |

## Bloco 6 — Veterinário

| Achado | Ação | Solução proposta | Ponderação |
|---|---|---|---|
| [[vet_procedimentos_consulta]] não passa pelo módulo de Vendas | 🧭 | Confirmar se é intencional; atualizar relatórios financeiros ou integrar como o e-commerce. | Afeta correção de números financeiros hoje — auditar dashboards existentes. |
| [[vet_partner_link]]: compartilhamento entre tenants | 🧭 | Agendar auditoria de segurança dedicada do filtro de `tenancy/filters.py`. | Desenho deliberado e sensível — não é bug confirmado. |
| Prescrição desconectada do estoque | 🧭 | Decidir se o catálogo de medicamentos deveria ter FK real para `produtos`. | Confirmar com a operação clínica se é dor real percebida. |
| Inconsistência produto: `insumos` JSON vs. [[vet_orcamento_itens]]`.produto_id` FK real | 🔧 | Alinhar `insumos` para FK real ou validar na aplicação. | Migrar de JSON pra tabela associativa é migration de dado, não só schema. |
| [[vet_orcamentos]] sem conversão automática em procedimento/venda | 🧭 | Confirmar se a conversão deveria ser automática. | Pode ser lacuna real de produto — validar com quem usa o módulo. |
| Padrão "veterinário = Cliente" sem validação de tipo no banco | 🔧 | Validação na camada de serviço garantindo `tipo_cadastro=veterinario`. | Constraint de banco não é trivial aqui — mais realista na aplicação. |
| FKs fantasmas em [[vet_conhecimento_documentos]]/[[vet_evolucoes_internacao]] | 🔧 | Restaurar FKs reais para `users.id`. | Baixo risco, isoladas. |
| Nenhuma duplicação de tabela neste bloco | ✅ | Nenhuma ação. | — |

## Bloco 7 — Banho & Tosa

| Achado | Ação | Solução proposta | Ponderação |
|---|---|---|---|
| Docstring enganosa de `PerfilComportamental` | 🔧 ⚠️ | Corrigir a docstring ou implementar o vínculo de fato. | Vitória rápida — é uma frase, não mudança de schema. |
| Padrão de cobrança correto (usa `VendaService` normalmente) | ✅ | Nenhuma ação — usar como referência para corrigir o Veterinário. | — |
| Consumo de estoque correto via `EstoqueService` | ✅ | Nenhuma ação — bom exemplo de integração. | — |
| Várias FKs fantasmas pontuais (taxi dog, custo snapshot, DRE) | 🔧 | Restaurar as FKs listadas. | Nenhuma com efeito prático negativo confirmado — prioridade baixa. |
| Nenhuma duplicação e nenhum router morto | ✅ | Nenhuma ação. | — |

## Bloco 8 — E-commerce & Pedido Integrado & Marketplaces

| Achado | Ação | Solução proposta | Ponderação |
|---|---|---|---|
| Padrão correto confirmado (Pedido→Venda) | ✅ | Nenhuma ação — referência para corrigir iFood/Veterinário. | — |
| Ambiguidade [[pedidos]] vs. [[pedidos_integrados]] | 🧭 | Considerar renomear `pedidos_integrados`/`PedidoIntegrado`, ou reforçar com docstring. | Renomear em produção é migration + atualizar código; avaliar custo x benefício. |
| [[cliente_segmentos]]: ORM só leitura, escrita via SQL cru | 🔧 | Migrar escrita para sessão ORM. | Baixa urgência hoje — resolver oportunisticamente. |
| [[oferta_publicacao_tokens]]: entropia do token não auditada | 🧭 | Confirmar uso de `secrets` do Python com comprimento suficiente. | Rápido de verificar, mas é chave pública sem autenticação. |
| FKs fantasmas pontuais (`Pedido.cliente_id` etc.) | 🔧 | Restaurar as FKs listadas. | Épico geral de FKs fantasmas. |
| Nenhuma duplicação e nenhum router morto | ✅ | Nenhuma ação. | — |

## Bloco 9 — Integrações externas (Bling, iFood, Stone, WhatsApp)

| Achado | Ação | Solução proposta | Ponderação |
|---|---|---|---|
| Módulo Stone morto + criptografia prometida não implementada | 🧭 ⚠️ | Apagar se fora do roadmap; se não, implementar criptografia real antes de qualquer credencial real. | Achado de segurança — avisar quem cuida de integrações. |
| [[ifood_orders]]: padrão bypass (não gera Venda) | 🧭 | Confirmar intencionalidade; integrar como o e-commerce se não for. | Mesmo achado do Bloco 6 — tratar as duas decisões juntas. |
| [[bling_company_tenant_links]]: outro caso de cross-tenant deliberado | 🧭 | Incluir na mesma auditoria de segurança do [[vet_partner_link]]. | Tem checagem de conflito de `company_id` — bom sinal, mas ainda merece confirmação formal. |
| Duplicação estrutural em `bling_flow_monitor_routes.py` | 🔧 | Escolher um padrão só (registrar direto ou mover handlers pra `bling_routes.py`). | Não afeta comportamento, só confunde quem for debugar. |
| Inconsistência de `tenant_id` dentro do módulo WhatsApp | 🔧 | Adicionar FK real nas tabelas de `whatsapp/security.py`. | Mudança aditiva de baixo risco — confirmar dados existentes antes. |
| [[tenant_whatsapp_config]]: bom exemplo de migração de segredo | ✅ | Nenhuma ação — modelo para corrigir `stone_configs`. | — |
| FKs fantasmas com TODO explícito no comentário | 🔧 | Restaurar FKs para `users.id` em [[data_access_logs]]/[[data_deletion_requests]]/[[security_audit_logs]]. | Um dos mais fáceis de corrigir — o comentário já documenta o que fazer. |

## Bloco 10 — RH

| Achado | Ação | Solução proposta | Ponderação |
|---|---|---|---|
| `Cliente.cargo_id`: FK comentada no código | 🔧 ⚠️ | Descomentar `ForeignKey("cargos.id")` e gerar migration. | Vitória rápida — [[cargos]] já existe e está em uso por 7+ serviços. |
| Não existe módulo de ponto/escala/jornada | ✅ | Nenhuma ação — constatação de escopo. | — |
| Férias/13º/provisões sem tabela própria (cálculo on-the-fly) | 🧭 | Criar tabela de snapshot mensal se houver necessidade de auditoria histórica. | Não é bug — é limitação de rastreabilidade; só mexer se houver dor real relatada. |
| `funcionario_contagens`/`_itens`: nome enganoso (é estoque, não RH) | 🔧 | Considerar renomear. | Cosmético, baixa prioridade. |
| Nenhuma duplicação; routers registrados | ✅ | Nenhuma ação. | — |

## Bloco 11 — Entregas & Rotas

| Achado | Ação | Solução proposta | Ponderação |
|---|---|---|---|
| `app/ia/aba8_models.py`: mais uma duplicação morta | 🔧 ⚠️ | Apagar o arquivo inteiro. | Checar migrations aplicadas com colunas exclusivas desse arquivo antes. |
| Padrão "ORM incompleto" em [[rotas_entrega]]/[[rotas_entrega_paradas]] | 🔧 | Formalizar as colunas como `Column` reais, com migration definitiva. | Simplifica o código que hoje faz SQL cru + atributo dinâmico. |
| Rota sempre liga a [[Venda]], nunca a Pedido de e-commerce | ✅ | Nenhuma ação — documentar como regra de domínio confirmada. | — |
| "Entregador" sempre modelado como [[Cliente]] | ✅ | Nenhuma ação. | — |
| [[banho_tosa_taxi_dog]]`.rota_entrega_id`: FK fantasma (já tratada no Bloco 7) | ✅ | Ver ação do Bloco 7. | — |
| [[rotas_entrega_rastreio_tokens]] segue o bom padrão de [[oferta_publicacao_tokens]] | ✅ | Incluir na mesma verificação de entropia do Bloco 8. | — |

## Bloco 12 — Plataforma & Segurança

| Achado | Ação | Solução proposta | Ponderação |
|---|---|---|---|
| Override manual do `id` em 4 tabelas | 🔧 ⚠️ | Remover o override em [[audit_logs]]/[[acertos_parceiro]]/`emails_templates`/`email_envios`. | Exige migration de identity + `setval()`. Checar Sentry por duplicate-key antes. |
| `audit.py::log_audit` nunca importado | 🔧 | Remover — manter só `audit_log.py::log_action`. | Checar rapidamente se há alguma vantagem de design antes de apagar. |
| [[idempotency_keys]]`.user_id` com três semânticas diferentes | 🔧 | Separar em `actor_id` + `actor_type` explícito. | Contrato usado em 4+ pontos de escrita — coordenar todos os callers. |
| [[app_notifications]]: esquema de idempotência próprio e paralelo | 🧭 | Avaliar migrar para a tabela genérica. | Só vale se o time for unificar os pontos de idempotência do sistema. |
| [[platform_admins]] corretamente isolado | ✅ | Nenhuma ação. | — |
| Padrão "parceiro = Cliente" confirmado em acerto/e-mail | ✅ | Nenhuma ação. | — |

## Bloco 13 — IA & Catálogo Mestre & Oportunidades

| Achado | Ação | Solução proposta | Ponderação |
|---|---|---|---|
| `ai_core/` inteiro nunca conectado | 🧭 ⚠️ | Remover o pacote ou plugar a um fluxo real + registrar no Alembic. | Maior esforço da lista — não decidir sozinho, puxar histórico do porquê foi criado. |
| [[dre_detalhe_canais]] e outras tabelas `ia/` fora do Alembic | 🔧 ⚠️ | Adicionar os imports faltantes em `db/base.py`/`alembic/env.py`. | Inspecionar o diff do autogenerate linha a linha antes de aplicar. |
| FKs com nome de tabela errado (`"usuarios"`/`"cliente"`) | 🔧 | Corrigir para `users.id`/`clientes.id` em [[conversas_whatsapp]]/`analise_cliente_inteligente`. | Erro de digitação, nunca funcionaria mesmo ativado — fácil de corrigir. |
| Scaffolding CQRS abandonado ([[pedido_checkout_read]], [[pedido_dashboard_read]]) | 🧭 | Completar seguindo [[read_vendas_resumo_diario]] ou remover. | Bom par de exemplos (funcionando vs. abandonado) para a decisão. |
| [[opportunities]] confirmada órfã | 🧭 | Remover se confirmado que nunca será implementada. | Baixo risco — nada depende dela. |
| `CatalogMasterScheduler` nunca instanciado | 🧭 | Decidir se o enriquecimento deveria ser automático. | Só vira problema se o catálogo ficar defasado sem ninguém notar. |
| Achados pontuais menores (DRE legado, timestamp duplicado, comentário duplicado, acoplamento cross-domain) | 🔧 | Faxina independente por item. | Nenhum tem risco relevante — resolver de passagem. |

## Bloco 14 — Diversos

| Achado | Ação | Solução proposta | Ponderação |
|---|---|---|---|
| [[kit_config_fiscal]]: duplicação já corrigida pelo time | ✅ | Nenhuma ação — usar como checklist para os casos pendentes. | — |
| `controle_processamento_mensal`: código morto | 🧭 | Confirmar necessidade; conectar a um gatilho real ou remover. | Mesmo padrão do `CatalogMasterScheduler`. |
| Assimetria de FK em `ops_models.py` | ✅ | Nenhuma correção obrigatória — decisão de design. | — |
| [[data_subject_requests]] não confundir com LGPD do WhatsApp | ✅ | Nenhuma ação — já documentado. | — |
| Templates de onboarding ligados por código+versão em texto | 🔧 | Checagem de integridade na aplicação ao instalar um bundle. | Baixo risco — fluxo interno, não input externo. |
| Confirmado: nenhuma tabela adicional fora do levantamento | ✅ | Fecha o mapeamento. | — |
