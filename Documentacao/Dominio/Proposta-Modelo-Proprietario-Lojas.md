---
tipo: proposta
atualizado: 2026-09-16
---

# Proposta — Proprietário nativo acima da Loja

Documento de proposta técnica, para discussão com o time antes de qualquer implementação. Não é uma decisão tomada — é uma recomendação com comparação de alternativas, riscos e plano de fases. Ver [[EmpresaGrupo]] (estado atual, documentado em detalhe), [[Tenant]], [[Plano]], [[Cliente]], [[Produto]].

> **v2 (2026-09-16):** revisão após discussão em equipe — o valor da proposta deixou de ser só "cobrança consolidada" e passou a incluir **catálogo de produto compartilhado entre lojas do mesmo dono**, hoje resolvido apenas por vínculo manual pós-cadastro (`EmpresaGrupoProdutoVinculo`). Ver seção 3.

## 1. O problema que estamos resolvendo

Hoje, um cliente CorePet com 7 lojas físicas tem **7 Tenants completamente independentes** (ver [[Tenant]], [[Cliente]] — "1 Tenant = 1 loja"). As 7 lojas podem, opcionalmente, se juntar depois num [[EmpresaGrupo]], que hoje resolve bem estoque compartilhado, transferência integrada e análise consolidada de vendas/estoque/financeiro — mas não resolve dois problemas de fundo:

**Cobrança fragmentada.** Não existe, em lugar nenhum do sistema, uma entidade que represente "o dono do negócio" como conta única — só lojas individuais e um grupo operacional opcional. O dono de 7 lojas recebe (ou deveria receber) 7 cobranças Asaas separadas, sem vínculo formal entre elas, e não há tela nem relatório de "quanto esse cliente paga no total pelo CorePet".

**Catálogo de produto duplicado.** Cadastrar o mesmo produto na loja 1 não cria, atualiza nem reflete nada nas lojas 2 a 7 (confirmado em [[Produto]]) — nome, descrição, fotos e ficha técnica são redigitados independentemente em cada loja. O único mecanismo cruzando lojas, `EmpresaGrupoProdutoVinculo`, só **casa dois produtos já divergentes** depois do fato (pra transferência de estoque acertar o item certo) — não evita a duplicação de cadastro nem mantém nada sincronizado. Confirmamos também que o **Catálogo Mestre** já existente no sistema (`catalogo_mestre_models.py`) não resolve isso: é uma base de curadoria global entre *todos* os clientes CorePet, alimentada só num sentido (loja → catálogo) e a própria docstring do modelo é explícita — "nenhuma FK aponta de volta para o cadastro operacional e nenhuma sincronização deste módulo altera lojas".

E, de forma mais branda, um terceiro ponto: hoje não há forma de reconhecer que "o cliente da loja 1" e "o cliente da loja 3" são a mesma pessoa, mesmo sendo lojas do mesmo dono — cada loja recadastra do zero.

O grupo (`EmpresaGrupo`) só nasce se alguém explicitamente criar e convidar — é um passo manual a mais, não uma consequência natural de "esse dono tem várias lojas".

## 2. Modelos externos que já resolveram isso

Vale separar as referências por qual dos três problemas elas resolvem — a maioria dos sistemas multi-loja trata **conta/cobrança** e **catálogo** como camadas distintas, ambas acima da loja, mas frequentemente confundidas como "a mesma decisão".

### 2.1 Conta e cobrança

| Sistema | Camada "dono" | Onde fica o isolamento operacional |
|---|---|---|
| Square / Toast / Lightspeed | "Conta do Negócio" — identidade, cobrança, relatório agregado | "Localização" é o limite de PDV/clientes do dia a dia |
| AWS Organizations / GCP Resource Manager | "Organização" — billing consolidado e governança | Conta/Projeto é o limite de recurso |
| QuickBooks / Xero | Login único do contador (já temos via `UserTenant`) | Cada "company file" é cobrado e isolado separadamente |

### 2.2 Catálogo compartilhado entre lojas — a referência mais forte

Essa é a parte em que eu tinha simplificado demais antes: em sistemas de varejo multi-loja de verdade, **o catálogo não fica isolado por loja** — só o estoque e, às vezes, o preço.

