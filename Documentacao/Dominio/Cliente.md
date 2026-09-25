---
tipo: dominio
atualizado: 2026-09-22
---

# Entidade — Cliente

Ver [[Pet]], [[Funcionalidades]] (Pessoas/Clientes), [[Venda]], [[Tenant]], [[EmpresaGrupo]], [[UserTenant]], [[Plano]].

## Relação com Tenant, lojas e grupos de empresa

**1 [[Tenant]] = 1 loja.** Não existe, em lugar nenhum do sistema, um modelo "Loja"/"Filial"/"Unidade" separado dentro de um Tenant (confirmado por busca no código — não há nenhuma classe assim). Cada `Tenant` já **é** uma loja/empresa individual: tem seu próprio isolamento de dados via Row Level Security no Postgres, e seu próprio ciclo de contratação (`plan`/`billing_status`/módulos — ver [[Plano]]).

**Cliente do CorePet com 7 lojas físicas → 7 Tenants, não 1 Tenant com 7 "lojas" dentro dele.** Cada loja vira um `Tenant` próprio, com assinatura, trial e faturamento **totalmente independentes** — confirmado: o modelo que junta lojas do mesmo grupo comercial ([[EmpresaGrupo]]) não tem nenhuma coluna de plano ou billing. As 7 lojas podem, opcionalmente, ser ligadas por um `EmpresaGrupo`, que:
- permite compartilhar **estoque de produto** seletivamente entre lojas (ver [[Produto]] para o mecanismo exato — nunca mexe em Cliente);
- permite transferências de itens entre lojas do grupo (gera lançamento financeiro real nos dois tenants — não é "grátis");
- **não** une nem afeta o licenciamento — as 7 lojas continuam pagando e contratando módulos cada uma por si.

**Quem acessa as 7 lojas é a mesma pessoa, mas o sistema enxerga isso como 7 vínculos separados.** O dono é 1 único `User` (uma conta de login), com uma linha [[UserTenant]] por loja — 7 linhas, cada uma podendo ter um perfil (`Role`) diferente (ex.: Administrador nas 7, ou Administrador em 3 e Gerente nas outras 4). No login, ele escolhe em qual das 7 lojas quer trabalhar (`POST /auth/select-tenant`); a partir daí, tudo que ele vê nas telas normais do sistema (clientes, produtos, módulos liberados) é só da loja escolhida naquele momento.
Exceção real e confirmada: se as 7 lojas estiverem no mesmo [[EmpresaGrupo]], existe um **dashboard de visão consolidada** (`GET /grupos-empresas/{grupo_id}/visao-consolidada` e endpoints de detalhamento) que soma vendas/estoque/financeiro das 7 de uma vez, calculado com segurança (entra no contexto de cada loja uma por vez, respeitando o isolamento de cada uma, e só soma o resultado depois) — ver [[EmpresaGrupo]] para os detalhes. Isso cobre venda, estoque e financeiro; **não cobre Cliente** (ver abaixo).

**Cliente (o comprador/tutor) é 100% isolado por loja — não existe cliente compartilhado nem uma visão consolidada de clientes entre lojas do mesmo grupo.** Cada linha da tabela `clientes` pertence a exatamente um `tenant_id`. ⚠️ Se a mesma pessoa física compra na loja 1 e na loja 3 do mesmo grupo, ela vira **dois cadastros de Cliente completamente separados e sem nenhuma ligação** — mesmo no dashboard de visão consolidada do grupo (que existe para venda/estoque/financeiro, ver acima), o nome do cliente só aparece como rótulo de exibição em cada venda individual, sempre resolvido dentro do `tenant_id` daquela venda — não há nenhuma listagem, agregação ou deduplicação de clientes entre lojas do mesmo grupo (diferente do que existe para [[Produto]], que tem um vínculo manual de equivalência entre lojas — ver lá). O único merge de Cliente que existe (`merged_into_id`, campo desta tabela) é para duplicados **dentro do mesmo tenant**, nunca entre tenants diferentes.

## Confirmado no código
- Modelo: `backend/app/models_cadastros.py:55-272` (`Cliente`), tabela `clientes`.
- `user_id`, `auth_user_id` → `users.id` (vínculo opcional com login de app/e-commerce).
- `merged_into_id` → auto-referência (`clientes.id`) usada para **merge de clientes duplicados** — existe `PessoaMergeLog` (`models_authz.py`) para auditar essas fusões.
- `fornecedor_grupo_id` → `fornecedor_grupos.id` (um "Cliente" também pode representar um fornecedor no schema — reaproveitamento de cadastro).
- Tem muitos `Pet` (cascade delete-orphan).
- Usado também como `fornecedor_id` em [[ContaPagar]] e como `entregador_id`/`funcionario_id` em algumas vendas — o schema reaproveita a entidade `Cliente` para papéis que vão além de "cliente comprador" (fornecedor, entregador, veterinário, funcionário/RH, entregador). ⚠️ Isso é uma observação estrutural, não um erro — mas pode confundir quem espera uma entidade separada para "Fornecedor" ou "Entregador".
- `UniqueConstraint(tenant_id, codigo)`; índice único parcial `(tenant_id, auth_user_id)` só quando `auth_user_id` não é nulo e o cliente está ativo — impede duas contas de login ativas para a mesma pessoa no mesmo tenant.

