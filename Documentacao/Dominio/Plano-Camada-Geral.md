---
tipo: plano
atualizado: 2026-09-25
---

> **Status (2026-09-19): Checkpoints 1-5 implementados e verificados contra Postgres real** (migrations aplicadas, boot limpo, rotas confirmadas no OpenAPI, lógica de sugestão/vínculo/desvínculo testada ao vivo pra cada domínio). Pendência declarada desde o início: nenhum teste `pytest` formal ainda — só verificação manual/ao vivo, mesmo padrão do Checkpoint 0. Ver "Notas de implementação" no fim do documento pra detalhes de cada checkpoint.

# Plano — Camada geral (Pessoas, Produtos, Pet, taxonomias)

Roteiro de execução da segunda fase da reestruturação de grupo — a primeira (`GrupoComercial` obrigatório) está com o código pronto, faltando só testes/validação (ver "Checkpoint 0"). Ver [[Proposta-Modelo-Proprietario-Lojas]] (a origem conceitual disto) e [[EmpresaGrupo]] (ainda com o nome antigo — precisa de atualização, ver Checkpoint 0).

Cada checkpoint só é considerado fechado quando o critério de "pronto" dele for verdade — não avançar pro próximo com um checkpoint pela metade. Escopo de cada um é deliberadamente pequeno; a tentação de fazer tudo de uma vez é exatamente o que gera as tabelas duplicadas/campos órfãos que achamos no levantamento original.

## O padrão técnico (estabelecido uma vez, no Checkpoint 1, reaproveitado depois)

Toda entidade "mestre" segue a mesma forma:

- Tabela nova `xxx_mestre`, escopada por `grupo_id` (FK pra `grupos_comerciais.id`, **não** `tenant_id` — é uma entidade de grupo, igual o próprio `GrupoComercial`, não herda `BaseTenantModel`).
- Guarda só os campos de **identidade** (o que é igual em qualquer loja). Campos **operacionais** (preço, estoque, histórico de compra, disponibilidade) continuam 100% na tabela local de cada loja, sem exceção.
- Tabela local ganha uma coluna nova, opcional, `xxx_mestre_id` — nullable, sem quebrar quem nunca usar isso.
- **Sem vínculo**: loja continua funcionando exatamente como hoje, cadastro 100% independente.
- **Com vínculo**: campos de identidade são herdados do mestre por padrão; uma loja pode sobrescrever um campo específico, mas isso precisa ficar sinalizado na UI ("personalizado nesta loja") — nunca uma divergência silenciosa.
- Cada domínio pega esse molde e só decide *quais campos* são identidade vs. operacional — a mecânica (tabela, FK, herança, override) é a mesma nos quatro.

## Checkpoint 0 — Fundação (feito, com pendência)

**Status:** código completo (rename `EmpresaGrupo`→`GrupoComercial`, grupo-de-1 automático, "adicionar loja ao grupo", onboarding assistido de ops), verificado via build/boot real. **Falta:** testes automatizados (`test_grupo_comercial_service.py`, cobertura de `adicionar_loja`/fechamento de grupo-de-1/onboarding em loop), teste manual no navegador dos dois fluxos novos, atualização do `EmpresaGrupo.md` pro nome novo, commit/push/PR/CI, merge com a `main`.

**Critério de pronto:** PR mergeado na `main` com CI verde. — *Sem isso, os checkpoints abaixo ficam construindo em cima de uma fundação não testada.*

## Checkpoint 1 — Espécie / Raça mestre (prova de conceito do padrão) ✅ Feito

**Por quê primeiro:** é o caso mais simples que existe — dado de taxonomia pura, sem ambiguidade de negócio, sem dado sensível, sem campo operacional nenhum pra separar. Serve pra provar o padrão técnico (tabela mestre + FK local + herança) uma vez, num caso de baixíssimo risco, antes de aplicar em algo mais delicado.

**Escopo:**
- `especie_mestre`/`raca_mestre`, escopadas por `grupo_id`.
- `Especie.especie_mestre_id` / `Raca.raca_mestre_id`, nullable.
- Serviço simples: ao cadastrar espécie/raça numa loja, se já existir uma com nome igual (case-insensitive) no mestre do grupo, sugerir vincular em vez de duplicar.
- Migration só-schema (tabela + FK), sem backfill de dado — não vale a pena tentar casar nomes automaticamente aqui, é baixo volume.

