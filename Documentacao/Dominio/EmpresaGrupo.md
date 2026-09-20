---
tipo: dominio
atualizado: 2026-09-20
---

# Entidade — GrupoComercial (grupo de empresas)

> Nome da entidade no código é **`GrupoComercial`** (renomeado a partir de
> `EmpresaGrupo` em 18/09/2026 — tabelas, rotas, serviço, tudo). Este doc
> continua no arquivo `EmpresaGrupo.md` só para não quebrar os `[[EmpresaGrupo]]`
> já espalhados por outros docs — o conteúdo abaixo já está 100% no nome/
> comportamento atual.

Ver [[Tenant]], [[Produto]], [[Cliente]], [[ContaPagar]], [[ContaReceber]], [[Plano]], [[Venda]], [[Plano-Camada-Geral]].

## Definição

Agrupa vários [[Tenant]] (lojas) sob um mesmo grupo econômico, permitindo que operem de forma coordenada em três frentes — **estoque seletivamente compartilhado**, **transferência integrada de mercadoria com lançamento financeiro automático** e **análise consolidada de indicadores** — sem nunca unir o cadastro, o licenciamento ou o isolamento de dados de cada loja. É puramente uma camada operacional que **atravessa** tenants por natureza; por isso os modelos não herdam `BaseTenantModel`, e todo acesso passa obrigatoriamente por um service que valida manualmente o tenant do ator em cada operação.

Desde 18/09/2026, **todo tenant novo já nasce dentro de um grupo comercial automaticamente** — um "grupo-de-1", só ele mesmo como membro `responsavel`. Grupo comercial deixou de ser um recurso opcional que a empresa "adere"; é infraestrutura obrigatória do cadastro. Uma mesma empresa (tenant) **pode participar de mais de um grupo ao mesmo tempo** — não há nenhuma constraint ou validação que impeça isso; `GrupoComercialMembro` só garante `UniqueConstraint(grupo_id, empresa_id)`, ou seja, só impede entrar duas vezes *no mesmo* grupo.

## Duas camadas de controle de acesso

Desde 20/09/2026 existem **duas camadas independentes** decidindo quem pode fazer o quê num grupo — importante não confundir uma com a outra:

1. **Papel da empresa dentro do grupo** (`GrupoComercialMembro.papel`) — decide qual **loja/tenant** pode disparar ações de composição do grupo (adicionar loja, remover membro). Não mudou desde a criação do recurso.
2. **Acesso de gestão do grupo, por usuário** (`User.master_grupo_id` + `GrupoComercialGestor`) — decide qual **pessoa/login**, dentro daquela loja, pode efetivamente ver e mexer na tela de gestão do grupo (lojas, cobrança consolidada). Novo, adicionado em 20/09/2026.

Uma ação de composição do grupo (ex.: adicionar loja) **exige as duas** ao mesmo tempo: a empresa logada precisa ser a `responsavel` do grupo **e** o usuário logado precisa ter acesso de gestão (ser master ou gestor concedido). Antes de 20/09/2026 só existia a camada 1 — qualquer usuário com a permissão genérica `configuracoes.empresa`/`configuracoes.editar` na loja responsável conseguia mexer no grupo inteiro, mesmo sem nenhuma relação direta com a administração dele. Essa era a lacuna que motivou a camada 2.

### Camada 1 — papel da empresa (`GrupoComercialMembro.papel`)

| Papel | Como se torna | Privilégios |
|---|---|---|
| `responsavel` | Automático para quem cria o grupo (`criar_grupo`) — seja no cadastro público (grupo-de-1) ou no onboarding assistido de ops. Nunca é atribuído de outra forma — não existe rota para "promover" um membro a responsável ou transferir a responsabilidade. | Única empresa a partir da qual dá pra disparar `adicionar_loja` e `remover_membro` (ainda sujeito à camada 2). Também é o único papel de onde se cria/remove vínculo de equivalência de produto (`vincular_produtos`/`remover_vinculo`). |
| `membro` | Automático quando uma loja nova é criada via `adicionar_loja` (self-service, feito por quem já tem acesso de gestão) ou pelo onboarding assistido de ops. | Pode usar estoque compartilhado (como origem ou consumidora, se autorizado), ver análises/consolidados do grupo, ver vínculos de produto. |