## Campos

Todos os campos da tabela `clientes` (além de `id`/`tenant_id`, herdados de `BaseTenantModel`), na mesma ordem/agrupamento em que aparecem no código-fonte.

### Identificação e vínculo de login
| Campo | Tipo | Observação |
|---|---|---|
| `user_id` | Integer, FK `users.id`, **NOT NULL** | Criador/dono legado do registro — não usar para conceder acesso operacional |
| `auth_user_id` | Integer, FK `users.id` (SET NULL), nullable | Conta que de fato loga como esta pessoa (app/e-commerce) |
| `merged_into_id` | Integer, FK `clientes.id` (SET NULL), nullable | Preenchido quando este cadastro foi fundido em outro (merge de duplicados) |
| `codigo` | String(20), nullable | Código único do cliente por tenant (ex.: `9923`) |

### Tipo de cadastro e pessoa
| Campo | Tipo | Observação |
|---|---|---|
| `origem_cliente` | String(50), nullable | Sem default — registros antigos/importados não comprovam origem |
| `tipo_cadastro` | String(50), **NOT NULL**, default `"cliente"` | ⚠️ **OBSOLETO** (desde 2026-09-22, ver [[pessoas]]) — mantido só por compatibilidade com consumidores ainda não migrados (backend/frontend, lista documentada na skill [[pessoas]]). No create, preenchido automaticamente com a primeira flag `true` numa ordem fixa sem significado de negócio (`cliente`→`fornecedor`→`veterinario`→`funcionario`). Não usar para decisão de negócio nova — usar as 4 flags abaixo |
| `is_cliente` | Boolean, **NOT NULL**, default `false` | Uma pessoa pode acumular vários tipos ao mesmo tempo — substitui `tipo_cadastro` como fonte de verdade |
| `is_fornecedor` | Boolean, **NOT NULL**, default `false` | Idem |
| `is_veterinario` | Boolean, **NOT NULL**, default `false` | Idem |
| `is_funcionario` | Boolean, **NOT NULL**, default `false` | Idem |
| `tipo_pessoa` | String(2), **NOT NULL**, default `"PF"` | `PF` ou `PJ` |
| `fornecedor_grupo_id` | Integer, FK `fornecedor_grupos.id` (SET NULL), nullable | Agrupa fornecedores com CNPJs separados sob um mesmo grupo comercial |

### Dados pessoais (PF) / Nome Fantasia (PJ)
| Campo | Tipo | Observação |
|---|---|---|
| `nome` | String(255), **NOT NULL** | |
| `cpf` | String(14), nullable | |
| `telefone` | String(50), nullable | |
| `celular` | String(50), nullable | |
| `email` | String(255), nullable | |
| `data_nascimento` | DateTime, nullable | Aniversário — usado em campanhas |

### Dados de Pessoa Jurídica
| Campo | Tipo | Observação |
|---|---|---|
| `cnpj` | String(18), nullable | |
| `inscricao_estadual` | String(20), nullable | |
| `razao_social` | String(255), nullable | |
| `nome_fantasia` | String(255), nullable | |
| `responsavel` | String(255), nullable | Nome do contato/responsável |

### Veterinário
| Campo | Tipo | Observação |
|---|---|---|
| `crmv` | String(20), nullable | Registro no CRMV |

### Sistema de parceiros (comissões)
Qualquer pessoa (cliente, veterinário, funcionário, fornecedor) pode ser parceiro.

| Campo | Tipo | Observação |
|---|---|---|
| `parceiro_ativo` | Boolean, default `False` | |
| `parceiro_desde` | DateTime(tz), nullable | Data de ativação como parceiro |
| `parceiro_observacoes` | Text, nullable | |
| `parceiro_tipo_acerto` | String(20), default `"mensal"` | `mensal` \| `quinzenal` \| `semanal` \| `manual` |
| `parceiro_dia_acerto` | Integer, default `1` | Dia do mês/semana para o acerto |
| `parceiro_notificar` | Boolean, default `True` | Enviar e-mail de acerto? |
| `parceiro_email_principal` | String(255), nullable | Sobrepõe o `email` do cadastro para fins de acerto |
| `parceiro_emails_copia` | Text, nullable | E-mails adicionais separados por vírgula |

