---
tipo: dominio
atualizado: 2026-09-16
---

# Entidade — EmpresaGrupo (grupo de empresas)

Ver [[Tenant]], [[Produto]], [[Cliente]], [[ContaPagar]], [[ContaReceber]], [[Plano]], [[Venda]].

## Definição

Agrupa vários [[Tenant]] (lojas) sob um mesmo grupo econômico, permitindo que operem de forma coordenada em três frentes — **estoque seletivamente compartilhado**, **transferência integrada de mercadoria com lançamento financeiro automático** e **análise consolidada de indicadores** — sem nunca unir o cadastro, o licenciamento ou o isolamento de dados de cada loja. É puramente uma camada operacional que **atravessa** tenants por natureza; por isso os modelos não herdam `BaseTenantModel`, e todo acesso passa obrigatoriamente por um service que valida manualmente o tenant do ator em cada operação.

Uma mesma empresa (tenant) **pode participar de mais de um grupo ao mesmo tempo** — não há nenhuma constraint ou validação que impeça isso; `EmpresaGrupoMembro` só garante `UniqueConstraint(grupo_id, empresa_id)`, ou seja, só impede entrar duas vezes *no mesmo* grupo.

## Quem pode fazer o quê

Dentro de um grupo existem só dois papéis, guardados em `EmpresaGrupoMembro.papel`:

| Papel | Como se torna | Privilégios |
|---|---|---|
| `responsavel` | Automático para quem cria o grupo (`criar_grupo`). Nunca é atribuído de outra forma — não existe rota para "promover" um membro a responsável ou transferir a responsabilidade. | Único papel que pode: convidar novas empresas (`convidar`), remover um membro (`remover_membro`), criar/remover vínculos de equivalência de produto (`vincular_produtos`/`remover_vinculo`). |
| `membro` | Automático ao aceitar um convite (`responder_convite` com `aceitar=True`). | Pode usar estoque compartilhado (como origem ou consumidora, se autorizado), ver análises/consolidados do grupo, ver vínculos de produto — mas não pode convidar nem remover ninguém, nem mexer nos vínculos. |

⚠️ **A empresa responsável nunca pode ser removida do próprio grupo** — bloqueio explícito em `remover_membro` (`HTTP 400`). Como também não existe rota para transferir o papel de responsável, **um grupo fica permanentemente amarrado à empresa que o criou**: não há como "aposentar" o criador original sem apagar o grupo inteiro (e não existe rota de exclusão de grupo — `EmpresaGrupo.status` só é setado como `"ativo"` em todo o código lido; não há caminho para `"inativo"`/`"encerrado"`).

Todas as rotas de configuração (criar grupo, convidar, responder convite, remover membro, gerenciar estoque compartilhado) exigem a permissão `configuracoes.empresa` **ou** `configuracoes.editar` (RBAC normal, resolvido por tenant — ver [[Role-Permission]]). As rotas de análise/consolidado exigem `relatorios.gerencial` **ou** `relatorios.financeiro`. Em ambos os casos, além da permissão, o service sempre confere que a empresa do usuário logado é membro **ativo** do grupo — a permissão sozinha não basta.

## Ciclo de vida — criação, convite, entrada e saída

### 1. Criação do grupo
`POST /grupos-empresas` → `EmpresaGrupoService.criar_grupo`. Qualquer usuário com a permissão de configuração, de uma empresa **ativa** (`Tenant.status == "active"`), pode criar um grupo a qualquer momento — não exige aprovação de ninguém, não tem limite de quantos grupos uma empresa pode criar. A empresa criadora vira automaticamente o único membro, com `papel="responsavel"`.

### 2. Código de convite (por empresa, mensal)
Cada empresa tem um código próprio (`EmpresaGrupoCodigo`), **não é o grupo que gera o código, é a empresa a ser convidada**. Buscado sob demanda (`obter_codigo`, embutido em `GET /grupos-empresas/resumo`):
- 12 caracteres, alfabeto sem ambiguidade visual (`ABCDEFGHJKLMNPQRSTUVWXYZ23456789` — sem `I`, `O`, `0`, `1`), gerado com `secrets.choice` (criptograficamente seguro).
- Válido pela **competência do mês corrente** (fuso `America/Sao_Paulo`) — expira automaticamente à meia-noite do dia 1 do mês seguinte. No mês seguinte, um código novo é gerado na primeira consulta.
- Uma empresa só tem 1 código ativo por competência (`UniqueConstraint(empresa_id, competencia)`) — reaproveita o mesmo código o mês inteiro, não gera um novo a cada consulta.
- O código não pertence a nenhum grupo específico — é uma credencial da empresa, usada para provar identidade no momento do convite.