⚠️ **A empresa responsável nunca pode ser removida do próprio grupo** — bloqueio explícito em `remover_membro` (`HTTP 400`). Como também não existe rota para transferir o papel de responsável, **um grupo fica permanentemente amarrado à empresa que o criou**: não há como "aposentar" o criador original sem apagar o grupo inteiro (e não existe rota de exclusão de grupo — `GrupoComercial.status` só é setado como `"ativo"` em todo o código lido; não há caminho para `"inativo"`/`"encerrado"`).

### Camada 2 — acesso de gestão do grupo, por usuário

- **Usuário MASTER** (`User.master_grupo_id`): cada grupo tem um usuário master permanente — quem criou o grupo (fundador do cadastro público, ou o titular do onboarding assistido de ops). Acesso total e automático, sempre, a **todas as lojas do próprio grupo** — inclusive lojas que entrarem no grupo depois, mesmo que ele não tenha sido quem as adicionou (`GrupoComercialService._garantir_acesso_master`, chamado de dentro de `adicionar_loja`, dá a ele um `UserTenant`/`Role` novo na loja nova automaticamente, se ele ainda não tiver). Esse acesso:
  - Não pode ser reduzido nem removido por nenhuma tela — `usuarios_routes.py` recusa (`403`) mudar o `role_id` ou desativar o vínculo de um usuário que é master de algum grupo, em qualquer loja.
  - Faz bypass de permissão dentro do próprio grupo (`check_permission` em `permissions_service.py`) — sempre com acesso total, inclusive a permissões criadas depois que o `Role` dele já existia. **Nunca** um bypass fora do grupo dele.
  - Grupos que já existiam antes de 20/09/2026 ganharam um master via migration de backfill, a partir do usuário já registrado como `responsavel` de cada um (ou, na ausência de referência direta, o usuário mais antigo com vínculo ativo naquela empresa) — nenhum grupo ficou sem master.
- **Gestor do grupo** (`GrupoComercialGestor`): um usuário qualquer (de qualquer loja do grupo) ao qual o **master** concedeu acesso à tela de gestão. Só o master concede ou revoga (`conceder_gestor`/`revogar_gestor` — `403` se quem chama não for master); quem recebe **não** vira master e **não** pode repassar o acesso a outra pessoa.
- O que a camada 2 protege, na prática (`exigir_acesso_gestao`, chamado a partir do service): `listar_resumo` (filtra quais grupos aparecem — ver abaixo), `adicionar_loja`, `remover_membro`, conceder/revogar/listar gestor, billing consolidado (ver seção própria). **Não** protege: estoque compartilhado, vínculos de produto, visão consolidada/análises, mestres do grupo — essas rotas continuam só na permissão genérica de tenant (`configuracoes.empresa`/`configuracoes.editar` ou `relatorios.gerencial`/`relatorios.financeiro`, conforme o caso).

`GET /grupos-comerciais/resumo` retorna só os grupos em que o usuário logado tem acesso de gestão (master ou gestor); se a empresa participa de um grupo mas o usuário não tem esse acesso, o grupo some da lista e a resposta sinaliza `tem_grupo_sem_acesso=true` — a tela mostra uma mensagem pedindo pra falar com o responsável, em vez de simplesmente não achar nada.

## Como um grupo cresce hoje — só "adicionar loja"

> ⚠️ **Mudou em 20/09/2026**: o fluxo de convite/código mensal entre empresas
> já independentes (`GrupoComercialCodigo`, `GrupoComercialConvite`,
> `convidar`/`responder_convite`) **foi removido por completo** — tabelas
> dropadas via migration, rotas e serviço apagados. Decisão de produto: um
> grupo só cresce criando loja nova direto nele, nunca juntando duas
> empresas que já existiam separadas.

### 1. Criação do grupo
`GrupoComercialService.criar_grupo` — hoje só é alcançado indiretamente: pelo cadastro público (todo tenant novo cria seu próprio grupo-de-1) ou pelo onboarding assistido de ops (contrato inicial com N lojas). Não existe mais um botão "criar grupo novo" isolado para quem já está logado no sistema. Quem cria vira automaticamente `responsavel` **e** master do grupo.