**Fora do escopo agora:** UI dedicada — pode ser só um campo "usar do grupo" no formulário que já existe de Espécie/Raça.

**Critério de pronto:** uma espécie cadastrada como mestre num grupo aparece disponível (herdada) em todas as lojas do grupo; loja continua podendo ter espécie 100% própria sem tocar no mestre; testes cobrindo os dois casos.

## Checkpoint 2 — Produto mestre ⚠️ Eliminado em 10/2026

**Superado**: o mecanismo de `produto_mestre` descrito abaixo (vínculo opcional
entre cópias de Produto por loja, cópia única no momento do vínculo, nunca mais
sincronizada depois) foi **removido por inteiro** — modelo (`ProdutoMestre` +
`CategoriaMestre`/`MarcaMestre`/`DepartamentoMestre`), service, rotas e as 4
tabelas (migration `zzzzc20261015a1_drop_produto_mestre.py`). Produto passou a
ter identidade compartilhada automática: uma única `ProdutoIdentidade` por item
físico, vinculada por correspondência automática de código de barras/GTIN
dentro do grupo comercial (sem vínculo manual), editável por qualquer loja do
grupo, com a mudança propagando pra todas as lojas ligadas — mesmo padrão já
usado em Cliente/Pet (`origem_tenant_id` + RLS), adaptado pra dividir campos
(preço/estoque/lote continuam 100% por loja, só a identidade física é
compartilhada). Ver Checkpoint 7 abaixo e `app/services/produto_identidade_service.py`.
Resto desta seção fica só como histórico do desenho anterior.

**Escopo** (já desenhado em detalhe na [[Proposta-Modelo-Proprietario-Lojas]], seção 5.2):
- `produto_mestre` (nome, descrição, fotos, categoria/marca/departamento, ficha técnica, GTIN, dados fiscais de referência) + `categoria_mestre`/`marca_mestre`/`departamento_mestre` andando junto.
- `Produto.produto_mestre_id`, nullable.
- Fluxo "adotar produto-mestre existente" ao cadastrar em loja adicional do mesmo grupo (busca por nome/GTIN).
- Sugestão automática usando o Catálogo Mestre **global** já existente (`catalogo_mestre_produtos`) como fonte de dados prontos pra criar um produto-mestre novo — só sugestão, nunca escrita automática.
- Override explícito por campo, sinalizado na UI.

**Fora do escopo agora:** migrar produtos já cadastrados nas lojas pra um mestre automaticamente (isso é o Checkpoint 6, "adoção assistida" — requer matching difuso, é trabalho à parte).

**Critério de pronto:** cadastrar um produto numa 2ª loja do grupo permite escolher "usar produto existente do grupo" e herdar nome/descrição/fotos, mantendo preço/estoque 100% locais; teste cobrindo herança + override; smoke manual no PDV confirmando que preço/estoque continuam corretos por loja.

## Checkpoint 3 — Pet mestre ✅ Feito

**Por quê antes de Pessoa:** é o ganho mais visível pro usuário final (continuidade de atendimento entre lojas do mesmo grupo) e tem menos ambiguidade de consentimento do que Pessoa — dado do animal, não da pessoa em si.

**Escopo:**
- `pet_mestre` (nome, espécie/raça, sexo, data de nascimento, microchip, alergias, doenças crônicas, medicamentos contínuos, tipo sanguíneo, foto) + `PerfilComportamental` dobrado junto (temperamento, medo de tesoura/secador etc. — hoje já é satélite 1:1 do Pet).
- `Pet.pet_mestre_id`, nullable.
- **Continua 100% local:** toda consulta, vacina, exame, internação — eventos clínicos não sobem pro mestre, só a identidade do pet.
- Vínculo Especie/Raça do pet aponta pro mestre do Checkpoint 1, quando existir.

**Fora do escopo agora:** consolidar o *histórico clínico* entre lojas (isso seria um relatório de leitura, à parte — não faz parte de "camada mestre", é uma feature de consulta, decisão separada).

**Critério de pronto:** tutor que leva o pet a duas lojas do mesmo grupo não precisa recadastrar alergia/doença crônica/microchip na segunda; consulta na loja 2 lê o perfil comportamental cadastrado na loja 1; teste cobrindo isso.