### 3. Convite
`POST /grupos-empresas/{grupo_id}/convites` → `EmpresaGrupoService.convidar`, restrito à empresa **responsável**. Fluxo: a empresa que quer entrar gera/consulta seu próprio código (passo 2) e **compartilha esse código fora do sistema** (telefone, e-mail, WhatsApp — não há nenhum envio automático) com o responsável do grupo; o responsável digita esse código em `codigo_empresa`. Validações, nesta ordem:
1. Código precisa existir e não ter expirado (senão `404`).
2. A empresa dona do código precisa estar ativa (senão `404`).
3. Não pode convidar a própria empresa responsável (`400`).
4. Não pode convidar quem já é membro **ativo** do grupo (`409`).
5. Não pode haver já um convite **pendente e não expirado** para a mesma empresa (`409`) — evita duplicar convite. Se existir um convite antigo já respondido ou expirado, ele é **reaproveitado** (upsert: vira pendente de novo, com nova validade).

Todo o fluxo usa `with_for_update()` (lock pessimista) no grupo e no convite, para não haver corrida em convites simultâneos.

### 4. Aceite/recusa
`POST /grupos-empresas/convites/{id}/aceitar` ou `/recusar` → `responder_convite`, só a própria empresa convidada pode responder (checado por `empresa_convidada_id == empresa_id` na query, não é um "código" — é a sessão logada). Se o convite já expirou no momento da resposta, é marcado `"expirado"` e retorna `410`.
- **Aceitar**: cria (ou reativa, se a empresa já tinha sido membro removido antes) uma linha `EmpresaGrupoMembro` com `papel="membro"` — nunca `"responsavel"`. Incrementa `EmpresaGrupo.versao_membros` (contador otimista de mudança de composição do grupo).
- **Recusar**: só marca o convite como `"recusado"`; nenhuma linha de membro é criada.

### 5. Saída/remoção de um membro
⚠️ **Não existe rota de "sair do grupo" self-service.** A única forma de uma empresa deixar de participar é o **responsável** removê-la: `DELETE /grupos-empresas/{grupo_id}/membros/{empresa_id}` → `remover_membro`. Ao remover:
1. `EmpresaGrupoMembro.status` vira `"removido"` (soft-delete, nunca é apagado fisicamente — `removido_em` registra quando).
2. **Cascata automática sobre estoque compartilhado**: todo `EmpresaGrupoEstoqueCompartilhado` ativo que envolva a empresa removida — seja como origem (doadora de estoque) ou como consumidora — é marcado `status="removido"` na mesma transação. Ou seja, a loja removida imediatamente para de vender pelo saldo de outra loja e para de ceder o próprio saldo.
3. `versao_membros` é incrementado.
4. Evento de auditoria `empresa_grupo_membro_removido` é registrado (`log_business_event`).

⚠️ **Achado — o que NÃO é limpo na remoção**: `EmpresaGrupoProdutoVinculo` (equivalência de produto entre lojas) **não é tocado** pela remoção de membro — nenhum service cancela ou desativa vínculos que envolvam a empresa removida. Isso tem um efeito colateral concreto: `EmpresaGrupoAnaliseDetalhesService._contexto()` monta o dicionário `membros_por_id` só com membros **ativos**; `EmpresaGrupoProdutoVinculoService._serializar_vinculo()` faz `membros_por_id[str(vinculo.empresa_a_id)][1]` **sem fallback** — se um vínculo antigo ainda ativo referenciar a empresa recém-removida, `GET /{grupo_id}/vinculos-produtos` lança `KeyError` (erro 500) na primeira chamada depois da remoção, até alguém desativar manualmente esse vínculo específico. Recomenda-se ao time replicar, na remoção de membro, a mesma cascata já existente para estoque compartilhado.

## Estoque seletivamente compartilhado

Mecanismo central do grupo (`EmpresaGrupoEstoqueCompartilhado`, `EmpresaGrupoEstoqueCompartilhadoService`). Autoriza a empresa consumidora a vender, no seu próprio PDV, o saldo de um produto que pertence fisicamente a outra empresa do grupo — **o produto e o estoque nunca saem, fisicamente, do tenant de origem**; o registro só concede permissão de leitura/venda.