### RH — funcionários
| Campo | Tipo | Observação |
|---|---|---|
| `cargo_id` | Integer, nullable | ⚠️ **FK fantasma** — linha `ForeignKey("cargos.id")` está comentada no código com aviso desatualizado ("tabela cargos não existe ainda"); [[cargos]] existe e está em uso. Ver [[Plano-de-Acao]] (Bloco 10). |
| `salario_base_override` | Numeric(10,2), nullable | |
| `liquido_combinado` | Numeric(10,2), nullable | |
| `complemento_modo` | String(20), default `"automatico"` | |
| `complemento_fixo_valor` | Numeric(10,2), default `0` | |
| `remuneracao_observacoes` | Text, nullable | |

### Configuração de comissões
| Campo | Tipo | Observação |
|---|---|---|
| `data_fechamento_comissao` | Integer, nullable | Dia do mês (1-31) para fechamento |

### Endereço
| Campo | Tipo | Observação |
|---|---|---|
| `cep` | String(10), nullable | |
| `endereco` | Text, nullable | |
| `numero` | String(20), nullable | |
| `complemento` | String(100), nullable | |
| `bairro` | String(100), nullable | |
| `cidade` | String(100), nullable | |
| `estado` | String(2), nullable | |
| `endereco_entrega` | Text, nullable | Endereço de entrega principal (alternativo ao endereço acima) |
| `endereco_entrega_2` | Text, nullable | Segundo endereço de entrega |
| `enderecos_adicionais` | JSON, nullable | Array de endereços adicionais, com tipo/apelido etc. |

### Entregador (sistema completo)
| Campo | Tipo | Observação |
|---|---|---|
| `is_entregador` | Boolean, default `False` | |
| `is_terceirizado` | Boolean, default `False` | |
| `recebe_repasse` | Boolean, default `False` | |
| `gera_conta_pagar` | Boolean, default `False` | |
| `tipo_vinculo_entrega` | String(20), nullable | `funcionario` \| `terceirizado` \| `eventual` |
| `valor_padrao_entrega` | Numeric(10,2), nullable | |
| `valor_por_km` | Numeric(10,2), nullable | |
| `recebe_comissao_entrega` | Boolean, default `False` | |
| `entregador_ativo` | Boolean, default `True` | |
| `entregador_padrao` | Boolean, default `False` | Pré-selecionado nas rotas |
| `controla_rh` | Boolean, default `False` | |
| `gera_conta_pagar_custo_entrega` | Boolean, default `False` | Flag "matriz final" do custo de entrega |
| `media_entregas_configurada` | Integer, nullable | |
| `media_entregas_real` | Integer, nullable | |
| `custo_rh_ajustado` | Numeric(10,2), nullable | |
| `modelo_custo_entrega` | String(20), nullable | `rateio_rh` \| `taxa_fixa` \| `por_km` |
| `taxa_fixa_entrega` | Numeric(10,2), nullable | |
| `valor_por_km_entrega` | Numeric(10,2), nullable | |
| `moto_propria` | Boolean, default `True` | |
| `tipo_acerto_entrega` | String(20), nullable | `semanal` \| `quinzenal` \| `mensal` |
| `dia_semana_acerto` | Integer, nullable | 1=segunda … 7=domingo |
| `dia_mes_acerto` | Integer, nullable | 1-28 |
| `data_ultimo_acerto` | Date, nullable | Controle interno |

### DRE
| Campo | Tipo | Observação |
|---|---|---|
| `controla_dre` | Boolean, default `True` | `True` = entra no DRE; `False` = não classifica (ex.: fornecedor de produto para revenda) |

### Outros
| Campo | Tipo | Observação |
|---|---|---|
| `observacoes` | Text, nullable | |
| `alertas_pdv` | JSON, nullable | |
| `ativo` | Boolean, default `True` | |
| `credito` | DECIMAL(10,2), default `0.0` | Crédito de devoluções |

### Timestamps
| Campo | Tipo | Observação |
|---|---|---|
| `created_at` | DateTime(tz), server default `now()` | |
| `updated_at` | DateTime(tz), server default `now()`, `onupdate now()` | |

⚠️ Nenhum campo de `Cliente` distingue estruturalmente um dos seus vários papéis (fornecedor, veterinário, entregador, funcionário/parceiro) além das flags booleanas `is_cliente`/`is_fornecedor`/`is_veterinario`/`is_funcionario` (mais `is_entregador`/`parceiro_ativo`) — não há `CHECK`/enum garantindo que, por exemplo, um registro com `crmv` preenchido também tenha `is_veterinario=true`. Backend valida no create/update que pelo menos uma das 4 flags seja `true`, mas não impede inconsistência entre `crmv`/`cnpj` e as flags.

## Utilizado por
- Cadastro de Pessoas/Clientes no menu (ver [[Funcionalidades]])
- [[Pet]] (tutor)
- [[Venda]] (comprador, e também papéis de entregador/funcionário)
- [[ContaPagar]] (fornecedor)
- [[Bling]], [[Stone]] (fluxos de conciliação e sincronização)

## Não identificado
- ❓ Confirmar com o responsável se o reaproveitamento de `Cliente` para fornecedor/entregador é uma decisão de modelagem deliberada de longo prazo ou dívida técnica a ser separada futuramente.