## Checkpoint 4 — Pessoa mestre (Cliente / Fornecedor / Veterinário) ⚠️ Eliminado em 10/2026

**Superado**: o mecanismo de `pessoa_mestre` descrito abaixo (vínculo opcional entre cópias de Cliente por loja) foi **removido por inteiro** — modelo, service, rotas e tabela (migration `zzzy20261009a1_drop_pessoa_mestre.py`). Pessoa deixou de ser copiada por loja: agora existe um único `Cliente`, compartilhado automaticamente por todas as lojas ativas do grupo via RLS (`app/tenancy/filters.py::pessoa_visivel_no_grupo` + migrations `zzzq20261005a1`/`zzzv20261005a1`) — não precisa mais de vínculo manual nenhum. Ver [[Cliente]] (seção "Relação com Tenant, lojas e grupos de empresa") e [[EmpresaGrupo]] (seções "1. Criação do grupo"/"2. Adicionar loja") para o mecanismo atual. Resto desta seção fica só como histórico do desenho anterior.

**Por quê por último:** é a mais sensível (dado pessoal, LGPD) e a mais complexa (a mesma tabela hoje cobre cliente, fornecedor e veterinário via `tipo_cadastro`). Só começar depois que o padrão já estiver validado nos três anteriores.

**Escopo:**
- `pessoa_mestre` (nome, CPF/CNPJ, telefone, e-mail, endereço, tipo, CRMV quando aplicável).
- `Cliente.pessoa_mestre_id`, nullable.
- **Vínculo é sempre sugestão + confirmação manual, nunca automático** — mesmo padrão CDP já decidido na proposta: ao cadastrar um CPF/telefone que já existe em outra loja do grupo, sugerir "já existe cadastro em [loja], vincular histórico?".
- Continua 100% local: histórico de compra, segmentação, campos financeiros/DRE, consentimento — cada loja é dona do que coletou.

✅ **Mudou em 25/09/2026 — exceção para onboarding/criação de loja**: ao provisionar uma loja nova (cadastro público em `/auth/register`, onboarding assistido de ops e "adicionar loja", todos via `GrupoComercialService.criar_grupo`/`adicionar_loja`), o `Cliente` do titular é criado automaticamente em cada loja nova e **vinculado automaticamente** à mesma `PessoaMestre` do grupo — achada via `Cliente.auth_user_id` do titular em qualquer loja já membro, não por CPF/CNPJ — sem sugestão nem confirmação manual. Isso faz parte de uma reestruturação maior do processo de onboarding/criação de lojas: a regra "sempre sugestão + confirmação manual" acima segue valendo para o fluxo de tela (cadastro manual de um cliente comprador pré-existente), mas deixa de ser a regra padrão para toda vinculação — o vínculo automático em onboarding é a nova direção de produto, e os resquícios do fluxo manual-apenas fora deste caso devem ser eliminados depois (fora do escopo desta rodada). Ver [[EmpresaGrupo]], seções "1. Criação do grupo" e "2. Adicionar loja".

**Pré-requisito de negócio, não técnico:** confirmar com o usuário se os termos de uso já foram atualizados pra cobrir "consentimento vale pro grupo comercial" (mencionado por ele numa rodada anterior — não é bloqueio técnico, mas vale checar antes de ativar isso em produção).

**Critério de pronto:** cadastro de cliente já existente noutra loja do grupo sugere vínculo (nunca funde sozinho); teste cobrindo a sugestão e a recusa; confirmação de que o time validou o texto de consentimento antes de ligar isso pra clientes reais.

## Checkpoint 5 — Interface consolidada ✅ Feito (versão enxuta)

Depois dos 4 domínios prontos no backend: uma tela única (provavelmente dentro de "Grupos Comerciais", ao lado do que já existe) listando os mestres do grupo — produtos, pets, pessoas, espécies/raças — com quem está vinculado e a ação de vincular/desvincular. Sem isso, os recursos existem só via API, difícil de operar no dia a dia.

**Critério de pronto:** um usuário sem acesso ao backend consegue, sozinho, ver e gerenciar os vínculos do grupo.

## Checkpoint 6 — Adoção assistida (opcional, avaliar depois)

