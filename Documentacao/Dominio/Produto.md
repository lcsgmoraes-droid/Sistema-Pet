---
tipo: dominio
atualizado: 2026-09-12
---

# Entidade — Produto

Ver [[Produtos-Estoque]], [[Venda]], [[Bling]], [[Tenant]], [[EmpresaGrupo]], [[Cliente]].

## Relação com Tenant, lojas e grupos de empresa

Mesmo modelo descrito em [[Cliente]] (leia lá primeiro): **1 [[Tenant]] = 1 loja**, sem conceito de "loja" separado dentro de um Tenant. Um cliente do CorePet com 7 lojas físicas tem **7 Tenants**, não 1 Tenant com 7 lojas internamente.

Cada linha da tabela `produtos` pertence a exatamente um `tenant_id`. O catálogo de cada loja é uma base própria — **não há nenhuma linha de produto compartilhada por padrão** entre as 7 lojas do mesmo cliente/grupo, mesmo que vendam exatamente os mesmos itens.

**Quando 7 lojas do mesmo grupo comercial têm "o mesmo produto"** (ex.: a mesma ração vendida nas 7 unidades), isso vira **7 linhas de `produtos` independentes**, uma por tenant, com IDs sem nenhuma relação entre si. Isso é confirmado explicitamente no próprio código-fonte (`empresa_grupo_models.py`, docstring de `EmpresaGrupoProdutoVinculo`): *"Os IDs de produto não recebem chave estrangeira porque pertencem a tenants diferentes e podem se repetir."* O sistema não funde nem sincroniza automaticamente o catálogo entre lojas.

Se as lojas estiverem no mesmo [[EmpresaGrupo]], existem dois mecanismos **opcionais** (nada disso acontece sozinho):

1. **Equivalência manual entre produtos de lojas diferentes** (`EmpresaGrupoProdutoVinculo`) — um vínculo manual dizendo "o produto X da loja 1 é o mesmo item que o produto Y da loja 3". Não é uma FK real de banco (não pode ser — os IDs pertencem a tenants/tabelas logicamente separadas); é uma tabela de associação própria, validada pelo service a cada uso.
2. **Estoque seletivamente compartilhado** (`EmpresaGrupoEstoqueCompartilhado`) — autoriza a loja 3 a vender, no seu próprio PDV, o saldo de estoque que pertence fisicamente à loja 1, sem duplicar o produto nem mover estoque de fato. O produto e o estoque continuam sendo 100% da loja de origem; a loja consumidora só ganha permissão de leitura/venda sobre aquele saldo (ou sobre o catálogo inteiro, se `acesso_catalogo_completo=True`).

Fora desses dois mecanismos opt-in, cadastrar um produto na loja 1 **não** cria, atualiza ou reflete nada nas lojas 2 a 7.

✅ **Existe, sim, uma visão consolidada de vendas/estoque das 7 lojas** — mas é um relatório agregado, não uma fusão de cadastro: `GET /grupos-empresas/{grupo_id}/visao-consolidada` soma quantidade/valor de vendas e valor de estoque das lojas do grupo (calculado com segurança, loja por loja, sem furar o isolamento de cada uma), e `GET /grupos-empresas/{grupo_id}/produtos-vendidos` lista os produtos vendidos das 7 lojas numa lista só, com filtro por loja. Ver [[EmpresaGrupo]] para os detalhes — isso não muda nada do que já foi dito acima: cada `produtos.id` continua sendo uma linha própria de uma loja só.

**Não confundir com o Catálogo Mestre global** (`catalogo_mestre_produtos`): é um conceito diferente — uma base de referência/enriquecimento (GTIN, ficha técnica, imagens, dados regulatórios) mantida centralmente e usada como fonte auxiliar para *qualquer* tenant do sistema, não só os do mesmo grupo comercial de um cliente. Não é o catálogo operacional de venda de cada loja (que continua sendo só a tabela `produtos`, isolada por tenant); é uma camada de dados de apoio para enriquecer/padronizar esse catálogo.