| Sistema / padrão | Nível compartilhado (nome, descrição, foto, categoria) | Nível por loja |
|---|---|---|
| **Square — Item Library** | Item cadastrado uma vez na conta do negócio; editável centralmente | Cada localização liga/desliga o item e pode sobrescrever preço/disponibilidade |
| **Shopify — Product + Location** | `Product`/`Variant` pertence à loja (conta), não ao local físico | `InventoryLevel` por `Location` controla só quantidade; preço pode variar por "Market" |
| **Lightspeed Retail — Shops** | Produto criado uma vez na conta, empurrado pros "Shops" | Cada shop tem sua contagem de estoque e, opcionalmente, tabela de preço própria |
| **Toast (redes multi-unidade)** | Cardápio gerenciado centralmente ("Toast Central") | Loja marca item como indisponível (86'd) ou ajusta preço local |
| **Amazon Seller Central — ASIN vs. Offer** | ASIN = identidade única do produto no catálogo Amazon | Offer = preço/estoque/condição por vendedor — mesma ASIN, N ofertas |
| **Retail enterprise clássico — Item Master + Store Assortment** (SAP Retail, Oracle Retail) | "Item Master" — o registro canônico do artigo | "Store Assortment" define quais lojas carregam o item e com qual preço/posição local |
| **Categoria PIM (Product Information Management)** — Akeneo, Salsify, inRiver | O software inteiro existe pra isso: um "golden record" de produto, exportado com overrides por canal/loja | Cada canal/loja consome o PIM e ajusta só o que é genuinamente local |
| **AWS Organizations + Resource Access Manager (RAM)** | Um recurso (ex. uma sub-rede) é criado uma vez na conta central e *compartilhado* — não duplicado — pras contas-filhas | Conta-filha usa o recurso compartilhado, mas seu billing/uso continua próprio | 

O padrão que se repete aqui é praticamente unânime: **identidade do item é uma decisão de negócio, tomada uma vez; operação (preço, estoque, disponibilidade) é uma decisão de loja, tomada N vezes.** Isso é literalmente uma categoria inteira de software de mercado (PIM) — o problema que o CorePet tem hoje com produto duplicado é conhecido e já tem solução de referência há décadas no varejo.

### 2.3 Identidade de cliente entre lojas — mais delicado

Aqui a referência muda de forma: sistemas de fidelidade multi-loja (ex. redes de petshop com cartão fidelidade único) usam o padrão de **Customer Data Platform (CDP)**: existe um "perfil" de pessoa unificado, mas cada ponto de contato registra sua própria interação e, principalmente, seu próprio **consentimento**. A identidade é resolvida (por CPF, telefone, e-mail) e sugerida — nunca fundida automaticamente sem confirmação — porque o vínculo de consentimento LGPD costuma ser por relação comercial, não por pessoa.

## 3. Três ganhos, não um

A proposta original tratava o Proprietário como uma camada só de billing. Com essa pesquisa, fica claro que ele é o lugar natural pra três ganhos independentes — que podem, inclusive, ser entregues em velocidades diferentes:

| Pilar | Ganho | Nível de certeza |
|---|---|---|
| **Cobrança** | 1 conta Asaas por dono, cobrança itemizada por loja | Alto — dor conhecida, referência de mercado unânime |
| **Catálogo de produto** | Cadastrar uma vez, herdar em todas as lojas do dono; elimina redigitação e o vínculo manual pós-fato | Alto — referência de mercado ainda mais forte (é uma categoria de software inteira) |
| **Identidade de cliente** | Reconhecer que é a mesma pessoa entre lojas do dono, sem recadastro | Médio — ganho real, mas esbarra em consentimento/LGPD; tratar como decisão separada (seção 6) |

### Abordagem A — Proprietário "profundo" (rejeitada)
`proprietario_id` passaria a existir em **todas** as tabelas de negócio (Cliente, Produto, Venda, ContaPagar...), com `tenant_id` virando campo secundário. Custo: migration em centenas de tabelas, reescrita de toda RLS policy e do filtro fail-closed do ORM, meses de trabalho, risco de regressão de segurança em qualquer tabela esquecida no caminho. Carrega complexidade extra pra todo mundo, inclusive o cliente de loja única. **Continua rejeitada** mesmo com o novo escopo — nenhum dos três ganhos acima exige isso.

### Abordagem B — Proprietário "fino", com três módulos plugáveis (recomendada)
`tenant_id` continua o único limite de isolamento transacional em todas as tabelas de negócio. O Proprietário ganha, além do billing, uma tabela nova e independente para governar catálogo compartilhado — e, futuramente, um mecanismo opt-in de identidade de cliente. Cada módulo é aditivo (nenhum quebra o que existe) e pode ser priorizado sozinho.

## 4. Recomendação

**Abordagem B, com o catálogo compartilhado como primeiro módulo a entregar** — na prática, é o de menor risco jurídico/financeiro (ao contrário de billing, não mexe em dinheiro real) e o de dor mais visível hoje pro logista de múltiplas lojas. Billing consolidado continua valioso, mas pode vir depois, em paralelo ou não. Identidade de cliente fica como módulo deliberadamente adiado até a questão de consentimento ser resolvida (seção 6).

"Mais robusto" e "mais simples" convergem aqui pelo mesmo motivo de antes: cada módulo resolve um problema real e conhecido do mercado, sem duplicar o eixo de isolamento que já funciona.

## 5. Desenho proposto (alto nível)

### 5.1 Proprietário nasce automaticamente, não por convite manual
Hoje, um `EmpresaGrupo` só existe se alguém criar e convidar outra empresa (ver fluxo completo em [[EmpresaGrupo]]). Proposta: **todo `Tenant` novo já nasce com seu próprio "Proprietário" de 1 loja**, de forma transparente — o cliente de loja única nunca vê isso. O fluxo de convite/código mensal que já existe continua servindo pra juntar tenants que já existiam separados.

### 5.2 Catálogo mestre por Proprietário (o novo núcleo da proposta)
Nova tabela `produto_mestre`, escopada por `proprietario_id` (não por `tenant_id`, e **não** confundir com o `catalogo_mestre_produtos` global existente — ver caixa abaixo). Guarda os campos de **identidade do item**: nome, descrição, fotos, categoria, marca, ficha técnica, dados fiscais de referência (NCM/CEST), GTIN.

Cada `Produto` de cada loja ganha um FK opcional `produto_mestre_id`:
- **Sem vínculo** (padrão hoje): produto local, como já funciona — nada muda pra quem tem 1 loja.
- **Com vínculo**: nome/descrição/fotos/categoria são **herdados** do produto-mestre; a loja mantém só o que é genuinamente dela — preço, estoque, disponibilidade, dados fiscais operacionais. Se uma loja específica precisa divergir num campo (ex. um item que só ela vende sob outro nome), um override explícito e sinalizado na UI sobrescreve o herdado — nunca uma divergência silenciosa.
- Cadastrar um produto novo na loja 2 que já existe como produto-mestre do mesmo dono vira "adotar", não "redigitar".

> **Diferença para o Catálogo Mestre existente:** `catalogo_mestre_produtos` é uma base de curadoria **global**, entre todos os clientes CorePet, mantida por um worker de enriquecimento com IA, sem qualquer FK de volta pra loja. O `produto_mestre` novo é **do dono**, editável por ele, e alimenta as lojas dele diretamente. São camadas complementares: o Catálogo Mestre global pode **sugerir** dados prontos (nome, GTIN, fotos já curadas) na hora de criar um produto-mestre novo — evita o dono digitar do zero um item que a curadoria global já conhece — mas quem decide e edita o produto-mestre do dono é o próprio dono.

### 5.3 Billing sobe para o Proprietário; cobrança continua por loja
Hoje `plan`/`billing_status`/`billing_provider_customer_id`/`billing_subscription_id` vivem soltos em cada `Tenant` (ver [[Plano]]). Proposta: o **cliente Asaas** (conta, contrato, nota fiscal do serviço) passa a viver no Proprietário — 1 conta, 1 relacionamento comercial. Cada **Loja** continua com seu próprio `plan`/módulos/trial — a cobrança continua **itemizada por loja** dentro dessa conta única, como uma fatura de operadora com várias linhas (mesmo modelo de G Suite/Workspace e AWS Organizations).

### 5.4 O que não muda
- `tenant_id` continua a chave de isolamento em [[Venda]], [[ContaPagar]]/[[ContaReceber]], estoque, fiscal, e em todas as ~325 tabelas de negócio restantes. RLS e filtro fail-closed, intactos.
- Preço, estoque e disponibilidade de produto continuam 100% por loja — só a identidade do item (nome/descrição/foto) passa a poder ser compartilhada, e só quando a loja optar por vincular.
- Estoque compartilhado, transferência integrada e análises consolidadas do [[EmpresaGrupo]] continuam funcionando como hoje — passam a estar disponíveis desde o primeiro dia.

### 5.5 Correções que entram de graça nesse pacote
- Remoção de membro não limpa `EmpresaGrupoProdutoVinculo` — risco de erro 500 (`KeyError`), já registrado em [[Achados-Revisao-Equipe]].
- Hoje não existe forma de uma loja "sair" do proprietário por conta própria, nem transferir o papel de responsável, nem excluir um grupo. Com o proprietário virando nativo, esses fluxos passam de "nice to have" a essenciais.

## 6. E o Cliente — identidade entre lojas

Diferente de produto, aqui eu **não recomendo o mesmo modelo de herança automática**. Dois motivos:

1. **Consentimento LGPD é capturado por relação comercial**, tipicamente por loja/CNPJ — presumir que "aceitar dados na loja 1" autoriza visibilidade na loja 3 é uma decisão jurídica, não técnica, e depende de como os tenants do mesmo dono estão constituídos (mesma razão social, ou franquias com CNPJ próprio — não auditado).
2. Nome/preço/foto de produto é dado de negócio; nome/telefone/histórico de pet é dado pessoal — o padrão de mercado (CDP) trata os dois de formas diferentes por esse exato motivo.

**Proposta, alinhada ao padrão CDP:** um mecanismo de **sugestão de vínculo opt-in**, não fusão automática — ao cadastrar um cliente por CPF/telefone/e-mail já existente em outra loja do mesmo dono, o sistema sugere "esse cliente já existe na Loja X, deseja vincular o histórico?", com confirmação explícita e nunca automática. Isso resolve a fricção de recadastro sem tomar a decisão de consentimento por conta própria. Tratar como **módulo adiado** até o time validar o enquadramento legal (ver pergunta em aberto na seção 10).

O consolidado de vendas/clientes entre lojas via relatório (`EmpresaGrupoAnaliseDetalhesService`) já existe hoje e continua sendo o caminho pra "ver tudo junto" sem depender dessa identidade resolvida.

## 7. O que muda para quem usa o sistema

- **Dono de 1 loja**: nada muda. Continua vendo só a própria loja, sem saber que "proprietário" existe por baixo.
- **Dono de N lojas**: cadastra um produto uma vez e ele aparece nas outras lojas prontas pra só ajustar preço/estoque; ganha acesso automático a estoque compartilhado/transferência/análises consolidadas desde a segunda loja; e, no billing, uma cobrança consolidada em vez de N assinaturas soltas.
- **Suporte/vendas CorePet**: ganha, pela primeira vez, uma entidade real de "conta do cliente" — hoje, um dono de 7 lojas aparece como 7 registros sem nenhuma ligação formal.

## 8. Riscos e como mitigar

| Risco | Mitigação |
|---|---|
| Migrar tenants já existentes para ter um Proprietário | Script de backfill: cada `Tenant` sem grupo hoje ganha um Proprietário de 1 membro automaticamente — reversível, não toca em dado de negócio |
| Loja diverge de um campo do produto-mestre sem perceber que o item é compartilhado | Override sempre explícito e sinalizado na UI ("este campo foi personalizado nesta loja"); nunca sobrescrita silenciosa |
| Mudança no fluxo de billing/Asaas é código crítico (dinheiro real) | Rollout em fases, começando só com tenants novos; migração de tenants existentes por último, com janela de validação |
| Vincular clientes errados entre lojas (falso positivo de CPF/telefone) | Vínculo é sempre sugestão + confirmação manual, nunca automático |
| Confusão de produto: "proprietário" vs "loja" vs "grupo" (nomenclatura) | Decidir nome único antes de implementar — este documento não impõe o nome, só a estrutura |

## 9. Plano de fases sugerido

1. **Fase 1 — fundação**: `Tenant` ganha `proprietario_id` obrigatório; todo tenant novo nasce com proprietário de 1 membro automaticamente. Corrige os dois bugs de robustez do [[EmpresaGrupo]] atual. Nenhuma mudança de billing ou catálogo ainda.
2. **Fase 2 — catálogo mestre**: tabela `produto_mestre` + FK opcional em `produtos`; fluxo de "adotar produto-mestre existente" ao cadastrar em loja adicional. Entregável independente de billing — é o de maior dor visível hoje.
3. **Fase 3 — billing consolidado**: cliente Asaas migra para o nível do Proprietário; cobrança continua itemizada por loja. Começa só em tenants novos.
4. **Fase 4 — backfill**: tenants existentes recebem proprietário automático via script; tenants que já usam `EmpresaGrupo` são promovidos sem perder configuração; produtos existentes ganham sugestão de produto-mestre por GTIN/nome.
5. **Fase 5 — identidade de cliente (condicional)**: só entra em escopo depois do time validar o enquadramento LGPD descrito na seção 6.

## 10. Perguntas em aberto para o time decidir

- Nome definitivo do conceito na UI/produto: "Proprietário", "Conta", "Grupo Econômico", manter "Grupo de Empresas"?
- Quem pode editar o produto-mestre — só o "responsável" do proprietário (papel que já existe em [[EmpresaGrupo]]), ou qualquer loja membro?
- O plano/preço muda quando lojas entram no mesmo proprietário (desconto por volume), ou cada loja continua pagando o valor de tabela, só consolidado numa fatura?
- Vale um limite de lojas por proprietário no plano de entrada (hoje não existe nenhum limite, [[EmpresaGrupo]] confirma isso como "não identificado")?
- **Jurídico:** os tenants do mesmo dono normalmente compartilham CNPJ/razão social, ou é comum ser franquia com CNPJ próprio por loja? Essa resposta decide se a sugestão de vínculo de cliente (seção 6) é viável como está ou precisa de mais salvaguarda.