### 2. Adicionar loja (única forma de crescer)
`POST /grupos-comerciais/{grupo_id}/lojas` → `adicionar_loja`. Exige, ao mesmo tempo: (a) a empresa logada ser a `responsavel` do grupo e (b) o usuário logado ter acesso de gestão (master ou gestor). Provisiona uma loja nova do zero (mesmo fluxo de `provision_tenant` usado no cadastro público), reaproveitando o **mesmo usuário logado** — sem pedir e-mail/senha novos — e já anexa a loja nova ao grupo com `papel="membro"` (nunca `"responsavel"`, mesmo sendo o mesmo dono). Ao final, o master do grupo (se for uma pessoa diferente de quem chamou) ganha acesso automático à loja nova (ver camada 2 acima).

### 3. Saída/remoção de um membro
⚠️ **Não existe rota de "sair do grupo" self-service.** A única forma de uma loja deixar de participar é remoção pela `responsavel`, com acesso de gestão: `DELETE /grupos-comerciais/{grupo_id}/membros/{empresa_id}` → `remover_membro`. Ao remover:
1. `GrupoComercialMembro.status` vira `"removido"` (soft-delete, nunca é apagado fisicamente — `removido_em` registra quando).
2. **Cascata automática sobre estoque compartilhado**: todo `GrupoComercialEstoqueCompartilhado` ativo que envolva a empresa removida — seja como origem (doadora de estoque) ou como consumidora — é marcado `status="removido"` na mesma transação. Ou seja, a loja removida imediatamente para de vender pelo saldo de outra loja e para de ceder o próprio saldo.
3. `versao_membros` é incrementado.
4. Evento de auditoria `grupo_comercial_membro_removido` é registrado (`log_business_event`).

⚠️ **Achado, ainda válido — o que NÃO é limpo na remoção**: `GrupoComercialProdutoVinculo` (equivalência de produto entre lojas) **não é tocado** pela remoção de membro — nenhum service cancela ou desativa vínculos que envolvam a empresa removida. Isso tem um efeito colateral concreto: `GrupoComercialAnaliseDetalhesService._contexto()` monta o dicionário `membros_por_id` só com membros **ativos**; `GrupoComercialProdutoVinculoService._serializar_vinculo()` faz `membros_por_id[str(vinculo.empresa_a_id)][1]` **sem fallback** — se um vínculo antigo ainda ativo referenciar a empresa recém-removida, `GET /{grupo_id}/vinculos-produtos` lança `KeyError` (erro 500) na primeira chamada depois da remoção, até alguém desativar manualmente esse vínculo específico. Recomenda-se ao time replicar, na remoção de membro, a mesma cascata já existente para estoque compartilhado.

## Estoque seletivamente compartilhado

Mecanismo central do grupo (`GrupoComercialEstoqueCompartilhado`, `GrupoComercialEstoqueCompartilhadoService`). Autoriza a empresa consumidora a vender, no seu próprio PDV, o saldo de um produto que pertence fisicamente a outra empresa do grupo — **o produto e o estoque nunca saem, fisicamente, do tenant de origem**; o registro só concede permissão de leitura/venda. Gate de acesso continua só a permissão genérica de tenant (`configuracoes.empresa`/`configuracoes.editar`) — não passou a exigir acesso de gestão do grupo.

- Só produtos `ativo=True`, que não sejam serviço, e do tipo `SIMPLES` ou `VARIACAO` podem ser compartilhados (kits e produtos-pai ficam de fora, `TIPOS_COMPARTILHAVEIS`).
- Quem compartilha (a empresa de origem) escolhe o destino (`empresa_consumidora_id`) produto a produto, ou concede `acesso_catalogo_completo=True` para liberar o catálogo inteiro de uma vez.
- Só a própria origem pode ativar/desativar (`pode_remover` no retorno de `listar()` é calculado comparando `empresa_origem_id` com quem está pedindo) — a consumidora não pode se autoconceder acesso.
- Resolução em tempo de venda (`resolver_produto_venda`/`resolver_produto_catalogo`, usados pelo PDV): primeiro tenta achar o produto **localmente** no tenant do vendedor; só se não achar, procura um compartilhamento ativo que aponte para aquele `produto_id` numa empresa de origem — e troca de contexto de tenant (`tenant_context`) só para ler aquele produto específico, sem nunca abrir todo o catálogo alheio sem autorização.