Ferramenta de matching pra lojas que **já tinham** produtos/pets/clientes duplicados entre si antes da camada mestre existir — sugere pares prováveis (mesmo GTIN, mesmo CPF, nome de pet + tutor iguais) pra vincular em lote. Mais complexo (matching difuso, revisão humana antes de aplicar), decisão separada sobre se vale o esforço ou se a adoção orgânica (vincular conforme cadastra de novo) já resolve.

## Checkpoint 7 — Produto: identidade compartilhada (fase D) ✅ Backend feito

**Por quê revisitar Produto**: o Checkpoint 2 (`produto_mestre`) provou o
desenho de "tabela mestre + FK opcional" mas nunca saiu do papel na prática —
vínculo manual, cópia única, nunca exposto no formulário de produto de
verdade. O Lucas pediu o mesmo tratamento já dado a Pessoa no Checkpoint 4:
compartilhamento automático (sem vínculo manual) e vivo (edição em qualquer
loja propaga pra todas), só que, diferente de Pessoa, Produto precisa de
**divisão de campos** — preço/estoque/lote/fornecedor continuam 100% por
loja, só o que é fisicamente o mesmo item (nome, código de barras/GTIN, peso,
dimensões, foto, descrição, classificação de ração) é compartilhado.

**Escopo**:
- Tabela nova `produto_identidades` (model `ProdutoIdentidade`,
  `app/produto_identidade_models.py`) — mesmo padrão `origem_tenant_id` + RLS
  de grupo já usado em `Cliente`/`Pet` (`app/tenancy/filters.py`, clonado da
  migration `zzzv20261005a1_rls_grupo_pessoas_pets.py`), aplicado só a essa
  tabela nova. `Produto` ganha `produto_identidade_id` (nullable) e continua
  com as mesmas colunas inerentes de sempre, funcionando como espelho
  sincronizado — nenhum dos ~169 arquivos que já leem `Produto.nome`/
  `codigo_barras`/etc. direto precisou mudar.
- Correspondência automática por código de barras/GTIN exato (reaproveita a
  query já existente em `grupo_duplicados_service.py::produtos_duplicados`) —
  0 correspondências cria identidade nova, exatamente 1 vincula e herda os
  valores já estabelecidos, 2+ vai pra fila de conflito
  (`produto_identidade_conflitos`), nunca escolhe sozinho.
- Funil único de escrita (`app/services/produto_identidade_service.py`):
  grava na identidade, audita (`produto_identidades_historico_alteracoes`), e
  propaga (sobrescreve, nunca diff) pra toda loja do grupo ligada àquela
  identidade, cada uma dentro do seu próprio `tenant_context()` — nunca um
  UPDATE cross-tenant direto. Ligado em `ProdutoService.create_produto`,
  `atualizar_produto` e no endpoint de edição em lote (`AtualizacaoLoteRequest`).
- `ProdutoMestre` eliminado por inteiro (ver nota no Checkpoint 2 acima).

**Fora do escopo desta rodada**: varredura/fusão dos produtos já cadastrados
em lojas diferentes do grupo (script `backend/scripts/backfill_produto_identidades.py`
— desenhado no plano, ainda não implementado/rodado) e a separação visual do
formulário de produto (`ProdutosNovo.jsx`) em "dados compartilhados" vs. "dados
desta loja" — telas ainda não tocadas, produto recém-criado/editado já funciona
corretamente por baixo, só a UI não comunica isso ainda.

**Critério de pronto (backend)**: criar produto com GTIN batendo em outra loja
do mesmo grupo vincula e herda automaticamente; editar campo inerente em
qualquer loja aparece nas outras lojas ligadas; editar preço/estoque nunca
propaga; confirmado via teste manual real contra o grupo "Grupo Atacadão e
Gabi" (GS Multi Marcas + Atacadão das Rações Pet) no banco de dev.

---

## Ordem recomendada e por quê

`Checkpoint 0 → 1 → 2 → 3 → 4 → 5`, com `6` avaliado à parte depois. A lógica: prova o padrão no caso mais simples (1) antes de investir nos casos que o usuário realmente quer (2, 3, 4); deixa o mais sensível (Pessoa) por último, quando o time já confia no mecanismo; só constrói a interface consolidada (5) depois que houver mais de um domínio pra mostrar nela, senão ela fica pela metade.