- Só produtos `ativo=True`, que não sejam serviço, e do tipo `SIMPLES` ou `VARIACAO` podem ser compartilhados (kits e produtos-pai ficam de fora, `TIPOS_COMPARTILHAVEIS`).
- Quem compartilha (a empresa de origem) escolhe o destino (`empresa_consumidora_id`) produto a produto, ou concede `acesso_catalogo_completo=True` para liberar o catálogo inteiro de uma vez.
- Só a própria origem pode ativar/desativar (`pode_remover` no retorno de `listar()` é calculado comparando `empresa_origem_id` com quem está pedindo) — a consumidora não pode se autoconceder acesso.
- Resolução em tempo de venda (`resolver_produto_venda`/`resolver_produto_catalogo`, usados pelo PDV): primeiro tenta achar o produto **localmente** no tenant do vendedor; só se não achar, procura um compartilhamento ativo que aponte para aquele `produto_id` numa empresa de origem — e troca de contexto de tenant (`tenant_context`) só para ler aquele produto específico, sem nunca abrir todo o catálogo alheio sem autorização.

## Equivalência manual de produtos entre lojas

`EmpresaGrupoProdutoVinculo`, gerenciado só pelo **responsável** (`vincular_produtos`/`remover_vinculo`). Como cada loja tem seu próprio catálogo com IDs independentes (o mesmo produto real pode ter `produto_id=42` numa loja e `produto_id=891` noutra), este vínculo diz "este produto aqui é o mesmo item que aquele lá" — **não é uma FK de banco** (não pode ser, os IDs pertencem a namespaces de tenant diferentes), é uma tabela de associação validada pelo service a cada uso.
- Um produto só pode estar vinculado a **um** produto por empresa parceira por vez — tentar criar um segundo vínculo para um produto já vinculado naquele par de empresas retorna `409`.
- Vincular o mesmo par duas vezes é idempotente (retorna o vínculo já existente).
- **Efeito prático real**: esse vínculo é o que permite a `preparar_previa_transferencia` (ver abaixo) confirmar automaticamente "o produto de destino correto é X" sem depender só de bater código de barras — reduz erro humano na transferência entre lojas.

## Transferência integrada de mercadoria (o mecanismo mais elaborado do grupo)

`EmpresaGrupoTransferencia`, implementado em `backend/app/estoque/transferencia_grupo_service.py` — não tem rota própria dentro de `empresa_grupo_routes.py`, vive no módulo de estoque. Move mercadoria fisicamente de uma loja do grupo para outra, com lançamento financeiro automático nos dois lados.

**Antes de transferir, tudo precisa estar "mapeado"** (`preparar_previa_transferencia`): para cada item, o sistema tenta achar o produto correspondente na loja de destino, nesta ordem de prioridade:
1. Vínculo manual já cadastrado (`EmpresaGrupoProdutoVinculo`) — se houver mais de um candidato vinculado, o item fica `"ambiguo"` e bloqueia.
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

Três serviços de leitura, todos operando com o mesmo padrão seguro: **iterar cada empresa membro dentro do seu próprio `tenant_context()`**, nunca uma query cross-tenant direta — o isolamento de cada loja nunca é furado, só os resultados já calculados são somados/concatenados depois em Python.

- **`EmpresaGrupoAnaliseService`** (`GET /{grupo_id}/visao-consolidada`) — números agregados por loja e total do grupo: quantidade/valor de [[Venda]], estoque ([[Produto]]), financeiro em aberto/vencido ([[ContaPagar]]/[[ContaReceber]]). A própria classe se autodocumenta: *"Agrega indicadores sem expor cadastros ou lançamentos individuais"*.
- **`EmpresaGrupoAnaliseDetalhesService`** (`/pedidos`, `/produtos-vendidos`, `/pedidos-compra`, `/contas-pagar`) — linha a linha, das lojas do grupo combinadas numa lista só, com filtro opcional por uma loja específica (`empresa_id`) e busca por texto. `/pedidos` já traz o nome do cliente via `outerjoin`, mas o [[Cliente]] em si continua resolvido estritamente dentro do `tenant_id` daquela venda — não há nenhuma agregação de clientes entre lojas (ver [[Cliente]] para essa distinção).
- **`EmpresaGrupoPlanejamentoService`** (`/reposicao-inteligente`, `/analise-financeira`) — sugestão de reposição de estoque cruzando dados das lojas do grupo; não aprofundado a fundo neste levantamento.