## Equivalência manual de produtos entre lojas

`GrupoComercialProdutoVinculo`, gerenciado só pelo **responsável** (`vincular_produtos`/`remover_vinculo`, gate: permissão genérica de tenant). Como cada loja tem seu próprio catálogo com IDs independentes (o mesmo produto real pode ter `produto_id=42` numa loja e `produto_id=891` noutra), este vínculo diz "este produto aqui é o mesmo item que aquele lá" — **não é uma FK de banco** (não pode ser, os IDs pertencem a namespaces de tenant diferentes), é uma tabela de associação validada pelo service a cada uso.
- Um produto só pode estar vinculado a **um** produto por empresa parceira por vez — tentar criar um segundo vínculo para um produto já vinculado naquele par de empresas retorna `409`.
- Vincular o mesmo par duas vezes é idempotente (retorna o vínculo já existente).
- **Efeito prático real**: esse vínculo é o que permite a `preparar_previa_transferencia` (ver abaixo) confirmar automaticamente "o produto de destino correto é X" sem depender só de bater código de barras — reduz erro humano na transferência entre lojas.

## Transferência integrada de mercadoria (o mecanismo mais elaborado do grupo)

`GrupoComercialTransferencia`, implementado em `backend/app/estoque/transferencia_grupo_service.py` — não tem rota própria dentro de `grupo_comercial_routes.py`, vive no módulo de estoque. Move mercadoria fisicamente de uma loja do grupo para outra, com lançamento financeiro automático nos dois lados.

**Antes de transferir, tudo precisa estar "mapeado"** (`preparar_previa_transferencia`): para cada item, o sistema tenta achar o produto correspondente na loja de destino, nesta ordem de prioridade:
1. Vínculo manual já cadastrado (`GrupoComercialProdutoVinculo`) — se houver mais de um candidato vinculado, o item fica `"ambiguo"` e bloqueia.
2. Se não houver vínculo, casa automaticamente por código de barras/GTIN/GTIN tributário (normalizado, maiúsculo, sem espaços) — se achar mais de um produto com o mesmo código no destino, também fica `"ambiguo"`.
3. Se não achar nada, fica `"nao_encontrado"`; se o produto encontrado no destino for um produto-pai, um kit virtual, ou estiver inativo, fica `"invalido"`.

Se **qualquer** item não ficar `"mapeado"`, a transferência inteira é bloqueada (`409`) com a lista exata do que falta corrigir — não faz transferência parcial.

**Execução** (`executar_transferencia_integrada`), depois de tudo mapeado:
1. Idempotência: uma `chave_idempotencia` por empresa de origem (`UniqueConstraint(empresa_origem_id, chave_idempotencia)`) — reenviar a mesma chamada retorna o resultado já processado, sem duplicar.
2. **Cada empresa do grupo automaticamente ganha um cadastro de [[Cliente]] representando a outra empresa** (`_obter_ou_criar_parceiro_empresa`) — `tipo_cadastro="fornecedor"`, `tipo_pessoa="PJ"`, nome/CNPJ/telefone/e-mail copiados do próprio [[Tenant]] da outra empresa, marcado com um texto identificador em `parceiro_observacoes`. Isso é o que permite lançar o AR/AP de forma convencional, reaproveitando o fluxo normal de "saída para parceiro"/"entrada de parceiro" do módulo de estoque — **é a única situação identificada em todo o sistema onde um Cliente é criado automaticamente para representar outro tenant**, não uma pessoa real.
3. Gera uma **saída de estoque com [[ContaReceber]]** na empresa de origem (contra o Cliente-parceiro que representa o destino) e uma **entrada de estoque com [[ContaPagar]]** na empresa de destino (contra o Cliente-parceiro que representa a origem) — na mesma transação lógica, trocando de `tenant_context` no meio da função.
4. Se a origem ou o destino tiver Bling ativo, agenda sincronização de estoque em background para os dois lados (best-effort — falha de agendamento só gera um log de warning, não derruba a transferência).
5. Existe um fluxo de **cancelamento** dedicado (`transferencia_grupo_cancelamento_service.py`, acionado por `cancelar_transferencia_integrada_por_conta`), não aprofundado neste levantamento.