## Confirmado no código
- Modelo principal: `backend/app/produtos_catalogo_models.py:100-524` (`Produto`), tabela `produtos`, com `produtos_models.py` como facade de compatibilidade que reagrupa modelos espalhados em `produtos_compras_models.py`, `produtos_estoque_models.py`, `estoque_models.py` e outros.
- `categoria_id` → `categorias.id`, `marca_id` → `marcas.id`, `departamento_id` → `departamentos.id`.
- `fornecedor_id` → `clientes.id` (reaproveitamento de `Cliente`, ver [[Cliente]]).
- `produto_pai_id` → auto-FK (`produtos.id`) para variações/kits.
- Relaciona-se com `ProdutoLote` (controle de lote/validade), `ProdutoImagem`, `EstoqueMovimentacao`, `ListaPreco`.
- Faz parte também de um **Catálogo Mestre global** (`catalogo_mestre_models.py`), com worker dedicado de enriquecimento contínuo (`backend/scripts/run_catalogo_mestre_worker.py`) — um conceito de catálogo compartilhado entre tenants, além do catálogo próprio de cada empresa.
- Recorrência de compra (protocolos de recompra) é tratada em `services/product_recurrence.py` e modelos de lembrete associados.
- Índice único parcial `ux_produtos_tenant_codigo_lower` em `(tenant_id, lower(trim(codigo)))` — impede dois produtos com o mesmo código (case-insensitive) no mesmo tenant, só quando `codigo` não é vazio.
- Tabelas satélites diretas no mesmo arquivo: [[categorias|Categoria]] (`categorias`), [[marcas|Marca]] (`marcas`), [[departamentos|Departamento]] (`departamentos`) — ver campos delas no fim desta página.

## Campos

Todos os campos da tabela `produtos` (além de `id`/`tenant_id`, herdados de `BaseTenantModel`), no mesmo agrupamento usado no código-fonte.

### Informações básicas
| Campo | Tipo | Observação |
|---|---|---|
| `codigo` | String(50), **NOT NULL** | SKU |
| `nome` | String(200), **NOT NULL** | |
| `tipo` | String(20), default `"produto"` | `produto` \| `servico` \| `produto_servico` |
| `situacao` | Boolean, default `True` | Ativo/inativo |

### Produtos com variação e kit (Sprint 2/4)
| Campo | Tipo | Observação |
|---|---|---|
| `tipo_produto` | String(20), **NOT NULL**, default `"SIMPLES"` | `SIMPLES` \| `PAI` (agrupador, não vendável) \| `VARIACAO` (filho vendável) \| `KIT` |
| `produto_pai_id` | Integer, FK `produtos.id`, nullable | Aponta para o produto `PAI` |
| `is_parent` | Boolean, **NOT NULL**, default `False` | |
| `is_sellable` | Boolean, **NOT NULL**, default `True` | |
| `variation_attributes` | JSON, nullable | Ex.: `{"cor": "azul", "tamanho": "G"}` |
| `variation_signature` | String(255), nullable, indexado | Ex.: `"cor:azul\|tamanho:G"` |
| `tipo_kit` | String(20), nullable | `VIRTUAL` (custo/estoque somados dos componentes) \| `FISICO` (custo/estoque próprios) — só quando há composição |

### Descrição
| Campo | Tipo | Observação |
|---|---|---|
| `descricao_curta` | Text, nullable | |
| `descricao_completa` | Text, nullable | |
| `tags` | Text, nullable | Array serializado como JSON em texto |

### Código de barras
| Campo | Tipo | Observação |
|---|---|---|
| `codigo_barras` | String(20), nullable | Suporta EAN-14 e outros formatos |
| `codigos_barras_alternativos` | Text, nullable | Array serializado como JSON em texto |

### Relacionamentos (FKs)
| Campo | Tipo | Observação |
|---|---|---|
| `categoria_id` | Integer, FK `categorias.id`, nullable | |
| `subcategoria` | String(100), nullable | Campo texto livre, não FK |
| `marca_id` | Integer, FK `marcas.id`, nullable | |
| `fornecedor_id` | Integer, FK `clientes.id`, nullable | Ver [[Cliente]] |
| `departamento_id` | Integer, FK `departamentos.id`, nullable | |

### Preços
| Campo | Tipo | Observação |
|---|---|---|
| `preco_custo` | Float, default `0` | |
| `preco_venda` | Float, nullable, default `0` | Nullable porque produto `PAI` não tem preço |
| `preco_promocional` | Float, nullable | |
| `promocao_inicio` | DateTime, nullable | |
| `promocao_fim` | DateTime, nullable | |
| `promocao_ativa` | Boolean, default `False` | |

### Preços por canal
Se `NULL`, o canal usa o `preco_venda` padrão.

| Campo | Tipo | Observação |
|---|---|---|
| `preco_ecommerce` | Float, nullable | |
| `preco_ecommerce_promo` | Float, nullable | |
| `preco_ecommerce_promo_inicio` | DateTime(tz), nullable | |
| `preco_ecommerce_promo_fim` | DateTime(tz), nullable | |
| `preco_app` | Float, nullable | |
| `preco_app_promo` | Float, nullable | |
| `preco_app_promo_inicio` | DateTime(tz), nullable | |
| `preco_app_promo_fim` | DateTime(tz), nullable | |
| `anunciar_ecommerce` | Boolean, **NOT NULL**, default `True` | |
| `anunciar_app` | Boolean, **NOT NULL**, default `True` | |