## Relação com licenciamento

✅ Confirmado, sem ambiguidade: **não existe billing/plano de grupo**. Nenhum modelo em `empresa_grupo_models.py` tem coluna `plan`/`billing_status`/`modulos_ativos`. Cada [[Tenant]] do grupo mantém seu próprio [[Plano]], trial e módulos contratados de forma totalmente independente — entrar ou sair de um grupo não muda em nada o que aquela loja paga ou pode acessar.

## Detalhes técnicos de implementação

- **`empresa_id_igual`/`empresa_id_sql`** (`empresa_grupo_sql.py`): todas as comparações de ID de empresa passam por essas duas funções, que normalizam removendo hífens antes de comparar — existe explicitamente para tolerar bancos/ambientes onde a coluna de `tenant_id` é `UUID` nativo num lugar e `VARCHAR` legado noutro. Indício de uma migração de tipo de coluna que já aconteceu no passado.
- `EmpresaGrupo.criado_por_empresa_id`, `EmpresaGrupoMembro.empresa_id`, `EmpresaGrupoConvite.empresa_convidada_id`/`convidado_por_empresa_id`, `EmpresaGrupoTransferencia.empresa_origem_id`/`empresa_destino_id`, `EmpresaGrupoProdutoVinculo.empresa_a_id`/`empresa_b_id`/`criado_por_empresa_id` e `EmpresaGrupoEstoqueCompartilhado.empresa_origem_id`/`empresa_consumidora_id` são **todas FKs reais** para `tenants.id`, a maioria com `ondelete="RESTRICT"` — ou seja, o banco **impede fisicamente apagar um Tenant** enquanto ele aparecer em qualquer registro de grupo (criador, membro, convite, transferência, vínculo, compartilhamento). Isso é mais rígido do que a regra de negócio "responsável não pode ser removido do grupo" — é uma segunda camada de proteção, a nível de schema.
- Toda mutação relevante gera um evento de auditoria via `log_business_event` (`empresa_grupo_criado`, `_convite_enviado`, `_convite_aceito`/`_recusado`, `_membro_removido`, `_estoque_compartilhado_ativado`/`_removido`, `_produtos_vinculados`/`_desvinculados`, `transferencia_grupo_saida_integrada`/`_entrada_integrada`) e um contador de uso de funcionalidade via `registrar_uso_funcionalidade` (ver [[evolucao_funcionalidade_usos]]).

## Utilizado por
- PDV/vendas do tenant consumidor, ao vender produto de estoque compartilhado de outro membro do grupo (`resolver_produto_venda`/`resolver_produto_catalogo`).
- Módulo de estoque (`estoque/transferencia_grupo_service.py`) para transferência integrada entre lojas, com lançamento automático de [[ContaReceber]]/[[ContaPagar]] contra um [[Cliente]]-parceiro criado automaticamente.
- Reposição inteligente e análise financeira entre lojas do mesmo grupo (`EmpresaGrupoPlanejamentoService`).
- Dashboard de visão consolidada e análises detalhadas (vendas, produtos vendidos, compras, contas a pagar) entre lojas do mesmo grupo.
- Sincronização Bling em background, disparada após transferências integradas.

## Não identificado
- 🔴 **Achado de robustez, já detalhado acima**: remoção de membro não limpa `EmpresaGrupoProdutoVinculo`, causando risco real de `KeyError`/erro 500 em `listar_vinculos` se o vínculo remanescente for consultado depois da remoção.
- ❓ `EmpresaGrupoPlanejamentoService` (reposição inteligente e análise financeira) não foi auditado a fundo neste levantamento — só confirmado que existe e é chamado.
- ❓ `transferencia_grupo_cancelamento_service.py` (cancelamento de transferência integrada) não foi lido em detalhe.
- ❓ Não confirmado se há limite de número de membros por grupo ligado ao plano de alguma empresa — nada encontrado nos modelos/services lidos.
- ❓ Não existe rota para o responsável transferir seu papel a outro membro, nem para excluir/encerrar um grupo inteiro — não confirmado se isso é lacuna real de produto ou decisão deliberada (grupos são pensados para não serem desfeitos).