## Visão consolidada e análises entre lojas do grupo

Três serviços de leitura, todos operando com o mesmo padrão seguro: **iterar cada empresa membro dentro do seu próprio `tenant_context()`**, nunca uma query cross-tenant direta — o isolamento de cada loja nunca é furado, só os resultados já calculados são somados/concatenados depois em Python. Gate continua só `relatorios.gerencial`/`relatorios.financeiro` (permissão genérica de tenant) — não passou a exigir acesso de gestão do grupo.

- **`GrupoComercialAnaliseService`** (`GET /{grupo_id}/visao-consolidada`) — números agregados por loja e total do grupo: quantidade/valor de [[Venda]], estoque ([[Produto]]), financeiro em aberto/vencido ([[ContaPagar]]/[[ContaReceber]]). A própria classe se autodocumenta: *"Agrega indicadores sem expor cadastros ou lançamentos individuais"*.
- **`GrupoComercialAnaliseDetalhesService`** (`/pedidos`, `/produtos-vendidos`, `/pedidos-compra`, `/contas-pagar`) — linha a linha, das lojas do grupo combinadas numa lista só, com filtro opcional por uma loja específica (`empresa_id`) e busca por texto. `/pedidos` já traz o nome do cliente via `outerjoin`, mas o [[Cliente]] em si continua resolvido estritamente dentro do `tenant_id` daquela venda — não há nenhuma agregação de clientes entre lojas (ver [[Cliente]] para essa distinção).
- **`GrupoComercialPlanejamentoService`** (`/reposicao-inteligente`, `/analise-financeira`) — sugestão de reposição de estoque cruzando dados das lojas do grupo; não aprofundado a fundo neste levantamento.

## Relação com licenciamento — cobrança continua 100% por loja

✅ Confirmado, sem ambiguidade, e **não mudou em 20/09/2026**: **não existe billing/plano de grupo**. Nenhum modelo em `grupo_comercial_models.py` tem coluna `plan`/`billing_status`/`modulos_ativos`. Cada [[Tenant]] do grupo mantém seu próprio [[Plano]], trial e módulos contratados de forma totalmente independente — entrar ou sair de um grupo não muda em nada o que aquela loja paga ou pode acessar. Quando uma loja nova nasce via `adicionar_loja`, ela recebe seu próprio trial do zero, sem herdar nada da loja que a criou.

O que existe, desde 20/09/2026, é uma **visão consolidada de leitura** da cobrança (Asaas) de cada loja, para quem tem acesso de gestão do grupo (camada 2 acima):
- `GET /grupos-comerciais/{grupo_id}/billing` (`GrupoComercialBillingService.listar`) — para cada loja ativa do grupo, devolve o mesmo status já calculado por `asaas_billing_service.subscription_status` (o endpoint self-service `/billing/asaas/status` usa a mesma função): `billing_status`, `payment_status`, `billing_type`, `next_due_date`, `checkout_url`, e um booleano `adimplente` (`billing_status == "active"`).
- `POST /grupos-comerciais/{grupo_id}/lojas/{tenant_id}/billing/sincronizar` (`refresh_subscription_payment` em `asaas_billing_service.py`) — rebusca no Asaas o pagamento **atual** da assinatura já existente daquela loja (útil quando o link do boleto/fatura expirou) e atualiza o snapshot local. **Não cria uma cobrança nova** — não existe, em nenhum lugar do código, capacidade de gerar uma cobrança avulsa fora do ciclo normal da assinatura. Se isso vier a ser necessário, é decisão de negócio à parte (cobrar de novo dentro do mesmo ciclo?) que exige uma chamada nova à API do Asaas, ainda não implementada.

## Detalhes técnicos de implementação