---

## Notas de implementação (Checkpoints 1-5, 2026-09-19)

Registro do que foi construído de fato e onde desviou um pouco do desenho original acima — pra quem for mexer depois não precisar arqueologia de código.

**Arquivos por checkpoint** (todos seguem o mesmo molde: `*_mestre_models.py`, `*_mestre_service.py` com `sugerir_*`/`vincular_*`/`desvincular_*`, rotas próprias, registrado em `db/base.py` e `main_routers.py`):
- Checkpoint 1: `especie_raca_mestre_models.py`, `especie_raca_mestre_service.py`, rotas dentro de `cadastros_routes.py`. Migration `zzy20260918a1`.
- Checkpoint 2: `produto_mestre_models.py` (+ `CategoriaMestre`/`MarcaMestre`/`DepartamentoMestre` no mesmo arquivo), `produto_mestre_service.py`, `produto_mestre_routes.py`. Migration `zzz20260918a1`.
- Checkpoint 3: `pet_mestre_models.py`, `pet_mestre_service.py`, `pet_mestre_routes.py`. Migration `zzza20260918a1`.
- Checkpoint 4: `pessoa_mestre_models.py`, `pessoa_mestre_service.py`, `pessoa_mestre_routes.py`. Migration `zzzb20260918a1`.
- Helper compartilhado por todos: `grupo_comercial_contexto.py` (`obter_grupo_id_ativo`) — resolve o grupo comercial ativo de um tenant, criado no Checkpoint 1 e reaproveitado sem alteração nos outros três.

**Desvios do desenho original:**
- **Pet não tem FK real pra Espécie/Raça** — `especie`/`raca` no `Pet` local sempre foram texto livre, não `ForeignKey`. A frase original do plano ("vínculo Espécie/Raça do pet aponta pro mestre do Checkpoint 1") não foi implementada por isso; `pet_mestre.especie`/`raca` também guardam texto livre, copiado do pet local no momento do vínculo.
- **Sugestão por identificador forte, não só nome**: Produto prioriza GTIN, Pet prioriza microchip, Pessoa só sugere por CPF/CNPJ (nunca por nome) — mais rígido que o texto original do plano, decisão tomada durante a implementação porque nome sozinho é fraco demais pra dado sensível ou pra evitar falso-positivo.
- **Categoria/Marca/Departamento mestre** ganharam vínculo (`sugerir_*`/`vincular_*`/`desvincular_*`) e rotas próprias em `/produto-mestre/{categorias,marcas,departamentos}/...`, além do `produto_mestre` — não estava explícito no escopo original mas é o mesmo padrão, feito junto por consistência.
- **Checkpoint 5 saiu mais enxuto que o critério de pronto pedia**: a tela (`GrupoComercialMestres.jsx`, em `/configuracoes/grupos-comerciais/:grupoId/mestres`) resolve o "ver" por completo (lista os 5 domínios com contagem). O "gerenciar" ficou parcial — os endpoints de desvincular existem e funcionam (`DELETE .../vincular-mestre`, `DELETE .../vincular` em cada domínio), mas a UI de vincular/desvincular um registro específico não foi conectada aos formulários de cadastro de Produto/Pet/Cliente/Espécie (que não foram tocados nesta rodada). Ou seja: **hoje só dá pra vincular/desvincular via API** — falta o botão nos formulários existentes. Isso é a pendência real do Checkpoint 5, não risco técnico, só trabalho de UI que ficou de fora do escopo desta rodada.

**Verificação feita:** `py_compile` em todos os arquivos, metadata do SQLAlchemy conferida (156→164 tabelas ao longo dos 4 checkpoints), as 3 migrations aplicadas de verdade via `alembic upgrade head` contra o Postgres do `petshop-dev-postgres`, boot limpo do container confirmado a cada rodada, todas as 17 rotas novas conferidas no `/openapi.json` ao vivo, e um teste funcional real (criar → sugerir → vincular → confirmar FK → limpar) rodado contra o banco real pra cada um dos 4 domínios, com limpeza confirmada depois (sem lixo deixado no banco de dev). **Sem teste `pytest` automatizado formal** — mesma pendência do Checkpoint 0, ainda em aberto.