### Estoque
| Campo | Tipo | Observação |
|---|---|---|
| `estoque_atual` | Float, default `0` | |
| `estoque_minimo` | Float, default `0` | |
| `estoque_maximo` | Float, default `0` | |
| `estoque_fisico` | Float, default `0` | |
| `estoque_ecommerce` | Float, default `0` | |
| `localizacao` | String(50), nullable | |
| `crossdocking_dias` | Integer, default `0` | |
| `controle_lote` | Boolean, default `False` | |

### Unidade e condição
| Campo | Tipo | Observação |
|---|---|---|
| `unidade` | String(10), default `"UN"` | |
| `condicao` | String(20), default `"novo"` | `novo` \| `usado` \| `recondicionado` |
| `e_granel` | Boolean, **NOT NULL**, default `False` | Produto físico em kg derivado de uma ração/pacote pai |
| `participa_sugestao_compra` | Boolean, **NOT NULL**, default `True` | |

### Características físicas
| Campo | Tipo | Observação |
|---|---|---|
| `peso_liquido` | Float, nullable | |
| `peso_bruto` | Float, nullable | |
| `largura` | Float, nullable | |
| `altura` | Float, nullable | |
| `profundidade` | Float, nullable | |
| `volume` | Float, nullable | Calculado |
| `itens_por_caixa` | Integer, nullable | |
| `frete_gratis` | Boolean, default `False` | |
| `producao` | String(20), nullable | `propria` \| `terceiros` |

### Fiscal
| Campo | Tipo | Observação |
|---|---|---|
| `ncm` | String(8), nullable | |
| `cest` | String(7), nullable | |
| `gtin_ean` | String(20), nullable | |
| `gtin_ean_tributario` | String(20), nullable | |
| `origem` | String(1), nullable | 0-8 |
| `perfil_tributario` | String(50), nullable | |
| `forma_aquisicao` | String(50), nullable | |
| `tipo_item` | String(50), nullable | |
| `percentual_tributos` | Float, nullable | |
| `icms_base_retencao` | Float, nullable | |
| `icms_valor_retencao` | Float, nullable | |
| `icms_valor_proprio` | Float, nullable | |
| `ipi_codigo_excecao` | String(20), nullable | |
| `pis_valor_fixo` | Float, nullable | |
| `cofins_valor_fixo` | Float, nullable | |
| `cfop` | String(10), nullable | |
| `aliquota_icms` | Float, nullable | |
| `aliquota_pis` | Float, nullable | |
| `aliquota_cofins` | Float, nullable | |
| `informacoes_adicionais_nf` | Text, nullable | |

Ver também [[produto_config_fiscal]]/[[variacao_config_fiscal]]/[[kit_config_fiscal]] — config fiscal mais rica e específica, que sobrepõe estes campos na cadeia de resolução do PDV.

### Comissão e desconto
| Campo | Tipo | Observação |
|---|---|---|
| `comissao_padrao` | Float, default `0` | |
| `limite_desconto` | Float, default `0` | |

### Validade
| Campo | Tipo | Observação |
|---|---|---|
| `data_validade` | DateTime, nullable | Validade do produto em si (fora do controle por lote — ver [[produto_lotes]]) |

### Recorrência
⚠️ **Achado**: este bloco de 5 campos está declarado **duas vezes, de forma idêntica**, no código-fonte (`produtos_catalogo_models.py:262-276` e `:278-292` — mesmo comentário, mesmos campos). Não é um bug funcional (a segunda declaração só sobrescreve a primeira no mesmo nome de atributo Python, sem efeito prático), mas é resíduo de copiar/colar que vale limpar.

| Campo | Tipo | Observação |
|---|---|---|
| `tem_recorrencia` | Boolean, default `False` | |
| `tipo_recorrencia` | String(20), nullable | `daily` \| `weekly` \| `monthly` \| `yearly` |
| `intervalo_dias` | Integer, nullable | Dias entre doses/compras |
| `numero_doses` | Integer, nullable | Ex.: 3 para vacina V8 |
| `observacoes_recorrencia` | Text, nullable | |

### Compatibilidade de espécie
| Campo | Tipo | Observação |
|---|---|---|
| `especie_compativel` | String(50), nullable | `dog` \| `cat` \| `both` |

### Ração — calculadora
| Campo | Tipo | Observação |
|---|---|---|
| `classificacao_racao` | String(50), nullable | `super_premium` \| `premium` \| `especial` \| `standard` |
| `peso_embalagem` | Float, nullable | Kg |
| `tabela_nutricional` | Text, nullable | JSON: `{"proteina": 28, "gordura": 15, ...}` |
| `categoria_racao` | String(50), nullable | `filhote` \| `adulto` \| `senior` \| `gestante` etc. |
| `especies_indicadas` | String(100), nullable | |
| `tabela_consumo` | Text, nullable | JSON: peso × idade × quantidade diária |