- **`empresa_id_igual`/`empresa_id_sql`** (`grupo_comercial_sql.py`): todas as comparações de ID de empresa passam por essas duas funções, que normalizam removendo hífens antes de comparar — existe explicitamente para tolerar bancos/ambientes onde a coluna de `tenant_id` é `UUID` nativo num lugar e `VARCHAR` legado noutro. Indício de uma migração de tipo de coluna que já aconteceu no passado.
- `GrupoComercial.criado_por_empresa_id`, `GrupoComercialMembro.empresa_id`, `GrupoComercialTransferencia.empresa_origem_id`/`empresa_destino_id`, `GrupoComercialProdutoVinculo.empresa_a_id`/`empresa_b_id`/`criado_por_empresa_id` e `GrupoComercialEstoqueCompartilhado.empresa_origem_id`/`empresa_consumidora_id` são **todas FKs reais** para `tenants.id`, a maioria com `ondelete="RESTRICT"` — ou seja, o banco **impede fisicamente apagar um Tenant** enquanto ele aparecer em qualquer registro de grupo (criador, membro, transferência, vínculo, compartilhamento). Isso é mais rígido do que a regra de negócio "responsável não pode ser removido do grupo" — é uma segunda camada de proteção, a nível de schema.
- `User.master_grupo_id` é FK para `grupos_comerciais.id` (nullable) — não-nulo identifica o usuário master daquele grupo. `GrupoComercialGestor` tem FK para `grupos_comerciais.id` e duas para `users.id` (`user_id` e `concedido_por_user_id`).
- `GrupoComercialCodigo`/`GrupoComercialConvite` (as tabelas do antigo fluxo de convite, ver seção acima) foram **dropadas** por migration em 20/09/2026 — não existem mais no schema.
- Toda mutação relevante gera um evento de auditoria via `log_business_event` (`grupo_comercial_criado`, `_membro_removido`, `_loja_adicionada`, `_gestor_concedido`/`_revogado`, `_estoque_compartilhado_ativado`/`_removido`, `_produtos_vinculados`/`_desvinculados`, `transferencia_grupo_saida_integrada`/`_entrada_integrada`) e um contador de uso de funcionalidade via `registrar_uso_funcionalidade` (ver [[evolucao_funcionalidade_usos]]).

## Utilizado por
- PDV/vendas do tenant consumidor, ao vender produto de estoque compartilhado de outro membro do grupo (`resolver_produto_venda`/`resolver_produto_catalogo`).
- Módulo de estoque (`estoque/transferencia_grupo_service.py`) para transferência integrada entre lojas, com lançamento automático de [[ContaReceber]]/[[ContaPagar]] contra um [[Cliente]]-parceiro criado automaticamente.
- Reposição inteligente e análise financeira entre lojas do mesmo grupo (`GrupoComercialPlanejamentoService`).
- Dashboard de visão consolidada e análises detalhadas (vendas, produtos vendidos, compras, contas a pagar) entre lojas do mesmo grupo.
- Sincronização Bling em background, disparada após transferências integradas.
- Tela `/configuracoes/grupos-comerciais` (frontend) — abas "Lojas do grupo", "Cobrança" e "Acessos do grupo" (a última só visível ao master).

## Não identificado
- 🔴 **Achado de robustez, já detalhado acima**: remoção de membro não limpa `GrupoComercialProdutoVinculo`, causando risco real de `KeyError`/erro 500 em `listar_vinculos` se o vínculo remanescente for consultado depois da remoção.
- ❓ `GrupoComercialPlanejamentoService` (reposição inteligente e análise financeira) não foi auditado a fundo neste levantamento — só confirmado que existe e é chamado.
- ❓ `transferencia_grupo_cancelamento_service.py` (cancelamento de transferência integrada) não foi lido em detalhe.
- ❓ Não confirmado se há limite de número de membros por grupo ligado ao plano de alguma empresa — nada encontrado nos modelos/services lidos.
- ❓ Não existe rota para o responsável transferir seu papel a outro membro, nem para excluir/encerrar um grupo inteiro — não confirmado se isso é lacuna real de produto ou decisão deliberada (grupos são pensados para não serem desfeitos).
- ❓ `/me-multitenant` (permissões exibidas no frontend) não reflete o bypass de permissão do master — se uma permissão nova for criada no catálogo depois do `Role` do master já existir, o backend libera (bypass em `check_permission`) mas a lista de permissões devolvida ao frontend pode não mostrar a opção correspondente na UI. Não chegou a ser corrigido nesta rodada.