### Classificação inteligente de rações (IA)
| Campo | Tipo | Observação |
|---|---|---|
| `porte_animal` | JSONB, nullable | Array, ex.: `["Pequeno", "Médio", ...]` |
| `fase_publico` | JSONB, nullable | Array, ex.: `["Filhote", "Adulto", ...]` |
| `tipo_tratamento` | JSONB, nullable | Array, ex.: `["Obesidade", "Renal", ...]` |
| `sabor_proteina` | String(100), nullable | |
| `auto_classificar_nome` | Boolean, **NOT NULL**, default `True` | Ativa auto-classificação via IA |

### Opções de ração — sistema dinâmico
⚠️ **Achado novo, mesmo padrão já visto em outros módulos**: as 6 FKs abaixo estão comentadas no código com o aviso `"DESABILITADO TEMPORARIAMENTE: Tabelas não existem ainda"` — mas as 6 tabelas de opções **existem e estão em uso ativo** ([[linhas_racao]], [[portes_animal]], [[fases_publico]], [[tipos_tratamento]], [[sabores_proteina]], [[apresentacoes_peso]], todas com CRUD funcionando via `opcoes_racao_routes.py`). O comentário está desatualizado — mesmo padrão de "FK fantasma com premissa errada" já catalogado em [[Achados-Revisao-Equipe]].

| Campo | Tipo | Observação |
|---|---|---|
| `linha_racao_id` | Integer, nullable | Deveria ser FK → [[linhas_racao]]`.id` |
| `porte_animal_id` | Integer, nullable | Deveria ser FK → [[portes_animal]]`.id` |
| `fase_publico_id` | Integer, nullable | Deveria ser FK → [[fases_publico]]`.id` |
| `tipo_tratamento_id` | Integer, nullable | Deveria ser FK → [[tipos_tratamento]]`.id` |
| `sabor_proteina_id` | Integer, nullable | Deveria ser FK → [[sabores_proteina]]`.id` |
| `apresentacao_peso_id` | Integer, nullable | Deveria ser FK → [[apresentacoes_peso]]`.id` |

### Imagem
| Campo | Tipo | Observação |
|---|---|---|
| `imagem_principal` | String(255), nullable | URL/caminho; ver property `imagem_principal_thumbnail` |

### Auditoria
| Campo | Tipo | Observação |
|---|---|---|
| `user_id` | Integer, FK `users.id`, **NOT NULL** | |
| `ativo` | Boolean, default `True` | |
| `created_at` | DateTime, default `utcnow` | |
| `updated_at` | DateTime, default `utcnow`, `onupdate utcnow` | |
| `deleted_at` | DateTime, nullable | Soft delete |

### Predecessor/sucessor
Permite encadear produtos que se substituem, mantendo histórico consolidado (ex.: ração 350g → 300g por mudança de embalagem).

| Campo | Tipo | Observação |
|---|---|---|
| `produto_predecessor_id` | Integer, FK `produtos.id`, nullable | |
| `data_descontinuacao` | DateTime, nullable | |
| `motivo_descontinuacao` | String(255), nullable | Ex.: "Mudança de embalagem", "Reformulação" |

### Campos das tabelas satélites diretas

**`categorias`** ([[Categoria]]): `nome` (NOT NULL), `categoria_pai_id` (self-FK, hierarquia), `departamento_id` (FK), `descricao`, `icone`, `cor` (hex), `ordem`, `user_id` (FK, NOT NULL), `ativo`, `created_at`, `updated_at`.

**`marcas`** ([[Marca]]): `nome` (NOT NULL), `descricao`, `logo`, `site`, `user_id` (FK, NOT NULL), `ativo`, `created_at`, `updated_at`.

**`departamentos`** ([[Departamento]]): `nome` (NOT NULL), `descricao`, `user_id` (FK, NOT NULL), `ativo`, `created_at`, `updated_at`.

## Utilizado por
- [[Produtos-Estoque]] (cadastro, estoque, movimentações)
- [[PDV-Vendas]] (item vendido)
- [[Bling]] (sincronização de catálogo/estoque)
- [[Fiscal-IntNFe-SEFAZ]] (nota de entrada)
- [[iFood]], E-commerce (catálogo publicado)

## Não identificado
- ❓ Relação de governança entre o Catálogo Mestre global e o catálogo próprio de cada tenant (quem pode editar o quê, e como conflitos são resolvidos) — não auditado a fundo nesta rodada.
